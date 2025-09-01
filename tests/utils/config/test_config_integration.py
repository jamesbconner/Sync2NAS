"""
Integration tests for configuration normalization with LLM services.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from configparser import ConfigParser

from utils.sync2nas_config import load_configuration, get_config_value
from services.llm_factory import create_llm_service
from utils.config.config_normalizer import ConfigNormalizer


class TestConfigIntegration:
    """Test integration between configuration normalization and LLM services."""
    
    def test_load_configuration_normalized(self, tmp_path):
        """Test loading configuration with normalization enabled."""
        # Create test config file
        config_content = """
[OpenAI]
api_key = test_openai_key
model = gpt-4

[LLM]
service = openai

[TMDB]
api_key = test_tmdb_key
"""
        config_file = tmp_path / "test_config.ini"
        config_file.write_text(config_content)
        
        # Load with normalization
        config = load_configuration(str(config_file), normalize=True)
        
        # Should be a dict with normalized section names
        assert isinstance(config, dict)
        assert 'openai' in config
        assert 'llm' in config
        assert 'tmdb' in config
        
        # Values should be accessible
        assert config['openai']['api_key'] == 'test_openai_key'
        assert config['llm']['service'] == 'openai'
    
    def test_load_configuration_raw(self, tmp_path):
        """Test loading configuration without normalization."""
        # Create test config file
        config_content = """
[OpenAI]
api_key = test_openai_key

[llm]
service = openai
"""
        config_file = tmp_path / "test_config.ini"
        config_file.write_text(config_content)
        
        # Load without normalization
        config = load_configuration(str(config_file), normalize=False)
        
        # Should be ConfigParser
        assert isinstance(config, ConfigParser)
        assert 'OpenAI' in config.sections()
        assert 'llm' in config.sections()
    
    @patch.dict(os.environ, {
        'SYNC2NAS_LLM_SERVICE': 'anthropic',
        'SYNC2NAS_OPENAI_API_KEY': 'env_openai_key'
    })
    def test_environment_override_integration(self, tmp_path):
        """Test that environment variables override config file values."""
        # Create test config file
        config_content = """
[openai]
api_key = config_openai_key

[llm]
service = openai
"""
        config_file = tmp_path / "test_config.ini"
        config_file.write_text(config_content)
        
        # Load with normalization (includes env overrides)
        config = load_configuration(str(config_file), normalize=True)
        
        # Environment variables should override config values
        assert config['llm']['service'] == 'anthropic'
        assert config['openai']['api_key'] == 'env_openai_key'
    
    def test_get_config_value_with_dict(self):
        """Test get_config_value with normalized dict."""
        config = {
            'openai': {'api_key': 'test_key', 'model': 'qwen3:14b'},
            'llm': {'service': 'openai'}
        }
        
        # Test exact case
        assert get_config_value(config, 'openai', 'api_key') == 'test_key'
        
        # Test case insensitive
        assert get_config_value(config, 'OpenAI', 'model') == 'qwen3:14b'  # Uses actual config value
        assert get_config_value(config, 'LLM', 'service') == 'openai'
        
        # Test fallback
        assert get_config_value(config, 'openai', 'nonexistent', 'default') == 'default'
    
    def test_get_config_value_with_configparser(self):
        """Test get_config_value with ConfigParser."""
        config = ConfigParser()
        config.add_section('OpenAI')
        config.set('OpenAI', 'api_key', 'test_key')
        config.add_section('llm')
        config.set('llm', 'service', 'openai')
        
        # Test normal access
        assert get_config_value(config, 'OpenAI', 'api_key') == 'test_key'
        assert get_config_value(config, 'llm', 'service') == 'openai'
        
        # Test fallback
        assert get_config_value(config, 'OpenAI', 'nonexistent', 'default') == 'default'
        assert get_config_value(config, 'nonexistent', 'key', 'fallback') == 'fallback'
    
    @patch('services.llm_implementations.openai_implementation.openai.OpenAI')
    def test_llm_factory_with_normalized_config(self, mock_openai):
        """Test LLM factory with normalized configuration."""
        # Mock OpenAI client
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        # Create normalized config with valid test API key format
        config = {
            'openai': {'api_key': 'sk-' + 'x' * 49, 'model': 'qwen3:14b'},  # Valid format for testing
            'llm': {'service': 'openai'}
        }
        
        # Create LLM service without health check to avoid network calls
        service = create_llm_service(config, validate_health=False)
        
        # Should create OpenAI service with correct config
        assert service is not None
        assert service.api_key == 'sk-' + 'x' * 49
        assert service.model == 'qwen3:14b'  # Uses actual config value
    
    @patch('services.llm_implementations.openai_implementation.openai.OpenAI')
    def test_llm_factory_with_configparser(self, mock_openai):
        """Test LLM factory with ConfigParser."""
        # Mock OpenAI client
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        # Create ConfigParser with valid test API key format
        config = ConfigParser()
        config.add_section('openai')
        config.set('openai', 'api_key', 'sk-' + 'x' * 49)  # Valid format for testing
        config.set('openai', 'model', 'gpt-4')
        config.add_section('llm')
        config.set('llm', 'service', 'openai')
        
        # Create LLM service without health check to avoid network calls
        service = create_llm_service(config, validate_health=False)
        
        # Should create OpenAI service with correct config
        assert service is not None
        assert service.api_key == 'sk-' + 'x' * 49
        assert service.model == 'gpt-4'
    
    def test_case_insensitive_service_selection(self):
        """Test that LLM service selection is case insensitive."""
        test_cases = [
            {'llm': {'service': 'OpenAI'}},
            {'llm': {'service': 'OPENAI'}},
            {'llm': {'service': 'openai'}},
            {'llm': {'service': 'Ollama'}},
            {'llm': {'service': 'OLLAMA'}},
            {'llm': {'service': 'ollama'}},
        ]
        
        for config in test_cases:
            service_type = get_config_value(config, 'llm', 'service', 'ollama').lower()
            assert service_type in ['openai', 'ollama', 'anthropic']
    
    @patch('services.llm_implementations.ollama_implementation.Client')
    def test_ollama_with_normalized_config(self, mock_client):
        """Test Ollama service creation with normalized config."""
        config = {
            'ollama': {
                'model': 'qwen3:14b',
                'host': 'http://localhost:11434',
                'num_ctx': '4096'
            },
            'llm': {'service': 'ollama'}
        }
        
        service = create_llm_service(config)
        
        assert service is not None
        assert service.model == 'qwen3:14b'  # Uses actual config value
        assert service.num_ctx == 4096
        mock_client.assert_called_with(host='http://localhost:11434')
    
    def test_config_normalizer_integration(self):
        """Test direct ConfigNormalizer integration."""
        raw_config = {
            'OpenAI': {'api_key': 'test_key'},
            'LLM': {'service': 'openai'},
            'TMDB': {'api_key': 'tmdb_key'}
        }
        
        normalizer = ConfigNormalizer()
        normalized = normalizer.normalize_config(raw_config)
        
        # All sections should be lowercase
        assert 'openai' in normalized
        assert 'llm' in normalized
        assert 'tmdb' in normalized
        
        # Values should be preserved
        assert normalized['openai']['api_key'] == 'test_key'
        assert normalized['llm']['service'] == 'openai'
        assert normalized['tmdb']['api_key'] == 'tmdb_key'
