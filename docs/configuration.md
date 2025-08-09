You can specify a different config file using the `--config` CLI option or the `SYNC2NAS_CONFIG` environment variable.

---

## Configuration Sections

### [SFTP]

Configure your SFTP server connection and remote paths.

```ini
[SFTP]
host = your.sftpserver.com
port = 22
username = your_username
ssh_key_path = ./ssh/your_sftpserver_rsa
paths = /path/to/remote/files/,/another/remote/path/
```
- `host`: SFTP server hostname or IP address.
- `port`: SFTP server port (default: 22).
- `username`: SFTP username.
- `ssh_key_path`: Path to your SSH private key file.
- `paths`: Comma-separated list of remote directories to sync.

---

### [Database]

Select and configure your database backend.

```ini
[Database]
type = sqlite  # Options: sqlite, postgres, milvus
```

#### SQLite (default, recommended for most users)
```ini
[SQLite]
db_file = ./database/sync2nas.db
```

#### PostgreSQL
```ini
[PostgreSQL]
host = localhost
port = 5432
database = sync2nas
user = postgres
password = your_password
```

#### Milvus (experimental, for vector search)
```ini
[Milvus]
host = localhost
port = 19530
```

---

### [Transfers]

Configure the local directory where files are downloaded before routing.

```ini
[Transfers]
incoming = ./incoming
```
- `incoming`: Path to the local "incoming" directory.

---

### [Routing]

Configure where routed files should be placed.

```ini
[Routing]
anime_tv_path = d:/anime_tv/
movie_path = d:/movies/
```
- `anime_tv_path`: Path to your TV show library.
- `movie_path`: Path to your movie library (optional/future use).

---

### [TMDB]

Configure your TMDB API key for metadata enrichment.

```ini
[TMDB]
api_key = your_tmdb_api_key_here
```
- `api_key`: Get this from [The Movie Database](https://www.themoviedb.org/).

---

### [OpenAI] (Optional, for AI-powered filename parsing)

Configure OpenAI GPT integration for filename parsing.

```ini
[OpenAI]
api_key = your_openai_api_key
model = gpt-3.5-turbo
max_tokens = 150
temperature = 0.1
```
- `api_key`: Get this from [OpenAI](https://platform.openai.com/).
- `model`: OpenAI model to use (default: gpt-3.5-turbo).
- `max_tokens`: Maximum tokens for LLM responses (default: 150).
- `temperature`: Response randomness (default: 0.1 for consistent parsing).

---

### [API] (Optional, for REST API server)

Configure the API server.

```ini
[API]
host = 127.0.0.1
port = 8000
```
- `host`: Hostname to bind the API server (default: 127.0.0.1).
- `port`: Port for the API server (default: 8000).

---

### [Hashing] (Optional)

Configure hashing behavior for large files.

```ini
[Hashing]
; Either set chunk_size_bytes directly, or chunk_size_mib (MiB)
; chunk_size_bytes = 1048576
chunk_size_mib = 1
```
- `chunk_size_bytes`: Read chunk size in bytes used when hashing large files.
- `chunk_size_mib`: Convenience option; multiplied by 1,048,576 to derive bytes.

Defaults to 1 MiB if not specified.

---

### [llm] Section
Specifies which LLM backend to use for filename parsing.

```
[llm]
service = ollama  # or openai
```
- `service`: Which LLM backend to use. Options: `ollama`, `openai`.

### [ollama] Section
Configuration for the Ollama local LLM backend.

```
[ollama]
model = llama3.2
llm_confidence_threshold = 0.7
```
- `model`: The Ollama model to use (must be available locally).
- `llm_confidence_threshold`: Minimum confidence required to accept LLM results (float, 0.0-1.0).

### [openai] Section
Configuration for the OpenAI LLM backend.

```
[openai]
model = gpt-3.5-turbo
api_key = your_openai_api_key
max_tokens = 250
temperature = 0.1
```
- `model`: The OpenAI model to use.
- `api_key`: Your OpenAI API key.
- `max_tokens`: Maximum tokens for LLM responses.
- `temperature`: Sampling temperature for LLM responses.

---

## Complete Example

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
api_key = a1234567-b123-c123-d123-e12345678901

[OpenAI]
api_key = sk-your-openai-api-key
model = gpt-3.5-turbo
max_tokens = 150
temperature = 0.1

[Routing]
anime_tv_path = d:/anime_tv/
movie_path = d:/movies/

[API]
host = 127.0.0.1
port = 8000

[llm]
service = ollama

[ollama]
model = llama3.2
llm_confidence_threshold = 0.7

[openai]
model = gpt-3.5-turbo
api_key = your_openai_api_key
max_tokens = 250
temperature = 0.1
```

---

## Environment Variables

You can override some settings with environment variables:

- `SYNC2NAS_CONFIG`: Path to configuration file
- `SYNC2NAS_SFTP_HOST`: SFTP server hostname
- `SYNC2NAS_TMDB_API_KEY`: TMDB API key
- `SYNC2NAS_OPENAI_API_KEY`: OpenAI API key

---

## Security Best Practices

- **SSH keys:** Use SSH keys for SFTP, not passwords. Set permissions to 600.
- **API keys:** Never commit API keys to version control. Use environment variables for sensitive data.
- **Database:** Use strong passwords for PostgreSQL. Restrict access to the database file for SQLite.

---

## Troubleshooting

- **Missing config section:** Ensure all required sections are present in your config file.
- **SFTP errors:** Check SSH key permissions and server connectivity.
- **Database errors:** Verify backend type and connection details.
- **API key errors:** Make sure your TMDB/OpenAI keys are valid and not expired.
- **File permissions:** Ensure the app has read/write access to all configured paths.

---

## Tips

- Use `--config` to specify a custom config file.
- Use `-v` or `-vv` for more verbose logging.
- Use `--dry-run` to preview actions without making changes.
- Always backup your database before making major changes.

---

For more details on configuration options, see the main [README.md](../README.md) and the [Database Backends Guide](database_backends.md).

---

**Migration Note:**
- The old `LLMService` config options are no longer supported.
- You must migrate to the new `[llm]`, `[ollama]`, and `[openai]` sections as described above.
