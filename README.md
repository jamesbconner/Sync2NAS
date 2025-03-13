# SFTP to NAS Synchronization Script

## Introduction

This Python script synchronizes files from an SFTP server to a NAS, integrates with the TVDB API for metadata enrichment, and manages the data using an SQLite database. It supports routing downloaded media files into organized directories, creating and managing show records, and updating episode information.

## Configuration Requirements

The script requires a configuration file (`sync2nas_config.ini`) in the `config` subdirectory with the following fields:

### SFTP Settings

- `host`: SFTP server hostname.
- `port`: SFTP server port.
- `username`: Username for SFTP authentication.
- `ssh_key_path`: Path to the SSH private key for authentication.
- `path`: Remote path on the SFTP server to synchronize files from.

### SQLite Settings

- `db_file`: Path to the SQLite database file used to store metadata and manage show information.

### TVDB API Settings

- `api_key`: API key for authenticating with the TVDB API.

### Routing Settings

- `tv_path`: Path to the main TV show directory on the NAS.
- `anime_tv_path`: Path to the anime TV directory on the NAS.

### Transfer Settings

- `incoming`: Path to the incoming directory where files are initially downloaded before routing.

## Obtaining a TVDB API Key

To use the TVDB integration features, obtain an API key by registering an account with [TheTVDB](https://thetvdb.com/). This API key must be added to the configuration file under the `TVDB` section.

## TODOs in the Code

- **Show Existence Check**: When using the `--create-show` option, the script should first check if the show already exists in the database to avoid duplication.
- **Enhanced Logging**: Refine logging output to provide more granular control and improve readability.
- **Error Handling**: Strengthen exception handling to cover more edge cases, especially around network connectivity and API rate limits.

## Roadmap for Future Development

The argparse object includes options that are not fully implemented. These are planned for future releases:

- `--search-show`: Currently defined but not actively used. The future goal is to provide an interactive search feature.
- `--update-show`: Allow updating existing show records by specifying local and TVDB IDs.
- `--update-episodes`: Extend this functionality to fetch the latest episodes for a given series from TVDB.
- `--update-all-episodes`: Automate the process to check for new episodes across all shows in the database.
- Logging Level Customization: Enable setting logging levels via argparse for more control over output verbosity.

Additionally the following items are under consideration:
- Refactoring repetative code blocks for SFTP operations
- Optimize the `list_sftp_files` function to reduce redundant file_attr processing
- Better handing of database connections to ensure proper closures across connections
- Validate configuration inputes and handle missing configs gracefully
- Add type hints to functions
- Make function style-guide comments consistent

## Usage Examples

### Basic File Download from SFTP
Just download the new files from the SFTP server to the local Incoming directory without doing anything else.
```bash
python sync_script.py -d
```

### Route Files from Incoming to NAS Filesystem
Just route the files located in the Incoming directory to the destinations on the local NAS as defined in the database.
```bash
python sync_script.py -r
```

### Most Common Usage - Download and Route Files
Download new files to the Incoming directory, and route to the NAS afterwards.
```bash
python sync_script.py -d -r
```

### Refresh the Entire SFTP Table
Baseline the database with the contents of the SFTP server.  This uses a recursive search on all directories in the SFTP server path, so it takes a considerable amount of time.  These files will not be downloaded as a result of this command, nor will these files be downloaded in the future.
```bash
python sync_script.py --full-sftp-table-refresh
```

### Create a New Show Record Entry in DB and NAS Filesystem
When a show does not exist in the database or on the NAS filesystem, it needs to be created first before it can be routed.  This is to ensure the proper directory name and show/episode information is available for routing properly.
```bash
python sync_script.py --create-show="Show Name"
```

### Verbose Output for Debugging
Enable step by step verbose information printed out to the console.
```bash
python sync_script.py -v
```

## Contribution

Feel free to fork the repository and submit pull requests to enhance the features or fix bugs. Please ensure code is well-documented and tested.

