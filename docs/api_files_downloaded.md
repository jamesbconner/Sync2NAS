### API: List Downloaded Files

Endpoint
- GET `/api/files/downloaded`

Purpose
- Return files tracked by the `downloaded_files` table, supporting filtering and pagination.
- Defaults to `status=downloaded` when no status is provided.

Query parameters
- `status` (string, optional): Filter by processing status. One of:
  - `downloaded`, `processing`, `routed`, `error`, `deleted`
- `file_type` (string, optional): Filter by detected file type. One of:
  - `video`, `audio`, `subtitle`, `nfo`, `image`, `archive`, `unknown`
- `q` (string, optional): Free text search across `name`, `remote_path`, and `current_path`.
- `tmdb_id` (integer, optional): Filter by associated TMDB show id.
- `page` (integer, optional, default 1): Page number (1-based). Minimum 1.
- `page_size` (integer, optional, default 50): Page size (1–200).
- `sort_by` (string, optional, default `modified_time`): Sort column. Allowed:
  - `modified_time`, `fetched_at`, `name`, `size`
- `sort_order` (string, optional, default `desc`): `asc` or `desc`.

Response
- 200 OK
  - `success` (bool)
  - `count` (int): Total number of items matching the filters (not just the current page size)
  - `files` (array of objects): Each file has:
    - `id` (int | null)
    - `name` (string)
    - `remote_path` (string)
    - `previous_path` (string | null)
    - `current_path` (string | null)
    - `size` (int)
    - `modified_time` (ISO string | null)
    - `fetched_at` (ISO string | null)
    - `is_dir` (bool)
    - `status` (string)
    - `file_type` (string)
    - `file_hash_value` (string | null)

Examples (curl)

- Default (downloaded only, first page):
  ```bash
  curl -s "http://localhost:8000/api/files/downloaded"
  ```

- Filter by status (routed) and paginate (page 2, 25 per page):
  ```bash
  curl -s "http://localhost:8000/api/files/downloaded?status=routed&page=2&page_size=25"
  ```

- Search by substring in name/paths with sorting (name asc):
  ```bash
  curl -s "http://localhost:8000/api/files/downloaded?q=.mkv&sort_by=name&sort_order=asc"
  ```

- Filter by file_type (subtitle) and tmdb_id:
  ```bash
  curl -s "http://localhost:8000/api/files/downloaded?file_type=subtitle&tmdb_id=12345"
  ```

Notes
- The endpoint selects the appropriate backend repository (SQLite or Postgres) automatically.
- Hash values (CRC32) are computed during download and exposed via `file_hash_value`. Routing is not gated by hash yet (future feature).

### API: Get Downloaded File Detail

Endpoint
- GET `/api/files/downloaded/{id}`

Response
- 200 OK: A single DownloadedFile object (same shape as list items)
- 404 Not Found

### API: Update Downloaded File Status

Endpoint
- PATCH `/api/files/downloaded/{id}`

Body
- `status` (string, required): one of `downloaded`, `processing`, `routed`, `error`, `deleted`
- `error_message` (string, optional)

Responses
- 200 OK: `{ success: true, id, status, error_message }`
- 422 Unprocessable Entity for invalid status
- 404 Not Found if record missing

### API: Rehash Downloaded File

Endpoint
- POST `/api/files/downloaded/{id}/rehash`

Responses
- 200 OK: `{ success: true, id, file_hash_value, file_hash_algo }`
- 404 Not Found if record or on-disk file missing
- 422 Unprocessable Entity if hashing fails or item is a directory

