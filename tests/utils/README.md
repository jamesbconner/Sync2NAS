# Sync2NAS Test Infrastructure Documentation

This directory contains the enhanced test infrastructure for the Sync2NAS project, providing standardized test utilities, base classes, and patterns for comprehensive testing.

## Overview

The test infrastructure addresses the requirements for:
- Standardized test configuration setup (Requirements 6.1, 6.2, 6.3, 6.4)
- Backward compatibility for existing tests (Requirements 7.1, 7.2, 7.3, 7.4)
- Test environment configuration isolation
- Mock service creation with predictable behavior
- CLI context management for Click command testing

## Core Components

### 1. Test Base Classes (`test_base.py`)

#### BaseTestCase
The foundational test class that provides:
- Standardized test configuration creation
- Mock service creation and management
- Temporary directory and file management
- CLI context setup for Click commands
- Resource cleanup and isolation

```python
from tests.utils.test_base import BaseTestCase

class MyTestCase(BaseTestCase):
    def test_something(self):
        config = self.get_test_config()
        db_service = self.create_test_db_service(config)
        # ... test implementation
```

#### Specialized Test Classes
- **CLITestCase**: For testing Click commands with proper context management
- **ServiceTestCase**: For testing service classes with mocking utilities
- **DatabaseTestCase**: For testing database operations with isolation
- **ConfigurationTestCase**: For testing configuration loading and validation
- **FullTestCase**: Combines all mixins for comprehensive testing scenarios

### 2. Test Configuration Factory (`test_config_factory.py`)

Provides centralized creation of test configurations:

```python
from tests.utils.test_config_factory import TestConfigFactory

# Create base configuration
config = TestConfigFactory.create_base_config()

# Create configuration with overrides
config = TestConfigFactory.create_config_with_overrides(
    llm__service="openai",
    sqlite__db_file=":memory:"
)

# Create invalid configuration for testing validation
invalid_config = TestConfigFactory.create_invalid_config("database")
```

### 3. Mock Service Factory (`mock_service_factory.py`)

Provides standardized mock service creation:

```python
from tests.utils.mock_service_factory import MockServiceFactory

# Create mock services
db_service = MockServiceFactory.create_mock_db_service(config)
llm_service = MockServiceFactory.create_mock_llm_service(config, service_type="ollama")
sftp_service = MockServiceFactory.create_mock_sftp_service(config)
tmdb_service = MockServiceFactory.create_mock_tmdb_service(config)
```

## Usage Patterns

### 1. Basic Test Setup

```python
from tests.utils.test_base import BaseTestCase

class TestMyFeature(BaseTestCase):
    def test_basic_functionality(self):
        # Get test configuration
        config = self.get_test_config()
        
        # Create services
        db_service = self.create_test_db_service(config)
        llm_service = self.create_test_llm_service(config)
        
        # Test implementation
        result = my_function(db_service, llm_service)
        self.assertIsNotNone(result)
```

### 2. CLI Command Testing

```python
from tests.utils.test_base import CLITestCase
from cli.my_command import my_command

class TestMyCommand(CLITestCase):
    def test_command_execution(self):
        # Create CLI context
        context = self.create_cli_context()
        
        # Invoke command
        result = self.invoke_cli_command(
            my_command,
            ["--option", "value"],
            config=self.get_test_config()
        )
        
        # Assert success
        self.assert_cli_success(result, expected_output="Success")
```

### 3. Service Testing with Mocking

```python
from tests.utils.test_base import ServiceTestCase
from services.my_service import MyService

class TestMyService(ServiceTestCase):
    def test_service_initialization(self):
        config = self.get_test_config()
        service = MyService(config)
        
        # Assert proper initialization
        self.assert_service_initialized(service, ["config", "db", "llm"])
        
    def test_service_method(self):
        config = self.get_test_config()
        mock_db = self.create_test_db_service(config)
        
        service = MyService(config, db=mock_db)
        result = service.process_data("test_data")
        
        # Assert mock was called
        self.assert_service_method_called(mock_db, "add_show", "test_data")
```

### 4. Database Testing

```python
from tests.utils.test_base import DatabaseTestCase
from models.show import Show

class TestDatabaseOperations(DatabaseTestCase):
    def test_show_operations(self):
        db_service = self.create_test_database()
        
        # Test adding show
        show = Show(sys_name="Test Show", tmdb_id=123)
        db_service.add_show(show)
        
        # Assert show exists
        self.assert_show_exists(db_service, "Test Show")
```

### 5. Configuration Testing

```python
from tests.utils.test_base import ConfigurationTestCase

class TestConfiguration(ConfigurationTestCase):
    def test_valid_configurations(self):
        variations = self.create_test_config_variations()
        
        for name, config in variations.items():
            with self.subTest(config=name):
                self.assert_configuration_valid(config)
    
    def test_invalid_configurations(self):
        invalid_config = TestConfigFactory.create_invalid_config("database")
        self.assert_configuration_invalid(invalid_config, ["database.type"])
```

## Advanced Features

### 1. Test Environment Creation

For complex test scenarios requiring full environment setup:

```python
from tests.utils.test_base import create_test_environment, cleanup_test_environment

def test_complex_scenario():
    env = create_test_environment()
    try:
        config = env["config"]
        services = env["services"]
        
        # Complex test implementation
        
    finally:
        cleanup_test_environment(env)
```

### 2. Parametrized Testing

Use decorators for testing across multiple service types:

```python
from tests.utils.test_base import parametrize_llm_services, parametrize_database_types

@parametrize_llm_services
def test_llm_parsing(llm_service_type):
    config = TestConfigFactory.create_config_with_overrides(
        llm__service=llm_service_type
    )
    llm_service = MockServiceFactory.create_mock_llm_service(config, llm_service_type)
    
    result = llm_service.parse_filename("test_file.mkv")
    assert result["confidence"] > 0.5

@parametrize_database_types
def test_database_operations(db_type):
    config = TestConfigFactory.create_config_with_overrides(
        database__type=db_type
    )
    db_service = MockServiceFactory.create_mock_db_service(config)
    
    # Test database operations
```

### 3. External Service Skipping

Skip tests that require external services:

```python
from tests.utils.test_base import skip_if_no_external_service

@skip_if_no_external_service("tmdb")
def test_real_tmdb_integration():
    # This test will be skipped in unit test environment
    pass
```

## Configuration Patterns

### 1. Memory Database for Fast Tests

```python
config = self.get_memory_db_config()
db_service = self.create_test_db_service(config)
```

### 2. Service-Specific Configurations

```python
# OpenAI LLM configuration
config = self.get_test_config(llm__service="openai")

# Custom SFTP configuration
config = self.get_test_config(
    sftp__host="custom-host",
    sftp__port="2222"
)
```

### 3. Temporary File Management

```python
# Create temporary files
config_file = self.create_temp_config_file()
test_file = self.create_temp_file("test content", suffix=".txt")

# Files are automatically cleaned up
```

## Migration Guide

### From Old Test Patterns

#### Before (Direct Configuration Access)
```python
config = {"SQLite": {"db_file": "/tmp/test.db"}}
db_file = config["SQLite"]["db_file"]  # Case-sensitive, breaks with normalization
```

#### After (Using Test Infrastructure)
```python
config = self.get_test_config(sqlite__db_file="/tmp/test.db")
db_file = get_config_value(config, "sqlite", "db_file")  # Case-insensitive
```

#### Before (Manual Service Creation)
```python
mock_db = Mock()
mock_db.show_exists.return_value = False
```

#### After (Using Mock Factory)
```python
mock_db = self.create_test_db_service()
# All abstract methods automatically implemented
```

#### Before (Manual CLI Context)
```python
ctx = click.Context(command)
ctx.obj = {"db": mock_db, "config": config}
```

#### After (Using Test Infrastructure)
```python
context = self.create_cli_context()
result = self.invoke_cli_command(command, ["args"])
```

## Best Practices

### 1. Test Isolation
- Always use `BaseTestCase` or its subclasses for automatic cleanup
- Use in-memory databases for fast, isolated tests
- Create temporary directories for file operations

### 2. Mock Service Usage
- Use `MockServiceFactory` for consistent mock behavior
- Set custom responses using mock service methods when needed
- Track created services for proper cleanup

### 3. Configuration Management
- Use `TestConfigFactory` for standardized configurations
- Override only necessary configuration values
- Use case-insensitive configuration access helpers

### 4. CLI Testing
- Use `CLITestCase` for Click command testing
- Create proper CLI contexts with `create_cli_context()`
- Use assertion helpers like `assert_cli_success()`

### 5. Error Testing
- Test both success and failure scenarios
- Use `assert_cli_failure()` for expected failures
- Validate error messages and exit codes

## Troubleshooting

### Common Issues

1. **Configuration Section Not Found**
   - Use case-insensitive helpers: `get_config_section()`, `get_config_value()`
   - Check section names in test configurations

2. **Mock Service Method Not Found**
   - Ensure using `MockServiceFactory` for service creation
   - Check that all abstract methods are implemented in mock classes

3. **CLI Context Errors**
   - Use `create_cli_context()` for proper context setup
   - Ensure all required context keys are present

4. **Resource Cleanup Issues**
   - Always inherit from `BaseTestCase` for automatic cleanup
   - Use `addCleanup()` for custom cleanup requirements

5. **Test Performance Issues**
   - Use in-memory databases: `get_memory_db_config()`
   - Avoid creating real external service connections
   - Use mock services instead of real implementations

### Debugging Tips

1. **Enable Verbose Output**
   ```python
   result = self.invoke_cli_command(command, args)
   if result.exit_code != 0:
       print("CLI Output:", result.output)
       print("Exception:", result.exception)
   ```

2. **Check Mock Call History**
   ```python
   mock_service = self.create_test_db_service()
   # ... test code
   print("Mock calls:", mock_service.method_calls)
   ```

3. **Validate Configuration**
   ```python
   config = self.get_test_config()
   print("Config sections:", list(config.keys()))
   print("LLM config:", get_config_section(config, "llm"))
   ```

## Contributing

When adding new test infrastructure:

1. **Follow Naming Conventions**
   - Test classes: `*TestCase` or `*TestMixin`
   - Helper functions: `create_*`, `assert_*`, `get_*`
   - Mock classes: `Mock*Service`

2. **Add Documentation**
   - Include comprehensive docstrings
   - Add usage examples
   - Update this README

3. **Maintain Backward Compatibility**
   - Don't break existing test patterns
   - Provide migration paths for old patterns
   - Add deprecation warnings when appropriate

4. **Test the Test Infrastructure**
   - Write tests for new test utilities
   - Ensure proper cleanup and isolation
   - Validate mock service behavior

## Related Files

- `test_config_factory.py`: Configuration creation utilities
- `mock_service_factory.py`: Mock service creation utilities
- `../conftest.py`: Pytest configuration and fixtures
- `../../utils/sync2nas_config.py`: Configuration helper functions
- `../../utils/cli_helpers.py`: CLI utility functions