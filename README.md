# SFTP to NAS Synchronization Script
![Service Test Coverage](https://img.shields.io/badge/Service%20Test%20Coverage-100%25-success?style=flat-square&logo=pytest&logoColor=white)



## Introduction

This Python script synchronizes files from an SFTP server to a NAS, integrates with the TMDB API for metadata enrichment, and manages the data using an SQLite database. It supports routing downloaded media files into organized directories, creating and managing show records, and updating episode information.

## Testing Philosphies
[SFTP Testing Philosophy](docs/SFTP_Test_Philosophy.md)
[Database Testing Philosophy](docs/Database_Test_Philosophy.md)
[TMDB Testing Philosophy](docs/TMDB_Test_Philosophy.md)

## Service Testing Matrix
[Service Tests Coverage Matrix](docs/Services_Test_Coverage_Matrix.md)

## Configuration Requirements

The script requires a configuration file (`sync2nas_config.ini`) in the `config` subdirectory with the following fields:

### SFTP Settings

- `host`: SFTP server hostname.
- `port`: SFTP server port.
- `username`: Username for SFTP authentication.
- `ssh_key_path`: Path to the SSH private key for authentication.
- `paths`: Comma-separated list of remote paths on the SFTP server to synchronize files from.

### SQLite Settings

- `db_file`: Path to the SQLite database file used to store metadata and manage show information.

### TMDB API Settings

- `api_key`: API key for authenticating with the TMDB API.

### Routing Settings

- `anime_tv_path`: Path to the anime TV directory on the NAS.

### Transfer Settings

- `incoming`: Path to the incoming directory where files are initially downloaded before routing.

### Example sync2nas_config.ini
```
[SFTP]
host = your.sftpserver.com
port = 22
username = whatsyourname
ssh_key_path = ./ssh/your_sftpserver_rsa
paths = /path/to/remote/files/,/another/remote/path/,/third/remote/path/

[SQLite]
db_file = ./database/sync2nas.db

[Transfers]
incoming = ./incoming

[TMDB]
api_key = a1234567-b123-c123-d123-e12345678901

[Routing]
anime_tv_path = d:/anime_tv/
movie_path = d:/movies/
```

## Obtaining a TMDB API Key

To use the TMDB integration features, obtain an API key by registering an account with [The Movie Database](https://www.themoviedb.org/). This API key must be added to the configuration file under the `TMDB` section.

## TODOs in the Code

## Roadmap for Future Development

## Usage Examples

### Basic File Download from SFTP
Download new files from all configured SFTP paths to the local Incoming directory with DEBUG log verbosity. The command will process each path defined in the configuration file's `paths` setting.
```bash
python sync2nas.py -vv download-from-remote
```

### Route Files from Incoming to NAS Filesystem
Route the files located in the Incoming directory to the destinations on the local NAS as defined in the database.  Also add any unknown shows by looking up the TMDB entry.
```bash
python sync2nas.py route-files --auto-add 
```

### Add A New Show To The Database and NAS Filesystem Directory
Creates an entry for the show in the database, adds the episode information, and creates the path for the show on the NAS.  If the --tmdb-id flag is provided, it uses the ID for an exact match, otherwise it uses the show name for a search and uses the first result.  Using the --override-dir flag tells the command to ues the show name provided as the name of the directory on the path, rather than using the name provided by TMDB.  Useful when the showname contains invalid characters.
```bash
python sync2nas.py add-show "Example Showname" --tmdb-id 000000 --override-dir
```

### Refresh the Downloads Table
Baseline the downloads database with the contents of the SFTP server to the downloads table. This command will process all configured SFTP paths in the configuration file. It uses a recursive search on all directories in each SFTP server path, so it may take a considerable amount of time depending on the number and size of configured paths. These files will not be downloaded as a result of this command, nor will these files be downloaded in the future.
```bash
python sync2nas.py bootstrap-downloads
```

### Fix a misclassified show in the database
When a show gets added, either manually or via the --auto-add flag when routing files in the Incoming directory, the correct show might not be identified in the TMDB search results.  In that case, the show and episode information need to be corrected.  When using the fix-show CLI command, a show name argument is required in order to know what show to fix.  If the --tmdb-id flag is used, it will correct the given show name with the provided TMDB show ID.  If no --tmdb-id flag is provided, then an interactive session will appear in the terminal window with the top 20 results for the show.
```bash
python sync2nas.py fix-show "Show Name" --tmdb-id 000000
```

### Verbose Output for Debugging
Enable step by step verbose information printed out to the console.  Single -v is for INFO log level messages, -vv is for DEBUG level.
```bash
python sync2nas.py -vv
```

### Dry Running Commands
Most commands have a --dry-run flag enabled, so you can see what actions will be taken before commiting to that plan of action.
```bash
python sync2nas.py route-files --auto-add --dry-run
```

## Contribution

Feel free to fork the repository and submit pull requests to enhance the features or fix bugs. Please ensure code is well-documented and tested.

