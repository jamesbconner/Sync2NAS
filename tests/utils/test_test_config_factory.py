"""
Unit tests for the TestConfigFactory and MockServiceFactory classes.

Tests the functionality of creating valid and invalid test configurations,
configuration overrides, and mock service creation.
"""

import pytest
import tempfile
import configparser
from pathlib import Path
from unittest.mock import Mock, patch

from tests.utils.test_config_factory import TestConfigFactory, MockServiceFactory


class TestTestConfigFactory:
    """Test cases for TestConfigFactory class."""
    
    def test_create_base_config(self):
        """Test creation of base configuration."""
        config = TestConfigFactory.create_base_config()
        
        # Verify all required sections are present
        required_sections = [
            "database", "sqlite", "llm", "ollama", "openai", "anthropic",
            "sftp", "tmdb", "transfers", "routing"
        ]
        
        for section in required_sections:
            assert section in config, f"Missing required section: {section}"
        
        # Verify database configuration
        assert config["database"]["type"] == "sqlite"
        assert "db_file" in config["sqlite"]
        
        # Verify LLM configuration
        assert config["llm"]["service"] == "ollama"
        assert "model" in config["ollama"]
        assert "api_key" in config["openai"]
        assert "api_key" in config["anthropic"]
        
        # Verify SFTP configuration
        assert "host" in config["sftp"]
        assert "username" in config["sftp"]
        
        # Verify paths configuration
        assert "incoming" in config["transfers"]
        assert "anime_tv_path" in config["routing"]
    
    def test_create_config_with_overrides_nested(self):
        """Test configuration creation with nested overrides."""
        config = TestConfigFactory.create_config_with_overrides(
            llm__service="openai",
            ollama__model="custom-model",
            database__type="postgresql"
        )
        
        # Verify overrides were applied
        assert config["llm"]["service"] == "openai"
        assert config["ollama"]["model"] == "custom-model"
        assert config["database"]["type"] == "postgresql"
        
        # Verify other values remain unchanged
        assert "api_key" in config["openai"]
        assert "host" in config["sftp"]
    
    def test_create_config_with_overrides_section_level(self):
        """Test configuration creation with section-level overrides."""
        custom_sftp = {
            "host": "custom-host",
            "port": "2222",
            "username": "custom-user"
        }
        
        config = TestConfigFactory.create_config_with_overrides(
            sftp=custom_sftp
        )
        
        # Verify section-level override was applied
        assert config["sftp"]["host"] == "custom-host"
        assert config["sftp"]["port"] == "2222"
        assert config["sftp"]["username"] == "custom-user"
        
        # Verify other sections remain unchanged
        assert config["llm"]["service"] == "ollama"
    
    def test_create_invalid_config_database(self):
        """Test creation of invalid database configuration."""
        config = TestConfigFactory.create_invalid_config("database")
        
        assert config["database"]["type"] == "invalid_db_type"
        
        # Verify other sections remain valid
        assert config["llm"]["service"] == "ollama"
        assert "model" in config["ollama"]
    
    def test_create_invalid_config_llm(self):
        """Test creation of invalid LLM configuration."""
        config = TestConfigFactory.create_invalid_config("llm")
        
        assert config["llm"]["service"] == "invalid_llm_service"
        
        # Verify other sections remain valid
        assert config["database"]["type"] == "sqlite"
    
    def test_create_invalid_config_missing_required(self):
        """Test creation of configuration with missing required sections."""
        config = TestConfigFactory.create_invalid_config("missing_required")
        
        assert "database" not in config
        assert "llm" not in config
        
        # Verify other sections remain
        assert "sftp" in config
        assert "tmdb" in config
    
    def test_create_invalid_config_unknown_section(self):
        """Test that unknown invalid section raises ValueError."""
        with pytest.raises(ValueError, match="Unknown invalid section type"):
            TestConfigFactory.create_invalid_config("unknown_section")
    
    def test_create_minimal_config(self):
        """Test creation of minimal configuration."""
        config = TestConfigFactory.create_minimal_config()
        
        # Verify only required sections are present
        required_sections = ["database", "sqlite", "llm", "ollama"]
        assert set(config.keys()) == set(required_sections)
        
        # Verify minimal content
        assert config["database"]["type"] == "sqlite"
        assert config["llm"]["service"] == "ollama"
        assert "model" in config["ollama"]
    
    def test_create_memory_db_config(self):
        """Test creation of in-memory database configuration."""
        config = TestConfigFactory.create_memory_db_config()
        
        assert config["sqlite"]["db_file"] == ":memory:"
        
        # Verify other sections remain unchanged
        assert config["llm"]["service"] == "ollama"
    
    def test_create_llm_service_configs(self):
        """Test creation of LLM service-specific configurations."""
        configs = TestConfigFactory.create_llm_service_configs()
        
        # Verify all service types are present
        assert "ollama" in configs
        assert "openai" in configs
        assert "anthropic" in configs
        
        # Verify service configurations
        assert configs["ollama"]["llm"]["service"] == "ollama"
        assert configs["openai"]["llm"]["service"] == "openai"
        assert configs["anthropic"]["llm"]["service"] == "anthropic"
        
        # Verify each config is complete
        for service_name, config in configs.items():
            assert "database" in config
            assert "llm" in config
    
    def test_create_configparser_format(self):
        """Test conversion to ConfigParser format."""
        config_dict = {
            "database": {"type": "sqlite"},
            "sqlite": {"db_file": "/tmp/test.db"},
            "llm": {"service": "ollama"}
        }
        
        parser = TestConfigFactory.create_configparser_format(config_dict)
        
        # Verify ConfigParser structure
        assert isinstance(parser, configparser.ConfigParser)
        assert "Database" in parser.sections()
        assert "Sqlite" in parser.sections()
        assert "Llm" in parser.sections()
        
        # Verify values
        assert parser["Database"]["type"] == "sqlite"
        assert parser["Sqlite"]["db_file"] == "/tmp/test.db"
        assert parser["Llm"]["service"] == "ollama"
    
    def test_write_config_file_default_path(self):
        """Test writing configuration to default temporary file."""
        config = TestConfigFactory.create_minimal_config()
        
        file_path = TestConfigFactory.write_config_file(config)
        
        # Verify file was created
        assert file_path.exists()
        assert file_path.suffix == ".ini"
        
        # Verify file content
        parser = configparser.ConfigParser()
        parser.read(file_path)
        
        assert "Database" in parser.sections()
        assert parser["Database"]["type"] == "sqlite"
        
        # Cleanup
        file_path.unlink()
    
    def test_write_config_file_custom_path(self, tmp_path):
        """Test writing configuration to custom file path."""
        config = TestConfigFactory.create_minimal_config()
        custom_path = tmp_path / "custom_config.ini"
        
        file_path = TestConfigFactory.write_config_file(config, custom_path)
        
        # Verify correct path was used
        assert file_path == custom_path
        assert file_path.exists()
        
        # Verify file content
        parser = configparser.ConfigParser()
        parser.read(file_path)
        
        assert "Database" in parser.sections()
    
    def test_create_test_directories(self, tmp_path):
        """Test creation of test directories from configuration."""
        config = {
            "transfers": {"incoming": str(tmp_path / "incoming")},
            "routing": {"anime_tv_path": str(tmp_path / "anime_tv")},
            "sftp": {"ssh_key_path": str(tmp_path / "ssh" / "key")}
        }
        
        created_dirs = TestConfigFactory.create_test_directories(config)
        
        # Verify directories were created
        assert "incoming_dir" in created_dirs
        assert "anime_tv_dir" in created_dirs
        assert "ssh_key_dir" in created_dirs
        
        assert created_dirs["incoming_dir"].exists()
        assert created_dirs["anime_tv_dir"].exists()
        assert created_dirs["ssh_key_dir"].exists()
    
    def test_get_validation_test_cases(self):
        """Test retrieval of validation test cases."""
        test_cases = TestConfigFactory.get_validation_test_cases()
        
        # Verify test cases structure
        assert isinstance(test_cases, list)
        assert len(test_cases) > 0
        
        for test_case in test_cases:
            assert "name" in test_case
            assert "config" in test_case
            assert "should_be_valid" in test_case
            assert "expected_errors" in test_case
            
            # Verify config is a dictionary
            assert isinstance(test_case["config"], dict)
            assert isinstance(test_case["should_be_valid"], bool)
            assert isinstance(test_case["expected_errors"], list)
        
        # Verify we have both valid and invalid cases
        valid_cases = [tc for tc in test_cases if tc["should_be_valid"]]
        invalid_cases = [tc for tc in test_cases if not tc["should_be_valid"]]
        
        assert len(valid_cases) > 0
        assert len(invalid_cases) > 0


class TestMockServiceFactory:
    """Test cases for MockServiceFactory class."""
    
    def test_create_mock_llm_service_default(self):
        """Test creation of default mock LLM service."""
        config = {"ollama": {"model": "gemma3:12b"}}
        
        mock_service = MockServiceFactory.create_mock_llm_service(config)
        
        # Verify mock service properties
        assert mock_service.service_type == "ollama"
        assert mock_service.model == "gemma3:12b"  # Uses model from config
        
        # Verify mock methods
        result = mock_service.parse_filename("test_file.mkv")
        assert result["show_name"] == "Test Show"
        assert result["season"] == 1
        assert result["episode"] == 1
        assert result["confidence"] == 0.9
        
        suggestion = mock_service.suggest_show_name("test", [])
        assert suggestion["show_name"] == "Test Show"
        assert suggestion["tmdb_id"] == 123
        
        batch_result = mock_service.batch_parse_filenames(["file1.mkv"])
        assert len(batch_result) == 1
        assert batch_result[0]["filename"] == "file1.mkv"
    
    def test_create_mock_llm_service_openai(self):
        """Test creation of OpenAI mock LLM service."""
        config = {"openai": {"model": "gemma3:12b"}}
        
        mock_service = MockServiceFactory.create_mock_llm_service(config, "openai")
        
        assert mock_service.service_type == "openai"
        assert mock_service.model == "gemma3:12b"  # Uses model from config
    
    def test_create_mock_llm_service_anthropic(self):
        """Test creation of Anthropic mock LLM service."""
        config = {"anthropic": {"model": "gemma3:12b"}}
        
        mock_service = MockServiceFactory.create_mock_llm_service(config, "anthropic")
        
        assert mock_service.service_type == "anthropic"
        assert mock_service.model == "gemma3:12b"  # Uses model from config
    
    def test_create_mock_db_service_default(self):
        """Test creation of default mock database service."""
        mock_db = MockServiceFactory.create_mock_db_service()
        
        # Verify mock methods return expected defaults
        assert mock_db.show_exists("test") is False
        assert mock_db.episodes_exist(1) is False
        assert mock_db.get_all_shows() == []
        assert mock_db.get_downloaded_files() == []
        assert mock_db.get_inventory_files() == []
        
        # Verify operations don't raise exceptions
        mock_db.add_show(Mock())
        mock_db.add_episode(Mock())
        mock_db.initialize()
    
    def test_create_mock_db_service_custom_path(self):
        """Test creation of mock database service with custom path."""
        custom_path = "/tmp/custom.db"
        
        mock_db = MockServiceFactory.create_mock_db_service(custom_path)
        
        # Mock should be created regardless of path
        assert mock_db is not None
    
    def test_create_mock_sftp_service(self):
        """Test creation of mock SFTP service."""
        config = {
            "sftp": {
                "host": "test-host",
                "port": "2222",
                "username": "test-user",
                "ssh_key_path": "/tmp/test_key"
            }
        }
        
        mock_sftp = MockServiceFactory.create_mock_sftp_service(config)
        
        # Verify service properties
        assert mock_sftp.host == "test-host"
        assert mock_sftp.port == 2222
        assert mock_sftp.username == "test-user"
        assert mock_sftp.ssh_key_path == "/tmp/test_key"
        
        # Verify mock methods
        files = mock_sftp.list_remote_dir("/remote")
        assert len(files) == 1
        assert files[0]["name"] == "test_file.mkv"
        
        recursive_files = mock_sftp.list_remote_files_recursive("/remote")
        assert len(recursive_files) == 1
        
        assert mock_sftp.download_file("remote", "local") is True
        assert mock_sftp.download_dir("remote", "local") is True
        
        # Verify context manager behavior
        with mock_sftp as sftp:
            assert sftp is mock_sftp
    
    def test_create_mock_sftp_service_minimal_config(self):
        """Test creation of mock SFTP service with minimal configuration."""
        config = {"sftp": {}}
        
        mock_sftp = MockServiceFactory.create_mock_sftp_service(config)
        
        # Verify default values are used
        assert mock_sftp.host == "localhost"
        assert mock_sftp.port == 22
        assert mock_sftp.username == "testuser"
        assert mock_sftp.ssh_key_path == "/tmp/test_key"


class TestConfigFactoryIntegration:
    """Integration tests for configuration factory functionality."""
    
    def test_config_factory_with_normalizer(self):
        """Test that factory configs work with ConfigNormalizer."""
        from utils.config.config_normalizer import ConfigNormalizer
        
        config = TestConfigFactory.create_base_config()
        normalizer = ConfigNormalizer()
        
        # Should not raise any exceptions
        normalized = normalizer.normalize_config(config)
        
        # Verify normalization preserves structure
        assert "database" in normalized
        assert "llm" in normalized
        assert normalized["llm"]["service"] == "ollama"
    
    def test_config_factory_with_validation(self):
        """Test that factory configs work with validation systems."""
        # This is a placeholder for when validation systems are available
        config = TestConfigFactory.create_base_config()
        
        # Basic validation - config should have required sections
        required_sections = ["database", "llm"]
        for section in required_sections:
            assert section in config
    
    def test_mock_services_integration(self):
        """Test that mock services work together."""
        config = TestConfigFactory.create_base_config()
        
        # Create all mock services
        llm_service = MockServiceFactory.create_mock_llm_service(config)
        db_service = MockServiceFactory.create_mock_db_service()
        sftp_service = MockServiceFactory.create_mock_sftp_service(config)
        
        # Verify they can be used together
        assert llm_service is not None
        assert db_service is not None
        assert sftp_service is not None
        
        # Test basic interactions
        parse_result = llm_service.parse_filename("test.mkv")
        assert parse_result["show_name"] == "Test Show"
        
        db_service.add_show(Mock())
        files = sftp_service.list_remote_dir("/test")
        assert len(files) == 1
    
    def test_temporary_file_cleanup(self):
        """Test that temporary files are properly handled."""
        config = TestConfigFactory.create_minimal_config()
        
        # Write config to temporary file
        file_path = TestConfigFactory.write_config_file(config)
        
        # Verify file exists
        assert file_path.exists()
        
        # Manual cleanup for test
        file_path.unlink()
        assert not file_path.exists()