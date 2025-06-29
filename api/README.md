# Sync2NAS API Documentation

## Overview

The Sync2NAS API is a RESTful web service that provides programmatic access to Sync2NAS functionality. It converts the existing CLI commands into HTTP endpoints, allowing for integration with other applications, automation, and web-based management interfaces.

## Architecture

The API is built using **FastAPI** and follows a layered architecture: 

```
┌─────────────────┐
│   FastAPI App   │  ← Main application entry point
├─────────────────┤
│   API Routes    │  ← HTTP endpoint handlers
├─────────────────┤
│  API Services   │  ← Business logic layer
├─────────────────┤
│ Existing Utils  │  ← Reused CLI utilities
├─────────────────┤
│  Core Services  │  ← Database, SFTP, TMDB
└─────────────────┘
```

### Key Components

- **`api/main.py`**: FastAPI application with middleware and route registration
- **`api/dependencies.py`**: Dependency injection for services
- **`api/routes/`**: HTTP endpoint handlers organized by domain
- **`api/services/`**: Business logic layer that wraps existing utilities
- **`api/models/`**: Pydantic models for request/response validation

## Quick Start

### Prerequisites

1. **Python 3.11+** with required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configuration file** at `./config/sync2nas_config.ini` (see main README.md for details)

3. **TMDB API Key** (see main README.md for setup instructions)

### Running the API Server

#### Development Mode
```bash
# From project root
python run_api.py
```

#### Production Mode
```bash
# Using uvicorn directly
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

#### Environment Variables
- `SYNC2NAS_CONFIG`: Path to configuration file (default: `./config/sync2nas_config.ini`)
- `SYNC2NAS_HOST`: Server host (default: `0.0.0.0`)
- `SYNC2NAS_PORT`: Server port (default: `8000`)

### API Documentation

Once running, access the interactive API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Health Check
- **GET** `/health` - Check API service health
- **GET** `/` - Basic API information

### Shows Management (`/api/shows`)

#### Get All Shows
```http
GET /api/shows/
```

#### Get Specific Show
```http
GET /api/shows/{show_id}
```

#### Add New Show
```http
POST /api/shows/
Content-Type: application/json

{
  "show_name": "Breaking Bad",
  "tmdb_id": 1396,
  "override_dir": false
}
```

#### Update Episodes for Show
```http
POST /api/shows/{show_id}/episodes/refresh
Content-Type: application/json

{
  "show_name": "Breaking Bad"
}
```

#### Delete Show
```http
DELETE /api/shows/{show_id}
```

### File Operations (`/api/files`)

#### Route Files from Incoming
```http
POST /api/files/route
Content-Type: application/json

{
  "dry_run": false,
  "auto_add": true
}
```

**Response:**
```json
{
  "success": true,
  "files_routed": 5,
  "files": [
    {
      "original_path": "/incoming/show.s01e01.mkv",
      "routed_path": "/shows/Show/Season 01/show.s01e01.mkv",
      "show_name": "Show",
      "season": "01",
      "episode": "01"
    }
  ],
  "message": "5 file(s) routed successfully"
}
```

#### List Incoming Files
```http
GET /api/files/incoming
```

#### LLM Show Name Parsing

#### Parse Filename Using LLM
```http
POST /api/files/parse-filename
Content-Type: application/json

{
  "filename": "Breaking.Bad.S01E01.1080p.mkv",
  "llm_confidence_threshold": 0.7
}
```

**Response:**
```json
{
  "show_name": "Breaking Bad",
  "season": 1,
  "episode": 1,
  "confidence": 0.95,
  "reasoning": "Clear S01E01 format"
}
```

- `llm_confidence_threshold` is a float (default 0.7) and can be set per request to control the minimum confidence required for the LLM result to be accepted.
- If the LLM's confidence is below the threshold, the API will return a 422 error.

### Remote Operations (`/api/remote`)

#### Download from SFTP
```http
POST /api/remote/download
Content-Type: application/json

{
  "dry_run": false
}
```

#### List Remote Files
```http
POST /api/remote/list
Content-Type: application/json

{
  "path": "/tv",
  "recursive": true,
  "populate_sftp_temp": false,
  "dry_run": false
}
```

#### Check SFTP Connection
```http
GET /api/remote/status
```

### Admin Operations (`/api/admin`)

#### Bootstrap Shows from Directory
```http
POST /api/admin/bootstrap/shows
Content-Type: application/json

{
  "dry_run": false
}
```

#### Bootstrap Episodes
```http
POST /api/admin/bootstrap/episodes
Content-Type: application/json

{
  "dry_run": false
}
```

#### Database Backup
```http
POST /api/admin/backup
```

#### Initialize Database
```http
POST /api/admin/init-db
```

## Postman Configuration

### Import Collection

1. **Download the Postman Collection**:
   ```json
   {
     "info": {
       "name": "Sync2NAS API",
       "description": "API collection for Sync2NAS operations",
       "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
     },
     "variable": [
       {
         "key": "base_url",
         "value": "http://localhost:8000",
         "type": "string"
       }
     ],
     "item": [
       {
         "name": "Health Check",
         "request": {
           "method": "GET",
           "header": [],
           "url": {
             "raw": "{{base_url}}/health",
             "host": ["{{base_url}}"],
             "path": ["health"]
           }
         }
       },
       {
         "name": "Get All Shows",
         "request": {
           "method": "GET",
           "header": [],
           "url": {
             "raw": "{{base_url}}/api/shows/",
             "host": ["{{base_url}}"],
             "path": ["api", "shows", ""]
           }
         }
       },
       {
         "name": "Add Show",
         "request": {
           "method": "POST",
           "header": [
             {
               "key": "Content-Type",
               "value": "application/json"
             }
           ],
           "body": {
             "mode": "raw",
             "raw": "{\n  \"show_name\": \"Breaking Bad\",\n  \"tmdb_id\": 1396,\n  \"override_dir\": false\n}"
           },
           "url": {
             "raw": "{{base_url}}/api/shows/",
             "host": ["{{base_url}}"],
             "path": ["api", "shows", ""]
           }
         }
       },
       {
         "name": "Route Files",
         "request": {
           "method": "POST",
           "header": [
             {
               "key": "Content-Type",
               "value": "application/json"
             }
           ],
           "body": {
             "mode": "raw",
             "raw": "{\n  \"dry_run\": false,\n  \"auto_add\": true\n}"
           },
           "url": {
             "raw": "{{base_url}}/api/files/route",
             "host": ["{{base_url}}"],
             "path": ["api", "files", "route"]
           }
         }
       },
       {
         "name": "Download from Remote",
         "request": {
           "method": "POST",
           "header": [
             {
               "key": "Content-Type",
               "value": "application/json"
             }
           ],
           "body": {
             "mode": "raw",
             "raw": "{\n  \"dry_run\": false\n}"
           },
           "url": {
             "raw": "{{base_url}}/api/remote/download",
             "host": ["{{base_url}}"],
             "path": ["api", "remote", "download"]
           }
         }
       },
       {
         "name": "Delete Show",
         "request": {
           "method": "DELETE",
           "header": [
             {
               "key": "Content-Type",
               "value": "application/json"
             }
           ],
           "url": {
             "raw": "{{base_url}}/api/shows/{{show_id}}",
             "host": ["{{base_url}}"],
             "path": ["api", "shows", "{{show_id}}"]
           }
         }
       }
     ]
   }
   ```

2. **Import into Postman**:
   - Open Postman
   - Click "Import" → "Raw text"
   - Paste the JSON above
   - Click "Import"

### Environment Variables

Create a Postman environment with these variables:

| Variable | Value | Description |
|----------|-------|-------------|
| `base_url` | `http://localhost:8000` | API base URL |
| `show_id` | `1` | Example show ID for testing |

### Testing Workflows

#### Basic Show Management
1. **Health Check** → Verify API is running
2. **Get All Shows** → Check current shows
3. **Add Show** → Add a new show
4. **Get Specific Show** → Verify show was added
5. **Update Episodes** → Refresh episode data

#### File Processing Workflow
1. **Download from Remote** → Get files from SFTP
2. **List Incoming Files** → Check downloaded files
3. **Route Files** → Move files to show directories

#### Fix Mis-identified Show Workflow
1. **Identify the problematic show**: `GET /api/shows/` to find the show with wrong identification
2. **Delete the mis-identified show**: `DELETE /api/shows/{show_id}` to remove it from database
3. **Re-add with correct identification**: `POST /api/shows/` with correct show name or TMDB ID
4. **Verify the fix**: `GET /api/shows/{new_show_id}` to confirm correct data

## Error Handling

### HTTP Status Codes

- **200**: Success
- **400**: Bad Request (validation errors)
- **404**: Not Found (show not found, etc.)
- **409**: Conflict (show already exists)
- **500**: Internal Server Error
- **503**: Service Unavailable (health check failures)

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Error Scenarios

1. **Missing Configuration**: Ensure `sync2nas_config.ini` exists and is valid
2. **TMDB API Issues**: Verify TMDB API key is valid and has quota remaining
3. **SFTP Connection**: Check SFTP server connectivity and credentials
4. **Database Issues**: Ensure database is accessible and properly initialized

## Development

### Code Structure

```
api/
├── __init__.py              # Package initialization
├── main.py                  # FastAPI application
├── dependencies.py          # Dependency injection
├── models/                  # Pydantic models
│   ├── __init__.py
│   ├── requests.py         # Request models
│   └── responses.py        # Response models
├── routes/                  # HTTP endpoints
│   ├── __init__.py
│   ├── shows.py            # Show management
│   ├── files.py            # File operations
│   ├── remote.py           # SFTP operations
│   └── admin.py            # Admin operations
└── services/               # Business logic
    ├── __init__.py
    ├── show_service.py     # Show business logic
    ├── file_service.py     # File business logic
    ├── remote_service.py   # SFTP business logic
    └── admin_service.py    # Admin business logic
```

### Adding New Endpoints

1. **Create Request/Response Models** in `api/models/`
2. **Add Business Logic** in `api/services/`
3. **Create Route Handler** in `api/routes/`
4. **Register Route** in `api/main.py`
5. **Add Tests** in `tests/api/`

### Logging

The API uses structured logging with file and function context:

```python
logger.info(f"api/routes/shows.py::add_show - Successfully added show: {show_name}")
```

Log levels:
- **DEBUG**: Detailed debugging information
- **INFO**: General operational messages
- **WARNING**: Warning conditions
- **ERROR**: Error conditions
- **EXCEPTION**: Exception details with stack traces

## TODOs and Known Issues

### API-Specific TODOs

1. **Health Check Enhancement** (`api/main.py:67`)
   - Extend health check to verify database connectivity
   - Add SFTP connection verification
   - Include service status in health response

2. **Download Count Tracking** (`api/services/remote_service.py:36`)
   - Implement actual file count tracking in download operations
   - Replace placeholder with real download statistics

3. **Database Backup Implementation** (`api/services/admin_service.py:125`)
   - Implement actual database backup functionality
   - Add backup file management and rotation
   - Include backup verification

4. **Database Initialization** (`api/services/admin_service.py:140`)
   - Implement proper database initialization
   - Add schema creation and migration support
   - Include initialization verification

### General TODOs (from main codebase)

The API inherits these TODOs from the main Sync2NAS codebase:

- [ ] Add search functions for shows in the database
- [ ] Add TMDB search functionality
- [ ] Implement show/episode rename handling
- [ ] Add AniDB hash verification for file integrity
- [ ] Implement inventory checking against episodes table
- [ ] Add filename transformation for Jellyfin compatibility
- [ ] Implement duplicate detection and removal
- [ ] Improve special character handling in show names
- [ ] Add IMDB, TVDB, and AniDB API integrations
- [ ] Better handling of specials and OVAs
- [ ] Add genre and language identifiers
- [ ] Implement MCP LLM integration for filename parsing
- [ ] Add vector database support for similarity search
- [ ] Implement semantic search capabilities
- [ ] Add RSS feed integration for notifications

### Performance Considerations

1. **Rate Limiting**: Implement rate limiting for TMDB API calls
2. **Caching**: Add caching for frequently accessed data
3. **Async Operations**: Ensure all I/O operations are properly async
4. **Connection Pooling**: Implement connection pooling for database and SFTP
5. **Background Tasks**: Use FastAPI background tasks for long-running operations

### Security Considerations

1. **Authentication**: Add API key or JWT authentication
2. **Authorization**: Implement role-based access control
3. **Input Validation**: Ensure all inputs are properly validated
4. **CORS Configuration**: Configure CORS appropriately for production
5. **HTTPS**: Use HTTPS in production environments

## Contributing

When contributing to the API:

1. **Follow existing patterns** for logging, error handling, and documentation
2. **Add comprehensive tests** for new endpoints
3. **Update this README** with new endpoint documentation
4. **Use type hints** throughout the codebase
5. **Follow FastAPI best practices** for endpoint design

## Support

For issues and questions:

1. Check the main Sync2NAS README.md for general information
2. Review the interactive API documentation at `/docs`
3. Check the logs for detailed error information
4. Verify configuration file settings
5. Test individual components (database, SFTP, TMDB) separately 