# LLM Architecture - LangChain Integration

## Overview

Sync2NAS uses LangChain for all LLM operations, providing a robust, scalable, and maintainable architecture for AI-powered filename parsing, show matching, and content generation. The system uses JSON-optimized models with native structured output for reliable, type-safe responses without requiring response cleaning or field translation workarounds.

## Architecture Components

### Core Components

- **LangChain Chains**: Composable processing pipelines using LCEL (LangChain Expression Language)
- **Native Structured Output**: Direct Pydantic object generation using `with_structured_output()`
- **JSON-Optimized Models**: Models specifically trained for JSON output (ministral-3:14b, qwen2.5:7b, llama3.2:3b)
- **Pydantic Schemas**: Type-safe structured output for all LLM responses
- **Singleton Pattern**: Efficient chain reuse across the application
- **Caching Layer**: Optional SQLite-based caching for improved performance
- **Tracing Integration**: Optional LangSmith integration for debugging and monitoring

### Chain Types

#### 1. Filename Parser Chain
- **Purpose**: Extract show metadata from filenames
- **Input**: Raw filename string
- **Output**: `ParsedFilename` Pydantic model with show name, season, episode, CRC32, confidence, and reasoning
- **Implementation**: System/user prompt split with native structured output
- **Features**: Direct Pydantic validation, confidence scoring, fallback handling

#### 2. Batch Filename Parser Chain
- **Purpose**: Process multiple filenames efficiently
- **Input**: List of filename strings
- **Output**: List of `ParsedFilename` models
- **Features**: Parallel processing (max_concurrency=5), order preservation, batch optimization

#### 3. Short Name Suggester Chain
- **Purpose**: Generate shortened names for directories and files
- **Input**: Long name and maximum length
- **Output**: Shortened string respecting character restrictions
- **Features**: Type-aware suggestions (directory vs filename), length compliance, character sanitization

#### 4. Show Matcher Chain
- **Purpose**: Select best TMDB match from candidates
- **Input**: Show name and TMDB candidate list
- **Output**: `ShowMatch` Pydantic model with TMDB ID, show name, confidence, and reasoning
- **Features**: Candidate formatting, confidence scoring, intelligent selection

## Configuration

### LLM Service Selection

```ini
[llm]
service = ollama  # Options: ollama, openai, anthropic
```

### Ollama Configuration (Recommended)

```ini
[ollama]
host = http://localhost:11434
model = ministral-3:14b  # JSON-optimized model (recommended)
temperature = 1.0
```

**JSON-Optimized Models** (recommended for best results):
- `ministral-3:14b` - Default, excellent JSON output (recommended)
- `ministral-3:8b` - Lighter weight alternative with excellent JSON output
- `qwen2.5:7b` - Alternative with strong JSON capabilities
- `llama3.2:3b` - Compact option

**Legacy Models** (may require additional handling):
- `llama3.2` - Works but not optimized for JSON
- `llama2` - Older model, less reliable JSON output

### Caching Configuration

```ini
[llm]
enable_cache = true
cache_path = .langchain_cache.db
```

### Tracing Configuration

```ini
[llm]
enable_tracing = true
langsmith_api_key = your_api_key_here
langsmith_project = sync2nas
```

### Environment Variables

All configuration can be overridden via environment variables:

```bash
export SYNC2NAS_LLM_ENABLE_CACHE=true
export SYNC2NAS_LLM_CACHE_PATH=.langchain_cache.db
export SYNC2NAS_LLM_ENABLE_TRACING=true
export SYNC2NAS_LLM_LANGSMITH_API_KEY=your_key
export SYNC2NAS_LLM_LANGSMITH_PROJECT=sync2nas
```

## Usage Patterns

### Simplified Chain Implementation

The new architecture uses native structured output for clean, maintainable code:

```python
from services.llm.chains import create_filename_parser
from services.llm_factory import create_llm_service
from utils.sync2nas_config import load_configuration

# Create LLM service
config = load_configuration()
llm = create_llm_service(config)

# Create parser chain with native structured output
parser = create_filename_parser(llm)

# Parse filename - returns Pydantic object directly
result = parser.invoke({"filename": "Show.Name.S01E05.1080p.mkv"})
print(f"Show: {result.show_name}, S{result.season}E{result.episode}")
print(f"Confidence: {result.confidence:.2f}")
```

### Chain Composition Pattern

All chains follow the simplified LCEL pattern:

```python
# Filename parser: prompt | structured_llm
prompt = create_chat_prompt_from_files(
    system_prompt_name="system_parse_filename_v1",
    user_prompt_name="user_parse_filename_v1",
    input_variables=["filename"]
)
structured_llm = llm.with_structured_output(ParsedFilename)
chain = prompt | structured_llm

# Show matcher: format_candidates | prompt | structured_llm
chain = (
    RunnableLambda(format_candidates)
    | prompt
    | structured_llm
)
```

### Service-Based Usage (Recommended)

Use the LLMChainService for managed chain instances:

```python
from services.llm_chain_service import LLMChainService

# Create service with LLM instance
llm_chains = LLMChainService(llm)

# Parse single filename
result = llm_chains.parse_filename("Show.Name.S01E05.mkv")

# Parse multiple filenames
results = llm_chains.parse_filenames(["file1.mkv", "file2.mkv"])

# Match show
match = llm_chains.match_show("Attack on Titan", tmdb_candidates)
```

### Batch Processing

```python
from services.llm.chains import parse_filenames

# Process multiple files efficiently
filenames = ["Show1.S01E01.mkv", "Show2.S02E03.mkv", "Show3.S01E12.mkv"]
results = parse_filenames(filenames)

for filename, result in zip(filenames, results):
    print(f"{filename} -> {result.show_name} S{result.season}E{result.episode}")
```

### Integration with Existing Code

The chains integrate seamlessly with existing utilities:

```python
# utils/filename_parser.py uses chains internally
from utils.filename_parser import parse_filename

# Returns dict for backward compatibility
metadata = parse_filename("Show.Name.S01E05.mkv")
print(metadata["show_name"])  # Works with existing code

# utils/show_adder.py uses chains for show matching
from utils.show_adder import add_show_interactively

# Uses LangChain chains when use_llm=True
add_show_interactively(
    show_name="Attack on Titan",
    tmdb_id=None,
    use_llm=True,
    # ... other parameters
)
```

## Benefits of JSON-Optimized Models

### Reliability
- **Direct Pydantic Objects**: No JSON parsing or cleaning required
- **Type Safety**: Automatic validation through Pydantic
- **Consistent Output**: Models trained specifically for JSON generation

### Simplicity
- **Removed Workarounds**: ~200 lines of response cleaning code eliminated
- **Native Structured Output**: Uses LangChain's `with_structured_output()` method
- **No Field Translation**: Models use correct field names (crc32, not crc_hash)

### Performance
- **Fewer Processing Steps**: Direct object creation without intermediate parsing
- **Better Error Handling**: Pydantic validation errors are clear and actionable
- **Reduced Latency**: No post-processing overhead

### Example Comparison

**Old Approach (SFT Model)**:
```python
# Complex workaround with response cleaning
response = llm.invoke(prompt)
cleaned = _clean_llm_response(response.content)
parsed = json.loads(cleaned)
if "crc_hash" in parsed:
    parsed["crc32"] = parsed.pop("crc_hash")  # Field translation
result = ParsedFilename(**parsed)
```

**New Approach (JSON-Optimized Model)**:
```python
# Simple, direct structured output
structured_llm = llm.with_structured_output(ParsedFilename)
result = (prompt | structured_llm).invoke({"filename": filename})
```

## Performance Optimizations

### Singleton Pattern

Chains are created once and reused throughout the application lifecycle:

```python
# LLMChainService manages singleton chain instances
llm_chains = LLMChainService(llm)

# First call creates the chain
result1 = llm_chains.parse_filename("file1.mkv")

# Subsequent calls reuse the same chain instance
result2 = llm_chains.parse_filename("file2.mkv")  # No chain recreation overhead
```

### Native Structured Output Benefits

JSON-optimized models with native structured output provide:

1. **Faster Processing**: No post-processing or response cleaning
2. **Lower Memory**: Direct Pydantic object creation
3. **Better Reliability**: Fewer failure points in the pipeline
4. **Cleaner Code**: Simpler implementation, easier to maintain

### Caching

When enabled, LLM responses are cached to avoid redundant API calls:

```python
# First call makes LLM request and caches result
result1 = parse_filename("Show.Name.S01E01.mkv")

# Second call with same input returns cached result
result2 = parse_filename("Show.Name.S01E01.mkv")  # No LLM call
```

### Batch Processing

Multiple items are processed in parallel with controlled concurrency:

```python
# Processes up to 5 items concurrently
results = parse_filenames(large_filename_list)
```

## Error Handling

### Graceful Degradation

The system maintains backward compatibility with regex fallbacks:

1. **LangChain Chain Execution**: Primary processing method
2. **Regex Fallback**: Used when LLM fails or confidence is too low
3. **Error Logging**: Comprehensive logging for debugging

### Exception Propagation

Chain errors are properly propagated with context:

```python
try:
    result = parse_filename("invalid_filename")
except Exception as e:
    logger.error(f"Filename parsing failed: {e}")
    # Fallback to regex parsing
```

## Monitoring and Debugging

### LangSmith Integration

When enabled, all chain executions are traced:

- **Chain Execution Flow**: Step-by-step execution visualization
- **Input/Output Tracking**: Complete request/response logging
- **Performance Metrics**: Timing and token usage statistics
- **Error Analysis**: Detailed error context and stack traces

### Logging

Comprehensive logging at multiple levels:

```python
import logging
logging.getLogger("services.llm.chains").setLevel(logging.DEBUG)
```

## Future Extensibility

The LangChain architecture provides foundations for:

### Conversation Memory
```python
# services/memory/ - Future conversation context
from services.memory import ConversationMemory
```

### Vector Stores
```python
# services/vectorstore/ - Future show embeddings
from services.vectorstore import ShowEmbeddings
```

### Tool Integration
```python
# services/tools/ - Future MCP tools integration
from services.tools import MCPTools
```

## Troubleshooting

### Ollama Package Issues

If you encounter errors related to Ollama LLM creation:

#### ImportError: No module named 'langchain_ollama'

**Problem**: The new dedicated Ollama package is not installed.

**Solution**: Install the required package:
```bash
pip install langchain-ollama
```

**Background**: As of LangChain 0.3.1, the `Ollama` class from `langchain_community.llms` is deprecated. The new `langchain-ollama` package provides the `ChatOllama` class with better performance, structured output support, and future compatibility.

#### Deprecation Warnings

If you see warnings like:
```
LangChainDeprecationWarning: The class `Ollama` was deprecated in LangChain 0.3.1
```

**Problem**: Your installation is using the old deprecated Ollama class.

**Solution**: Ensure you have the latest version of Sync2NAS and the `langchain-ollama` package installed:
```bash
pip install -U langchain-ollama
```

#### Configuration Compatibility

All existing Ollama configuration continues to work:

```ini
[ollama]
host = http://localhost:11434
model = ministral-3:14b
temperature = 1.0
num_ctx = 8192  # Optional: Context window size (defaults to model's default if not specified)
```

The new `ChatOllama` class uses the same parameters as the deprecated `Ollama` class and provides enhanced support for structured output with JSON-optimized models.

**Note on `num_ctx`**: This parameter is optional. If not specified, Ollama uses the model's default context window (typically 2048-8192 tokens depending on the model). Only set this if you need to override the default for your specific use case.

### General LLM Issues

#### Service Creation Failures

Check your configuration and ensure the required packages are installed:

- **Ollama**: `pip install langchain-ollama`
- **OpenAI**: `pip install langchain-openai`
- **Anthropic**: `pip install langchain-anthropic`

#### Performance Issues

1. **Enable Caching**: Set `enable_cache = true` in your `[llm]` configuration
2. **Batch Processing**: Use `parse_filenames()` for multiple files
3. **Monitor Resources**: Check memory usage and API rate limits

#### Connection Issues

For Ollama specifically:
1. **Verify Server**: Ensure Ollama server is running on the configured host
2. **Check Model**: Verify the specified model is available
3. **Network Access**: Ensure network connectivity to the Ollama server

## Migration Notes

### From Legacy LLM Services

The new LangChain architecture maintains backward compatibility:

- **Configuration**: Existing config files work without changes
- **API**: Function signatures remain the same
- **Return Types**: Converted to dicts for compatibility
- **Error Handling**: Same fallback behavior

### Testing

All chains include comprehensive test coverage:

- **Unit Tests**: Individual chain functionality
- **Property Tests**: Universal correctness properties
- **Integration Tests**: End-to-end workflows
- **Mock Testing**: No actual LLM calls during testing

## Best Practices

### Configuration Management

1. **Use Environment Variables**: For sensitive data and deployment-specific settings
2. **Enable Caching**: For better performance in production
3. **Configure Tracing**: For debugging and monitoring in development

### Performance Optimization

1. **Batch Processing**: Use `parse_filenames()` for multiple items
2. **Singleton Reuse**: Don't reset chains unnecessarily
3. **Cache Management**: Monitor cache size and performance

### Error Handling

1. **Graceful Degradation**: Always provide fallback mechanisms
2. **Comprehensive Logging**: Log errors with sufficient context
3. **User Feedback**: Provide clear error messages to users

### Development Workflow

1. **Test with Mocks**: Use proper mocking to avoid LLM calls during testing
2. **Property Testing**: Validate universal properties with Hypothesis
3. **Integration Testing**: Test end-to-end workflows with real chains