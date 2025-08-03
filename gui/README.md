# Sync2NAS GUI

A Windows desktop GUI application for the Sync2NAS CLI tool with comprehensive functionality and modern styling.

## Features

- **Download Management**: Download files from remote SFTP servers with configurable worker threads
- **File Routing**: Route downloaded files to appropriate show directories with LLM-powered filename parsing
- **Search Functionality**: Search local database and TMDB API for shows with nullable filters
- **Show Management**: Add new shows and fix misclassified shows in the database
- **Database Operations**: Initialize, backup, and bootstrap database with various operations
- **Real-time Logging**: View live log output from CLI operations
- **Configuration Management**: Load and manage Sync2NAS configuration files
- **Dry Run Mode**: Test operations without making actual changes
- **LLM Configuration**: Configure different LLM services (Ollama, OpenAI, Anthropic) and models
- **Temporary Config Overrides**: Apply configuration changes without modifying the original file
- **Modern Styling**: ttkbootstrap integration for a professional look and feel
- **Threaded Operations**: Non-blocking CLI command execution
- **Unicode Support**: Proper handling of special characters and emojis
- **Scrollable Sections**: Mousewheel support for extensive configuration options

## Getting Started

### Prerequisites

- Python 3.7 or higher
- Sync2NAS dependencies installed (see main project requirements.txt)
- Valid Sync2NAS configuration file
- **ttkbootstrap** package (install with `pip install ttkbootstrap`) for modern styling

### Running the GUI

1. **From the project root directory:**
   ```bash
   python sync2nas_gui.py
   ```

2. **Or using the batch file:**
   ```bash
   run_gui.bat
   ```

3. **Or double-click the batch file** in Windows Explorer

## GUI Layout

The GUI organizes functionality into tabs in the following order:
1. **Frequently Executed Operations** (Default) - Most commonly used operations
2. **Search** - Database and TMDB search functionality
3. **Show Management** - Add and fix show operations
4. **Database Operations** - Database initialization, backup, and bootstrap operations
5. **Configuration** - Advanced configuration options
6. **Logs** - Real-time log output

### Frequently Executed Operations Tab (Default)
This tab combines the most commonly used operations in a clean, simplified layout:

#### Global Configuration Section
- **Dry Run Mode**: Enable to test operations without making changes
- **Verbosity**: Set logging level (WARNING, INFO, DEBUG) - defaults to WARNING

#### Download Operations Section
- **Max Workers**: Number of concurrent download threads (1-10)
- Download Button: Start downloading files from remote SFTP server
- Status: Current download status

#### File Routing Operations Section
- **Auto-add Shows**: Automatically add missing shows to database
- **Use LLM**: Enable LLM-powered filename parsing
- **LLM Confidence**: Minimum confidence threshold (0.0-1.0) using a spinbox for precise control
- Route Button: Start file routing process
- Status: Current routing status

### Search Tab
The Search tab provides two main search functionalities:

#### Show Search (Local Database) Section
- **Show Name**: Enter the name of a show to search in the local database
- **TMDB ID**: Optional TMDB ID filter (nullable - can be left empty)
- **Search Options**:
  - **Verbose Output**: Enable detailed logging
  - **Partial Matching**: Search for partial name matches
  - **Exact Matching**: Search for exact name matches
- **Search Button**: Execute the search
- **Status**: Current search status

#### TMDB Search Section
- **Show Name**: Enter the name of a show to search in TMDB API
- **TMDB ID**: Optional TMDB ID filter (nullable - can be left empty)
- **Search Options**:
  - **Verbose Output**: Enable detailed logging
  - **Result Limit**: Maximum number of results to return (1-50)
  - **Year Filter**: Optional year filter (nullable - can be left empty)
- **Search Button**: Execute the search
- **Status**: Current search status

#### Search Results Section
- **Results Display**: Shows the output from search operations
- **Clear Results**: Clear the results display
- **Save Results**: Save results to a text file

### Show Management Tab
The Show Management tab provides functionality to add new shows and fix misclassified shows in the database:

#### Add Show Section
- **Show Name**: Enter the name of a show to add to the database (optional if TMDB ID provided)
- **TMDB ID**: Optional TMDB ID for exact show matching (nullable - can be left empty)
- **Options**:
  - **Use LLM for suggestions**: Enable LLM-powered show name and directory name suggestions
  - **Override directory name**: Use the provided show name directly for the folder name
  - **LLM Confidence**: Minimum confidence threshold for LLM suggestions (0.0-1.0)
- **Add Show Button**: Execute the add-show process
- **Status**: Current add show status

#### Fix Show Section
- **Show Name**: Enter the name of a show to fix in the database (required)
- **TMDB ID**: Optional TMDB ID to override interactive search (nullable - can be left empty)
- **Fix Show Button**: Execute the fix-show process
- **Status**: Current fix show status

*Note: The fix-show command will perform an interactive TMDB search if no TMDB ID is provided, allowing you to select the correct show from search results.*

### Database Operations Tab
The Database Operations tab provides comprehensive database management functionality with a scrollable interface:

#### Database Initialization Section
- **Initialize Database**: Create and initialize the SQLite database with required tables
- **Status**: Current initialization status

#### Database Backup Section
- **Backup Database**: Create a backup of the current database
- **Status**: Current backup status

#### Update Episodes Section
- **Show Name**: Enter the name of a show to update episodes for
- **TMDB ID**: Optional TMDB ID filter (nullable - can be left empty)
- **Options**:
  - **Verbose Output**: Enable detailed logging
- **Update Episodes Button**: Refresh episodes for the specified show from TMDB
- **Status**: Current update status

#### Bootstrap Operations Section
One-time operations to populate the database with initial data:

- **Bootstrap TV Shows**: Populate tv_shows table from anime_tv_path directory
- **Bootstrap Episodes**: Populate episodes for all shows from TMDB
- **Bootstrap Downloads**: Baseline downloaded_files from SFTP listing
- **Bootstrap Inventory**: Populate inventory from existing media files

Each bootstrap operation includes:
- **Description**: What the operation does
- **Execute Button**: Start the bootstrap process
- **Status**: Current operation status

### Configuration Tab
Advanced configuration options for selecting configuration files and overriding settings. The tab includes a scrollable interface to accommodate all configuration sections:

#### Log Level Section
- **Log Level**: Set logging level (WARNING, INFO, DEBUG) - defaults to WARNING

#### Configuration File Section
- **Config File**: Select your Sync2NAS configuration file (.ini)
- **Browse Button**: Open file dialog to choose a configuration file

#### Database Configuration Section
- **Database Type**: Choose between SQLite (default), PostgreSQL, or Milvus
- **SQLite Configuration** (shown when SQLite is selected):
  - **Database File**: Path to the SQLite database file
  - **Browse Button**: Select database file location
- **PostgreSQL Configuration** (shown when PostgreSQL is selected):
  - **Host**: Database server hostname
  - **Port**: Database server port (default: 5432)
  - **Database**: Database name
  - **User**: Database username
  - **Password**: Database password
- **Milvus Configuration** (shown when Milvus is selected):
  - **Host**: Milvus server hostname
  - **Port**: Milvus server port (default: 19530)

#### SFTP Configuration Section
- **Host**: SFTP server hostname
- **Port**: SFTP server port (default: 22)
- **Username**: SFTP username
- **SSH Key Path**: Path to SSH private key file
- **Browse Button**: Select SSH key file
- **Remote Path**: Remote directory path(s) to scan

#### TMDB Configuration Section
- **API Key**: TMDB API key for show information lookup

#### Routing Configuration Section
- **Anime TV Path**: Directory path for anime TV shows
- **Browse Button**: Select anime TV directory

#### LLM Configuration Section
- **LLM Service**: Choose between Ollama, OpenAI, or Anthropic
- **Model**: Select appropriate model for the chosen service
  - **Ollama Models**: gemma3:12b (default), qwen3:14b, mistral:latest, deepseek-r1:32b, llama3.2:latest
  - **OpenAI Models**: gpt-3.5-turbo, gpt-4, gpt-4-turbo
  - **Anthropic Models**: claude-3-5-sonnet-20240620, claude-3-opus-20240229, claude-3-sonnet-20240229
- **API Key**: Enter API key for cloud-based services (OpenAI/Anthropic)
- **Max Tokens**: Maximum tokens for API responses
- **Temperature**: Model temperature setting

#### Path Overrides Section
- **Incoming Path Override**: Override the incoming path from the config file
- **Browse Button**: Select incoming directory

#### Configuration Actions Section
- **Load Configuration**: Reload the configuration file
- **Apply Configuration Overrides**: Create a temporary config file with GUI settings
- **Clear Overrides**: Remove the temporary config file

### Logs Tab
- **Log Output**: Real-time display of CLI command output
- **Clear Logs**: Clear the log display
- **Save Logs**: Save log output to file

## Usage

### GUI Workflow
1. **Load Configuration**: Start by loading your Sync2NAS configuration file
2. **Configure Overrides** (Optional): Use the Configuration tab to set up LLM options or path overrides
3. **Apply Overrides**: Click "Apply Configuration Overrides" to create a temporary config file
4. **Execute Operations**: Use the Frequently Executed Operations tab for download and routing
5. **Monitor Progress**: Watch the Logs tab for real-time operation status

## Configuration

The GUI uses the same configuration file as the CLI tool. Make sure your `sync2nas_config.ini` file is properly configured with:

- SFTP connection details
- Database settings
- TMDB API key
- File paths
- LLM service configuration

### Temporary Configuration Files

The GUI can create temporary configuration files when you apply overrides. These files:
- Are automatically cleaned up when the GUI closes
- Allow you to test different settings without modifying your original config
- Are used for all CLI operations until cleared or the GUI is restarted

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure you're running from the project root directory
2. **Configuration Errors**: Verify your config file path and format
3. **Permission Errors**: Ensure the GUI has access to the directories specified in your config
4. **Verbosity Selection**: The verbosity dropdown uses string values (WARNING, INFO, DEBUG) instead of numeric values
5. **ttkbootstrap Not Available**: The GUI will fall back to standard ttk styling if ttkbootstrap is not installed

### Recent Fixes

- **Fixed verbosity handling**: The combobox properly handles string values and converts them to appropriate CLI flags
- **Fixed lambda error handling**: Exception handling in threaded operations now properly captures error messages
- **Fixed database connection in dry-run mode**: Resolved SQLite URI mode issues on Windows for read-only database access
- **Updated CLI command structure**: GUI now uses `sync2nas.py` instead of `cli.main` and properly handles global `--dry-run` flag
- **Fixed global option ordering**: Global options like `--dry-run` and `--config` are now placed before subcommands as required by Click
- **Fixed Unicode encoding issues**: Added proper UTF-8 encoding handling for CLI output and replaced Unicode characters with ASCII equivalents to prevent encoding errors on Windows
- **Optimized GUI Code**: Refactored to eliminate duplication and improve maintainability
- **Enhanced Testing**: Comprehensive test suite with proper Tkinter isolation and threading management

### Logs

Check the Logs tab for detailed error messages and operation status. You can save logs to a file for troubleshooting.

## Development

The GUI is built using Python's built-in tkinter library, making it lightweight and dependency-free. It uses ttkbootstrap for modern styling when available. The application runs CLI commands in separate threads to prevent UI freezing during long operations.

### File Structure

```
gui/
├── main.py              # Main GUI application with ttkbootstrap styling
└── README.md            # This file

sync2nas_gui.py          # GUI launcher script
run_gui.bat              # GUI batch launcher
```

### Adding New Features

To add support for additional CLI commands:

1. Add new tabs or sections to the GUI
2. Create corresponding methods in the GUI class
3. Use the same subprocess pattern as existing commands
4. Update the logging to capture command output

## License

This GUI is part of the Sync2NAS project and follows the same license terms. 