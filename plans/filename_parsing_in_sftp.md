# Plan: Integrate filename parsing into SFTP download flow

## Goal
Populate `show_name`, `season`, `episode`, `confidence`, and `reasoning` on `downloaded_files` during the SFTP download process by parsing filenames. Make the LLM usage and confidence threshold configurable, and expose CLI flags to enable/disable parsing and LLM.

## Scope of changes
- Wire filename parsing in `utils/sftp_orchestrator.py` within `process_sftp_diffs` after each file download and before DB upsert.
- Add parameters to orchestrator functions to control parsing behavior:
  - `parse_filenames: bool = True` (default on)
  - `use_llm: bool = True` (default on)
  - `llm_confidence_threshold: float = 0.7`
- Use `utils.filename_parser.parse_filename` with `llm_service` only when `use_llm` is True; otherwise force regex fallback.
- Update `cli/download_from_remote.py` to add flags:
  - `--parse/--no-parse` (default `--parse`)
  - `--llm/--no-llm` (default `--llm`)
  - `--llm-threshold FLOAT` (default `0.7`)
- No directory-name parsing (only files). No DB schema changes required; existing upsert already persists these fields.

## Detailed implementation steps

1) `utils/sftp_orchestrator.py`
- Imports:
  - Add `from utils.filename_parser import parse_filename`.
- Function signatures:
  - Update `process_sftp_diffs(..., llm_service=None, max_workers: int = 4, hashing_service: Optional[HashingService] = None)` to also accept:
    - `parse_filenames: bool = True`
    - `use_llm: bool = True`
    - `llm_confidence_threshold: float = 0.7`
  - Update `download_from_remote(...)` to accept the same three arguments and pass them through to `process_sftp_diffs`.
- Within `process_sftp_diffs` (file branch, after constructing `file_model` and before `upsert_downloaded_file`):
  - Determine effective `active_llm_service = llm_service or getattr(sftp_service, "llm_service", None)`.
  - If `parse_filenames` is True and `entry["is_dir"]` is False:
    - Call `metadata = parse_filename(file_model.name, llm_service=active_llm_service if use_llm else None, llm_confidence_threshold=llm_confidence_threshold)`.
    - Set `file_model.show_name`, `season`, `episode`, `confidence`, and `reasoning` from `metadata`.
  - Optional log at INFO level summarizing the parse result.
- Keep CRC32 hashing as-is. Parsing is independent of hashing.

2) `cli/download_from_remote.py`
- Add Click options:
  - `@click.option("--parse/--no-parse", default=True, show_default=True, help="Enable filename parsing to populate show/season/episode")`
  - `@click.option("--llm/--no-llm", default=True, show_default=True, help="Use configured LLM for parsing; disable for regex fallback")`
  - `@click.option("--llm-threshold", type=float, default=0.7, show_default=True, help="Minimum LLM confidence to accept parse result")`
- Plumb these through to the orchestrator call:
  - Pass `parse_filenames=parse`, `use_llm=llm`, and `llm_confidence_threshold=llm_threshold` into `downloader(...)`.
- Maintain existing behavior for `--dry-run` and hashing service.

3) Behavior notes
- If parsing fails or returns empty `show_name`, fields remain `None` (DB upsert tolerates this).
- `use_llm=False` will still parse via regex; `parse_filenames=False` skips parsing entirely.
- Threading: parsing occurs after file download in the thread pool. LLM calls may be concurrent; if the backing LLM client is not thread-safe, we can serialize later, but default is to proceed.

4) Acceptance criteria
- When `--parse` (default) and `--llm` (default) are active:
  - Downloaded files have `show_name/season/episode/confidence/reasoning` populated when parse succeeds.
- When `--no-parse` is used:
  - No parsing occurs; fields remain `NULL`/`None`.
- When `--parse --no-llm` is used:
  - Regex fallback is used; fields populate for recognizable patterns.
- `llm_confidence_threshold` honored: LLM results below threshold fallback to regex; above threshold accepted.

5) Files touched
- `utils/sftp_orchestrator.py` (signature + parsing integration)
- `cli/download_from_remote.py` (new flags and plumbing)

6) Out of scope
- Parsing directory names.
- Changes to DB schema or `DownloadedFile` model (already supports fields).
- API endpoints and docs updates (can be handled separately).

7) Rollout
- Implement orchestrator and CLI changes.
- Run existing tests; add targeted unit tests for parsing enable/disable and LLM toggle in a follow-up if needed.
