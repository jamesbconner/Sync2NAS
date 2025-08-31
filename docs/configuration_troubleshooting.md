# Configuration Troubleshooting Guide

This guide helps you resolve common configuration issues with Sync2NAS, particularly related to LLM service configuration.

## Quick Diagnosis

### Configuration Health Check

The fastest way to diagnose configuration issues is using the built-in validator:

```bash
# Check all configuration
python sync2nas.py config-check

# Check specific service
python sync2nas.py config-check --service openai
python sync2nas.py config-check --service anthropic
python sync2nas.py config-check --service ollama

# Verbose output with suggestions
python sync2nas.py config-check --verbose
```

## Common Configuration Issues

### 1. Case Sensitivity Problems

**Problem:** Configuration sections not recognized due to case differences.

**Symptoms:**
- "Missing configuration section" errors
- LLM service fails to initialize
- Settings appear to be ignored

**Solution:**
Use lowercase section names consistently:

```ini
# ✅ Correct (lowercase preferred)
[openai]
api_key = your_key_here

[ollama]
model = gemma3:12b

[anthropic]
api_key = your_key_here

# ❌ Avoid (mixed case)
[OpenAI]
[OLLAMA]
[Anthropic]
```

**Note:** The system accepts both formats but prefers lowercase. Mixed case may cause confusion.

### 2. Typos in Section Names

**Problem:** Common misspellings in configuration sections.

**Common Typos:**
- `[olama]` → should be `[ollama]`
- `[opena]` → should be `[openai]`
- `[anthropi]` → should be `[anthropic]`

**Automatic Detection:**
The system detects typos and provides suggestions:

```
❌ Configuration Issues:
  • Section '[olama]' might be '[ollama]'
  • Section '[OpenAI]' should be '[openai]' (lowercase preferred)
```

### 3. Missing Required Configuration

**Problem:** Required configuration keys are missing for selected LLM service.

#### OpenAI Service Missing Configuration

```ini
[llm]
service = openai

# ❌ Missing [openai] section entirely
```

**Solution:**
```ini
[llm]
service = openai

[openai]
api_key = your_openai_api_key_here
model = gpt-4
max_tokens = 4000
temperature = 0.1
```

#### Ollama Service Missing Configuration

```ini
[llm]
service = ollama

# ❌ Missing [ollama] section
```

**Solution:**
```ini
[llm]
service = ollama

[ollama]
model = gemma3:12b
host = http://localhost:11434
timeout = 30
```

### 4. Invalid Configuration Values

**Problem:** Configuration values have incorrect format or invalid content.

#### Invalid API Key Formats

```ini
# ❌ Invalid OpenAI API key format
[openai]
api_key = invalid_key

# ❌ Invalid Anthropic API key format
[anthropic]
api_key = sk-wrong-format
```

**Solution:**
```ini
# ✅ Valid OpenAI API key (starts with sk-, 51+ characters)
[openai]
api_key = sk-1234567890abcdef1234567890abcdef1234567890abcdef

# ✅ Valid Anthropic API key (starts with sk-ant-, 40+ characters)
[anthropic]
api_key = sk-ant-1234567890abcdef1234567890abcdef12345678
```

#### Invalid Model Names

```ini
# ❌ Common model name mistakes
[openai]
model = gpt4  # Should be gpt-4

[anthropic]
model = claude3  # Should be claude-3-sonnet-20240229

[ollama]
model = llama  # Should include tag: llama2:7b
```

**Solution:**
```ini
# ✅ Correct model names
[openai]
model = gpt-4  # or gpt-3.5-turbo

[anthropic]
model = claude-3-sonnet-20240229  # or claude-3-haiku-20240307

[ollama]
model = gemma3:12b  # or llama2:7b, mistral:7b
```

#### Invalid URLs

```ini
# ❌ Missing protocol
[ollama]
host = localhost:11434

# ❌ Wrong port
[ollama]
host = http://localhost:8080
```

**Solution:**
```ini
# ✅ Correct Ollama host
[ollama]
host = http://localhost:11434
```

### 5. Environment Variable Issues

**Problem:** Environment variables not overriding configuration correctly.

#### Incorrect Environment Variable Names

```bash
# ❌ Wrong format
export OPENAI_API_KEY=your_key
export OLLAMA_MODEL=gemma3:12b

# ✅ Correct format
export SYNC2NAS_OPENAI_API_KEY=your_key
export SYNC2NAS_OLLAMA_MODEL=gemma3:12b
```

#### Environment Variable Precedence

Environment variables **always** override config file values:

```ini
# Config file
[openai]
api_key = old_key
model = gpt-3.5-turbo
```

```bash
# Environment override
export SYNC2NAS_OPENAI_API_KEY=new_key
# Result: Uses new_key, keeps gpt-3.5-turbo from config
```

## Service-Specific Troubleshooting

### OpenAI Configuration

#### Getting API Keys
1. Visit [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create account or sign in
3. Generate new API key
4. Copy key to configuration

#### Common Issues
- **Invalid API key**: Check format (starts with `sk-`, 51+ characters)
- **Insufficient credits**: Verify account has available credits
- **Model access**: Ensure you have access to the specified model

#### Testing OpenAI Configuration
```bash
# Test OpenAI connectivity
python sync2nas.py config-check --service openai

# Test with verbose output
python sync2nas.py config-check --service openai --verbose
```

### Anthropic Configuration

#### Getting API Keys
1. Visit [Anthropic Console](https://console.anthropic.com/)
2. Create account or sign in
3. Generate API key
4. Copy key to configuration

#### Common Issues
- **Invalid API key**: Check format (starts with `sk-ant-`, 40+ characters)
- **Model availability**: Verify model name is correct
- **Rate limits**: Check if you're hitting API rate limits

#### Testing Anthropic Configuration
```bash
# Test Anthropic connectivity
python sync2nas.py config-check --service anthropic
```

### Ollama Configuration

#### Installing Ollama
1. Download from [Ollama.ai](https://ollama.ai/)
2. Install and start the service
3. Pull required models

```bash
# Install a model
ollama pull gemma3:12b

# List installed models
ollama list

# Check Ollama status
curl http://localhost:11434/api/version
```

#### Common Issues
- **Service not running**: Start Ollama service
- **Model not found**: Pull the model with `ollama pull model_name`
- **Connection refused**: Check if Ollama is running on correct port
- **Wrong host URL**: Ensure host includes protocol (`http://`)

#### Testing Ollama Configuration
```bash
# Test Ollama connectivity
python sync2nas.py config-check --service ollama

# Test Ollama directly
curl http://localhost:11434/api/version
```

## Configuration Templates

### Minimal Working Configuration

```ini
# Minimal configuration for Ollama (recommended for beginners)
[database]
type = sqlite

[sqlite]
db_file = ./database/sync2nas.db

[tmdb]
api_key = your_tmdb_api_key_here

[llm]
service = ollama

[ollama]
model = gemma3:12b
host = http://localhost:11434
```

### Production Configuration with Environment Variables

```ini
# Production config (sensitive data via environment variables)
[database]
type = sqlite

[sqlite]
db_file = ./database/sync2nas.db

[tmdb]
# API key provided via SYNC2NAS_TMDB_API_KEY environment variable

[llm]
service = openai

[openai]
# API key provided via SYNC2NAS_OPENAI_API_KEY environment variable
model = gpt-4
max_tokens = 4000
temperature = 0.1
```

```bash
# Environment variables for production
export SYNC2NAS_TMDB_API_KEY=your_tmdb_key
export SYNC2NAS_OPENAI_API_KEY=your_openai_key
```

## Advanced Troubleshooting

### Configuration Validation Errors

The system provides detailed validation with suggestions:

```bash
python sync2nas.py config-check --verbose
```

**Example output:**
```
🚨 Configuration Issues Found:
  • [openai] api_key: Required key missing
  • [ollama] model: Invalid model format 'llama' (should be 'llama2:7b')

💡 Intelligent Suggestions:
  • Get OpenAI API key from: https://platform.openai.com/api-keys
  • Install Ollama model: ollama pull llama2:7b
  • Use environment variable: SYNC2NAS_OPENAI_API_KEY=your_key

🔧 Potential Typos Detected:
  • Section '[OpenAI]' should be '[openai]' (lowercase preferred)
  • Key 'api_ky' might be 'api_key'
```

### Debugging Configuration Loading

Enable verbose logging to see configuration loading process:

```bash
# Debug configuration loading
python sync2nas.py -vv config-check

# Debug with specific service
python sync2nas.py -vv config-check --service openai
```

### Configuration File Locations

The system looks for configuration files in this order:
1. Path specified with `--config` flag
2. `./config/sync2nas_config.ini` (default)
3. Environment variables (always override file values)

### Resetting Configuration

To start fresh:
1. Copy `config/sync2nas_config.ini.example` to `config/sync2nas_config.ini`
2. Edit with your specific settings
3. Test with `python sync2nas.py config-check`

## Getting Help

If you're still experiencing issues:

1. **Run configuration check**: `python sync2nas.py config-check --verbose`
2. **Check logs**: Use `-v` or `-vv` flags for detailed logging
3. **Verify services**: Test external services (Ollama, API connectivity) independently
4. **Review examples**: Compare your config with working examples in this guide
5. **Environment variables**: Try using environment variables to isolate config file issues

For additional support, include the output of `python sync2nas.py config-check --verbose` when reporting issues.