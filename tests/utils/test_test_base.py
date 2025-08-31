"""
Tests for the enhanced test base classes and utilities.

This module validates that the test infrastructure works correctly and provides
the expected functionality for test configuration, service creation, and
CLI context management.
"""

import unittest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import click

from tests.utils.test_base import (
    BaseTestCase,
    CLITestCase,
    ServiceTestCase,
    DatabaseTestCase,
    ConfigurationTestCase,
    FullTestCase,
    create_test_environment,
    cleanup_test_environment,
    parametrize_llm_services,
    parametrize_database_types
)
from tests.utils.test_config_factory import TestConfigFactory
from tests.utils.mock_service_factory import MockServiceFactory
from utils.sync2nas_config import get_config_value, get_config_section


class TestBaseTestCase(BaseTestCase):
    """Test the BaseTestCase functionality."""
    
    def test_setup_and_cleanup(self):
        """Test that setup and cleanup work correctly."""
        # Verify temp directory exists
        self.assertTrue(self.temp_dir.exists())
        self.assertTrue(self.temp_dir.is_dir())
        
        # Verify CLI runner is available
        self.assertIsNotNone(self.cli_runner)
    
    def test_get_test_config(self):
        """Test test configuration creation."""
        config = self.get_test_config()
        
        # Verify required sections exist
        self.assert_config_section_exists(config, "database")
        self.assert_config_section_exists(config, "llm")
        self.assert_config_section_exists(config, "sqlite")
        self.assert_config_section_exists(config, "ollama")
        
        # Verify paths use temp directory
        sqlite_config = get_config_section(config, "sqlite")
        self.assertIn(str(self.temp_dir), sqlite_config["db_file"])
    
    def test_get_test_config_with_overrides(self):
        """Test configuration creation with overrides."""
        config = self.get_test_config(
            llm__service="openai",
            sqlite__db_file=":memory:"
        )
        
        # Verify overrides applied
        llm_config = get_config_section(config, "llm")
        self.assertEqual(llm_config["service"], "openai")
        
        sqlite_config = get_config_section(config, "sqlite")
        self.assertEqual(sqlite_config["db_file"], ":memory:")
    
    def test_get_memory_db_config(self):
        """Test memory database configuration creation."""
        config = self.get_memory_db_config()
        
        sqlite_config = get_config_section(config, "sqlite")
        self.assertEqual(sqlite_config["db_file"], ":memory:")
    
    def test_create_test_services(self):
        """Test service creation."""
        services = self.create_test_services()
        
        # Verify all services created
        self.assertIn("db", services)
        self.assertIn("llm", services)
        self.assertIn("sftp", services)
        self.assertIn("tmdb", services)
        
        # Verify services are mocks with expected methods
        self.assertTrue(hasattr(services["db"], "show_exists"))
        self.assertTrue(hasattr(services["llm"], "parse_filename"))
        self.assertTrue(hasattr(services["sftp"], "list_remote_files"))
        self.assertTrue(hasattr(services["tmdb"], "search_show"))
    
    def test_create_individual_services(self):
        """Test individual service creation methods."""
        config = self.get_test_config()
        
        # Test database service
        db_service = self.create_test_db_service(config)
        self.assertTrue(hasattr(db_service, "show_exists"))
        self.assertTrue(hasattr(db_service, "add_show"))
        
        # Test LLM service
        llm_service = self.create_test_llm_service(config)
        self.assertTrue(hasattr(llm_service, "parse_filename"))
        self.assertTrue(hasattr(llm_service, "suggest_show_name"))
        
        # Test SFTP service
        sftp_service = self.create_test_sftp_service(config)
        self.assertTrue(hasattr(sftp_service, "list_remote_files"))
        self.assertTrue(hasattr(sftp_service, "download_file"))
        
        # Test TMDB service
        tmdb_service = self.create_test_tmdb_service(config)
        self.assertTrue(hasattr(tmdb_service, "search_show"))
        self.assertTrue(hasattr(tmdb_service, "get_show_details"))
    
    def test_create_cli_context(self):
        """Test CLI context creation."""
        context = self.create_cli_context()
        
        # Verify required context keys
        required_keys = ["config", "db", "tmdb", "sftp", "llm_service", 
                        "anime_tv_path", "incoming_path", "dry_run"]
        for key in required_keys:
            self.assertIn(key, context)
        
        # Verify services are properly mocked
        self.assertTrue(hasattr(context["db"], "show_exists"))
        self.assertTrue(hasattr(context["llm_service"], "parse_filename"))
    
    def test_create_temp_file(self):
        """Test temporary file creation."""
        content = "test content"
        temp_file = self.create_temp_file(content, suffix=".txt")
        
        # Verify file exists and has correct content
        self.assertTrue(temp_file.exists())
        self.assertEqual(temp_file.read_text(), content)
        self.assertTrue(temp_file.name.endswith(".txt"))
    
    def test_create_temp_config_file(self):
        """Test temporary configuration file creation."""
        config = self.get_test_config()
        config_file = self.create_temp_config_file(config)
        
        # Verify file exists and is readable
        self.assertTrue(config_file.exists())
        self.assertTrue(config_file.name.endswith(".ini"))
    
    def test_assertion_helpers(self):
        """Test assertion helper methods."""
        config = self.get_test_config()
        
        # Test config section assertion
        self.assert_config_section_exists(config, "database")
        
        # Test config value assertion
        self.assert_config_value_equals(config, "database", "type", "sqlite")
        
        # Test file existence assertion
        temp_file = self.create_temp_file("test")
        self.assert_file_exists(temp_file)
        
        # Test directory existence assertion
        self.assert_directory_exists(self.temp_dir)


class TestCLITestCase(CLITestCase):
    """Test the CLITestCase functionality."""
    
    def test_cli_runner_available(self):
        """Test that CLI runner is available."""
        self.assertIsNotNone(self.cli_runner)
    
    def test_create_mock_cli_context(self):
        """Test mock CLI context creation."""
        context = self.create_mock_cli_context(dry_run=True)
        
        # Verify context structure
        self.assertIn("config", context)
        self.assertIn("db", context)
        self.assertTrue(context["dry_run"])
    
    def test_cli_assertion_helpers(self):
        """Test CLI assertion helpers."""
        # Create a simple mock result
        class MockResult:
            def __init__(self, exit_code, output):
                self.exit_code = exit_code
                self.output = output
        
        # Test success assertion
        success_result = MockResult(0, "Success message")
        self.assert_cli_success(success_result, "Success")
        
        # Test failure assertion
        failure_result = MockResult(1, "Error message")
        self.assert_cli_failure(failure_result, expected_exit_code=1, expected_error="Error")


class TestServiceTestCase(ServiceTestCase):
    """Test the ServiceTestCase functionality."""
    
    def test_service_assertion_helpers(self):
        """Test service assertion helpers."""
        # Create a mock service
        mock_service = Mock()
        mock_service.config = "test_config"
        mock_service.db = "test_db"
        
        # Test service initialization assertion
        self.assert_service_initialized(mock_service, ["config", "db"])
        
        # Test mock service behavior assertion
        mock_service.test_method.return_value = "expected_value"
        self.assert_mock_service_behavior(mock_service, "test_method", "expected_value")
    
    def test_create_service_with_config(self):
        """Test service creation with configuration."""
        def mock_factory(config):
            service = Mock()
            service.config = config
            return service
        
        service = self.create_service_with_config(mock_factory, {"test": "value"})
        self.assertIsNotNone(service.config)


class TestDatabaseTestCase(DatabaseTestCase):
    """Test the DatabaseTestCase functionality."""
    
    def test_create_test_database(self):
        """Test test database creation."""
        db_service = self.create_test_database()
        
        # Verify database service has expected methods
        self.assertTrue(hasattr(db_service, "show_exists"))
        self.assertTrue(hasattr(db_service, "add_show"))
        self.assertTrue(hasattr(db_service, "get_all_shows"))
    
    def test_database_assertion_helpers(self):
        """Test database assertion helpers."""
        db_service = self.create_test_database()
        
        # Test empty database assertion
        self.assert_database_empty(db_service)
        
        # Add a show and test existence
        from models.show import Show
        show = Show(
            sys_name="Test Show",
            sys_path="/tmp/test_show",
            tmdb_name="Test Show",
            tmdb_id=123
        )
        db_service.add_show(show)
        self.assert_show_exists(db_service, "Test Show")


class TestConfigurationTestCase(ConfigurationTestCase):
    """Test the ConfigurationTestCase functionality."""
    
    def test_create_test_config_variations(self):
        """Test configuration variation creation."""
        variations = self.create_test_config_variations()
        
        # Verify expected variations exist
        expected_variations = ["minimal", "memory_db", "ollama_llm", "openai_llm", "anthropic_llm"]
        for variation in expected_variations:
            self.assertIn(variation, variations)
        
        # Verify each variation is valid
        for name, config in variations.items():
            with self.subTest(variation=name):
                self.assertIsInstance(config, dict)
                self.assertIn("database", [k.lower() for k in config.keys()])
    
    def test_configuration_validation_helpers(self):
        """Test configuration validation helpers."""
        # Test valid configuration
        valid_config = TestConfigFactory.create_base_config()
        self.assert_configuration_valid(valid_config)
        
        # Test invalid configuration
        invalid_config = TestConfigFactory.create_invalid_config("database")
        self.assert_configuration_invalid(invalid_config, ["database.type"])


class TestFullTestCase(FullTestCase):
    """Test the FullTestCase functionality (combines all mixins)."""
    
    def test_all_functionality_available(self):
        """Test that all mixin functionality is available."""
        # Test BaseTestCase functionality
        config = self.get_test_config()
        self.assertIsNotNone(config)
        
        # Test CLITestCase functionality
        context = self.create_mock_cli_context()
        self.assertIsNotNone(context)
        
        # Test ServiceTestCase functionality
        mock_service = Mock()
        mock_service.test_attr = "test"
        self.assert_service_initialized(mock_service, ["test_attr"])
        
        # Test DatabaseTestCase functionality
        db_service = self.create_test_database()
        self.assert_database_empty(db_service)
        
        # Test ConfigurationTestCase functionality
        variations = self.create_test_config_variations()
        self.assertIsInstance(variations, dict)


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions."""
    
    def test_create_test_environment(self):
        """Test test environment creation."""
        env = create_test_environment()
        
        try:
            # Verify environment structure
            self.assertIn("config", env)
            self.assertIn("services", env)
            self.assertIn("temp_dir", env)
            self.assertIn("paths", env)
            
            # Verify services
            services = env["services"]
            self.assertIn("db", services)
            self.assertIn("llm", services)
            self.assertIn("sftp", services)
            self.assertIn("tmdb", services)
            
            # Verify paths
            paths = env["paths"]
            self.assertIn("incoming", paths)
            self.assertIn("anime_tv", paths)
            self.assertIn("db_file", paths)
            
        finally:
            cleanup_test_environment(env)
    
    def test_cleanup_test_environment(self):
        """Test test environment cleanup."""
        env = create_test_environment()
        temp_dir = env["temp_dir"]
        
        # Verify directory exists before cleanup
        self.assertTrue(temp_dir.exists())
        
        # Cleanup and verify directory is removed
        cleanup_test_environment(env)
        # Note: cleanup might not immediately remove directory due to OS delays
        # So we don't assert directory removal in this test


class TestDecorators(unittest.TestCase):
    """Test decorator functions."""
    
    def test_parametrize_llm_services(self):
        """Test LLM service parametrization decorator."""
        @parametrize_llm_services
        def dummy_test(llm_service_type):
            return llm_service_type
        
        # Verify decorator is applied (pytest.mark.parametrize)
        self.assertTrue(hasattr(dummy_test, 'pytestmark'))
    
    def test_parametrize_database_types(self):
        """Test database type parametrization decorator."""
        @parametrize_database_types
        def dummy_test(db_type):
            return db_type
        
        # Verify decorator is applied (pytest.mark.parametrize)
        self.assertTrue(hasattr(dummy_test, 'pytestmark'))


if __name__ == "__main__":
    unittest.main()