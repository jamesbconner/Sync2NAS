# Sync2NAS - TV Show Management and File Synchronization Tool
![Service Test Coverage](https://img.shields.io/badge/Service%20Test%20Coverage-100%25-success?style=flat-square&logo=pytest&logoColor=white)

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Quick Start](#quick-start)
- [Documentation](#documentation)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Usage Examples](#usage-examples)
- [Development](#development)
- [Contributing](#contributing)

## Overview

Sync2NAS is a comprehensive Python tool for managing TV shows, synchronizing files via SFTP, and providing both CLI and API interfaces for show management. It integrates with TMDB for metadata enrichment and supports multiple database backends (SQLite, PostgreSQL, Milvus).

### What Sync2NAS Does

- **File Synchronization**: Downloads files from SFTP servers to your NAS
- **Intelligent File Routing**: Routes media files to organized show directories
- **Metadata Management**: Integrates with TMDB for show and episode information
- **Database Management**: Supports multiple database backends with a factory pattern
- **AI-Powered Parsing**: Uses OpenAI GPT and Ollama models for intelligent filename parsing
- **Dual Interface**: Provides both CLI commands and REST API endpoints

## Features

### Core Functionality
- **SFTP Integration**: Secure file transfer with SSH key authentication
- **Database Factory**: Easily switch between SQLite, PostgreSQL, and Milvus backends
- **TMDB Integration**: Automatic show and episode metadata enrichment
- **File Routing**: Intelligent routing of media files to organized directories
- **Bootstrap Operations**: Easy migration of existing media libraries

### Advanced Features
- **AI-Powered Filename Parsing**: Uses modular LLM backends (Ollama or OpenAI) for accurate show name extraction, configurable via the config file
- **Confidence Scoring**: LLM provides confidence levels for parsing decisions
- **Fallback Support**: Automatic fallback to regex if LLM fails
- **Search Capabilities**: Search local database and TMDB for shows
- **Show Management**: Add, fix, and manage show metadata

### Technical Features
- **REST API**: Full API for programmatic access to all functionality
- **Configurable Logging**: Verbose logging with file output support
- **Dry Run Mode**: Test operations without making changes
- **Comprehensive Testing**: Extensive test coverage with service contracts
- **Plugin Architecture**: Extensible design for future enhancements

## Quick Start

### Prerequisites
- Python 3.12 or higher
- SFTP server access
- TMDB API key (optional but recommended)
- OpenAI API key (optional, for AI-powered parsing)
- Ollama service running your preferred model (default llama3.2)
**Note:** Sync2NAS does not manage Ollama models. You must ensure that any model specified here (e.g., `llama3.2`) is already installed and available in your local Ollama instance. Use `ollama pull <model>` to install models as needed.


### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/sync2nas.git
   cd sync2nas
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create configuration file**
   ```bash
   cp config/sync2nas_config.ini.example config/sync2nas_config.ini
   # Edit config/sync2nas_config.ini with your settings
   ```

4. **Test installation**
   ```bash
   python sync2nas.py --help
   ```

### Basic Setup

1. **Configure your settings** in `config/sync2nas_config.ini`
2. **Bootstrap existing media** (if any):
   ```bash
   python sync2nas.py bootstrap-tv-shows
   python sync2nas.py bootstrap-episodes
   ```
3. **Download and route files**:
   ```bash
   python sync2nas.py download-from-remote
   python sync2nas.py route-files --auto-add
   ```

## Documentation

### User Documentation
- **[CLI Commands](docs/cli_commands.md)**: Complete guide to all CLI commands
- **[Configuration Guide](docs/configuration.md)**: Detailed configuration options
- **[File Routing](docs/file_routing.md)**: Understanding file routing and AI parsing
- **[Database Backends](docs/database_backends.md)**: Database setup and management

### Developer Documentation
- **[API Documentation](#api-documentation)**: REST API reference and examples
- **[Architecture](docs/architecture.md)**: System design and component overview
- **[Testing](docs/testing.md)**: Testing philosophy and coverage matrix
- **[Contributing](docs/contributing.md)**: Development setup and guidelines

### Service Testing Documentation
- **[SFTP Service](docs/SFTP_Test_Philosophy.md)**: SFTP integration details
- **[Database Service](docs/Database_Test_Philosophy.md)**: Database backend details
- **[TMDB Service](docs/TMDB_Test_Philosophy.md)**: TMDB API integration
- **[Services Test Coverage](docs/Services_Test_Coverage_Matrix.md)**: Test coverage matrix

## Configuration

### Required Configuration

Create `config/sync2nas_config.ini` with the following sections:

#### SFTP Settings
```ini
[SFTP]
host = your.sftpserver.com
port = 22
username = your_username
ssh_key_path = ./ssh/your_sftpserver_rsa
paths = /path/to/remote/files/
```

#### Database Settings
```ini
[Database]
type = sqlite  # sqlite, postgres, or milvus

[SQLite]
db_file = ./database/sync2nas.db
```

#### Transfer Settings
```ini
[Transfers]
incoming = ./incoming

[Routing]
anime_tv_path = d:/anime_tv/
```

### Optional Configuration

#### TMDB Integration
```ini
[TMDB]
api_key = your_tmdb_api_key_here
```

#### LLM Backend Selection
```ini
[llm]
service = ollama  # ollama or openai
```

#### Ollama LLM Backend
```ini
[ollama]
model = llama3.2
llm_confidence_threshold = 0.7
```

#### OpenAI LLM Backend
```ini
[openai]
api_key = your_openai_api_key_here
model = gpt-3.5-turbo
max_tokens = 150
temperature = 0.1
llm_confidence_threshold = 0.7
```

### Complete Configuration Example
```ini
[SFTP]
host = your.sftpserver.com
port = 22
username = your_username
ssh_key_path = ./ssh/your_sftpserver_rsa
paths = /path/to/remote/files/,/another/remote/path/

[Database]
type = sqlite

[SQLite]
db_file = ./database/sync2nas.db

[Transfers]
incoming = ./incoming

[TMDB]
api_key = your_tmdb_api_key_here

[llm]
service = ollama  # or openai

[ollama]
model = llama3
llm_confidence_threshold = 0.7

[openai]
api_key = your_openai_api_key_here
model = gpt-3.5-turbo
max_tokens = 150
temperature = 0.1
llm_confidence_threshold = 0.7

[Routing]
anime_tv_path = d:/anime_tv/
```

## API Documentation

Sync2NAS provides a comprehensive REST API for programmatic access to all functionality.

### API Overview
- **Base URL**: `http://localhost:8000`
- **Documentation**: Interactive API docs at `http://localhost:8000/docs`
- **Alternative Docs**: ReDoc at `http://localhost:8000/redoc`

### Quick API Start
```bash
# Start the API server
python run_api.py

# Or use the CLI
python sync2nas.py api-start
```

### API Features
- **Show Management**: Add, search, update, and delete shows
- **File Operations**: Route files, list remote files, download from SFTP
- **Episode Management**: Update episode information from TMDB
- **Admin Operations**: Database backup, initialization, bootstrap operations

### Detailed API Documentation
For complete API documentation, including:
- All available endpoints
- Request/response schemas
- Authentication details
- Usage examples
- Postman collection

**See: [API Documentation](api/README.md)**

## Usage Examples

### File Management

#### Download Files from SFTP
```bash
# Download new files with debug logging
python sync2nas.py -vv download-from-remote

# List files on remote server
python sync2nas.py list-remote
```

#### Route Files to Media Library
```bash
# Standard routing with regex parsing
python sync2nas.py route-files --auto-add

# Enhanced routing with AI-powered LLM parsing
python sync2nas.py route-files --auto-add --use-llm
# The LLM backend (Ollama or OpenAI) is selected via the config file

# Dry run to see what would happen
python sync2nas.py route-files --dry-run
```

### Show Management

#### Add New Shows
```bash
# Add show by name (interactive search)
python sync2nas.py add-show "Breaking Bad"

# Add show by TMDB ID
python sync2nas.py add-show --tmdb-id 1396

# Override directory name
python sync2nas.py add-show "Show Name" --override-dir
```

#### Search for Shows
```bash
# Search local database
python sync2nas.py search-show "Breaking Bad"
python sync2nas.py search-show --tmdb-id 1396

# Search TMDB directly
python sync2nas.py search-tmdb "One Piece"
python sync2nas.py search-tmdb --tmdb-id 37854
```

#### Fix Misclassified Shows
```bash
# Interactive fix with TMDB search
python sync2nas.py fix-show "Show Name"

# Fix with specific TMDB ID
python sync2nas.py fix-show "Show Name" --tmdb-id 123456
```

### Database Operations

#### Bootstrap Operations
```bash
# Bootstrap existing SFTP downloads
python sync2nas.py bootstrap-downloads

# Bootstrap existing media library
python sync2nas.py bootstrap-tv-shows

# Bootstrap episode information
python sync2nas.py bootstrap-episodes
```

#### Database Maintenance
```bash
# Backup database
python sync2nas.py backup-db

# Initialize database
python sync2nas.py init-db
```

### Advanced Features

#### AI-Powered Parsing
```bash
# Route files with LLM parsing
python sync2nas.py route-files --use-llm

# Custom confidence threshold (overrides config value)
python sync2nas.py route-files --use-llm --llm-confidence 0.8
# The backend (Ollama or OpenAI) is selected via the [llm] config section
```

#### Verbose Output and Debugging
```bash
# INFO level logging
python sync2nas.py -v route-files

# DEBUG level logging
python sync2nas.py -vv route-files

# Log to file
python sync2nas.py -v --logfile sync2nas.log route-files
```

## Migration Notes

If you are upgrading from a previous version:
- The `[llm]` section is required to select the LLM backend (`ollama` or `openai`).
- The `[openAI]` section is now optional and only used if `[llm] service = openai`.
- The `[ollama]` section is required if using Ollama.
- All LLM configuration is now modular and extensible; see [docs/configuration.md](docs/configuration.md) for details.
- Deprecated references to `llm_service.py` and `LLMService` have been removed; see migration notes in the documentation if you have custom integrations.

## Development

### Project Structure

```text
sync2nas/
├── cli/         # CLI command implementations
├── api/         # REST API implementation
├── services/    # Core service objects
├── models/      # Data models
├── utils/       # Utility functions
├── tests/       # Test suite
├── config/      # Configuration files
└── docs/        # Documentation
```
### API and CLI Architecture Diagram

```text
                ┌─────────────────────────────┐
                │        Sync2NAS App         │
                └─────────────┬───────────────┘
                              │
        ┌─────────────────────┼────────────────────┐
        │                                          │
┌───────▼───────┐                         ┌────────▼────────┐
│     CLI       │                         │      API        │
│ (sync2nas.py) │                         │ (FastAPI app)   │
└───────┬───────┘                         └────────┬────────┘
        │                                          │
        │                                          │
┌───────▼────────┐                       ┌─────────▼─────────┐
│ CLI Commands   │                       │     API Routes    │
│ (cli/*.py)     │                       │ (api/routes/*.py) │
└───────┬────────┘                       └─────────┬─────────┘
        │                                          │
        └─────────────────────┬────────────────────┘
                              │
              ┌───────────────▼──────────────┐
              │         Core Services        │
              │ (services/, utils/, models/) │
              └──────────────────────────────┘
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=sync2nas

# Run specific test categories
pytest tests/services/
pytest tests/cli/
```

### Development Setup
```bash
# Install in development mode
pip install -e .

# Install development dependencies
pip install -r requirements-dev.txt

# Run linting
flake8 sync2nas/
black sync2nas/
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](docs/contributing.md) for details.

### Getting Started
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Development Guidelines
- Follow the existing code style
- Add comprehensive tests
- Update documentation
- Use meaningful commit messages

### Reporting Issues
- Use the GitHub issue tracker
- Include detailed reproduction steps
- Provide relevant configuration and logs

---

**Need Help?**
- Check the [documentation](docs/)
- Review [API documentation](api/README.md)
- Open an [issue](https://github.com/yourusername/sync2nas/issues)
- Join our [discussions](https://github.com/yourusername/sync2nas/discussions)