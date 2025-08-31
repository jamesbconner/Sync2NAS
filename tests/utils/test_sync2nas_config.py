import pytest
import configparser
from utils.sync2nas_config import (
    parse_sftp_paths, 
    get_config_section, 
    validate_test_config,
    get_config_value,
    get_config_int,
    get_config_float,
    get_config_bool,
    get_config_string,
    has_config_section,
    has_config_key,
    get_config_sections
)
from tests.utils.test_config_factory import TestConfigFactory

def test_parse_multiple_paths_from_config():
    config = configparser.ConfigParser()
    config["SFTP"] = {"paths": "/a,/b , /c/"}
    assert parse_sftp_paths(config) == ["/a", "/b", "/c/"]

def test_parse_single_path_from_config():
    config = configparser.ConfigParser()
    config["SFTP"] = {"paths": "/a"}
    assert parse_sftp_paths(config) == ["/a"]


class TestGetConfigSection:
    """Test cases for get_config_section function."""
    
    def test_get_config_section_normalized_dict(self):
        """Test getting section from normalized configuration dict."""
        config = {
            "database": {"type": "sqlite"},
            "llm": {"service": "ollama"}
        }
        
        section = get_config_section(config, "database")
        assert section == {"type": "sqlite"}
        
        section = get_config_section(config, "llm")
        assert section == {"service": "ollama"}
    
    def test_get_config_section_case_insensitive_dict(self):
        """Test case-insensitive section lookup in normalized dict."""
        config = {
            "database": {"type": "sqlite"},
            "llm": {"service": "ollama"}
        }
        
        # Should work with different cases
        section = get_config_section(config, "DATABASE")
        assert section == {"type": "sqlite"}
        
        section = get_config_section(config, "LLM")
        assert section == {"service": "ollama"}
    
    def test_get_config_section_configparser(self):
        """Test getting section from ConfigParser."""
        config = configparser.ConfigParser()
        config["Database"] = {"type": "sqlite"}
        config["LLM"] = {"service": "ollama"}
        
        section = get_config_section(config, "Database")
        assert section == {"type": "sqlite"}
        
        section = get_config_section(config, "LLM")
        assert section == {"service": "ollama"}
    
    def test_get_config_section_configparser_case_insensitive(self):
        """Test case-insensitive section lookup in ConfigParser."""
        config = configparser.ConfigParser()
        config["Database"] = {"type": "sqlite"}
        config["LLM"] = {"service": "ollama"}
        
        # Should work with different cases
        section = get_config_section(config, "database")
        assert section == {"type": "sqlite"}
        
        section = get_config_section(config, "llm")
        assert section == {"service": "ollama"}
    
    def test_get_config_section_not_found_dict(self):
        """Test error when section not found in dict."""
        config = {"database": {"type": "sqlite"}}
        
        with pytest.raises(ValueError, match="Configuration section 'missing' not found"):
            get_config_section(config, "missing")
    
    def test_get_config_section_not_found_configparser(self):
        """Test error when section not found in ConfigParser."""
        config = configparser.ConfigParser()
        config["Database"] = {"type": "sqlite"}
        
        with pytest.raises(ValueError, match="Configuration section 'missing' not found"):
            get_config_section(config, "missing")


class TestValidateTestConfig:
    """Test cases for validate_test_config function."""
    
    def test_validate_test_config_valid_base(self):
        """Test validation of valid base configuration."""
        config = TestConfigFactory.create_base_config()
        
        # Should not raise any exceptions
        result = validate_test_config(config)
        assert result is True
    
    def test_validate_test_config_valid_minimal(self):
        """Test validation of valid minimal configuration."""
        config = TestConfigFactory.create_minimal_config()
        
        # Should not raise any exceptions
        result = validate_test_config(config)
        assert result is True
    
    def test_validate_test_config_missing_database_section(self):
        """Test validation failure when database section is missing."""
        config = {"llm": {"service": "ollama"}}
        
        with pytest.raises(ValueError, match="Configuration validation failed"):
            validate_test_config(config)
    
    def test_validate_test_config_missing_llm_section(self):
        """Test validation failure when LLM section is missing."""
        config = {"database": {"type": "sqlite"}}
        
        with pytest.raises(ValueError, match="Configuration validation failed"):
            validate_test_config(config)
    
    def test_validate_test_config_missing_database_type(self):
        """Test validation failure when database type is missing."""
        config = {
            "database": {},
            "llm": {"service": "ollama"},
            "ollama": {"model": "test"}
        }
        
        with pytest.raises(ValueError, match="Database type is required"):
            validate_test_config(config)
    
    def test_validate_test_config_missing_sqlite_db_file(self):
        """Test validation failure when SQLite db_file is missing."""
        config = {
            "database": {"type": "sqlite"},
            "sqlite": {},
            "llm": {"service": "ollama"},
            "ollama": {"model": "test"}
        }
        
        with pytest.raises(ValueError, match="SQLite db_file is required"):
            validate_test_config(config)
    
    def test_validate_test_config_missing_llm_service(self):
        """Test validation failure when LLM service is missing."""
        config = {
            "database": {"type": "sqlite"},
            "sqlite": {"db_file": ":memory:"},
            "llm": {}
        }
        
        with pytest.raises(ValueError, match="LLM service is required"):
            validate_test_config(config)
    
    def test_validate_test_config_missing_ollama_model(self):
        """Test validation failure when Ollama model is missing."""
        config = {
            "database": {"type": "sqlite"},
            "sqlite": {"db_file": ":memory:"},
            "llm": {"service": "ollama"},
            "ollama": {}
        }
        
        with pytest.raises(ValueError, match="Ollama model is required"):
            validate_test_config(config)
    
    def test_validate_test_config_missing_openai_api_key(self):
        """Test validation failure when OpenAI API key is missing."""
        config = {
            "database": {"type": "sqlite"},
            "sqlite": {"db_file": ":memory:"},
            "llm": {"service": "openai"},
            "openai": {}
        }
        
        with pytest.raises(ValueError, match="OpenAI API key is required"):
            validate_test_config(config)
    
    def test_validate_test_config_missing_anthropic_api_key(self):
        """Test validation failure when Anthropic API key is missing."""
        config = {
            "database": {"type": "sqlite"},
            "sqlite": {"db_file": ":memory:"},
            "llm": {"service": "anthropic"},
            "anthropic": {}
        }
        
        with pytest.raises(ValueError, match="Anthropic API key is required"):
            validate_test_config(config)
    
    def test_validate_test_config_all_llm_services(self):
        """Test validation of all supported LLM services."""
        llm_configs = TestConfigFactory.create_llm_service_configs()
        
        for service_name, config in llm_configs.items():
            # Should not raise any exceptions
            result = validate_test_config(config)
            assert result is True


class TestConfigValueHelpers:
    """Test cases for configuration value helper functions."""
    
    def test_get_config_value_with_type_conversion(self):
        """Test get_config_value with type conversion."""
        config = {
            "database": {"timeout": "30", "enabled": "true", "max_connections": "10"}
        }
        
        # Test integer conversion
        timeout = get_config_value(config, "database", "timeout", 0, int)
        assert timeout == 30
        assert isinstance(timeout, int)
        
        # Test boolean conversion
        enabled = get_config_value(config, "database", "enabled", False, bool)
        assert enabled is True
        assert isinstance(enabled, bool)
        
        # Test float conversion
        max_conn = get_config_value(config, "database", "max_connections", 0.0, float)
        assert max_conn == 10.0
        assert isinstance(max_conn, float)
    
    def test_get_config_value_fallback_on_conversion_error(self):
        """Test fallback when type conversion fails."""
        config = {
            "database": {"invalid_int": "not_a_number"}
        }
        
        # Should return fallback when conversion fails
        result = get_config_value(config, "database", "invalid_int", 42, int)
        assert result == 42
    
    def test_get_config_value_case_insensitive_key(self):
        """Test case-insensitive key lookup."""
        config = {
            "database": {"TimeOut": "30", "ENABLED": "true"}
        }
        
        # Should find keys regardless of case
        timeout = get_config_value(config, "database", "timeout", 0, int)
        assert timeout == 30
        
        enabled = get_config_value(config, "database", "enabled", False, bool)
        assert enabled is True
    
    def test_get_config_int(self):
        """Test get_config_int helper function."""
        config = {"section": {"key": "42"}}
        
        result = get_config_int(config, "section", "key", 0)
        assert result == 42
        assert isinstance(result, int)
        
        # Test fallback
        result = get_config_int(config, "section", "missing", 99)
        assert result == 99
    
    def test_get_config_float(self):
        """Test get_config_float helper function."""
        config = {"section": {"key": "3.14"}}
        
        result = get_config_float(config, "section", "key", 0.0)
        assert result == 3.14
        assert isinstance(result, float)
        
        # Test fallback
        result = get_config_float(config, "section", "missing", 2.71)
        assert result == 2.71
    
    def test_get_config_bool(self):
        """Test get_config_bool helper function."""
        config = {"section": {"enabled": "true", "disabled": "false"}}
        
        result = get_config_bool(config, "section", "enabled", False)
        assert result is True
        
        result = get_config_bool(config, "section", "disabled", True)
        assert result is False
        
        # Test fallback
        result = get_config_bool(config, "section", "missing", True)
        assert result is True
    
    def test_get_config_string(self):
        """Test get_config_string helper function."""
        config = {"section": {"key": "value"}}
        
        result = get_config_string(config, "section", "key", "default")
        assert result == "value"
        assert isinstance(result, str)
        
        # Test fallback
        result = get_config_string(config, "section", "missing", "default")
        assert result == "default"
    
    def test_has_config_section(self):
        """Test has_config_section helper function."""
        config = {"database": {"type": "sqlite"}, "llm": {"service": "ollama"}}
        
        assert has_config_section(config, "database") is True
        assert has_config_section(config, "DATABASE") is True  # Case insensitive
        assert has_config_section(config, "missing") is False
    
    def test_has_config_key(self):
        """Test has_config_key helper function."""
        config = {"database": {"type": "sqlite", "TimeOut": "30"}}
        
        assert has_config_key(config, "database", "type") is True
        assert has_config_key(config, "database", "TYPE") is True  # Case insensitive
        assert has_config_key(config, "database", "timeout") is True  # Case insensitive
        assert has_config_key(config, "database", "missing") is False
        assert has_config_key(config, "missing_section", "key") is False
    
    def test_get_config_sections(self):
        """Test get_config_sections helper function."""
        config = {"database": {}, "llm": {}, "sftp": {}}
        
        sections = get_config_sections(config)
        assert set(sections) == {"database", "llm", "sftp"}
        
        # Test with ConfigParser
        import configparser
        parser = configparser.ConfigParser()
        parser["Database"] = {}
        parser["LLM"] = {}
        
        sections = get_config_sections(parser)
        assert set(sections) == {"Database", "LLM"}


class TestConfigErrorHandling:
    """Test cases for configuration error handling."""
    
    def test_get_config_section_none_config(self):
        """Test error handling when config is None."""
        with pytest.raises(ValueError, match="Configuration object cannot be None"):
            get_config_section(None, "section")
    
    def test_get_config_section_empty_section_name(self):
        """Test error handling when section name is empty."""
        config = {"database": {}}
        
        with pytest.raises(ValueError, match="Section name must be a non-empty string"):
            get_config_section(config, "")
        
        with pytest.raises(ValueError, match="Section name must be a non-empty string"):
            get_config_section(config, "   ")
    
    def test_get_config_section_unsupported_type(self):
        """Test error handling when config is unsupported type."""
        with pytest.raises(TypeError, match="Unsupported configuration type"):
            get_config_section(["not", "a", "dict"], "section")
    
    def test_get_config_value_invalid_inputs(self):
        """Test error handling for invalid inputs in get_config_value."""
        config = {"database": {"key": "value"}}
        
        with pytest.raises(ValueError, match="Section name must be a non-empty string"):
            get_config_value(config, "", "key")
        
        with pytest.raises(ValueError, match="Key name must be a non-empty string"):
            get_config_value(config, "database", "")
    
    def test_validate_test_config_invalid_type(self):
        """Test validation error when config is not a dictionary."""
        with pytest.raises(TypeError, match="Configuration must be a dictionary"):
            validate_test_config("not a dict")
    
    def test_validate_test_config_empty_config(self):
        """Test validation error when config is empty."""
        with pytest.raises(ValueError, match="Configuration cannot be empty"):
            validate_test_config({})
    