# SFTP to NAS Synchronization Script
![Service Test Coverage](https://img.shields.io/badge/Service%20Test%20Coverage-100%25-success?style=flat-square&logo=pytest&logoColor=white)



## Introduction

This Python script synchronizes files from an SFTP server to a NAS, integrates with the TMDB API for metadata enrichment, and manages the data using a pluggable database backend (SQLite, PostgreSQL, or Milvus). It supports routing downloaded media files into organized directories, creating and managing show records, and updating episode information.

## Service Test Coverage

| Service  | Coverage Matrix | Testing Philosophy |
|:---------|:----------------|:-------------------|
| SFTP     | [SFTP Service Matrix](docs/Services_Test_Coverage_Matrix.md#sftpservice-tests) | [SFTP Testing Philosophy](docs/SFTP_Test_Philosophy.md) |
| Database | [DB Service Matrix](docs/Services_Test_Coverage_Matrix.md#dbservice-tests) | [DB Testing Philosophy](docs/Database_Test_Philosophy.md) |
| TMDB     | [TMDB Service Matrix](docs/Services_Test_Coverage_Matrix.md#tmdbservice-tests) | [TMDB Testing Philosophy](docs/TMDB_Test_Philosophy.md) |

## Key Features

- **Database Factory:** Easily switch between SQLite, PostgreSQL, and Milvus backends via config. The factory pattern allows future database types to be added with minimal code changes.
- **Rich Configuration:** Supports advanced routing of files, multiple database backends, SFTP options, etc.
- **Bootstrap TV Shows:** Populate the TV shows table from the NAS directory structure.
- **Bootstrap Existing Media:** Easily add your existing media to the database.
- **Robust File Routing:** Supports routing to multiple media types.
- **Configurable Logging:** Verbosity and log file output are fully configurable.
- **Comprehensive Test Coverage:** Tests focus on service contracts and use the factory for backend-agnostic testing.

## Configuration Requirements

The script requires a configuration file (`sync2nas_config.ini`) in the `config` subdirectory with the following fields:

### SFTP Settings

- `host`: SFTP server hostname.
- `port`: SFTP server port.
- `username`: Username for SFTP authentication.
- `ssh_key_path`: Path to the SSH private key for authentication.
- `paths`: Comma-separated list of remote paths on the SFTP server to synchronize files from.

### Database Backend Selection

- `[Database]` section with `type` key: `sqlite`, `postgres`, or `milvus`.
- Each backend has its own section for connection details.

### SQLite Settings

- `db_file`: Path to the SQLite database file used to store metadata and manage show information.

### PostgreSQL Settings

- `host`, `port`, `database`, `user`, `password`: Standard PostgreSQL connection parameters.

### Milvus Settings

- `host`, `port`: Milvus vector database connection parameters.

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

[Database]
#type = postgres
#type = milvus
type = sqlite

[PostgreSQL]
host = localhost
port = 5432
database = sync2nas
user = postgres
password = your_password

[Milvus]
host = localhost
port = 19530

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

- [x] Database backup function (implemented)
- [ ] Add a function to check for and handle show/episode renames and updates to the database
- [ ] Check downloaded file against AniDB hash to confirm file integrity and correctly identify episode
- [ ] Check inventory hashes against AniDB hashes to confirm file integrity and correctly identify episode
- [ ] Inventory check against episodes table to identify missing episodes
- [ ] Filename transformer to convert absolute episode number to relative season/episode number (Jellyfin)
- [ ] Check for new seasons of shows existing in the inventory on AniDb (periodic pull of AniDB)
- [ ] Add a de-dupe function to identify duplicate show/episodes in the inventory for pruning
- [ ] Rework special character handling in show names (primary and aliases)
- [ ] Add IMDB, TVDB and AniDB APIs as optional sources for show information if TMDB info missing
- [ ] Better checks for handling specials and OVAs
- [ ] Add genre, language and other identifiers to the search and fix-show functions
- [ ] MCP LLM integration for show and episode filename parsing
- [ ] MCP Server integration with TMDB, AniDB, TVDB, IMDB, etc. to get show and episode information
- [ ] MCP Server integration with database backend to update/add shows, episodes, etc. (already supports SQLite)
- [ ] Try vector DB for similarity search and recommendations (Milvus, Chroma, Qdrant, Weaviate, Faiss, etc.)
- [ ] Semantic search and content-based retrieval of shows and episodes
- [ ] MCP Server RSS Feed integration for new show notifications

## Roadmap for Future Development

See the TODOs above for planned features and improvements. Contributions are welcome!

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

### Database Backup
Back up the current database using the configured backend.
```bash
python sync2nas.py backup-db
```

### Verbose Output for Debugging
Enable step by step verbose information printed out to the console.  Single -v is for INFO log level messages, -vv is for DEBUG level.
```bash
python sync2nas.py -vv
```

### Dry Running Commands
Most commands have a --dry-run flag enabled, so you can see what actions will be taken before committing to that plan of action.
```bash
python sync2nas.py route-files --auto-add --dry-run
```

## Contribution

Feel free to fork the repository and submit pull requests to enhance the features or fix bugs. Please ensure code is well-documented and tested.

