# Environment Variables Guide

Sync2NAS supports environment variable overrides for all configuration settings. This is particularly useful for:
- Secure API key management
- Deployment-specific configurations
- Containerized environments
- CI/CD pipelines

## Environment Variable Format

All environment variables follow the pattern:
```
SYNC2NAS_<SECTION>_<KEY>
```

Where:
- `SYNC2NAS` is the prefix
- `<SECTION>` is the configuration section name (uppercase)
- `<KEY>` is the configuration key name (uppercase)

## Precedence Rules

Environment variables **always override** configuration file values:

1. **Environment Variable** (highest priority)
2. **Configuration File** (lower priority)

This allows you to keep sensitive data out of configuration files while maintaining default values.

## Supported Environment Variables

### LLM Service Configuration

#### Service Selection
```bash
# Override which LLM service to use
export SYNC2NAS_LLM_SERVICE=openai        # Options: ollama, openai, anthropic
```

#### OpenAI Configuration
```bash
export SYNC2NAS_OPENAI_API_KEY=sk-your-openai-key-here
export SYNC2NAS_OPENAI_MODEL=gpt-4                      # Default: gpt-4
export SYNC2NAS_OPENAI_MAX_TOKENS=4000                  # Default: 4000
export SYNC2NAS_OPENAI_TEMPERATURE=0.1                  # Default: 0.1
```

#### Anthropic Configuration
```bash
export SYNC2NAS_ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
export SYNC2NAS_ANTHROPIC_MODEL=claude-3-sonnet-20240229    # Default model
export SYNC2NAS_ANTHROPIC_MAX_TOKENS=4000                   # Default: 4000
export SYNC2NAS_ANTHROPIC_TEMPERATURE=0.1                   # Default: 0.1
```

#### Ollama Configuration
```bash
export SYNC2NAS_OLLAMA_HOST=http://localhost:11434     # Default: http://localhost:11434
export SYNC2NAS_OLLAMA_MODEL=gemma3:12b                # Default: gemma3:12b
export SYNC2NAS_OLLAMA_TIMEOUT=30                      # Default: 30 seconds
export SYNC2NAS_OLLAMA_NUM_CTX=4096                    # Context window size
```

### Core Service Configuration

#### Database Configuration
```bash
export SYNC2NAS_DATABASE_TYPE=sqlite                   # Options: sqlite, postgresql, milvus

# SQLite specific
export SYNC2NAS_SQLITE_DB_FILE=./database/sync2nas.db

# PostgreSQL specific
export SYNC2NAS_POSTGRESQL_HOST=localhost
export SYNC2NAS_POSTGRESQL_PORT=5432
export SYNC2NAS_POSTGRESQL_DATABASE=sync2nas
export SYNC2NAS_POSTGRESQL_USER=postgres
export SYNC2NAS_POSTGRESQL_PASSWORD=your_password

# Milvus specific
export SYNC2NAS_MILVUS_HOST=localhost
export SYNC2NAS_MILVUS_PORT=19530
```

#### SFTP Configuration
```bash
export SYNC2NAS_SFTP_HOST=your.sftpserver.com
export SYNC2NAS_SFTP_PORT=22
export SYNC2NAS_SFTP_USERNAME=your_username
export SYNC2NAS_SFTP_SSH_KEY_PATH=./ssh/your_key_rsa
export SYNC2NAS_SFTP_PATHS="/path1/,/path2/"           # Comma-separated paths
```

#### TMDB Configuration
```bash
export SYNC2NAS_TMDB_API_KEY=your_tmdb_api_key_here
```

#### File Transfer Configuration
```bash
export SYNC2NAS_TRANSFERS_INCOMING=./incoming
export SYNC2NAS_ROUTING_ANIME_TV_PATH=/path/to/anime/
```

## Usage Examples

### Example 1: Secure Production Deployment

**Configuration file** (`config/sync2nas_config.ini`):
```ini
# Production config - no sensitive data
[database]
type = sqlite

[sqlite]
db_file = ./database/sync2nas.db

[llm]
service = openai

[openai]
model = gpt-4
max_tokens = 4000
temperature = 0.1
# API key provided via environment variable

[tmdb]
# API key provided via environment variable
```

**Environment variables**:
```bash
# Sensitive data via environment variables
export SYNC2NAS_OPENAI_API_KEY=sk-your-secret-openai-key
export SYNC2NAS_TMDB_API_KEY=your-secret-tmdb-key
```

### Example 2: Development vs Production

**Shared config file**:
```ini
[llm]
service = ollama

[ollama]
model = gemma3:12b
host = http://localhost:11434
```

**Development environment**:
```bash
# Use local Ollama for development
export SYNC2NAS_LLM_SERVICE=ollama
export SYNC2NAS_OLLAMA_HOST=http://localhost:11434
```

**Production environment**:
```bash
# Use OpenAI for production
export SYNC2NAS_LLM_SERVICE=openai
export SYNC2NAS_OPENAI_API_KEY=sk-production-key-here
```

### Example 3: Docker Container Deployment

**Dockerfile**:
```dockerfile
FROM python:3.12

# Copy application
COPY . /app
WORKDIR /app

# Install dependencies
RUN pip install -r requirements.txt

# Configuration will be provided via environment variables
CMD ["python", "sync2nas.py", "route-files", "--auto-add"]
```

**Docker run with environment variables**:
```bash
docker run -d \
  -e SYNC2NAS_LLM_SERVICE=openai \
  -e SYNC2NAS_OPENAI_API_KEY=sk-your-key \
  -e SYNC2NAS_TMDB_API_KEY=your-tmdb-key \
  -e SYNC2NAS_DATABASE_TYPE=sqlite \
  -e SYNC2NAS_SQLITE_DB_FILE=/data/sync2nas.db \
  -v /host/data:/data \
  sync2nas:latest
```

### Example 4: CI/CD Pipeline

**GitHub Actions workflow**:
```yaml
name: Test Sync2NAS
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    env:
      SYNC2NAS_LLM_SERVICE: ollama
      SYNC2NAS_OLLAMA_HOST: http://localhost:11434
      SYNC2NAS_DATABASE_TYPE: sqlite
      SYNC2NAS_SQLITE_DB_FILE: ./test.db
      SYNC2NAS_TMDB_API_KEY: ${{ secrets.TMDB_API_KEY }}
    
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest
```

## Environment Variable Validation

Environment variables are validated just like configuration file values:

```bash
# Test environment variable configuration
export SYNC2NAS_OPENAI_API_KEY=invalid_key
python sync2nas.py config-check

# Output:
# ❌ Configuration Issues:
#   • [openai] api_key: API key format invalid
#   • Suggestion: API key should start with "sk-" and be 51+ characters
```

## Best Practices

### Security
1. **Never commit API keys** to version control
2. **Use environment variables** for all sensitive data
3. **Rotate keys regularly** and update environment variables
4. **Use secrets management** in production (AWS Secrets Manager, Azure Key Vault, etc.)

### Organization
1. **Group related variables** together in deployment scripts
2. **Document required variables** for each deployment environment
3. **Use consistent naming** following the `SYNC2NAS_<SECTION>_<KEY>` pattern
4. **Validate configuration** after setting environment variables

### Development
1. **Use `.env` files** for local development (with proper `.gitignore`)
2. **Provide example values** in documentation
3. **Test with environment variables** to ensure they work correctly
4. **Use different values** for development vs production

## Troubleshooting Environment Variables

### Common Issues

#### Environment Variable Not Taking Effect
```bash
# Check if variable is set
echo $SYNC2NAS_OPENAI_API_KEY

# Verify configuration loading
python sync2nas.py config-check --verbose
```

#### Wrong Variable Name Format
```bash
# ❌ Wrong format
export OPENAI_API_KEY=your_key

# ✅ Correct format
export SYNC2NAS_OPENAI_API_KEY=your_key
```

#### Case Sensitivity
Environment variable names are case-sensitive and should be uppercase:
```bash
# ❌ Wrong case
export sync2nas_openai_api_key=your_key

# ✅ Correct case
export SYNC2NAS_OPENAI_API_KEY=your_key
```

### Debugging Environment Variables

Enable verbose logging to see environment variable processing:

```bash
# Debug environment variable loading
python sync2nas.py -vv config-check

# Check specific service with environment variables
export SYNC2NAS_LLM_SERVICE=openai
export SYNC2NAS_OPENAI_API_KEY=your_key
python sync2nas.py -vv config-check --service openai
```

## Complete Environment Variable Reference

| Environment Variable | Config Section | Config Key | Description | Example |
|---------------------|----------------|------------|-------------|---------|
| `SYNC2NAS_LLM_SERVICE` | `[llm]` | `service` | LLM service selection | `ollama` |
| `SYNC2NAS_OPENAI_API_KEY` | `[openai]` | `api_key` | OpenAI API key | `sk-...` |
| `SYNC2NAS_OPENAI_MODEL` | `[openai]` | `model` | OpenAI model name | `gpt-4` |
| `SYNC2NAS_OPENAI_MAX_TOKENS` | `[openai]` | `max_tokens` | Max tokens per request | `4000` |
| `SYNC2NAS_OPENAI_TEMPERATURE` | `[openai]` | `temperature` | Response randomness | `0.1` |
| `SYNC2NAS_ANTHROPIC_API_KEY` | `[anthropic]` | `api_key` | Anthropic API key | `sk-ant-...` |
| `SYNC2NAS_ANTHROPIC_MODEL` | `[anthropic]` | `model` | Anthropic model name | `claude-3-sonnet-20240229` |
| `SYNC2NAS_ANTHROPIC_MAX_TOKENS` | `[anthropic]` | `max_tokens` | Max tokens per request | `4000` |
| `SYNC2NAS_ANTHROPIC_TEMPERATURE` | `[anthropic]` | `temperature` | Response randomness | `0.1` |
| `SYNC2NAS_OLLAMA_HOST` | `[ollama]` | `host` | Ollama server URL | `http://localhost:11434` |
| `SYNC2NAS_OLLAMA_MODEL` | `[ollama]` | `model` | Ollama model name | `gemma3:12b` |
| `SYNC2NAS_OLLAMA_TIMEOUT` | `[ollama]` | `timeout` | Request timeout (seconds) | `30` |
| `SYNC2NAS_DATABASE_TYPE` | `[database]` | `type` | Database backend | `sqlite` |
| `SYNC2NAS_SQLITE_DB_FILE` | `[sqlite]` | `db_file` | SQLite database file | `./database/sync2nas.db` |
| `SYNC2NAS_TMDB_API_KEY` | `[tmdb]` | `api_key` | TMDB API key | `your_tmdb_key` |
| `SYNC2NAS_SFTP_HOST` | `[sftp]` | `host` | SFTP server hostname | `your.server.com` |
| `SYNC2NAS_SFTP_PORT` | `[sftp]` | `port` | SFTP server port | `22` |
| `SYNC2NAS_SFTP_USERNAME` | `[sftp]` | `username` | SFTP username | `your_user` |
| `SYNC2NAS_SFTP_SSH_KEY_PATH` | `[sftp]` | `ssh_key_path` | SSH private key path | `./ssh/key_rsa` |
| `SYNC2NAS_TRANSFERS_INCOMING` | `[transfers]` | `incoming` | Incoming files directory | `./incoming` |
| `SYNC2NAS_ROUTING_ANIME_TV_PATH` | `[routing]` | `anime_tv_path` | Media library path | `/path/to/anime/` |

This comprehensive environment variable support makes Sync2NAS highly configurable and suitable for various deployment scenarios while maintaining security best practices.