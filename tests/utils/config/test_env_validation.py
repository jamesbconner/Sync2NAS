"""
Tests for environment variable validation functionality.
"""

import os
import pytest
from unittest.mock import patch

from utils.config.config_validator import ConfigValidator
from utils.config.config_normalizer import ConfigNormalizer
from utils.config.validation_models import ValidationResult, ErrorCode


class TestEnvironmentVariableValidation:
    """Test environment variable validation scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ConfigValidator()
        self.normalizer = ConfigNormalizer()
    
    @patch.dict(os.environ, {
        'SYNC2NAS_LLM_SERVICE': 'openai',
        'SYNC2NAS_OPENAI_API_KEY': 'sk-' + 'x' * 49,  # Valid format
        'SYNC2NAS_OPENAI_MODEL': 'gpt-4'
    })
    def test_valid_env_var_configuration(self):
        """Test that valid environment variables pass validation."""
        # Start with minimal config
        config = {'llm': {'service': 'ollama'}}  # Will be overridden by env var
        
        # Validate with environment overrides
        result = self.validator.validate_llm_config(config)
        
        # Should be valid
        assert result.is_valid
        assert len(result.errors) == 0
    
    @patch.dict(os.environ, {
        'SYNC2NAS_LLM_SERVICE': 'openai',
        'SYNC2NAS_OPENAI_API_KEY': 'invalid-key',  # Invalid format
    })
    def test_invalid_env_var_api_key(self):
        """Test that invalid environment variable API key fails validation."""
        config = {'llm': {'service': 'ollama'}}
        
        result = self.validator.validate_llm_config(config)
        
        # Should be invalid due to bad API key from env var
        assert not result.is_valid
        assert len(result.errors) > 0
        
        # Check that error mentions API key validation
        api_key_errors = [e for e in result.errors if 'api key' in e.message.lower()]
        assert len(api_key_errors) > 0
    
    @patch.dict(os.environ, {
        'SYNC2NAS_LLM_SERVICE': 'invalid_service'
    })
    def test_invalid_env_var_service(self):
        """Test that invalid environment variable service fails validation."""
        config = {'llm': {'service': 'openai'}}
        
        result = self.validator.validate_llm_config(config)
        
        # Should be invalid due to bad service from env var
        assert not result.is_valid
        assert len(result.errors) > 0
        
        # Check that error mentions invalid service
        service_errors = [e for e in result.errors if 'invalid llm service' in e.message.lower()]
        assert len(service_errors) > 0
    
    @patch.dict(os.environ, {
        'SYNC2NAS_OPENAI_TEMPERATURE': '5.0'  # Too high
    })
    def test_invalid_env_var_numeric_value(self):
        """Test that invalid numeric environment variables fail validation."""
        config = {
            'llm': {'service': 'openai'},
            'openai': {'api_key': 'sk-' + 'x' * 49, 'model': 'gemma3:12b'}
        }
        
        result = self.validator.validate_llm_config(config)
        
        # Should be invalid due to bad temperature from env var
        assert not result.is_valid
        assert len(result.errors) > 0
        
        # Check that error mentions temperature validation
        temp_errors = [e for e in result.errors if 'temperature' in e.message.lower()]
        assert len(temp_errors) > 0
    
    @patch.dict(os.environ, {
        'SYNC2NAS_OLLAMA_HOST': 'not-a-url'  # Invalid URL
    })
    def test_invalid_env_var_url(self):
        """Test that invalid URL environment variables fail validation."""
        config = {
            'llm': {'service': 'ollama'},
            'ollama': {'model': 'gemma3:12b'}
        }
        
        result = self.validator.validate_llm_config(config)
        
        # Should be invalid due to bad URL from env var
        assert not result.is_valid
        assert len(result.errors) > 0
        
        # Check that error mentions URL validation
        url_errors = [e for e in result.errors if 'url' in e.message.lower() or 'host' in e.message.lower()]
        assert len(url_errors) > 0
    
    @patch.dict(os.environ, {
        'SYNC2NAS_LLM_SERVICE': 'anthropic',
        'SYNC2NAS_ANTHROPIC_API_KEY': 'sk-ant-' + 'x' * 40,  # Valid format
        'SYNC2NAS_ANTHROPIC_MODEL': 'claude-3-sonnet-20240229'
    })
    def test_env_var_overrides_config_file(self):
        """Test that environment variables properly override config file values."""
        # Config file has OpenAI, but env vars specify Anthropic
        config = {
            'llm': {'service': 'openai'},
            'openai': {'api_key': 'sk-config-key', 'model': 'gemma3:12b'}
        }
        
        # Normalize with environment overrides
        normalized = self.normalizer.normalize_and_override(config)
        
        # Should use Anthropic from environment variables
        assert normalized['llm']['service'] == 'anthropic'
        assert normalized['anthropic']['api_key'] == 'sk-ant-' + 'x' * 40
        assert normalized['anthropic']['model'] == 'claude-3-sonnet-20240229'
        
        # OpenAI config should still exist but not be used
        assert 'openai' in normalized
        assert normalized['openai']['api_key'] == 'sk-config-key'
    
    @patch.dict(os.environ, {
        'SYNC2NAS_OLLAMA_MODEL': 'llama3.2',
        'SYNC2NAS_OLLAMA_HOST': 'http://remote-ollama:11434'
    })
    def test_env_var_creates_new_section(self):
        """Test that environment variables can create new configuration sections."""
        # Config has no Ollama section
        config = {
            'llm': {'service': 'openai'},
            'openai': {'api_key': 'sk-test', 'model': 'gemma3:12b'}
        }
        
        # Normalize with environment overrides
        normalized = self.normalizer.normalize_and_override(config)
        
        # Should create Ollama section from environment variables
        assert 'ollama' in normalized
        assert normalized['ollama']['model'] == 'llama3.2'
        assert normalized['ollama']['host'] == 'http://remote-ollama:11434'
    
    @patch.dict(os.environ, {}, clear=True)
    def test_no_env_vars_uses_config_file(self):
        """Test that without environment variables, config file values are used."""
        config = {
            'llm': {'service': 'openai'},
            'openai': {'api_key': 'sk-' + 'x' * 49, 'model': 'gemma3:12b'}
        }
        
        result = self.validator.validate_llm_config(config)
        
        # Should be valid using config file values
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_get_supported_env_vars(self):
        """Test that all expected environment variables are supported."""
        env_vars = self.normalizer.get_supported_env_vars()
        
        # Check that all expected variables are present
        expected_vars = [
            'SYNC2NAS_LLM_SERVICE',
            'SYNC2NAS_OPENAI_API_KEY',
            'SYNC2NAS_OPENAI_MODEL',
            'SYNC2NAS_OPENAI_MAX_TOKENS',
            'SYNC2NAS_OPENAI_TEMPERATURE',
            'SYNC2NAS_ANTHROPIC_API_KEY',
            'SYNC2NAS_ANTHROPIC_MODEL',
            'SYNC2NAS_ANTHROPIC_MAX_TOKENS',
            'SYNC2NAS_ANTHROPIC_TEMPERATURE',
            'SYNC2NAS_OLLAMA_HOST',
            'SYNC2NAS_OLLAMA_MODEL',
            'SYNC2NAS_OLLAMA_NUM_CTX',
        ]
        
        for var in expected_vars:
            assert var in env_vars, f"Environment variable {var} not found in supported variables"
        
        # Check mappings are correct
        assert env_vars['SYNC2NAS_LLM_SERVICE'] == ('llm', 'service')
        assert env_vars['SYNC2NAS_OPENAI_API_KEY'] == ('openai', 'api_key')
        assert env_vars['SYNC2NAS_ANTHROPIC_MODEL'] == ('anthropic', 'model')
        assert env_vars['SYNC2NAS_OLLAMA_HOST'] == ('ollama', 'host')
    
    @patch.dict(os.environ, {
        'SYNC2NAS_LLM_SERVICE': 'openai',
        'SYNC2NAS_OPENAI_API_KEY': 'sk-' + 'x' * 49,
        'SYNC2NAS_OPENAI_MODEL': 'gpt-4',
        'SYNC2NAS_OPENAI_MAX_TOKENS': '2000',
        'SYNC2NAS_OPENAI_TEMPERATURE': '0.5'
    })
    def test_multiple_env_vars_same_service(self):
        """Test multiple environment variables for the same service."""
        config = {'llm': {'service': 'ollama'}}  # Will be overridden
        
        # Normalize with environment overrides
        normalized = self.normalizer.normalize_and_override(config)
        
        # All OpenAI values should come from environment
        assert normalized['llm']['service'] == 'openai'
        assert normalized['openai']['api_key'] == 'sk-' + 'x' * 49
        assert normalized['openai']['model'] == 'gpt-4'
        assert normalized['openai']['max_tokens'] == '2000'
        assert normalized['openai']['temperature'] == '0.5'
        
        # Validate the result
        result = self.validator.validate_llm_config({'llm': {'service': 'ollama'}})
        assert result.is_valid
    
    @patch.dict(os.environ, {
        'SYNC2NAS_UNKNOWN_VAR': 'some_value'
    })
    def test_unknown_env_vars_ignored(self):
        """Test that unknown environment variables are ignored."""
        config = {
            'llm': {'service': 'openai'},
            'openai': {'api_key': 'sk-' + 'x' * 49, 'model': 'gemma3:12b'}
        }
        
        # Normalize with environment overrides
        normalized = self.normalizer.normalize_and_override(config)
        
        # Unknown env var should not affect configuration
        assert 'unknown' not in normalized
        assert normalized['llm']['service'] == 'openai'
        assert normalized['openai']['api_key'] == 'sk-' + 'x' * 49
        
        # Should still validate successfully
        result = self.validator.validate_llm_config(config)
        assert result.is_valid