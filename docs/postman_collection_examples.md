### Postman examples: Downloaded Files API

Base URL
- `http://localhost:8000`

Collection items

1) List downloaded (default)
- Method: GET
- URL: `/api/files/downloaded`
- Params: none (defaults to `status=downloaded`, `page=1`, `page_size=50`)

2) List routed files with pagination
- Method: GET
- URL: `/api/files/downloaded`
- Params:
  - `status=routed`
  - `page=1`
  - `page_size=25`

3) Search for mkv files, sort by name ascending
- Method: GET
- URL: `/api/files/downloaded`
- Params:
  - `q=.mkv`
  - `sort_by=name`
  - `sort_order=asc`

4) Filter by file type (subtitle) and tmdb_id
- Method: GET
- URL: `/api/files/downloaded`
- Params:
  - `file_type=subtitle`
  - `tmdb_id=12345`

Response assertions (suggested)
- Status code is 200
- `success` is true
- `count` is a number (>= 0)
- Each `files[i]` contains keys: `name`, `remote_path`, `current_path`, `status`, `file_type`

Postman environment variables (optional)
- `base_url`: `http://localhost:8000`
- Use `{{base_url}}/api/files/downloaded` in request URLs.

5) Get downloaded file by id
- Method: GET
- URL: `/api/files/downloaded/{id}`

6) Update status to processing
- Method: PATCH
- URL: `/api/files/downloaded/{id}`
- Body (json): `{ "status": "processing" }`

7) Rehash a file
- Method: POST
- URL: `/api/files/downloaded/{id}/rehash`

