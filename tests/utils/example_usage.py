"""
Example usage of the enhanced test infrastructure.

This file demonstrates how to use the new test base classes and utilities
for different types of testing scenarios in the Sync2NAS project.
"""

import unittest
from unittest.mock import Mock, patch
import click

from tests.utils.test_base import (
    BaseTestCase,
    CLITestCase,
    ServiceTestCase,
    DatabaseTestCase,
    ConfigurationTestCase,
    FullTestCase,
    parametrize_llm_services,
    parametrize_database_types
)
from tests.utils.test_config_factory import TestConfigFactory
from tests.utils.mock_service_factory import MockServiceFactory


class ExampleBasicTest(BaseTestCase):
    """Example of basic test using BaseTestCase."""
    
    def test_basic_functionality(self):
        """Example test showing basic test infrastructure usage."""
        # Get test configuration with overrides
        config = self.get_test_config(
            llm__service="ollama",
            sqlite__db_file=":memory:"
        )
        
        # Create test services
        db_service = self.create_test_db_service(config)
        llm_service = self.create_test_llm_service(config)
        
        # Test assertions
        self.assert_config_section_exists(config, "database")
        self.assert_config_value_equals(config, "llm", "service", "ollama")
        
        # Test service functionality
        self.assertTrue(hasattr(db_service, "show_exists"))
        self.assertTrue(hasattr(llm_service, "parse_filename"))
        
        # Test file operations
        temp_file = self.create_temp_file("test content", suffix=".txt")
        self.assert_file_exists(temp_file)


class ExampleCLITest(CLITestCase):
    """Example of CLI testing using CLITestCase."""
    
    def test_cli_command_example(self):
        """Example test showing CLI command testing."""
        # Create a simple mock command for demonstration
        @click.command()
        @click.pass_context
        def mock_command(ctx):
            """Mock CLI command for testing."""
            db = ctx.obj["db"]
            config = ctx.obj["config"]
            
            # Simulate command logic
            if db.show_exists("Test Show"):
                click.echo("Show exists")
            else:
                click.echo("Show not found")
            
            return 0
        
        # Create CLI context
        context = self.create_cli_context()
        
        # Configure mock behavior
        context["db"].show_exists.return_value = True
        
        # Invoke command
        result = self.cli_runner.invoke(
            mock_command,
            [],
            obj=context,
            catch_exceptions=False
        )
        
        # Assert success
        self.assert_cli_success(result, expected_output="Show exists")


class ExampleServiceTest(ServiceTestCase):
    """Example of service testing using ServiceTestCase."""
    
    def test_service_creation_and_behavior(self):
        """Example test showing service testing patterns."""
        # Create service with custom configuration
        config = self.get_test_config(llm__service="openai")
        
        # Create mock LLM service
        llm_service = self.create_test_llm_service(config, service_type="openai")
        
        # Test service initialization
        self.assert_service_initialized(llm_service, ["service_type", "model"])
        
        # Test service behavior
        result = llm_service.parse_filename("Test.Show.S01E01.mkv")
        self.assertIsInstance(result, dict)
        self.assertIn("show_name", result)
        self.assertIn("confidence", result)
        
        # Test mock service method calls
        self.assert_service_method_called(llm_service, "parse_filename", "Test.Show.S01E01.mkv")


class ExampleDatabaseTest(DatabaseTestCase):
    """Example of database testing using DatabaseTestCase."""
    
    def test_database_operations(self):
        """Example test showing database testing patterns."""
        # Create test database
        db_service = self.create_test_database()
        
        # Test initial state
        self.assert_database_empty(db_service)
        
        # Add test data
        from models.show import Show
        show = Show(
            sys_name="Example Show",
            sys_path="/tmp/example_show",
            tmdb_name="Example Show",
            tmdb_id=12345
        )
        db_service.add_show(show)
        
        # Test data existence
        self.assert_show_exists(db_service, "Example Show")
        
        # Test episodes
        self.assert_episodes_exist(db_service, 12345)


class ExampleConfigurationTest(ConfigurationTestCase):
    """Example of configuration testing using ConfigurationTestCase."""
    
    def test_configuration_variations(self):
        """Example test showing configuration testing patterns."""
        # Test multiple configuration variations
        variations = self.create_test_config_variations()
        
        for name, config in variations.items():
            with self.subTest(config=name):
                # Validate each configuration
                self.assert_configuration_valid(config)
                
                # Test specific configuration aspects
                if name == "openai_llm":
                    self.assert_config_value_equals(config, "llm", "service", "openai")
                elif name == "memory_db":
                    self.assert_config_value_equals(config, "sqlite", "db_file", ":memory:")
    
    def test_invalid_configurations(self):
        """Example test showing invalid configuration testing."""
        # Test invalid database configuration
        invalid_config = TestConfigFactory.create_invalid_config("database")
        self.assert_configuration_invalid(invalid_config, ["database.type"])
        
        # Test missing LLM configuration
        invalid_config = TestConfigFactory.create_invalid_config("missing_required")
        self.assert_configuration_invalid(invalid_config, ["database", "llm"])


class ExampleFullTest(FullTestCase):
    """Example of comprehensive testing using FullTestCase."""
    
    def test_end_to_end_scenario(self):
        """Example test showing end-to-end testing with all utilities."""
        # Create comprehensive test environment
        config = self.get_test_config(
            llm__service="ollama",
            sqlite__db_file=":memory:"
        )
        
        # Create all services
        services = self.create_test_services(config)
        
        # Test configuration
        self.assert_configuration_valid(config)
        
        # Test database operations
        db_service = services["db"]
        self.assert_database_empty(db_service)
        
        # Test LLM service
        llm_service = services["llm"]
        parse_result = llm_service.parse_filename("Test.Show.S01E01.mkv")
        self.assertIsInstance(parse_result, dict)
        
        # Test CLI context creation
        cli_context = self.create_cli_context(config)
        self.assertIn("db", cli_context)
        self.assertIn("llm_service", cli_context)
        
        # Test file operations
        temp_file = self.create_temp_file("test data")
        self.assert_file_exists(temp_file)


# Example of parametrized testing
class ExampleParametrizedTest(BaseTestCase):
    """Example of parametrized testing across service types."""
    
    @parametrize_llm_services
    def test_llm_service_types(self, llm_service_type):
        """Test functionality across different LLM service types."""
        config = self.get_test_config(llm__service=llm_service_type)
        llm_service = self.create_test_llm_service(config, service_type=llm_service_type)
        
        # Test that all service types can parse filenames
        result = llm_service.parse_filename("Test.Show.S01E01.mkv")
        self.assertIsInstance(result, dict)
        self.assertIn("show_name", result)
        self.assertGreater(result.get("confidence", 0), 0)
    
    @parametrize_database_types
    def test_database_types(self, db_type):
        """Test functionality across different database types."""
        config = self.get_test_config(database__type=db_type)
        db_service = self.create_test_db_service(config)
        
        # Test that all database types support basic operations
        self.assertTrue(hasattr(db_service, "show_exists"))
        self.assertTrue(hasattr(db_service, "add_show"))
        self.assertTrue(hasattr(db_service, "get_all_shows"))


# Example of integration testing
class ExampleIntegrationTest(FullTestCase):
    """Example of integration testing with multiple components."""
    
    def test_show_addition_workflow(self):
        """Test complete show addition workflow."""
        # Setup
        config = self.get_test_config()
        services = self.create_test_services(config)
        
        # Mock TMDB response
        services["tmdb"].search_show.return_value = {
            "results": [
                {
                    "id": 12345,
                    "name": "Test Show",
                    "first_air_date": "2020-01-01",
                    "overview": "A test show"
                }
            ]
        }
        
        # Mock LLM parsing
        services["llm"].parse_filename.return_value = {
            "show_name": "Test Show",
            "season": 1,
            "episode": 1,
            "confidence": 0.9
        }
        
        # Test workflow
        # 1. Parse filename
        parse_result = services["llm"].parse_filename("Test.Show.S01E01.mkv")
        self.assertEqual(parse_result["show_name"], "Test Show")
        
        # 2. Search TMDB
        search_result = services["tmdb"].search_show("Test Show")
        self.assertEqual(len(search_result["results"]), 1)
        
        # 3. Add to database
        from models.show import Show
        show = Show(
            sys_name="Test Show",
            sys_path="/tmp/test_show",
            tmdb_name="Test Show",
            tmdb_id=12345
        )
        services["db"].add_show(show)
        
        # 4. Verify addition
        self.assert_show_exists(services["db"], "Test Show")


if __name__ == "__main__":
    # Run example tests
    unittest.main(verbosity=2)