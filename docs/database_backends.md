# Database Backends Guide

This guide explains the different database backends supported by Sync2NAS and how to configure them.

## Overview

Sync2NAS uses a database factory pattern to support multiple database backends. This allows you to choose the database that best fits your needs and scale.

## Supported Backends

### SQLite (Recommended)

SQLite is the default and recommended database for most users. It's lightweight, requires no server setup, and stores all data in a single file.

#### Advantages
- **Simple Setup**: No server installation required
- **Portable**: Single file contains all data
- **Reliable**: ACID compliant with excellent data integrity
- **Fast**: Excellent performance for typical workloads
- **Zero Configuration**: Works out of the box

#### Configuration
```ini
[Database]
type = sqlite

[SQLite]
db_file = ./database/sync2nas.db
```

#### File Structure 
database/
└── sync2nas.db # SQLite database file
├── tv_shows # Show information
├── episodes # Episode information
├── downloaded_files # Downloaded file tracking
├── sftp_temp_files # SFTP file listings
└── anime_tv_inventory # Local file inventory
├── downloaded_files # Downloaded file tracking
├── sftp_temp_files # SFTP file listings
└── anime_tv_inventory # Local file inventory

#### Design Patterns
- **Command Pattern**: Each command is a separate module
- **Dependency Injection**: Services injected via context object
- **Factory Pattern**: Dynamic command discovery

#### Example Command Structure
```python
@click.command("add-show")
@click.argument("show_name", required=False)
@click.option("--tmdb-id", type=int, help="TMDB ID")
@click.pass_context
def add_show(ctx, show_name, tmdb_id):
    """Add a show to the database."""
    db = ctx.obj["db"]
    tmdb = ctx.obj["tmdb"]
    # Command implementation
```

### 2. API Layer (`api/`)

The API layer provides REST endpoints for programmatic access.

#### Structure
```
api/
├── main.py              # FastAPI application
├── dependencies.py      # Dependency injection
├── models/              # Request/response models
│   ├── requests.py      # Request schemas
│   └── responses.py     # Response schemas
├── routes/              # API endpoints
│   ├── shows.py         # Show management
│   ├── files.py         # File operations
│   ├── remote.py        # SFTP operations
│   └── admin.py         # Admin operations
└── services/            # API-specific services
    ├── show_service.py  # Show business logic
    ├── file_service.py  # File business logic
    └── admin_service.py # Admin operations
```

#### Design Patterns
- **REST API**: Standard REST endpoints
- **Dependency Injection**: Services injected via FastAPI dependencies
- **Pydantic Models**: Request/response validation
- **Service Layer**: Business logic separation

#### Example API Structure
```python
@router.post("/shows/", response_model=AddShowResponse)
async def add_show(
    request: AddShowRequest,
    show_service: ShowService = Depends(get_show_service)
):
    """Add a new show."""
    return await show_service.add_show(
        show_name=request.show_name,
        tmdb_id=request.tmdb_id
    )
```

### 3. Service Layer (`services/`)

The service layer contains core business logic and external integrations.

#### Structure
```
services/
├── db_factory.py        # Database factory
├── tmdb_service.py      # TMDB API integration
├── sftp_service.py      # SFTP operations
├── llm_service.py       # OpenAI integration
└── db_implementations/  # Database backends
    ├── db_interface.py  # Abstract interface
    ├── sqlite_implementation.py
    ├── postgres_implementation.py
    └── milvus_implementation.py
```

#### Design Patterns
- **Factory Pattern**: Database backend selection
- **Strategy Pattern**: Different database implementations
- **Adapter Pattern**: External API integrations
- **Service Pattern**: Business logic encapsulation

#### Example Service Structure
```python
class TMDBService:
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def search_show(self, name: str) -> Dict[str, Any]:
        """Search for shows on TMDB."""
        # Implementation
    
    def get_show_details(self, tmdb_id: int) -> Dict[str, Any]:
        """Get detailed show information."""
        # Implementation
```

### 4. Model Layer (`models/`)

The model layer defines data structures and validation.

#### Structure
```
models/
├── __init__.py
├── show.py              # Show data model
└── episode.py           # Episode data model
```

#### Design Patterns
- **Data Classes**: Clean data representation
- **Validation**: Input/output validation
- **Serialization**: Database/API serialization

#### Example Model Structure
```python
@dataclass
class Show:
    tmdb_id: int
    tmdb_name: str
    sys_name: str
    sys_path: str
    
    @classmethod
    def from_tmdb(cls, details: Dict[str, Any], **kwargs) -> "Show":
        """Create Show from TMDB data."""
        # Implementation
    
    @classmethod
    def from_db_record(cls, record: Dict[str, Any]) -> "Show":
        """Create Show from database record."""
        # Implementation
```

### 5. Utility Layer (`utils/`)

The utility layer provides helper functions and configuration management.

#### Structure
```
utils/
├── sync2nas_config.py   # Configuration management
├── logging_config.py    # Logging setup
├── file_routing.py      # File routing logic
├── episode_updater.py   # Episode update logic
├── show_adder.py        # Show addition logic
├── sftp_orchestrator.py # SFTP orchestration
├── file_filters.py      # File filtering
├── cli_helpers.py       # CLI utilities
└── sftp_orchestrator.py # SFTP operations
```

#### Design Patterns
- **Utility Functions**: Pure functions for specific tasks
- **Configuration Pattern**: Centralized configuration management
- **Orchestration Pattern**: Complex operation coordination

## Design Patterns

### 1. Factory Pattern

Used for database backend selection and service creation.

```python
def create_db_service(config: Dict[str, Any]) -> DatabaseInterface:
    db_type = config["Database"]["type"]
    
    if db_type == "sqlite":
        return SQLiteDBService(config["SQLite"]["db_file"])
    elif db_type == "postgres":
        return PostgresDBService(config["PostgreSQL"])
    elif db_type == "milvus":
        return MilvusDBService(config["Milvus"])
    else:
        raise ValueError(f"Unsupported database type: {db_type}")
```

### 2. Strategy Pattern

Used for different filename parsing strategies (regex vs LLM).

```python
def parse_filename(filename: str, llm_service: Optional[LLMInterface] = None) -> dict:
    if llm_service:
        result = llm_service.parse_filename(filename)
        if result.get("confidence", 0.0) >= 0.7:
            return result
    
    return _regex_parse_filename(filename)
```

### 3. Dependency Injection

Used throughout the application for service injection.

```python
@click.pass_context
def add_show(ctx, show_name, tmdb_id):
    db: DatabaseInterface = ctx.obj["db"]
    tmdb: TMDBService = ctx.obj["tmdb"]
    # Use injected services
```

### 4. Command Pattern

Used for CLI command organization.

```python
@click.command("add-show")
def add_show():
    """Add a show to the database."""
    # Command implementation

# Dynamic registration
sync2nas_cli.add_command(add_show)
```

## Data Flow

### 1. File Download Flow

```
User Command → CLI → SFTP Service → Database → File System
     ↓              ↓              ↓           ↓
download-from-remote → list_remote_files → store_metadata → save_files
```

### 2. File Routing Flow

```
User Command → CLI → File Routing → Database → File System
     ↓              ↓              ↓           ↓
route-files → list_remote_files → store_metadata → save_files
```

## Migration Between Backends

### SQLite to PostgreSQL

1. **Export Data**
   ```bash
   # Backup SQLite database
   python sync2nas.py backup-db
   ```

2. **Update Configuration**
   ```ini
   [Database]
   type = postgres
   
   [PostgreSQL]
   host = localhost
   port = 5432
   database = sync2nas
   user = sync2nas_user
   password = your_password
   ```

3. **Initialize New Database**
   ```bash
   python sync2nas.py init-db
   ```

4. **Import Data** (manual process required)
   - Export data from SQLite
   - Import to PostgreSQL
   - Verify data integrity

### PostgreSQL to SQLite

1. **Export Data**
   ```bash
   # Use PostgreSQL tools to export
   pg_dump sync2nas > sync2nas_backup.sql
   ```

2. **Update Configuration**
   ```ini
   [Database]
   type = sqlite
   
   [SQLite]
   db_file = ./database/sync2nas.db
   ```

3. **Initialize New Database**
   ```bash
   python sync2nas.py init-db
   ```

4. **Import Data** (manual process required)

## Backup and Recovery

### SQLite Backup
```bash
# Automatic backup
python sync2nas.py backup-db

# Manual backup
cp ./database/sync2nas.db ./database/sync2nas_backup_$(date +%Y%m%d).db
```

### PostgreSQL Backup
```bash
# Full backup
pg_dump sync2nas > sync2nas_backup_$(date +%Y%m%d).sql

# Compressed backup
pg_dump sync2nas | gzip > sync2nas_backup_$(date +%Y%m%d).sql.gz
```

### Milvus Backup
```bash
# Milvus backup (requires Milvus tools)
milvus backup --collection tv_shows --backup_path ./backup/
```

## Performance Tuning

### SQLite Optimization
```ini
# Enable WAL mode for better concurrency
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=10000;
PRAGMA temp_store=MEMORY;
```

### PostgreSQL Optimization
```sql
-- Create indexes for better performance
CREATE INDEX idx_tv_shows_tmdb_id ON tv_shows(tmdb_id);
CREATE INDEX idx_episodes_tmdb_id ON episodes(tmdb_id);
CREATE INDEX idx_episodes_absolute ON episodes(absolute_episode);

-- Analyze tables
ANALYZE tv_shows;
ANALYZE episodes;
```

### Milvus Optimization
```python
# Configure collection parameters
collection_params = {
    "dimension": 384,
    "index_file_size": 1024,
    "metric_type": "L2"
}
```

## Troubleshooting

### Common Issues

#### Connection Failures
- **SQLite**: Check file permissions and disk space
- **PostgreSQL**: Verify server is running and credentials are correct
- **Milvus**: Check if Milvus server is accessible

#### Performance Issues
- **SQLite**: Consider migrating to PostgreSQL for large datasets
- **PostgreSQL**: Add indexes and optimize queries
- **Milvus**: Adjust collection parameters and hardware resources

#### Data Corruption
- **SQLite**: Use backup and restore
- **PostgreSQL**: Use pg_dump/pg_restore
- **Milvus**: Use Milvus backup tools

### Monitoring

#### SQLite Monitoring
```bash
# Check database size
ls -lh ./database/sync2nas.db

# Check integrity
sqlite3 ./database/sync2nas.db "PRAGMA integrity_check;"
```

#### PostgreSQL Monitoring
```sql
-- Check table sizes
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables WHERE schemaname = 'public';

-- Check connection count
SELECT count(*) FROM pg_stat_activity;
```

#### Milvus Monitoring
```python
# Check collection statistics
collection = Collection("tv_shows")
print(f"Entity count: {collection.num_entities}")
print(f"Index status: {collection.has_index()}")
```

## Recommendations

### Choose SQLite If:
- You have a small to medium media library (< 10,000 episodes)
- You want simple setup and maintenance
- You don't need concurrent access
- You're just getting started

### Choose PostgreSQL If:
- You have a large media library (> 10,000 episodes)
- You need concurrent access from multiple processes
- You want enterprise-grade reliability
- You plan to scale significantly

### Choose Milvus If:
- You want similarity search and recommendations
- You're experimenting with advanced features
- You have the resources to manage a vector database
- You're building a recommendation system

# Database and LLM Backend Architecture

## Pattern
- Both database and LLM backends use a factory and interface/implementation pattern.
- The backend is selected via config, and the factory instantiates the correct implementation.

## Extensibility
- This pattern makes it easy to add new database or LLM backends in the future.
- To add a new backend, implement the interface, add your class, and update the factory.

## LLM Example
- The LLM system now supports both Ollama and OpenAI using this pattern.
- See `services/llm_factory.py` and `services/llm_implementations/` for details.

