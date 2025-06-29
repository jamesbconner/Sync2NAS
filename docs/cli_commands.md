# CLI Commands Reference

This document provides a comprehensive reference for all Sync2NAS CLI commands.

## Command Overview

All commands follow the pattern: `python sync2nas.py <command> [options]`

## Core Commands

### File Management

#### `download-from-remote`
Downloads new files from configured SFTP paths to the local incoming directory.

```bash
python sync2nas.py download-from-remote [options]
```

**Options:**
- `--verbose, -v`: Enable verbose output
- `--logfile, -l`: Specify log file path
- `--config, -c`: Specify configuration file path

**Examples:**
```bash
# Basic download
python sync2nas.py download-from-remote

# Download with debug logging
python sync2nas.py -vv download-from-remote

# Download with custom log file
python sync2nas.py download-from-remote --logfile downloads.log
```

#### `route-files`
Routes files from the incoming directory to their proper destinations based on show metadata.

```bash
python sync2nas.py route-files [options]
```

**Options:**
- `--auto-add`: Automatically add unknown shows to database
- `--use-llm`: Enable AI-powered filename parsing
- `--llm-confidence`: Set minimum confidence threshold (0.0-1.0)
- `--dry-run`: Simulate operations without moving files
- `--incoming, -i`: Specify incoming directory path

**Examples:**
```bash
# Standard routing
python sync2nas.py route-files

# Auto-add unknown shows
python sync2nas.py route-files --auto-add

# Use AI-powered parsing
python sync2nas.py route-files --use-llm

# Dry run with LLM parsing
python sync2nas.py route-files --use-llm --dry-run
```

#### `list-remote`
Lists files on the remote SFTP server.

```bash
python sync2nas.py list-remote [options]
```

**Options:**
- `--path, -p`: Specify remote path to list
- `--recursive, -r`: List files recursively
- `--populate-sftp-temp, -s`: Populate SFTP temporary table
- `--dry-run, -d`: Simulate without listing

### Show Management

#### `add-show`
Adds a new show to the database and creates the directory structure.

```bash
python sync2nas.py add-show [SHOW_NAME] [options]
```

**Arguments:**
- `SHOW_NAME`: Name of the show to add (optional if --tmdb-id provided)

**Options:**
- `--tmdb-id`: TMDB ID for exact show matching
- `--override-dir`: Use provided name for directory instead of TMDB name
- `--dry-run`: Simulate without creating directories or database entries

**Examples:**
```bash
# Add by name (interactive search)
python sync2nas.py add-show "Breaking Bad"

# Add by TMDB ID
python sync2nas.py add-show --tmdb-id 1396

# Override directory name
python sync2nas.py add-show "Show Name" --override-dir
```

#### `search-show`
Searches for shows in the local database.

```bash
python sync2nas.py search-show [SHOW_NAME] [options]
```

**Arguments:**
- `SHOW_NAME`: Name of the show to search for (optional)

**Options:**
- `--tmdb-id`: Search by TMDB ID instead of name
- `--verbose, -v`: Show detailed information
- `--partial, -p`: Enable partial matching (default)
- `--exact, -e`: Use exact matching only
- `--dry-run`: Simulate search without displaying results

**Examples:**
```bash
# Search by name
python sync2nas.py search-show "Breaking Bad"

# Search by TMDB ID
python sync2nas.py search-show --tmdb-id 1396

# Verbose output
python sync2nas.py search-show "One Piece" --verbose
```

#### `search-tmdb`
Searches for shows directly on TMDB.

```bash
python sync2nas.py search-tmdb [SHOW_NAME] [options]
```

**Arguments:**
- `SHOW_NAME`: Name of the show to search for (optional)

**Options:**
- `--tmdb-id`: Search by TMDB ID instead of name
- `--verbose, -v`: Show detailed information
- `--limit, -l`: Limit number of results (default: 10)
- `--year, -y`: Filter results by year
- `--dry-run`: Simulate search without API calls

**Examples:**
```bash
# Search by name
python sync2nas.py search-tmdb "One Piece"

# Search by TMDB ID
python sync2nas.py search-tmdb --tmdb-id 37854

# Limited results with verbose output
python sync2nas.py search-tmdb "Breaking" --limit 5 --verbose
```

#### `fix-show`
Fixes misclassified shows in the database.

```bash
python sync2nas.py fix-show SHOW_NAME [options]
```

**Arguments:**
- `SHOW_NAME`: Name of the show to fix

**Options:**
- `--tmdb-id`: Use specific TMDB ID for correction
- `--dry-run`: Simulate correction without database changes

**Examples:**
```bash
# Interactive fix
python sync2nas.py fix-show "Show Name"

# Fix with specific TMDB ID
python sync2nas.py fix-show "Show Name" --tmdb-id 123456
```

### Database Operations

#### `bootstrap-downloads`
Populates the downloads table with existing SFTP files.

```bash
python sync2nas.py bootstrap-downloads
```

**Purpose:** Records existing remote files so they won't be re-downloaded.

#### `bootstrap-tv-shows`
Populates the TV shows table from existing media directories.

```bash
python sync2nas.py bootstrap-tv-shows
```

**Purpose:** Adds existing shows to the database from your media library.

#### `bootstrap-episodes`
Populates episode information for all shows in the database.

```bash
python sync2nas.py bootstrap-episodes
```

**Purpose:** Fetches episode metadata from TMDB for all shows.

#### `backup-db`
Creates a backup of the current database.

```bash
python sync2nas.py backup-db
```

**Purpose:** Safeguards your database before major operations.

#### `init-db`
Initializes a new database with the required schema.

```bash
python sync2nas.py init-db
```

**Purpose:** Sets up a fresh database for new installations.

### Utility Commands

#### `update-episodes`
Updates episode information for a specific show.

```bash
python sync2nas.py update-episodes [SHOW_NAME] [options]
```

**Options:**
- `--tmdb-id`: Update episodes for specific TMDB ID
- `--dry-run`: Simulate without database changes

## Global Options

All commands support these global options:

- `--verbose, -v`: Enable verbose output (can be used multiple times: -vv for debug)
- `--logfile, -l`: Specify log file path
- `--config, -c`: Specify configuration file path (default: ./config/sync2nas_config.ini)
- `--dry-run`: Simulate operations without making changes

## Examples

### Complete Workflow
```bash
# 1. Download new files
python sync2nas.py download-from-remote

# 2. Route files with AI parsing
python sync2nas.py route-files --use-llm --auto-add

# 3. Check results
python sync2nas.py search-show "New Show" --verbose
```

### Debugging
```bash
# Enable debug logging
python sync2nas.py -vv route-files --dry-run

# Log to file
python sync2nas.py -v --logfile debug.log route-files
```

### Batch Operations
```bash
# Add multiple shows
python sync2nas.py add-show "Show 1" --tmdb-id 123
python sync2nas.py add-show "Show 2" --tmdb-id 456

# Update all episodes
python sync2nas.py update-episodes
```