"""Tests for configuration validation system."""

import pytest
from unittest.mock import Mock, patch
from configparser import ConfigParser

from utils.config.config_validator import ConfigValidator
from utils.config.validation_models import ValidationResult, ValidationError, ErrorCode


class TestConfigValidator:
    """Test cases for ConfigValidator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ConfigValidator()
    
    def test_valid_openai_configuration(self):
        """Test validation of valid OpenAI configuration."""
        config = {
            'llm': {'service': 'openai'},
            'openai': {
                'api_key': 'sk-' + 'x' * 48,
                'model': 'qwen3:14b',
                'max_tokens': '4000',
                'temperature': '0.1'
            }
        }
        
        result = self.validator.validate_llm_config(config)
        
        assert result.is_valid
        assert len(result.errors) == 0
        assert len(result.suggestions) > 0  # Should have helpful suggestions
    
    def test_valid_anthropic_configuration(self):
        """Test validation of valid Anthropic configuration."""
        config = {
            'llm': {'service': 'anthropic'},
            'anthropic': {
                'api_key': 'sk-ant-' + 'x' * 35,
                'model': 'qwen3:14b',
                'max_tokens': '4000'
            }
        }
        
        result = self.validator.validate_llm_config(config)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_valid_ollama_configuration(self):
        """Test validation of valid Ollama configuration."""
        config = {
            'llm': {'service': 'ollama'},
            'ollama': {
                'model': 'qwen3:14b',
                'host': 'http://localhost:11434',
                'timeout': '30'
            }
        }
        
        result = self.validator.validate_llm_config(config)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_missing_llm_section(self):
        """Test validation fails when [llm] section is missing."""
        config = {
            'openai': {'api_key': 'sk-test123'}
        }
        
        result = self.validator.validate_llm_config(config)
        
        assert not result.is_valid
        assert len(result.errors) == 1
        assert result.errors[0].section == 'llm'
        assert result.errors[0].error_code == ErrorCode.MISSING_SECTION
    
    def test_missing_service_key(self):
        """Test validation fails when service key is missing."""
        config = {
            'llm': {},
            'openai': {'api_key': 'sk-test123'}
        }
        
        result = self.validator.validate_llm_config(config)
        
        assert not result.is_valid
        assert any(error.key == 'service' for error in result.errors)
        assert any(error.error_code == ErrorCode.MISSING_KEY for error in result.errors)
    
    def test_invalid_service_name(self):
        """Test validation fails with invalid service name."""
        config = {
            'llm': {'service': 'invalid_service'},
        }
        
        result = self.validator.validate_llm_config(config)
        
        assert not result.is_valid
        assert any(error.error_code == ErrorCode.INVALID_SERVICE for error in result.errors)
    
    def test_missing_service_section(self):
        """Test validation fails when service section is missing."""
        config = {
            'llm': {'service': 'openai'}
            # Missing [openai] section
        }
        
        result = self.validator.validate_llm_config(config)
        
        assert not result.is_valid
        assert any(error.section == 'openai' for error in result.errors)
        assert any(error.error_code == ErrorCode.MISSING_SECTION for error in result.errors)
    
    def test_missing_required_api_key(self):
        """Test validation fails when required API key is missing."""
        config = {
            'llm': {'service': 'openai'},
            'openai': {
                'model': 'qwen3:14b'
                # Missing api_key
            }
        }
        
        result = self.validator.validate_llm_config(config)
        
        assert not result.is_valid
        assert any(error.key == 'api_key' for error in result.errors)
        assert any(error.error_code == ErrorCode.MISSING_KEY for error in result.errors)
    
    def test_invalid_openai_api_key_format(self):
        """Test validation fails with invalid OpenAI API key format."""
        config = {
            'llm': {'service': 'openai'},
            'openai': {
                'api_key': 'invalid-key-format',
                'model': 'qwen3:14b'
            }
        }
        
        result = self.validator.validate_llm_config(config)
        
        assert not result.is_valid
        assert any(error.error_code == ErrorCode.API_KEY_INVALID for error in result.errors)
    
    def test_invalid_anthropic_api_key_format(self):
        """Test validation fails with invalid Anthropic API key format."""
        config = {
            'llm': {'service': 'anthropic'},
            'anthropic': {
                'api_key': 'sk-invalid-format',
                'model': 'qwen3:14b'
            }
        }
        
        result = self.validator.validate_llm_config(config)
        
        assert not result.is_valid
        assert any(error.error_code == ErrorCode.API_KEY_INVALID for error in result.errors)
    
    def test_invalid_numeric_values(self):
        """Test validation fails with invalid numeric values."""
        config = {
            'llm': {'service': 'openai'},
            'openai': {
                'api_key': 'sk-' + 'x' * 48,
                'model': 'qwen3:14b',
                'max_tokens': 'not_a_number',
                'temperature': '5.0'  # Too high
            }
        }
        
        result = self.validator.validate_llm_config(config)
        
        assert not result.is_valid
        assert len(result.errors) == 2  # Both max_tokens and temperature
        assert all(error.error_code == ErrorCode.INVALID_VALUE for error in result.errors)
    
    def test_invalid_ollama_host_url(self):
        """Test validation fails with invalid Ollama host URL."""
        config = {
            'llm': {'service': 'ollama'},
            'ollama': {
                'model': 'qwen3:14b',
                'host': 'not-a-valid-url'
            }
        }
        
        result = self.validator.validate_llm_config(config)
        
        assert not result.is_valid
        assert any(error.key == 'host' for error in result.errors)
        assert any(error.error_code == ErrorCode.INVALID_VALUE for error in result.errors)
    
    def test_case_insensitive_validation(self):
        """Test validation works with case-insensitive configuration."""
        config = {
            'LLM': {'SERVICE': 'OpenAI'},
            'OpenAI': {
                'API_KEY': 'sk-' + 'x' * 48,
                'MODEL': 'gpt-4'
            }
        }
        
        result = self.validator.validate_llm_config(config)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_configparser_input(self):
        """Test validation works with ConfigParser input."""
        config_parser = ConfigParser()
        config_parser.add_section('llm')
        config_parser.set('llm', 'service', 'ollama')
        config_parser.add_section('ollama')
        config_parser.set('ollama', 'model', 'llama2:7b')
        
        result = self.validator.validate_llm_config(config_parser)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_service_config_openai(self):
        """Test service-specific validation for OpenAI."""
        config = {
            'openai': {
                'api_key': 'sk-' + 'x' * 48,
                'model': 'qwen3:14b'
            }
        }
        
        result = self.validator.validate_service_config('openai', config)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_service_config_missing_section(self):
        """Test service validation fails when service section is missing."""
        config = {}
        
        result = self.validator.validate_service_config('openai', config)
        
        assert not result.is_valid
        assert any(error.section == 'openai' for error in result.errors)
    
    def test_validate_service_config_invalid_service(self):
        """Test service validation fails with invalid service name."""
        config = {}
        
        result = self.validator.validate_service_config('invalid', config)
        
        assert not result.is_valid
        assert any(error.error_code == ErrorCode.INVALID_SERVICE for error in result.errors)
    
    def test_multiple_errors_reported(self):
        """Test that multiple errors are reported together."""
        config = {
            'llm': {'service': 'openai'},
            'openai': {
                'api_key': 'invalid-key',
                'max_tokens': 'not_a_number',
                'temperature': '10.0'
            }
        }
        
        result = self.validator.validate_llm_config(config)
        
        assert not result.is_valid
        assert len(result.errors) == 3  # Invalid API key, max_tokens, temperature
    
    def test_warnings_for_unknown_models(self):
        """Test warnings are generated for unknown model names."""
        config = {
            'llm': {'service': 'openai'},
            'openai': {
                'api_key': 'sk-' + 'x' * 48,
                'model': 'qwen3:14b'
            }
        }
        
        result = self.validator.validate_llm_config(config)
        
        assert result.is_valid  # Should still be valid
        assert len(result.warnings) > 0  # But should have warnings
    
    def test_suggestions_for_missing_optional_config(self):
        """Test suggestions are provided for missing optional configuration."""
        config = {
            'llm': {'service': 'openai'},
            'openai': {
                'api_key': 'sk-' + 'x' * 48
                # Missing optional model, max_tokens, temperature
            }
        }
        
        result = self.validator.validate_llm_config(config)
        
        assert result.is_valid
        assert len(result.suggestions) > 0
        assert any('optional' in suggestion for suggestion in result.suggestions)
    
    def test_api_key_format_validation(self):
        """Test API key format validation for different services."""
        # Valid OpenAI key
        assert self.validator._is_valid_openai_api_key('sk-' + 'x' * 48)
        # Invalid OpenAI key
        assert not self.validator._is_valid_openai_api_key('invalid')
        
        # Valid Anthropic key
        assert self.validator._is_valid_anthropic_api_key('sk-ant-' + 'x' * 35)
        # Invalid Anthropic key
        assert not self.validator._is_valid_anthropic_api_key('sk-invalid')
    
    def test_url_validation(self):
        """Test URL validation for Ollama host."""
        # Valid URLs
        assert self.validator._is_valid_url('http://localhost:11434')
        assert self.validator._is_valid_url('https://example.com')
        assert self.validator._is_valid_url('http://192.168.1.100:8080')
        
        # Invalid URLs
        assert not self.validator._is_valid_url('not-a-url')
        assert not self.validator._is_valid_url('ftp://example.com')
        assert not self.validator._is_valid_url('localhost:11434')  # Missing protocol
    
    def test_model_name_validation(self):
        """Test model name validation for different services."""
        # OpenAI models
        assert self.validator._is_valid_openai_model('gpt-4')
        assert self.validator._is_valid_openai_model('gpt-3.5-turbo')
        assert not self.validator._is_valid_openai_model('invalid-model')
        
        # Anthropic models
        assert self.validator._is_valid_anthropic_model('claude-3-sonnet-20240229')
        assert self.validator._is_valid_anthropic_model('claude-2.1')
        assert not self.validator._is_valid_anthropic_model('gpt-4')
        
        # Ollama models
        assert self.validator._is_valid_ollama_model('llama2:7b')
        assert self.validator._is_valid_ollama_model('mistral')
        assert self.validator._is_valid_ollama_model('codellama:13b')
    
    def test_empty_configuration(self):
        """Test validation of completely empty configuration."""
        config = {}
        
        result = self.validator.validate_llm_config(config)
        
        assert not result.is_valid
        assert len(result.errors) > 0
        assert any(error.error_code == ErrorCode.MISSING_SECTION for error in result.errors)
    
    def test_validation_result_merge(self):
        """Test merging of validation results."""
        result1 = ValidationResult(is_valid=True, errors=[], warnings=['warning1'], suggestions=['suggestion1'])
        result2 = ValidationResult(is_valid=False, errors=[
            ValidationError('test', 'key', 'message', 'suggestion', ErrorCode.MISSING_KEY)
        ], warnings=['warning2'], suggestions=['suggestion2'])
        
        result1.merge(result2)
        
        assert not result1.is_valid
        assert len(result1.errors) == 1
        assert len(result1.warnings) == 2
        assert len(result1.suggestions) == 2
    
    def test_validation_error_string_representation(self):
        """Test string representation of validation errors."""
        error = ValidationError(
            section='openai',
            key='api_key',
            message='API key is missing',
            suggestion='Add your API key',
            error_code=ErrorCode.MISSING_KEY
        )
        
        error_str = str(error)
        
        assert '[openai].api_key' in error_str
        assert 'API key is missing' in error_str
        assert 'Add your API key' in error_str
