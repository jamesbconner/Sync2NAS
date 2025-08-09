### DownloadedFile implementation plan

This plan defines the new `DownloadedFile` model and its integration across the system. It incorporates the following constraints:

- Keep `sftp_temp_*` logic unchanged.
- Manual DB migration only; old tables may be dropped outside of code changes.
- Use upsert keyed by `remote_path` to keep the current location accurate.
- Track SCD-style movement with `previous_path` and `current_path`.
- Compute and store CRC32 during download (uppercase), but do not gate routing by hash yet.
- No audit/event table; no `episode_id` FK in this refactor.

---

### Goals

- Establish a cohesive domain model (`DownloadedFile`) that accurately reflects file lifecycle and location.
- Normalize persistence with an explicit repository, moving away from ad-hoc dict persistence.
- Add integrity metadata (CRC32) computed at download time.
- Preserve existing `sftp_temp_*` flows and CLI/API/GUI behavior where not strictly necessary to change.

### Non-goals

- Automated migration tooling. Manual DB setup/teardown will be performed outside the codebase.
- Routing decisions based on hash integrity (future feature).
- Event/audit log and episode foreign keys (future features).

---

### Terminology

- **remote_path**: Path of the file on the source (remote) filesystem.
- **current_path**: The file’s current path on the local filesystem.
- **previous_path**: The immediate prior local path before `current_path` (SCD step tracking).
- **incoming path**: Local landing directory where downloads are placed.

---

### Data model (domain)

`DownloadedFile` (Pydantic v2) with status/type enums and helpers.

- Identity and paths
  - `id: int | None`
  - `name: str`
  - `remote_path: str` (unique key for upsert)
  - `current_path: str | None`
  - `previous_path: str | None`

- File metadata
  - `size: int`
  - `modified_time: datetime`
  - `fetched_at: datetime`
  - `is_dir: bool`
  - `file_type: enum[video,audio,subtitle,nfo,image,archive,unknown]` (derived from `name`)

- Processing and routing
  - `status: enum[downloaded,processing,routed,error,deleted]`
  - `routing_attempts: int`
  - `last_routing_attempt: datetime | None`
  - `error_message: str | None`

- Parsing/association (optional)
  - `show_name: str | None`
  - `season: int | None`
  - `episode: int | None`
  - `confidence: float | None`
  - `reasoning: str | None`
  - `tmdb_id: int | None`

- Integrity metadata
  - `file_hash_value: str | None` (CRC32 hex uppercase)
  - `file_hash_algo: str | None` (default "CRC32")
  - `hash_calculated_at: datetime | None`

- Helpers (no I/O inside the model):
  - `file_type` property (derived)
  - `can_be_routed()`, `mark_as_processing()`, `mark_as_routed(new_path)`, `mark_as_error(msg)`
  - `get_file_path()` -> `current_path or remote_path` (for convenience only)

Notes:
- Remove direct hashing logic from the model; use a service to compute and persist hashes.
- Keep CRC32 uppercase to match user preference.

---

### Database schema (single table)

Table: `downloaded_files`

- `id` INTEGER/BIGSERIAL PRIMARY KEY
- `name` TEXT NOT NULL
- `remote_path` TEXT NOT NULL UNIQUE
- `current_path` TEXT NULL
- `previous_path` TEXT NULL
- `size` BIGINT NOT NULL
- `modified_time` TIMESTAMP NOT NULL
- `fetched_at` TIMESTAMP NOT NULL
- `is_dir` BOOLEAN NOT NULL
- `status` TEXT NOT NULL
- `file_type` TEXT NOT NULL
- `file_hash_value` TEXT NULL
- `file_hash_algo` TEXT NULL
- `hash_calculated_at` TIMESTAMP NULL
- `show_name` TEXT NULL
- `season` INT NULL
- `episode` INT NULL
- `confidence` REAL NULL
- `reasoning` TEXT NULL
- `tmdb_id` INT NULL
- `routing_attempts` INT NOT NULL DEFAULT 0
- `last_routing_attempt` TIMESTAMP NULL
- `error_message` TEXT NULL
- `metadata` JSON/JSONB NULL

Indexes:
- `UNIQUE(remote_path)` (upsert key)
- Optional: `idx_downloaded_files_status`, `idx_downloaded_files_current_path`, `idx_downloaded_files_tmdb_id`

Notes:
- Manual creation and dropping of old tables handled outside of code.

---

### Repository interface

Create `DownloadedFileRepository` to encapsulate DB interactions and mapping.

Core methods:
- `upsert(file: DownloadedFile) -> DownloadedFile` (by `remote_path`)
- `set_hash(id: int, algo: str, value: str, calculated_at: datetime) -> None`
- `update_location(id: int, new_path: str, new_status: str) -> None`
  - Performs SCD step: `previous_path = current_path`, `current_path = new_path`, update `status`, `routing_attempts`, `last_routing_attempt`
- `mark_error(id: int, message: str) -> None`
- Query methods (non-exhaustive):
  - `get_by_status(status: str) -> list[DownloadedFile]`
  - `get_by_remote_path(remote_path: str) -> DownloadedFile | None`
  - `list_ready_to_route() -> list[DownloadedFile]` (currently: `status=downloaded`; no hash gating yet)

Implementations:
- `SQLiteDownloadedFileRepository`
- `PostgresDownloadedFileRepository`

Mapping:
- Provide converters model↔row and strict enum handling.

---

### Hashing utility

Use the existing `utils/hashing.py` module to perform streaming CRC32 computation.

- `calculate_crc32(file_path: str, chunk_size: int = 1_048_576) -> str` returns uppercase 8-char hex
- Errors are surfaced to the caller; routing is not blocked here by policy (download flow decides how to handle failures).
- The utility also supports MD5/SHA1 with the same 1 MiB chunk size reads.

Chunk size:
- Default chunk size: 1 MiB (1,048,576 bytes) for hashing large files efficiently.
- Make chunk size configurable via config/env for future tuning.

---

### SFTP download flow integration

Keep `sftp_temp_*` tables and diffs intact.

For each successfully downloaded file:
1) Determine paths:
   - `remote_path` from listing
   - `incoming_local_path` as the destination
2) Compute CRC32 via `utils.hashing.calculate_crc32` (uppercase).
3) Create/update `DownloadedFile` and upsert by `remote_path`:
   - `name`, `size`, `modified_time`, `fetched_at`, `is_dir`, `file_type`
   - `previous_path = remote_path`
   - `current_path = incoming_local_path`
   - `status = downloaded`
   - `file_hash_value`, `file_hash_algo = "CRC32"`, `hash_calculated_at`
4) On failures (download or hashing): upsert or update the record with `status=error` and `error_message`.

Pseudocode:

```python
for entry in diffs:
    remote_path = entry["path"]
    local_path = make_incoming_path(remote_path)
    download_file(remote_path, local_path)

    try:
        crc = hashing_service.compute_crc32(local_path)
        repo.upsert(DownloadedFile(
            name=entry["name"],
            remote_path=remote_path,
            previous_path=remote_path,
            current_path=local_path,
            size=entry["size"],
            modified_time=entry["modified_time"],
            fetched_at=now(),
            is_dir=entry["is_dir"],
            status="downloaded",
            file_type=derive_file_type(entry["name"]),
            file_hash_value=crc,
            file_hash_algo="CRC32",
            hash_calculated_at=now(),
        ))
    except Exception as e:
        repo.upsert(DownloadedFile(
            name=entry["name"],
            remote_path=remote_path,
            previous_path=None,
            current_path=None,
            size=entry["size"],
            modified_time=entry["modified_time"],
            fetched_at=now(),
            is_dir=entry["is_dir"],
            status="error",
            file_type=derive_file_type(entry["name"]),
            error_message=str(e),
        ))
```

---

### Routing flow integration

Do not gate by hash yet.

On successful route of a file:
- `repo.update_location(id=file.id, new_path=final_path, new_status="routed")`
- This sets `previous_path = old current_path`, updates `current_path`, `status`, `routing_attempts`, `last_routing_attempt`.

On routing failure:
- `repo.mark_error(id, message)`

---

### API/CLI/GUI considerations

- API response objects include: `remote_path`, `previous_path`, `current_path`, `status`, `file_hash_value`.
- CLI outputs (where relevant) may display location and status; no behavioral change needed otherwise.
- GUI can show current status and paths; no new actions required.

---

### Manual migration guidance (informational)

- Create the new `downloaded_files` table as defined above.
- Drop legacy tables when appropriate.
- Optionally bulk-import historical rows; map legacy `path` → `remote_path` and set `current_path` as applicable. Hash values will be recomputed on new downloads only.

---

### Milestones and acceptance criteria

Milestone 1: Domain model and repository
- Implement updated `DownloadedFile` class (rename `original_path` → `remote_path`; add `previous_path`).
- Define and implement repository for SQLite and Postgres (upsert by `remote_path`).
- Tests: model validation, enum serialization, upsert idempotency, SCD location updates.

Milestone 2: Hashing service and download integration
- Implement `HashingService` with streaming CRC32 (uppercase).
- Integrate into download flow after successful writes; persist hash and set `status=downloaded`.
- Keep `sftp_temp_*` code and diffs unchanged.
- Tests: download integration computes/stores CRC; error paths mark `status=error`.

Milestone 3: Routing with SCD updates
- Integrate repository into routing; update `previous_path`/`current_path` and statuses.
- Do not add hash gating.
- Tests: successful and error routing update fields and counters correctly.

Milestone 4: API/CLI exposure
- Extend API serializers to surface `remote_path`, `previous_path`, `current_path`, `status`, `file_hash_value`.
- Update CLI outputs/docs as needed without changing behavior.
- Tests: API contract and minimal CLI smoke.

Milestone 5: Documentation and cleanup
- Update docs on schema, lifecycle, and integrity handling.
- Remove old references to `original_path`.
- Confirm `sftp_temp_*` documentation as remote snapshot source-of-truth.

---

### Risks and mitigations

- Performance of hashing on large files: compute after each download in the same worker; use streaming; consider thread pool size. Mitigation: chunk size tuning and background threads already used by download tasks.
- Path normalization (Windows vs POSIX): enforce consistent storage (use `Path.as_posix()` or clear rules); explicitly test on Windows paths.
- Uniqueness conflicts on `remote_path`: ensure the remote listing provides a stable, canonical path. Validate and sanitize consistently.

---

### Future work (not in scope)

- Routing gate using CRC comparison from filename and/or stored hash.
- Event/audit trail (`downloaded_file_events`).
- Episode linkage (`episode_id` FK) and richer content graph.
- Background hash verification scans.


