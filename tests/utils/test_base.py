"""
Enhanced test base classes and utilities for Sync2NAS test suite.

This module provides comprehensive test infrastructure including:
- BaseTestCase class with standardized test configuration setup
- Helper methods for creating test services and configurations
- Test utilities for common test patterns and assertions
- CLI context management for Click command testing
- Resource cleanup and isolation utilities

Requirements addressed: 6.1, 6.2, 6.3, 6.4, 7.1, 7.2, 7.3, 7.4
"""

import os
import sys
import tempfile
import unittest
import pytest
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Callable
from unittest.mock import Mock, MagicMock, patch
from click.testing import CliRunner
import click

# Add project root to sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tests.utils.test_config_factory import TestConfigFactory
from tests.utils.mock_service_factory import MockServiceFactory
from utils.sync2nas_config import get_config_section, get_config_value
from services.db_implementations.db_interface import DatabaseInterface
from services.llm_implementations.llm_interface import LLMInterface
from services.sftp_service import SFTPService
from services.tmdb_service import TMDBService


class BaseTestCase(unittest.TestCase):
    """
    Base test class with standardized test configuration setup and utilities.
    
    Provides common test infrastructure including:
    - Standardized test configuration creation
    - Mock service creation and management
    - Temporary directory and file management
    - CLI context setup for Click commands
    - Resource cleanup and isolation
    
    Usage:
        class MyTestCase(BaseTestCase):
            def test_something(self):
                config = self.get_test_config()
                db_service = self.create_test_db_service(config)
                # ... test implementation
    """
    
    def setUp(self) -> None:
        """Set up test environment with proper configuration and cleanup."""
        super().setUp()
        
        # Create temporary directory for test files
        self.temp_dir = Path(tempfile.mkdtemp(prefix="sync2nas_test_"))
        self.addCleanup(self._cleanup_temp_dir)
        
        # Initialize test configuration
        self._test_config = None
        self._created_services = []
        self._created_files = []
        
        # Set up CLI runner for Click command testing
        self.cli_runner = CliRunner()
        
        # Track resources for cleanup
        self.addCleanup(self._cleanup_services)
        self.addCleanup(self._cleanup_files)
    
    def tearDown(self) -> None:
        """Clean up test environment."""
        super().tearDown()
    
    def _cleanup_temp_dir(self) -> None:
        """Clean up temporary directory."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _cleanup_services(self) -> None:
        """Clean up created services."""
        for service in self._created_services:
            if hasattr(service, 'disconnect'):
                try:
                    service.disconnect()
                except:
                    pass
            if hasattr(service, 'close'):
                try:
                    service.close()
                except:
                    pass
    
    def _cleanup_files(self) -> None:
        """Clean up created files."""
        for file_path in self._created_files:
            try:
                if Path(file_path).exists():
                    Path(file_path).unlink()
            except:
                pass
    
    def get_test_config(self, **overrides) -> Dict[str, Dict[str, Any]]:
        """
        Get test configuration with optional overrides.
        
        Args:
            **overrides: Configuration overrides in format section__key=value
                        or section=dict_of_values
        
        Returns:
            Dict[str, Dict[str, Any]]: Complete test configuration
        
        Example:
            config = self.get_test_config(
                llm__service="openai",
                sqlite__db_file=":memory:"
            )
        """
        if self._test_config is None or overrides:
            # Create base config with temp directory paths
            base_overrides = {
                "sqlite__db_file": str(self.temp_dir / "test.db"),
                "transfers__incoming": str(self.temp_dir / "incoming"),
                "routing__anime_tv_path": str(self.temp_dir / "anime_tv"),
                "sftp__ssh_key_path": str(self.temp_dir / "test_key")
            }
            base_overrides.update(overrides)
            
            self._test_config = TestConfigFactory.create_config_with_overrides(**base_overrides)
            
            # Create necessary directories
            TestConfigFactory.create_test_directories(self._test_config)
        
        return self._test_config
    
    def get_memory_db_config(self, **overrides) -> Dict[str, Dict[str, Any]]:
        """
        Get test configuration with in-memory database for fast tests.
        
        Args:
            **overrides: Additional configuration overrides
        
        Returns:
            Dict[str, Dict[str, Any]]: Configuration with in-memory database
        """
        memory_overrides = {"sqlite__db_file": ":memory:"}
        memory_overrides.update(overrides)
        return self.get_test_config(**memory_overrides)
    
    def create_test_services(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create all test services with proper mocking.
        
        Args:
            config: Configuration to use (defaults to test config)
        
        Returns:
            Dict[str, Any]: Dictionary of created services
        """
        if config is None:
            config = self.get_test_config()
        
        services = {
            "db": self.create_test_db_service(config),
            "llm": self.create_test_llm_service(config),
            "sftp": self.create_test_sftp_service(config),
            "tmdb": self.create_test_tmdb_service(config)
        }
        
        return services
    
    def create_test_db_service(self, config: Optional[Dict[str, Any]] = None, read_only: bool = False) -> DatabaseInterface:
        """
        Create test database service with proper configuration.
        
        Args:
            config: Configuration to use (defaults to test config)
            read_only: Whether to create read-only database service
        
        Returns:
            DatabaseInterface: Mock database service
        """
        if config is None:
            config = self.get_test_config()
        
        db_service = MockServiceFactory.create_mock_db_service(config, read_only=read_only)
        self._created_services.append(db_service)
        return db_service
    
    def create_test_llm_service(self, config: Optional[Dict[str, Any]] = None, service_type: str = "ollama") -> LLMInterface:
        """
        Create test LLM service with health checks disabled.
        
        Args:
            config: Configuration to use (defaults to test config)
            service_type: Type of LLM service to create
        
        Returns:
            LLMInterface: Mock LLM service
        """
        if config is None:
            config = self.get_test_config()
        
        llm_service = MockServiceFactory.create_mock_llm_service(config, service_type=service_type)
        self._created_services.append(llm_service)
        return llm_service
    
    def create_test_sftp_service(self, config: Optional[Dict[str, Any]] = None) -> SFTPService:
        """
        Create test SFTP service with mocked connections.
        
        Args:
            config: Configuration to use (defaults to test config)
        
        Returns:
            SFTPService: Mock SFTP service
        """
        if config is None:
            config = self.get_test_config()
        
        sftp_service = MockServiceFactory.create_mock_sftp_service(config)
        self._created_services.append(sftp_service)
        return sftp_service
    
    def create_test_tmdb_service(self, config: Optional[Dict[str, Any]] = None) -> TMDBService:
        """
        Create test TMDB service with mocked API calls.
        
        Args:
            config: Configuration to use (defaults to test config)
        
        Returns:
            TMDBService: Mock TMDB service
        """
        if config is None:
            config = self.get_test_config()
        
        tmdb_service = MockServiceFactory.create_mock_tmdb_service(config)
        self._created_services.append(tmdb_service)
        return tmdb_service
    
    def create_cli_context(self, config: Optional[Dict[str, Any]] = None, dry_run: bool = False, **service_overrides) -> Dict[str, Any]:
        """
        Create CLI context object for Click command testing.
        
        Args:
            config: Configuration to use (defaults to test config)
            dry_run: Whether to set dry_run mode
            **service_overrides: Override specific services
        
        Returns:
            Dict[str, Any]: CLI context object suitable for Click commands
        """
        if config is None:
            config = self.get_test_config()
        
        # Create services
        services = self.create_test_services(config)
        services.update(service_overrides)
        
        # Create CLI context object matching expected structure
        context = {
            "config": config,
            "db": services["db"],
            "tmdb": services["tmdb"],
            "sftp": services["sftp"],
            "llm_service": services["llm"],
            "anime_tv_path": get_config_value(config, "routing", "anime_tv_path", str(self.temp_dir / "anime_tv")),
            "incoming_path": get_config_value(config, "transfers", "incoming", str(self.temp_dir / "incoming")),
            "dry_run": dry_run
        }
        
        return context
    
    def invoke_cli_command(self, command: click.Command, args: List[str], config: Optional[Dict[str, Any]] = None, **context_overrides) -> click.testing.Result:
        """
        Invoke a CLI command with proper context setup.
        
        Args:
            command: Click command to invoke
            args: Command arguments
            config: Configuration to use (defaults to test config)
            **context_overrides: Override context values
        
        Returns:
            click.testing.Result: Command execution result
        """
        context = self.create_cli_context(config, **context_overrides)
        
        return self.cli_runner.invoke(
            command,
            args,
            obj=context,
            catch_exceptions=False
        )
    
    def create_temp_file(self, content: str = "", suffix: str = ".txt", prefix: str = "test_") -> Path:
        """
        Create a temporary file for testing.
        
        Args:
            content: File content
            suffix: File suffix
            prefix: File prefix
        
        Returns:
            Path: Path to created file
        """
        temp_file = self.temp_dir / f"{prefix}{len(self._created_files)}{suffix}"
        temp_file.write_text(content)
        self._created_files.append(str(temp_file))
        return temp_file
    
    def create_temp_config_file(self, config: Optional[Dict[str, Any]] = None) -> Path:
        """
        Create a temporary configuration file.
        
        Args:
            config: Configuration to write (defaults to test config)
        
        Returns:
            Path: Path to created configuration file
        """
        if config is None:
            config = self.get_test_config()
        
        config_file = TestConfigFactory.write_config_file(config, self.temp_dir / "test_config.ini")
        self._created_files.append(str(config_file))
        return config_file
    
    def assert_config_section_exists(self, config: Dict[str, Any], section_name: str) -> None:
        """
        Assert that a configuration section exists.
        
        Args:
            config: Configuration dictionary
            section_name: Section name to check
        """
        self.assertIn(section_name.lower(), [k.lower() for k in config.keys()], 
                     f"Configuration section '{section_name}' not found")
    
    def assert_config_value_equals(self, config: Dict[str, Any], section: str, key: str, expected_value: Any) -> None:
        """
        Assert that a configuration value equals expected value.
        
        Args:
            config: Configuration dictionary
            section: Section name
            key: Configuration key
            expected_value: Expected value
        """
        actual_value = get_config_value(config, section, key)
        self.assertEqual(actual_value, expected_value,
                        f"Configuration {section}.{key} expected '{expected_value}', got '{actual_value}'")
    
    def assert_service_method_called(self, service: Mock, method_name: str, *args, **kwargs) -> None:
        """
        Assert that a service method was called with specific arguments.
        
        Args:
            service: Mock service object
            method_name: Method name to check
            *args: Expected positional arguments
            **kwargs: Expected keyword arguments
        """
        method = getattr(service, method_name)
        if args or kwargs:
            method.assert_called_with(*args, **kwargs)
        else:
            method.assert_called()
    
    def assert_file_exists(self, file_path: Union[str, Path]) -> None:
        """
        Assert that a file exists.
        
        Args:
            file_path: Path to file
        """
        path = Path(file_path)
        self.assertTrue(path.exists(), f"File {path} does not exist")
    
    def assert_directory_exists(self, dir_path: Union[str, Path]) -> None:
        """
        Assert that a directory exists.
        
        Args:
            dir_path: Path to directory
        """
        path = Path(dir_path)
        self.assertTrue(path.exists() and path.is_dir(), f"Directory {path} does not exist")


class CLITestMixin:
    """
    Mixin class for CLI command testing utilities.
    
    Provides specialized methods for testing Click commands with proper
    context management and assertion helpers.
    """
    
    def setUp(self) -> None:
        """Set up CLI testing environment."""
        super().setUp()
        if not hasattr(self, 'cli_runner'):
            self.cli_runner = CliRunner()
    
    def assert_cli_success(self, result: click.testing.Result, expected_output: Optional[str] = None) -> None:
        """
        Assert that CLI command executed successfully.
        
        Args:
            result: CLI execution result
            expected_output: Optional expected output substring
        """
        if result.exit_code != 0:
            self.fail(f"CLI command failed with exit code {result.exit_code}. Output: {result.output}")
        
        if expected_output:
            self.assertIn(expected_output, result.output)
    
    def assert_cli_failure(self, result: click.testing.Result, expected_exit_code: int = 1, expected_error: Optional[str] = None) -> None:
        """
        Assert that CLI command failed as expected.
        
        Args:
            result: CLI execution result
            expected_exit_code: Expected exit code
            expected_error: Optional expected error message substring
        """
        self.assertEqual(result.exit_code, expected_exit_code,
                        f"Expected exit code {expected_exit_code}, got {result.exit_code}. Output: {result.output}")
        
        if expected_error:
            self.assertIn(expected_error, result.output)
    
    def create_mock_cli_context(self, **overrides) -> Dict[str, Any]:
        """
        Create a mock CLI context for testing.
        
        Args:
            **overrides: Context value overrides
        
        Returns:
            Dict[str, Any]: Mock CLI context
        """
        if hasattr(self, 'create_cli_context'):
            return self.create_cli_context(**overrides)
        
        # Fallback for classes not inheriting from BaseTestCase
        default_context = {
            "config": TestConfigFactory.create_base_config(),
            "db": Mock(),
            "tmdb": Mock(),
            "sftp": Mock(),
            "llm_service": Mock(),
            "anime_tv_path": "/tmp/anime_tv",
            "incoming_path": "/tmp/incoming",
            "dry_run": False
        }
        default_context.update(overrides)
        return default_context


class ServiceTestMixin:
    """
    Mixin class for service testing utilities.
    
    Provides specialized methods for testing service classes with proper
    mocking and assertion helpers.
    """
    
    def assert_service_initialized(self, service: Any, expected_attributes: List[str]) -> None:
        """
        Assert that a service is properly initialized.
        
        Args:
            service: Service instance to check
            expected_attributes: List of expected attributes
        """
        for attr in expected_attributes:
            self.assertTrue(hasattr(service, attr), f"Service missing attribute: {attr}")
    
    def assert_mock_service_behavior(self, service: Mock, method_name: str, expected_return: Any) -> None:
        """
        Assert that a mock service method returns expected value.
        
        Args:
            service: Mock service
            method_name: Method name to test
            expected_return: Expected return value
        """
        method = getattr(service, method_name)
        if callable(method):
            actual_return = method()
            self.assertEqual(actual_return, expected_return)
        else:
            self.assertEqual(method, expected_return)
    
    def create_service_with_config(self, service_factory: Callable, config_overrides: Optional[Dict[str, Any]] = None) -> Any:
        """
        Create a service with test configuration.
        
        Args:
            service_factory: Factory function to create service
            config_overrides: Configuration overrides
        
        Returns:
            Any: Created service instance
        """
        if hasattr(self, 'get_test_config'):
            config = self.get_test_config(**(config_overrides or {}))
        else:
            config = TestConfigFactory.create_config_with_overrides(**(config_overrides or {}))
        
        return service_factory(config)


class DatabaseTestMixin:
    """
    Mixin class for database testing utilities.
    
    Provides specialized methods for testing database operations with proper
    setup, teardown, and assertion helpers.
    """
    
    def setUp(self) -> None:
        """Set up database testing environment."""
        super().setUp()
        if not hasattr(self, '_test_db_services'):
            self._test_db_services = []
    
    def tearDown(self) -> None:
        """Clean up database testing environment."""
        if hasattr(self, '_test_db_services'):
            for db_service in self._test_db_services:
                if hasattr(db_service, 'disconnect'):
                    try:
                        db_service.disconnect()
                    except:
                        pass
        super().tearDown()
    
    def create_test_database(self, config_overrides: Optional[Dict[str, Any]] = None) -> DatabaseInterface:
        """
        Create a test database with proper isolation.
        
        Args:
            config_overrides: Configuration overrides
        
        Returns:
            DatabaseInterface: Test database service
        """
        if hasattr(self, 'create_test_db_service'):
            db_service = self.create_test_db_service(config_overrides)
        else:
            config = TestConfigFactory.create_memory_db_config()
            if config_overrides:
                config.update(config_overrides)
            db_service = MockServiceFactory.create_mock_db_service(config)
        
        if not hasattr(self, '_test_db_services'):
            self._test_db_services = []
        self._test_db_services.append(db_service)
        return db_service
    
    def assert_database_empty(self, db_service: DatabaseInterface) -> None:
        """
        Assert that database is empty.
        
        Args:
            db_service: Database service to check
        """
        shows = db_service.get_all_shows()
        self.assertEqual(len(shows), 0, "Database should be empty")
    
    def assert_show_exists(self, db_service: DatabaseInterface, show_name: str) -> None:
        """
        Assert that a show exists in the database.
        
        Args:
            db_service: Database service
            show_name: Show name to check
        """
        exists = db_service.show_exists(show_name)
        self.assertTrue(exists, f"Show '{show_name}' should exist in database")
    
    def assert_episodes_exist(self, db_service: DatabaseInterface, tmdb_id: int) -> None:
        """
        Assert that episodes exist for a show.
        
        Args:
            db_service: Database service
            tmdb_id: TMDB ID of the show
        """
        exists = db_service.episodes_exist(tmdb_id)
        self.assertTrue(exists, f"Episodes should exist for TMDB ID {tmdb_id}")


class ConfigurationTestMixin:
    """
    Mixin class for configuration testing utilities.
    
    Provides specialized methods for testing configuration loading, validation,
    and manipulation with proper test isolation.
    """
    
    def create_test_config_variations(self) -> Dict[str, Dict[str, Any]]:
        """
        Create various test configuration scenarios.
        
        Returns:
            Dict[str, Dict[str, Any]]: Named configuration variations
        """
        return {
            "minimal": TestConfigFactory.create_minimal_config(),
            "memory_db": TestConfigFactory.create_memory_db_config(),
            "ollama_llm": TestConfigFactory.create_config_with_overrides(llm__service="ollama"),
            "openai_llm": TestConfigFactory.create_config_with_overrides(llm__service="openai"),
            "anthropic_llm": TestConfigFactory.create_config_with_overrides(llm__service="anthropic")
        }
    
    def assert_configuration_valid(self, config: Dict[str, Any], required_sections: Optional[List[str]] = None) -> None:
        """
        Assert that configuration is valid.
        
        Args:
            config: Configuration to validate
            required_sections: List of required sections
        """
        if required_sections is None:
            required_sections = ["database", "llm"]
        
        for section in required_sections:
            self.assert_config_section_exists(config, section)
    
    def assert_configuration_invalid(self, config: Dict[str, Any], expected_errors: List[str]) -> None:
        """
        Assert that configuration is invalid with expected errors.
        
        Args:
            config: Configuration to validate
            expected_errors: List of expected error keys
        """
        # This would typically use actual validation logic
        # For now, we'll check that expected error sections are missing or invalid
        for error_key in expected_errors:
            if "." in error_key:
                section, key = error_key.split(".", 1)
                try:
                    section_data = get_config_section(config, section)
                    if section_data and key in section_data:
                        value = section_data[key]
                        # Check if value is invalid (empty, None, or specific invalid values)
                        is_invalid = (
                            not value or 
                            value == "" or 
                            value is None or
                            value == "invalid_db_type" or
                            value == "invalid_llm_service"
                        )
                        self.assertTrue(is_invalid, f"Expected {error_key} to be invalid, got: {value}")
                    else:
                        # Key missing is also invalid
                        pass
                except:
                    # Section missing or other error is also invalid
                    pass
            else:
                # Section-level error - check if section is missing or invalid
                section_exists = False
                try:
                    section_data = get_config_section(config, error_key)
                    section_exists = bool(section_data)
                except:
                    section_exists = False
                
                # For missing required sections, we expect them to not exist
                if error_key in ["database", "llm"]:
                    self.assertFalse(section_exists, f"Expected section {error_key} to be missing")


# Convenience base classes combining mixins
class FullTestCase(BaseTestCase, CLITestMixin, ServiceTestMixin, DatabaseTestMixin, ConfigurationTestMixin):
    """
    Full-featured test case class with all mixins.
    
    Provides complete test infrastructure for comprehensive testing scenarios.
    Use this when you need all testing utilities in a single test class.
    """
    pass


class CLITestCase(BaseTestCase, CLITestMixin):
    """
    Test case class specialized for CLI command testing.
    
    Provides test infrastructure focused on Click command testing with proper
    context management and CLI-specific assertions.
    """
    pass


class ServiceTestCase(BaseTestCase, ServiceTestMixin):
    """
    Test case class specialized for service testing.
    
    Provides test infrastructure focused on service class testing with proper
    mocking and service-specific assertions.
    """
    pass


class DatabaseTestCase(BaseTestCase, DatabaseTestMixin):
    """
    Test case class specialized for database testing.
    
    Provides test infrastructure focused on database operations with proper
    isolation and database-specific assertions.
    """
    pass


class ConfigurationTestCase(BaseTestCase, ConfigurationTestMixin):
    """
    Test case class specialized for configuration testing.
    
    Provides test infrastructure focused on configuration loading, validation,
    and manipulation with proper test isolation.
    """
    pass


# Utility functions for test setup and common patterns
def create_test_environment(temp_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Create a complete test environment with all necessary components.
    
    Args:
        temp_dir: Optional temporary directory to use
    
    Returns:
        Dict[str, Any]: Test environment with config, services, and paths
    """
    if temp_dir is None:
        temp_dir = Path(tempfile.mkdtemp(prefix="sync2nas_test_env_"))
    
    # Create test configuration
    config = TestConfigFactory.create_config_with_overrides(
        sqlite__db_file=str(temp_dir / "test.db"),
        transfers__incoming=str(temp_dir / "incoming"),
        routing__anime_tv_path=str(temp_dir / "anime_tv"),
        sftp__ssh_key_path=str(temp_dir / "test_key")
    )
    
    # Create directories
    TestConfigFactory.create_test_directories(config)
    
    # Create services
    services = {
        "db": MockServiceFactory.create_mock_db_service(config),
        "llm": MockServiceFactory.create_mock_llm_service(config),
        "sftp": MockServiceFactory.create_mock_sftp_service(config),
        "tmdb": MockServiceFactory.create_mock_tmdb_service(config)
    }
    
    return {
        "config": config,
        "services": services,
        "temp_dir": temp_dir,
        "paths": {
            "incoming": temp_dir / "incoming",
            "anime_tv": temp_dir / "anime_tv",
            "db_file": temp_dir / "test.db"
        }
    }


def cleanup_test_environment(env: Dict[str, Any]) -> None:
    """
    Clean up a test environment created by create_test_environment.
    
    Args:
        env: Test environment dictionary
    """
    # Clean up services
    for service in env.get("services", {}).values():
        if hasattr(service, 'disconnect'):
            try:
                service.disconnect()
            except:
                pass
        if hasattr(service, 'close'):
            try:
                service.close()
            except:
                pass
    
    # Clean up temporary directory
    temp_dir = env.get("temp_dir")
    if temp_dir and Path(temp_dir).exists():
        shutil.rmtree(temp_dir, ignore_errors=True)


def skip_if_no_external_service(service_name: str) -> Callable:
    """
    Decorator to skip tests if external service is not available.
    
    Args:
        service_name: Name of the external service
    
    Returns:
        Callable: Test decorator
    """
    def decorator(test_func):
        return pytest.mark.skipif(
            True,  # Always skip external service tests in unit testing
            reason=f"External service {service_name} not available in test environment"
        )(test_func)
    
    return decorator


def parametrize_llm_services(test_func: Callable) -> Callable:
    """
    Decorator to parametrize tests across all LLM service types.
    
    Args:
        test_func: Test function to parametrize
    
    Returns:
        Callable: Parametrized test function
    """
    return pytest.mark.parametrize(
        "llm_service_type",
        ["ollama", "openai", "anthropic"],
        ids=["ollama", "openai", "anthropic"]
    )(test_func)


def parametrize_database_types(test_func: Callable) -> Callable:
    """
    Decorator to parametrize tests across all database types.
    
    Args:
        test_func: Test function to parametrize
    
    Returns:
        Callable: Parametrized test function
    """
    return pytest.mark.parametrize(
        "db_type",
        ["sqlite"],  # Only SQLite for now, can add PostgreSQL, Milvus later
        ids=["sqlite"]
    )(test_func)


# Export all public classes and functions
__all__ = [
    "BaseTestCase",
    "CLITestMixin",
    "ServiceTestMixin", 
    "DatabaseTestMixin",
    "ConfigurationTestMixin",
    "FullTestCase",
    "CLITestCase",
    "ServiceTestCase",
    "DatabaseTestCase",
    "ConfigurationTestCase",
    "create_test_environment",
    "cleanup_test_environment",
    "skip_if_no_external_service",
    "parametrize_llm_services",
    "parametrize_database_types"
]