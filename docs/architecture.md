# Sync2NAS Architecture

This document provides an overview of the Sync2NAS system architecture, components, and design patterns.

## System Overview

Sync2NAS is built using a modular, service-oriented architecture that separates concerns and enables easy testing and extension.

## Architecture Diagram 
┌─────────────────────────────────────────────────────────────┐
│ Sync2NAS System                                             │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐             │
│ │ CLI │ │ API │ │ Utils       │ │             |             |
│ │ Commands    │ │ Endpoints   │ │ Functions   │             │
│ └─────────────┘ └─────────────┘ └─────────────┘             │
├─────────────────────────────────────────────────────────────┤
│ Service Layer                                               │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐             │
│ │ SFTP        │ │ TMDB        │ │ LLM         │             │
│ │ Service     │ │ Service     │ │ Service     │             │
│ └─────────────┘ └─────────────┘ └─────────────┘             │
├─────────────────────────────────────────────────────────────┤
│ Database Layer │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐             │
│ │ SQLite      │ │ PostgreSQL  │ │ Milvus      │             │
│ │ Backend     │ │ Backend     │ │ Backend     │             │
│ └─────────────┘ └─────────────┘ └─────────────┘             │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. CLI Layer (`cli/`)

The CLI layer provides command-line interface for all Sync2NAS functionality.

#### Structure
```
cli/
├── main.py              # Main CLI entry point
├── add_show.py          # Show addition commands
├── route_files.py       # File routing commands
├── search_show.py       # Database search commands
├── search_tmdb.py       # TMDB search commands
├── download_from_remote.py # SFTP download commands
├── list_remote.py       # Remote file listing
├── fix_show.py          # Show correction commands
├── bootstrap_*.py       # Bootstrap operations
└── backup_db.py         # Database backup
```

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
def parse_filename(filename: str, llm_service: Optional[LLMService] = None) -> dict:
    if llm_service:
        try:
            result = llm_service.parse_filename(filename)
            if result.get("confidence", 0.0) >= 0.7:
                return result
        except Exception:
            pass
    
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

cli/
├── main.py # Main CLI entry point
├── add_show.py # Show addition commands
├── route_files.py # File routing commands
├── search_show.py # Database search commands
├── search_tmdb.py # TMDB search commands
├── download_from_remote.py # SFTP download commands
├── list_remote.py # Remote file listing
├── fix_show.py # Show correction commands
├── bootstrap_.py # Bootstrap operations
└── backup_db.py # Database backup

api/
├── main.py # FastAPI application
├── dependencies.py # Dependency injection
├── models/ # Request/response models
│ ├── requests.py # Request schemas
│ └── responses.py # Response schemas
├── routes/ # API endpoints
│ ├── shows.py # Show management
│ ├── files.py # File operations
│ ├── remote.py # SFTP operations
│ └── admin.py # Admin operations
└── services/ # API-specific services
├── show_service.py # Show business logic
├── file_service.py # File business logic
└── admin_service.py # Admin operations

services/
├── db_factory.py # Database factory
├── tmdb_service.py # TMDB API integration
├── sftp_service.py # SFTP operations
├── llm_service.py # OpenAI integration
└── db_implementations/ # Database backends
├── db_interface.py # Abstract interface
├── sqlite_implementation.py
├── postgres_implementation.py
└── milvus_implementation.py



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

models/
├── init.py
├── show.py # Show data model
└── episode.py # Episode data model

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

utils/
├── sync2nas_config.py # Configuration management
├── logging_config.py # Logging setup
├── file_routing.py # File routing logic
├── episode_updater.py # Episode update logic
├── show_adder.py # Show addition logic
├── sftp_orchestrator.py # SFTP orchestration
├── file_filters.py # File filtering
├── cli_helpers.py # CLI utilities
└── sftp_orchestrator.py # SFTP operations

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
def parse_filename(filename: str, llm_service: Optional[LLMService] = None) -> dict:
    if llm_service:
        try:
            result = llm_service.parse_filename(filename)
            if result.get("confidence", 0.0) >= 0.7:
                return result
        except Exception:
            pass
    
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
User Command → CLI → SFTP Service → Database → File System
↓ ↓ ↓ ↓
download-from-remote → list_remote_files → store_metadata → save_files