# Configuration Guide

Sync2NAS uses an INI-style configuration file to manage all settings. The default configuration file is `config/sync2nas_config.ini`.

You can specify a different config file using the `--config` CLI option or the `SYNC2NAS_CONFIG` environment variable.

**Important:** Use lowercase section names for consistency. While the system accepts mixed case, lowercase is preferred and recommended.

---

## Configuration Sections

### [sftp] - SFTP Server Configuration

Configure your SFTP server connection and remote paths.

```ini
[sftp]
host = your.sftpserver.com
port = 22
username = your_username
ssh_key_path = ./ssh/your_sftpserver_rsa
paths = /path/to/remote/files/,/another/remote/path/
```
- `host`: SFTP server hostname or IP address
- `port`: SFTP server port (default: 22)
- `username`: SFTP username
- `ssh_key_path`: Path to your SSH private key file
- `paths`: Comma-separated list of remote directories to sync

---

### [database] - Database Backend Selection

Select and configure your database backend.

```ini
[database]
type = sqlite  # Options: sqlite, postgresql, milvus
```

#### SQLite (default, recommended for most users)
```ini
[sqlite]
db_file = ./database/sync2nas.db
```

#### PostgreSQL
```ini
[postgresql]
host = localhost
port = 5432
database = sync2nas
user = postgres
password = your_password
```

#### Milvus (experimental, for vector search)
```ini
[milvus]
host = localhost
port = 19530
```

---

### [transfers] - File Transfer Settings

Configure the local directory where files are downloaded before routing.

```ini
[transfers]
incoming = ./incoming
```
- `incoming`: Path to the local "incoming" directory

---

### [routing] - Media Library Paths

Configure where routed files should be placed.

```ini
[routing]
anime_tv_path = d:/anime_tv/
movie_path = d:/movies/
```
- `anime_tv_path`: Path to your TV show library
- `movie_path`: Path to your movie library (optional/future use)

---

### [tmdb] - TMDB API Configuration

Configure your TMDB API key for metadata enrichment.

```ini
[tmdb]
api_key = your_tmdb_api_key_here
```
- `api_key`: Get this from [The Movie Database](https://www.themoviedb.org/)

---

## LLM Configuration

### [llm] - LLM Service Selection (Required)

Specifies which LLM backend to use for AI-powered filename parsing.

```ini
[llm]
service = ollama  # Options: ollama, openai, anthropic
```
- `service`: Which LLM backend to use. Options: `ollama`, `openai`, `anthropic`

### [ollama] - Ollama Configuration (Default)

Configuration for the Ollama local LLM backend. **Recommended for most users** as it's free and runs locally.

```ini
[ollama]
model = qwen3:14b
host = http://localhost:11434
timeout = 30
```
- `model`: The Ollama model to use (must be installed locally)
- `host`: Ollama server URL (default: http://localhost:11434)
- `timeout`: Request timeout in seconds (default: 30)

**Setup Ollama:**
1. Install from [ollama.ai](https://ollama.ai/)
2. Pull a model: `ollama pull qwen3:14b`
3. Verify: `ollama list`

### [openai] - OpenAI Configuration (Optional)

Configuration for the OpenAI LLM backend. Requires API key and credits.

```ini
[openai]
api_key = your_openai_api_key_here
model = gpt-4
max_tokens = 4000
temperature = 0.1
```
- `api_key`: Your OpenAI API key from [platform.openai.com](https://platform.openai.com/api-keys)
- `model`: OpenAI model to use (recommended: gpt-4)
- `max_tokens`: Maximum tokens for LLM responses (default: 4000)
- `temperature`: Response randomness (default: 0.1 for consistent parsing)

### [anthropic] - Anthropic Configuration (Optional)

Configuration for the Anthropic Claude LLM backend. Requires API key.

```ini
[anthropic]
api_key = your_anthropic_api_key_here
model = claude-3-sonnet-20240229
max_tokens = 4000
temperature = 0.1
```
- `api_key`: Your Anthropic API key from [console.anthropic.com](https://console.anthropic.com/)
- `model`: Anthropic model to use (recommended: claude-3-sonnet-20240229)
- `max_tokens`: Maximum tokens for LLM responses (default: 4000)
- `temperature`: Response randomness (default: 0.1 for consistent parsing)

---

## Optional Configuration Sections

### [api] - REST API Server (Optional)

Configure the API server.

```ini
[api]
host = 127.0.0.1
port = 8000
```
- `host`: Hostname to bind the API server (default: 127.0.0.1)
- `port`: Port for the API server (default: 8000)

---

### [hashing] - File Hashing (Optional)

Configure hashing behavior for large files.

```ini
[hashing]
# Either set chunk_size_bytes directly, or chunk_size_mib (MiB)
# chunk_size_bytes = 1048576
chunk_size_mib = 1
```
- `chunk_size_bytes`: Read chunk size in bytes used when hashing large files
- `chunk_size_mib`: Convenience option; multiplied by 1,048,576 to derive bytes

Defaults to 1 MiB if not specified.

---

## Complete Configuration Example

```ini
# Core Services Configuration (lowercase section names preferred)
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

# LLM Configuration - Choose one service
[llm]
service = ollama  # Options: ollama, openai, anthropic

# Ollama Configuration (Default - Free local LLM)
[ollama]
model = qwen3:14b
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

# Optional API Server
[api]
host = 127.0.0.1
port = 8000
```

---

## Environment Variables

You can override any configuration value using environment variables. This is especially useful for sensitive data like API keys.

### Environment Variable Format
Environment variables follow the pattern: `SYNC2NAS_<SECTION>_<KEY>`

### Common Environment Variables
```bash
# LLM Service Selection
export SYNC2NAS_LLM_SERVICE=openai

# API Keys (recommended for production)
export SYNC2NAS_OPENAI_API_KEY=your_openai_key
export SYNC2NAS_ANTHROPIC_API_KEY=your_anthropic_key
export SYNC2NAS_TMDB_API_KEY=your_tmdb_key

# Ollama Configuration
export SYNC2NAS_OLLAMA_HOST=http://localhost:11434
export SYNC2NAS_OLLAMA_MODEL=qwen3:14b

# Database Configuration
export SYNC2NAS_DATABASE_TYPE=sqlite
export SYNC2NAS_SQLITE_DB_FILE=./database/sync2nas.db
```

**For complete environment variable documentation, see:** [Environment Variables Guide](environment_variables.md)

---

## Configuration Validation

Sync2NAS includes built-in configuration validation with intelligent error suggestions:

```bash
# Validate your entire configuration
python sync2nas.py config-check

# Check specific LLM service
python sync2nas.py config-check --service openai

# Get detailed suggestions
python sync2nas.py config-check --verbose
```

The validator provides:
- **Typo detection**: Suggests corrections for common misspellings
- **Missing configuration**: Lists exactly what needs to be added
- **Format validation**: Checks API key formats, URLs, etc.
- **Intelligent suggestions**: Context-aware recommendations

**Example validation output:**
```
❌ Configuration Issues Found:
  • [openai] api_key: Required key missing
  • Suggestion: Get your API key from https://platform.openai.com/api-keys

💡 Intelligent Suggestions:
  • Section '[OpenAI]' should be '[openai]' (lowercase preferred)
  • Use environment variable: SYNC2NAS_OPENAI_API_KEY=your_key
```

---

## Security Best Practices

- **SSH keys:** Use SSH keys for SFTP, not passwords. Set permissions to 600
- **API keys:** Never commit API keys to version control. Use environment variables for sensitive data
- **Database:** Use strong passwords for PostgreSQL. Restrict access to the database file for SQLite
- **Environment variables:** Use `SYNC2NAS_*` environment variables for production deployments

---

## Troubleshooting

### Quick Diagnosis
```bash
# Check configuration health
python sync2nas.py config-check

# Test specific service
python sync2nas.py config-check --service ollama
```

### Common Issues
- **Case sensitivity:** Use lowercase section names (`[openai]` not `[OpenAI]`)
- **Missing sections:** Each selected LLM service needs its configuration section
- **Invalid API keys:** Check format and validity
- **Ollama not running:** Ensure Ollama service is started and models are installed

**For detailed troubleshooting, see:** [Configuration Troubleshooting Guide](configuration_troubleshooting.md)

---

## Migration Notes

**From older versions:**
- Use lowercase section names for consistency
- The `[llm]` section is now required to select LLM backend
- Old `[OpenAI]` sections should be renamed to `[openai]`
- Environment variables now use `SYNC2NAS_` prefix

---

## Additional Resources

- **[Environment Variables Guide](environment_variables.md)**: Complete environment variable reference
- **[Configuration Troubleshooting](configuration_troubleshooting.md)**: Detailed troubleshooting guide
- **[Database Backends Guide](database_backends.md)**: Database setup and configuration
- **[Main README](../README.md)**: General usage and setup information

---

## Tips

- Use `--config` to specify a custom config file
- Use `-v` or `-vv` for more verbose logging
- Use `--dry-run` to preview actions without making changes
- Always backup your database before making major changes
- Test configuration with `config-check` after making changes
