"""
Tests for ConfigNormalizer class.
"""

import os
import pytest
from unittest.mock import patch
from configparser import ConfigParser

from utils.config.config_normalizer import ConfigNormalizer


class TestConfigNormalizer:
    """Test cases for ConfigNormalizer functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.normalizer = ConfigNormalizer()
    
    def test_normalize_config_basic(self):
        """Test basic configuration normalization."""
        raw_config = {
            'OpenAI': {'api_key': 'test_key', 'model': 'gemma3:12b'},
            'TMDB': {'api_key': 'tmdb_key'},
            'llm': {'service': 'openai'}
        }
        
        normalized = self.normalizer.normalize_config(raw_config)
        
        assert 'openai' in normalized
        assert 'tmdb' in normalized
        assert 'llm' in normalized
        assert normalized['openai']['api_key'] == 'test_key'
        assert normalized['openai']['model'] == 'gemma3:12b'  # Normalizer preserves original values
        assert normalized['tmdb']['api_key'] == 'tmdb_key'
        assert normalized['llm']['service'] == 'openai'
    
    def test_normalize_config_duplicate_sections(self):
        """Test handling of duplicate sections with different cases."""
        raw_config = {
            'OpenAI': {'api_key': 'uppercase_key', 'model': 'gemma3:12b'},
            'openai': {'api_key': 'lowercase_key', 'temperature': '0.1'},
            'OPENAI': {'max_tokens': '150'}
        }
        
        normalized = self.normalizer.normalize_config(raw_config)
        
        # Should have only one 'openai' section
        assert len([k for k in normalized.keys() if k.lower() == 'openai']) == 1
        assert 'openai' in normalized
        
        # Lowercase section should take precedence for conflicting keys
        assert normalized['openai']['api_key'] == 'lowercase_key'
        
        # Non-conflicting keys should be merged
        assert normalized['openai']['model'] == 'gemma3:12b'  # Normalizer preserves original values
        assert normalized['openai']['temperature'] == '0.1'
        assert normalized['openai']['max_tokens'] == '150'
    
    def test_normalize_config_configparser_input(self):
        """Test normalization with ConfigParser input."""
        config_parser = ConfigParser()
        config_parser.add_section('OpenAI')
        config_parser.set('OpenAI', 'api_key', 'test_key')
        config_parser.set('OpenAI', 'model', 'gpt-3.5-turbo')
        
        config_parser.add_section('llm')
        config_parser.set('llm', 'service', 'openai')
        
        normalized = self.normalizer.normalize_config(config_parser)
        
        assert 'openai' in normalized
        assert 'llm' in normalized
        assert normalized['openai']['api_key'] == 'test_key'
        assert normalized['llm']['service'] == 'openai'
    
    def test_normalize_config_unknown_sections(self):
        """Test normalization with unknown section names."""
        raw_config = {
            'CustomSection': {'key1': 'value1'},
            'another_section': {'key2': 'value2'}
        }
        
        normalized = self.normalizer.normalize_config(raw_config)
        
        # Unknown sections should be normalized to lowercase
        assert 'customsection' in normalized
        assert 'another_section' in normalized
        assert normalized['customsection']['key1'] == 'value1'
        assert normalized['another_section']['key2'] == 'value2'
    
    @patch.dict(os.environ, {
        'SYNC2NAS_LLM_SERVICE': 'anthropic',
        'SYNC2NAS_OPENAI_API_KEY': 'env_openai_key',
        'SYNC2NAS_ANTHROPIC_MODEL': 'claude-3-sonnet'
    })
    def test_apply_env_overrides(self):
        """Test environment variable override functionality."""
        config = {
            'llm': {'service': 'openai'},
            'openai': {'api_key': 'config_key', 'model': 'gemma3:12b'},
            'anthropic': {'api_key': 'anthropic_key'}
        }
        
        result = self.normalizer.apply_env_overrides(config)
        
        # Environment variables should override config values
        assert result['llm']['service'] == 'anthropic'
        assert result['openai']['api_key'] == 'env_openai_key'
        assert result['anthropic']['model'] == 'claude-3-sonnet'
        
        # Non-overridden values should remain unchanged
        assert result['openai']['model'] == 'gemma3:12b'  # Normalizer preserves original values
        assert result['anthropic']['api_key'] == 'anthropic_key'
    
    @patch.dict(os.environ, {
        'SYNC2NAS_OLLAMA_HOST': 'http://localhost:11434',
        'SYNC2NAS_OLLAMA_MODEL': 'llama3.2'
    })
    def test_apply_env_overrides_new_section(self):
        """Test environment variables creating new configuration sections."""
        config = {
            'llm': {'service': 'ollama'}
        }
        
        result = self.normalizer.apply_env_overrides(config)
        
        # Should create new 'ollama' section from environment variables
        assert 'ollama' in result
        assert result['ollama']['host'] == 'http://localhost:11434'
        assert result['ollama']['model'] == 'llama3.2'
    
    @patch.dict(os.environ, {}, clear=True)
    def test_apply_env_overrides_no_env_vars(self):
        """Test environment override with no environment variables set."""
        config = {
            'llm': {'service': 'openai'},
            'openai': {'api_key': 'test_key'}
        }
        
        result = self.normalizer.apply_env_overrides(config)
        
        # Configuration should remain unchanged
        assert result == config
    
    def test_get_normalized_value(self):
        """Test case-insensitive value retrieval."""
        config = {
            'openai': {'api_key': 'test_key', 'model': 'gemma3:12b'},
            'llm': {'service': 'openai'}
        }
        
        # Test with exact case
        assert self.normalizer.get_normalized_value(config, 'openai', 'api_key') == 'test_key'
        
        # Test with different case
        assert self.normalizer.get_normalized_value(config, 'OpenAI', 'api_key') == 'test_key'
        assert self.normalizer.get_normalized_value(config, 'OPENAI', 'model') == 'gemma3:12b'  # Normalizer preserves original values
        
        # Test with fallback
        assert self.normalizer.get_normalized_value(config, 'openai', 'nonexistent', 'default') == 'default'
        assert self.normalizer.get_normalized_value(config, 'nonexistent', 'key', 'fallback') == 'fallback'
    
    @patch.dict(os.environ, {
        'SYNC2NAS_LLM_SERVICE': 'anthropic',
        'SYNC2NAS_ANTHROPIC_API_KEY': 'env_key'
    })
    def test_normalize_and_override_complete_pipeline(self):
        """Test the complete normalization and override pipeline."""
        raw_config = {
            'OpenAI': {'api_key': 'openai_key'},
            'anthropic': {'model': 'gemma3:12b'},
            'LLM': {'service': 'openai'}
        }
        
        result = self.normalizer.normalize_and_override(raw_config)
        
        # Should normalize section names
        assert 'openai' in result
        assert 'anthropic' in result
        assert 'llm' in result
        
        # Should apply environment overrides
        assert result['llm']['service'] == 'anthropic'
        assert result['anthropic']['api_key'] == 'env_key'
        
        # Should preserve non-overridden values
        assert result['openai']['api_key'] == 'openai_key'
        assert result['anthropic']['model'] == 'gemma3:12b'  # Normalizer preserves original values
    
    def test_get_supported_env_vars(self):
        """Test retrieval of supported environment variables."""
        env_vars = self.normalizer.get_supported_env_vars()
        
        # Should contain expected mappings
        assert 'SYNC2NAS_LLM_SERVICE' in env_vars
        assert 'SYNC2NAS_OPENAI_API_KEY' in env_vars
        assert 'SYNC2NAS_ANTHROPIC_API_KEY' in env_vars
        assert 'SYNC2NAS_OLLAMA_HOST' in env_vars
        
        # Should map to correct sections and keys
        assert env_vars['SYNC2NAS_LLM_SERVICE'] == ('llm', 'service')
        assert env_vars['SYNC2NAS_OPENAI_API_KEY'] == ('openai', 'api_key')
        assert env_vars['SYNC2NAS_ANTHROPIC_MODEL'] == ('anthropic', 'model')
    
    def test_clear_cache(self):
        """Test cache clearing functionality."""
        # This is mainly for coverage since cache is currently not used
        # but provides foundation for future caching implementation
        self.normalizer.clear_cache()
        assert len(self.normalizer._normalized_cache) == 0
    
    def test_section_precedence_order(self):
        """Test that lowercase sections take precedence over mixed case."""
        raw_config = {
            'OPENAI': {'api_key': 'upper_key', 'model': 'gemma3:12b'},
            'OpenAI': {'api_key': 'mixed_key', 'temperature': '0.5'},
            'openai': {'api_key': 'lower_key', 'max_tokens': '100'}
        }
        
        normalized = self.normalizer.normalize_config(raw_config)
        
        # Lowercase should win for conflicting keys
        assert normalized['openai']['api_key'] == 'lower_key'
        
        # All non-conflicting keys should be present
        assert normalized['openai']['model'] == 'gemma3:12b'  # Normalizer preserves original values
        assert normalized['openai']['temperature'] == '0.5'
        assert normalized['openai']['max_tokens'] == '100'
    
    def test_empty_config(self):
        """Test handling of empty configuration."""
        result = self.normalizer.normalize_config({})
        assert result == {}
        
        result = self.normalizer.apply_env_overrides({})
        assert result == {}
    
    @patch.dict(os.environ, {'SYNC2NAS_INVALID_VAR': 'value'})
    def test_unknown_env_vars_ignored(self):
        """Test that unknown environment variables are ignored."""
        config = {'llm': {'service': 'openai'}}
        
        result = self.normalizer.apply_env_overrides(config)
        
        # Should remain unchanged since SYNC2NAS_INVALID_VAR is not in mapping
        assert result == config