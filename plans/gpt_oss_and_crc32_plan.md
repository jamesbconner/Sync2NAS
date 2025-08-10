### Goals

- Add first-class support for Ollama `gpt-oss:20b` by making structured-output usage resilient when the model ignores the `format` parameter.
- Extract CRC32 hashes present in filenames during parsing and persist them as a separate field on `downloaded_files` for future verification features.

---

### Scope

- Ollama LLM integration (`services/llm_implementations/ollama_implementation.py`)
- Filename parsing prompt already updated (`services/llm_implementations/prompts/parse_filename.txt`)
- Data model and DB schema for `downloaded_files` (SQLite and Postgres implementations)
- Orchestration path that parses and upserts downloaded files (`utils/sftp_orchestrator.py`)
- Config toggles for Ollama behavior (optional)
- Tests (services, utils, DB implementations)

---

### Feature 1: Support Ollama gpt-oss:20b (schema-free fallback)

Problem: `gpt-oss` models can ignore or break when `format` (JSON schema) is passed, causing empty output or errors.

Design:
- Parse-filename path will attempt structured outputs when possible, then gracefully fall back if the model returns empty/invalid content.
- Reuse the robust flow proven in `parse_filename_cli.py`: try with schema; if no response or invalid JSON, retry without schema; then extract first JSON object, validate via Pydantic, and return sanitized dict.
- Apply the same fallback in any method that requests structured JSON (e.g., `suggest_show_name`). Methods that produce plain text (`suggest_short_dirname`, `suggest_short_filename`) remain unchanged, but keep their minimal sanitation.

Implementation plan:
- `services/llm_implementations/ollama_implementation.py`
  - `parse_filename(...)`:
    - Build request: `model`, `prompt`, `options`, and only add `format=ParsedFilename.model_json_schema()` when allowed.
    - If response text is empty or not valid JSON after extraction, retry once without `format`.
    - Reuse existing `_extract_first_json_object(...)` and Pydantic validation; keep strong typing and `_validate_and_clean_result(...)`.
    - Keep current prompt formatting; template already escapes braces.
  - `suggest_show_name(...)`:
    - Mirror the same structured-output retry logic: try with schema, on empty/invalid result, retry without schema; then JSON-parse and validate minimal required fields. Fall back to first candidate if still invalid.
  - Optional config (future-proof):
    - Add `ollama.use_schema=true|false` (default true) and automatically force `false` when `model` starts with `gpt-oss`.
    - Respect `ollama.model` from config and allow `gpt-oss:20b`.
  - Logging:
    - INFO: log model, parse attempts, and whether fallback was used.
    - DEBUG: log raw response prior to extraction; avoid logging very large responses.

Testing:
- Add service tests stubbing `Client.generate`:
  - Case A: returns valid JSON with schema → success path.
  - Case B: returns empty with schema, then valid JSON without schema → fallback success.
  - Case C: returns prose-wrapped JSON → extraction succeeds.
  - Case D: invalid JSON even after retry → fallback parser path used.
- Add a targeted test for `gpt-oss:20b` model name that triggers schema-free path automatically.

---

### Feature 2: Extract and persist CRC32 present in filenames

Problem: Filenames often include a CRC32 hash (e.g., `[A4DD1E71]`). We need to capture the provided hash at parse time and persist it separately from the computed file hash.

Design:
- The LLM prompt already returns a `hash` field. We will normalize and store this value in a new DB column `file_provided_hash_value` (separate from computed `file_hash_value`).
- Normalization: strip surrounding brackets if present, trim whitespace, uppercase, ensure exactly 8 hex characters. If invalid, store NULL.

Data model changes:
- `models/downloaded_file.py`
  - Add `file_provided_hash_value: Optional[str]`.
  - Map to/from DB in `from_db_record(...)`, `to_dict(...)`, and any serialization helpers.
  - Do not repurpose `file_hash` (which holds computed hash). Keep both fields independent.

Database schema:
- Add new column to `downloaded_files`:
  - `file_provided_hash_value TEXT NULL` (SQLite)
  - `file_provided_hash_value TEXT NULL` (Postgres)
- Init-time schemas:
  - Update the create-table SQL in both DB implementations so fresh databases include the new column.
- Migration:
  - No automated migration in code. You will handle `ALTER TABLE` manually as needed.

Persistence behavior:
- Upsert:
  - Include `file_provided_hash_value` in the insert column list and params.
  - On conflict update: `file_provided_hash_value = COALESCE(EXCLUDED.file_provided_hash_value, downloaded_files.file_provided_hash_value)` to avoid overriding an existing non-null value with null.

Orchestrator integration:
- `utils/sftp_orchestrator.process_sftp_diffs(...)`:
  - After successful LLM/regex parse and before upsert:
    - If parse result contains `hash`, normalize (strip `[]`, uppercase, length 8, hex-only). If valid, set `file_model.file_provided_hash_value`; else leave as None.
  - Continue computing content CRC32 via `HashingService` when configured, storing into `file_hash`/`file_hash_algo`/`hash_calculated_at` (unchanged behavior).

API/CLI exposure (non-blocking for this change):
- Existing endpoints and CLIs may continue to omit `file_provided_hash_value`. A later enhancement can expose it in responses and UIs.

Testing:
- Unit tests for normalization edge cases:
  - `"[A4DD1E71]"` → `A4DD1E71`
  - `"a4dd1e71"` → `A4DD1E71`
  - invalid length or non-hex → None
- Orchestrator flow test where parse returns a hash and DB upsert persists it.
- DB implementation tests verifying the column exists, insert/upsert behavior, and COALESCE on conflict.

---

### Step-by-step checklist

1) Ollama service
- Add schema-fallback logic to `parse_filename(...)` and `suggest_show_name(...)`.
- Auto-disable `format` when model starts with `gpt-oss` (or `ollama.use_schema=false`).
- Add targeted unit tests.

2) Model and schema
- Add `file_provided_hash_value` to `models/downloaded_file.py` with serialization and mapping updates.
- Update SQLite and Postgres create-table SQL to include the column.
- Update upsert statements and row parameterization to include the new column + COALESCE on conflict.
- No automated migration; ALTER TABLE will be performed manually outside the codebase.

3) Orchestrator
- Extract hash from parse result; normalize; set `file_provided_hash_value` before upsert.
- Add tests covering this path.

4) Docs
- Briefly note the new column and normalization behavior in `docs/database_backends.md` and `docs/Services_Test_Coverage_Matrix.md` (post-implementation).

Future enhancements (API/CLI exposure):
- API: include `file_provided_hash_value` and `file_hash_value` in file detail/list endpoints where appropriate.
- CLI: add flags/columns to show both the filename-provided hash and the computed hash in relevant commands (e.g., list/downloaded-files, verify).

---

### Risks and mitigations
- gpt-oss behavior variance: add robust logging and a schema-free retry to prevent hard failures.
- Back-compat for existing DBs: migration will be handled manually via `ALTER TABLE`; avoid breaking `add_downloaded_files(...)` legacy paths.
- Data correctness: strict normalization ensures consistent stored hash values.

---

### Validation plan
- Run unit tests for services, DB, and orchestrator.
- Manual test: point at local Ollama with `gpt-oss:20b`, parse several filenames that include and omit CRC32; verify database rows contain `file_provided_hash_value` and computed `file_hash_value` independently.
- Manual test: ensure parse still succeeds with `llama3.2` (structured outputs on first try).


