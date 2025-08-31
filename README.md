# Sync2NAS - TV Show Management and File Synchronization Tool
![Service Test Coverage](https://img.shields.io/badge/Service%20Test%20Coverage-86%25-success?style=flat-square&logo=pytest&logoColor=white)

## What's New (August 2025)

**Comprehensive Windows GUI Interface**
- Sync2NAS now includes a full-featured Windows desktop GUI built with tkinter and ttkbootstrap
- Provides access to all CLI functionality through an intuitive graphical interface
- Features real-time logging, configuration management, and threaded operations
- Includes search functionality for both local database and TMDB API
- Supports temporary configuration overrides without modifying original config files

**Enhanced Testing and Stability**
- Comprehensive GUI test suite with proper Tkinter isolation
- Fixed threading issues and background thread management
- Improved error handling and test coverage
- Robust test fixtures for consistent GUI testing

**Improved User Experience**
- Modern ttkbootstrap styling for a professional appearance
- Tabbed interface organized by functionality (Frequently Executed Operations, Search, Show Management, Database Operations, Configuration, Logs)
- Real-time status updates and operation monitoring
- Unicode support for international character handling

## What's New (July 2025)

**LLM-Powered Show Name Selection**
- When adding a show (via `add-show` or `route-files --auto-add`), Sync2NAS now uses an LLM to automatically select the best TMDB match and English show name—even if your search is in Japanese, Chinese, or another language. No more manual picking or mismatched names!

**Editable LLM Prompts**
- All LLM prompts (for filename parsing, show selection, directory/filename suggestion, etc.) are now stored as plain text files in `services/llm_implementations/prompts/`. You can easily tune or localize LLM behavior by editing these files—no code changes required.

**Windows Path Length Handling**
- Sync2NAS now automatically shortens directory and file names (using LLM or regex fallback) to avoid Windows path length errors. This applies to SFTP downloads and file routing.

**Anthropic LLM Support**
- You can now use Anthropic models (Claude) as your LLM backend, in addition to OpenAI and Ollama. Configure your preferred LLM in the config file.

**Improved Logging and Error Messages**
- All CLI commands and core utilities now include more detailed logging (with file/function context) and clearer error messages for easier troubleshooting.

**Configuration and Breaking Changes**
- If you have custom LLM prompts, move them to the new `services/llm_implementations/prompts/` directory and escape curly braces in JSON examples (use `{{` and `}}`).
- Review your config file for new LLM and path handling options.

---

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
- **Multiple Interfaces**: Provides CLI commands, REST API endpoints, and a GUI for ease of use

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
- **Fallback Support**: Automatic fallback to regex if LLM fails at show name parsing
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
- TMDB API key (Required, but free.  Read the [TMDB FAQ](https://developer.themoviedb.org/docs/faq#how-do-i-apply-for-an-api-key) to learn how to get one.)
- [OpenAI](https://openai.com/api/) API key (Optional, for AI-powered actions like filename parsing and automatic show matching)
- [Anthropic](https://www.anthropic.com/api) API key (Optional, for AI-powered actions like filename parsing and automatic show matching)
- [Ollama](https://ollama.com/) local LLM service running your preferred model (Default [gemma3:12b](https://ollama.com/library/gemma3). It's the best tradeoff between accuracy, compute resource and speed as of July 2025.)
**Note:** Sync2NAS does not manage Ollama models. You must ensure that any model specified here (e.g., `gemma3:12b`) is already installed and available in your local Ollama instance. Use `ollama pull gemma3:12b` to install models as needed.

### GUI Interface

Sync2NAS includes a comprehensive Windows desktop GUI for easy operation:

**Sync2NAS GUI:**
```bash
python sync2nas_gui.py
# or double-click run_gui.bat
```

The GUI provides:
- **Frequently Executed Operations**: Quick access to download and file routing with global configuration
- **Search & Show Management**: Search local database and TMDB API, add and fix shows
- **Database Operations**: Initialize, backup, update episodes, and bootstrap database
- **Configuration Management**: Complete configuration options with temporary override support
- **Real-time Logging**: View live CLI output in the GUI
- **Modern Styling**: ttkbootstrap integration for a modern look and feel

The GUI features:
- **Tabbed Interface**: Organized functionality across multiple tabs
- **Configuration Overrides**: Temporary config files for GUI settings
- **Threaded Operations**: Non-blocking CLI command execution
- **Unicode Support**: Proper handling of special characters and emojis
- **Scrollable Sections**: Mousewheel support for extensive configuration options

See the [GUI Documentation](gui/README.md) for detailed usage instructions and feature descriptions.


### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/jamesbconner/sync2nas.git
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
- **[GUI Interface](gui/README.md)**: Information about the GUI abilities
- **[Configuration Guide](docs/configuration.md)**: Detailed configuration options
- **[Environment Variables](docs/environment_variables.md)**: Complete environment variable reference
- **[Configuration Troubleshooting](docs/configuration_troubleshooting.md)**: Troubleshooting guide for configuration issues
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

#### TMDB Integration
```ini
[TMDB]
api_key = your_tmdb_api_key_here
```

### Optional Configuration
#### LLM Backend Selection
```ini
[llm]
service = ollama  # Options: ollama, openai, anthropic
```

#### Ollama LLM Backend (Default)
```ini
[ollama]
model = gemma3:12b
host = http://localhost:11434
timeout = 30
```

#### OpenAI LLM Backend (Optional)
```ini
[openai]
api_key = your_openai_api_key_here
model = gpt-4
max_tokens = 4000
temperature = 0.1
```

#### Anthropic LLM Backend (Optional)
```ini
[anthropic]
api_key = your_anthropic_api_key_here
model = claude-3-sonnet-20240229
max_tokens = 4000
temperature = 0.1
```

### Environment Variable Configuration

You can override any configuration value using environment variables. This is especially useful for sensitive data like API keys or deployment-specific settings.

#### Environment Variable Format
Environment variables follow the pattern: `SYNC2NAS_<SECTION>_<KEY>`

#### Supported Environment Variables

**LLM Service Selection:**
```bash
export SYNC2NAS_LLM_SERVICE=openai  # Override [llm] service
```

**OpenAI Configuration:**
```bash
export SYNC2NAS_OPENAI_API_KEY=your_openai_api_key_here
export SYNC2NAS_OPENAI_MODEL=gpt-4
export SYNC2NAS_OPENAI_MAX_TOKENS=4000
export SYNC2NAS_OPENAI_TEMPERATURE=0.1
```

**Anthropic Configuration:**
```bash
export SYNC2NAS_ANTHROPIC_API_KEY=your_anthropic_api_key_here
export SYNC2NAS_ANTHROPIC_MODEL=claude-3-sonnet-20240229
export SYNC2NAS_ANTHROPIC_MAX_TOKENS=4000
export SYNC2NAS_ANTHROPIC_TEMPERATURE=0.1
```

**Ollama Configuration:**
```bash
export SYNC2NAS_OLLAMA_HOST=http://localhost:11434
export SYNC2NAS_OLLAMA_MODEL=gemma3:12b
export SYNC2NAS_OLLAMA_NUM_CTX=4096
```

#### Environment Variable Precedence
- Environment variables **always override** config file values
- This allows secure deployment without modifying config files
- Useful for containerized deployments and CI/CD pipelines

#### Example: Secure API Key Management
```bash
# Set API key via environment variable (recommended for production)
export SYNC2NAS_OPENAI_API_KEY=sk-your-secret-key-here

# Config file can omit the API key
[openai]
model = gpt-4
max_tokens = 4000
temperature = 0.1
# api_key is provided via environment variable
```

### Complete Configuration Example
```ini
# Core Services Configuration
[sftp]
host = your.sftpserver.com
port = 22
username = your_username
ssh_key_path = ./ssh/your_sftpserver_rsa
paths = /path/to/remote/files/,/another/remote/path/

[database]
type = sqlite

[sqlite]
db_file = ./database/sync2nas.db

[transfers]
incoming = ./incoming

[tmdb]
api_key = your_tmdb_api_key_here

[routing]
anime_tv_path = d:/anime_tv/

# LLM Configuration (Choose one service)
[llm]
service = ollama  # Options: ollama, openai, anthropic

# Ollama Configuration (Default - Free local LLM)
[ollama]
model = gemma3:12b
host = http://localhost:11434
timeout = 30

# OpenAI Configuration (Optional - Requires API key)
[openai]
api_key = your_openai_api_key_here
model = gpt-4
max_tokens = 4000
temperature = 0.1

# Anthropic Configuration (Optional - Requires API key)
[anthropic]
api_key = your_anthropic_api_key_here
model = claude-3-sonnet-20240229
max_tokens = 4000
temperature = 0.1
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
python sync2nas_api.py
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
python sync2nas.py add-show "Attack on Titan"

# Add show by TMDB ID
python sync2nas.py add-show --tmdb-id 1429

# Override directory name
python sync2nas.py add-show "Show Name" --override-dir
```

#### Search for Shows
```bash
# Search local database
python sync2nas.py search-show "Attack on Titan"
python sync2nas.py search-show --tmdb-id 1429

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
# The backend (Ollama, Anthropic, or OpenAI) is selected via the [llm] config section
# Route files with LLM parsing and automatic show creation
python sync2nas.py route-files --use-llm --auto-add

# Custom confidence threshold (overrides config value)
python sync2nas.py route-files --use-llm --llm-confidence 0.8
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
- The `[anthropic]` section is now optional and only used if `[llm] service = anthropic`.
- The `[ollama]` section is required if using Ollama.
- All LLM configuration is now modular and extensible; see [docs/configuration.md](docs/configuration.md) for details.
- Deprecated references to `llm_service.py` and `LLMService` have been removed; see migration notes in the documentation if you have custom integrations.

## Development

### Project Structure

```text
sync2nas/
├── cli/         # CLI command implementations
├── api/         # REST API implementation
├── gui/         # GUI Implementation (tkinter)
├── services/    # Core service objects
├── models/      # Data models
├── utils/       # Utility functions
├── tests/       # Test suite
├── config/      # Configuration files
└── docs/        # Documentation
```

### Complete Architecture with GUI

```text
                                 ┌─────────────────────────────┐
                                 │        Sync2NAS App         │
                                 └─────────────┬───────────────┘
                                               │
                ┌──────────────────────────────┼                                              
  ┌─────────────▼────────────┐                 │
  │            GUI           │                 │
  │       (gui/main.py)      │                 │
  │                          │                 │
  │ • Tkinter/ttkbootstrap   │                 │
  │ • Threaded CLI execution │                 │
  │ • Real-time logging      │                 │
  │ • Config management      │                 │
  └─────────────┬────────────┘                 │
   Calls CLI    │                              │
 via subprocess │                              │
                │                              │
                └─────┐  ┌─────────────────────┼────────────────────┐
                      │  │                                          │
                 ┌────▼──▼───────┐                         ┌────────▼────────┐
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

## Troubleshooting

### Configuration Issues

#### LLM Service Configuration Problems

**Problem: "LLM service initialization failed"**
```bash
# Check your configuration with the built-in validator
python sync2nas.py config-check

# Test specific service connectivity
python sync2nas.py config-check --service openai
python sync2nas.py config-check --service ollama
```

**Problem: Case sensitivity errors**
- Use lowercase section names: `[openai]` not `[OpenAI]`
- The system accepts both but prefers lowercase
- Check for typos: `[olama]` should be `[ollama]`

**Problem: Missing API keys**
```bash
# Use environment variables for secure key management
export SYNC2NAS_OPENAI_API_KEY=your_key_here

# Or add to config file
[openai]
api_key = your_key_here
```

**Problem: Ollama connection issues**
```bash
# Verify Ollama is running
curl http://localhost:11434/api/version

# Check if your model is installed
ollama list

# Pull the required model
ollama pull gemma3:12b
```

#### Common Configuration Mistakes

1. **Wrong section names**: Use `[ollama]` not `[Ollama]`
2. **Missing required keys**: Each service needs specific configuration
3. **Invalid model names**: Use exact model names (e.g., `gpt-4` not `gpt4`)
4. **Incorrect URLs**: Ollama host should include protocol: `http://localhost:11434`

#### Configuration Validation

The system provides intelligent suggestions for common mistakes:

```bash
# Validate your entire configuration
python sync2nas.py config-check

# Get detailed suggestions for configuration issues
python sync2nas.py config-check --verbose
```

**Example validation output:**
```
❌ Configuration Issues Found:
  • [openai] api_key: Required key missing
  • Suggestion: Get your API key from https://platform.openai.com/api-keys

💡 Intelligent Suggestions:
  • Section '[OpenAI]' should be '[openai]' (lowercase preferred)
  • Key 'api_ky' might be 'api_key'
  • Consider using environment variable: SYNC2NAS_OPENAI_API_KEY
```

### Performance Issues

#### Slow LLM Responses
- **Ollama**: Use smaller models like `gemma3:7b` for faster responses
- **OpenAI**: Reduce `max_tokens` or use `gpt-3.5-turbo` instead of `gpt-4`
- **Network**: Check internet connectivity for cloud-based LLMs

#### File Processing Issues
```bash
# Use dry-run mode to test without making changes
python sync2nas.py route-files --dry-run

# Enable verbose logging for debugging
python sync2nas.py -vv route-files
```

### Getting Help

1. **Check Configuration**: Run `python sync2nas.py config-check`
2. **Review Logs**: Use `-v` or `-vv` flags for detailed logging
3. **Test Components**: Use individual commands to isolate issues
4. **Environment Variables**: Use `SYNC2NAS_*` variables for overrides

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
- Open an [issue](https://github.com/jamesbconner/sync2nas/issues)
- Join our [discussions](https://github.com/jamesbconner/sync2nas/discussions)