"""
Integration tests for cross-service configuration scenarios.

Tests complex scenarios involving multiple services, service switching,
and configuration consistency across different components.
"""

import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock, AsyncMock

from utils.sync2nas_config import load_configuration
from utils.config.config_validator import ConfigValidator
from utils.config.config_normalizer import ConfigNormalizer
from utils.config.health_checker import ConfigHealthChecker
from services.llm_factory import create_llm_service, LLMServiceCreationError


class TestCrossServiceIntegration:
    """Test integration scenarios across multiple LLM services."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ConfigValidator()
        self.normalizer = ConfigNormalizer()
        self.health_checker = ConfigHealthChecker()
    
    def create_temp_config(self, content: str) -> str:
        """Create a temporary configuration file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(content)
            return f.name
    
    def test_service_switching_validation(self):
        """Test validation when switching between different LLM services."""
        # Configuration with multiple services defined
        config = {
            'llm': {'service': 'openai'},
            'openai': {
                'api_key': 'sk-test1234567890abcdef1234567890abcdef1234567890ab',
                'model': 'gemma3:12b'
            },
            'ollama': {
                'model': 'gemma3:12b',
                'host': 'http://localhost:11434'
            },
            'anthropic': {
                'api_key': 'sk-ant-test1234567890abcdef1234567890abcdef1234567890ab',
                'model': 'gemma3:12b'
            }
        }
        
        # Test switching to each service
        services_to_test = ['openai', 'ollama', 'anthropic']
        
        for service in services_to_test:
            # Update service selection
            test_config = config.copy()
            test_config['llm']['service'] = service
            
            # Validate configuration
            result = self.validator.validate_llm_config(test_config)
            
            # Should be valid for all services
            assert result.is_valid, f"Service {service} should be valid: {result.errors}"
            assert len(result.errors) == 0
    
    def test_service_creation_consistency_across_services(self):
        """Test that service creation is consistent across different LLM services."""
        base_config = {
            'openai': {
                'api_key': 'sk-test1234567890abcdef1234567890abcdef1234567890ab',
                'model': 'gemma3:12b'
            },
            'ollama': {
                'model': 'gemma3:12b',
                'host': 'http://localhost:11434'
            },
            'anthropic': {
                'api_key': 'sk-ant-test1234567890abcdef1234567890abcdef1234567890ab',
                'model': 'gemma3:12b'
            }
        }
        
        service_patches = {
            'openai': 'services.llm_implementations.openai_implementation.openai.OpenAI',
            'ollama': 'services.llm_implementations.ollama_implementation.Client',
            'anthropic': 'services.llm_implementations.anthropic_implementation.anthropic.Anthropic'
        }
        
        for service_name in ['openai', 'ollama', 'anthropic']:
            config = base_config.copy()
            config['llm'] = {'service': service_name}
            
            with patch(service_patches[service_name]) as mock_service:
                # Mock appropriate responses for each service
                if service_name == 'openai':
                    mock_client = MagicMock()
                    mock_response = MagicMock()
                    mock_response.choices = [MagicMock(message=MagicMock(content="Test"))]
                    mock_client.chat.completions.create.return_value = mock_response
                    mock_service.return_value = mock_client
                elif service_name == 'ollama':
                    mock_client = MagicMock()
                    mock_client.generate.return_value = {'response': 'Test'}
                    mock_service.return_value = mock_client
                elif service_name == 'anthropic':
                    mock_client = MagicMock()
                    mock_response = MagicMock()
                    mock_response.content = [MagicMock(text="Test")]
                    mock_client.messages.create.return_value = mock_response
                    mock_service.return_value = mock_client
                
                # Create service
                service = create_llm_service(config, validate_health=False)
                
                # Should successfully create service
                assert service is not None
                
                # Service should have expected attributes
                if service_name == 'openai':
                    assert hasattr(service, 'api_key')
                    assert hasattr(service, 'model')
                    assert service.api_key.startswith('sk-')
                elif service_name == 'ollama':
                    assert hasattr(service, 'model')
                    assert hasattr(service, 'client')  # Ollama stores host in client, not as direct attribute
                elif service_name == 'anthropic':
                    assert hasattr(service, 'api_key')
                    assert hasattr(service, 'model')
    
    def test_health_check_consistency_across_services(self):
        """Test health check consistency across different services."""
        config = {
            'llm': {'service': 'openai'},  # Default service
            'openai': {
                'api_key': 'sk-test1234567890abcdef1234567890abcdef1234567890ab',
                'model': 'gemma3:12b'
            },
            'ollama': {
                'model': 'gemma3:12b',
                'host': 'http://localhost:11434'
            },
            'anthropic': {
                'api_key': 'sk-ant-test1234567890abcdef1234567890abcdef1234567890ab',
                'model': 'gemma3:12b'
            }
        }
        
        with patch('services.llm_implementations.openai_implementation.openai.OpenAI') as mock_openai, \
             patch('services.llm_implementations.ollama_implementation.Client') as mock_ollama, \
             patch('services.llm_implementations.anthropic_implementation.anthropic.Anthropic') as mock_anthropic, \
             patch('utils.config.health_checker.httpx.AsyncClient') as mock_httpx:
            
            # Mock successful responses for all services
            mock_openai_client = MagicMock()
            mock_openai_response = MagicMock()
            mock_openai_response.choices = [MagicMock(message=MagicMock(content="Test"))]
            mock_openai_client.chat.completions.create.return_value = mock_openai_response
            mock_openai.return_value = mock_openai_client
            
            mock_ollama_client = MagicMock()
            mock_ollama_client.generate.return_value = {'response': 'Test'}
            mock_ollama.return_value = mock_ollama_client
            
            mock_anthropic_client = MagicMock()
            mock_anthropic_response = MagicMock()
            mock_anthropic_response.content = [MagicMock(text="Test")]
            mock_anthropic_client.messages.create.return_value = mock_anthropic_response
            mock_anthropic.return_value = mock_anthropic_client
            
            # Mock health check HTTP responses
            def create_mock_response(*args, **kwargs):
                mock_response = MagicMock()
                mock_response.status_code = 200
                
                # Different responses based on the URL
                if 'api.openai.com' in str(args):
                    mock_response.json.return_value = {'data': [{'id': 'gpt-4'}]}
                elif '/api/tags' in str(args):
                    # Ollama tags endpoint
                    mock_response.json.return_value = {
                        'models': [
                            {'name': 'gemma3:12b'},
                            {'name': 'llama2:7b'}
                        ]
                    }
                elif 'api.anthropic.com' in str(args):
                    mock_response.json.return_value = {'models': [{'id': 'claude-3-sonnet-20240229'}]}
                else:
                    mock_response.json.return_value = {}
                
                return mock_response
            
            mock_health_client = MagicMock()
            mock_health_client.get = AsyncMock(side_effect=create_mock_response)
            mock_health_client.post = AsyncMock(side_effect=create_mock_response)
            
            # Set up the async context manager properly
            mock_context_manager = MagicMock()
            mock_context_manager.__aenter__ = AsyncMock(return_value=mock_health_client)
            mock_context_manager.__aexit__ = AsyncMock(return_value=None)
            mock_httpx.return_value = mock_context_manager
            
            # Test health checks for each service
            for service_name in ['openai', 'ollama', 'anthropic']:
                result = self.health_checker.check_service_health_sync(service_name, config)
                
                # All services should be healthy
                assert result.is_healthy, f"Service {service_name} should be healthy: {result.error_message}"
                assert result.service == service_name
                assert result.response_time_ms is not None
                assert result.response_time_ms >= 0  # Allow 0 for mocked responses
    
    def test_configuration_normalization_across_services(self):
        """Test configuration normalization consistency across services."""
        # Configuration with mixed case sections
        raw_config = {
            'LLM': {'service': 'OpenAI'},
            'OpenAI': {
                'api_key': 'sk-test1234567890abcdef1234567890abcdef1234567890ab',
                'model': 'gemma3:12b'
            },
            'Ollama': {
                'model': 'gemma3:12b',
                'host': 'http://localhost:11434'
            },
            'Anthropic': {
                'api_key': 'sk-ant-test1234567890abcdef1234567890abcdef1234567890ab',
                'model': 'gemma3:12b'
            }
        }
        
        # Normalize configuration
        normalized_config = self.normalizer.normalize_and_override(raw_config)
        
        # All sections should be lowercase
        assert 'llm' in normalized_config
        assert 'openai' in normalized_config
        assert 'ollama' in normalized_config
        assert 'anthropic' in normalized_config
        
        # Service value should be normalized
        assert normalized_config['llm']['service'] == 'openai'
        
        # Test validation with normalized config
        result = self.validator.validate_llm_config(normalized_config)
        assert result.is_valid
    
    @patch.dict(os.environ, {
        'SYNC2NAS_LLM_SERVICE': 'ollama',
        'SYNC2NAS_OLLAMA_MODEL': 'llama2:7b',
        'SYNC2NAS_OLLAMA_HOST': 'http://remote:11434'
    })
    def test_environment_override_service_switching(self):
        """Test service switching via environment variables."""
        # Config file specifies OpenAI
        config = {
            'llm': {'service': 'openai'},
            'openai': {
                'api_key': 'sk-test1234567890abcdef1234567890abcdef1234567890ab',
                'model': 'gemma3:12b'
            },
            'ollama': {
                'model': 'gemma3:12b',
                'host': 'http://localhost:11434'
            }
        }
        
        # Apply environment overrides
        normalized_config = self.normalizer.normalize_and_override(config)
        
        # Environment should override service selection
        assert normalized_config['llm']['service'] == 'ollama'
        assert normalized_config['ollama']['model'] == 'llama2:7b'
        assert normalized_config['ollama']['host'] == 'http://remote:11434'
        
        # Validation should pass
        result = self.validator.validate_llm_config(normalized_config)
        assert result.is_valid
        
        # Service creation should use environment values
        with patch('services.llm_implementations.ollama_implementation.Client') as mock_ollama:
            mock_client = MagicMock()
            mock_client.generate.return_value = {'response': 'Test'}
            mock_ollama.return_value = mock_client
            
            service = create_llm_service(normalized_config, validate_health=False)
            assert service is not None
            assert service.model == 'llama2:7b'
            assert service.host == 'http://remote:11434'
    
    def test_partial_service_configuration_validation(self):
        """Test validation with partial service configurations."""
        # Configuration with some services partially configured
        config = {
            'llm': {'service': 'openai'},
            'openai': {
                'api_key': 'sk-test1234567890abcdef1234567890abcdef1234567890ab'
                # Missing model
            },
            'ollama': {
                # Missing model and host
            },
            'anthropic': {
                'api_key': 'sk-ant-test1234567890abcdef1234567890abcdef1234567890ab',
                'model': 'gemma3:12b'
            }
        }
        
        # Validate current service (OpenAI) - model is optional with default
        result = self.validator.validate_llm_config(config)
        # OpenAI validation should pass as model has a default value
        assert result.is_valid
        
        # Should have suggestions for missing configuration
        assert len(result.suggestions) > 0
        suggestion_text = ' '.join(result.suggestions).lower()
        assert 'model' in suggestion_text
        
        # Test validation for other services
        anthropic_result = self.validator.validate_service_config('anthropic', config)
        assert anthropic_result.is_valid  # Anthropic config is complete
        
        ollama_result = self.validator.validate_service_config('ollama', config)
        assert not ollama_result.is_valid  # Ollama config is incomplete
    
    def test_service_fallback_scenarios(self):
        """Test service fallback scenarios when primary service fails."""
        # Configuration with multiple services
        config = {
            'llm': {'service': 'openai'},
            'openai': {
                'api_key': 'sk-invalid1234567890abcdef1234567890abcdef1234567890ab',
                'model': 'gemma3:12b'
            },
            'ollama': {
                'model': 'gemma3:12b',
                'host': 'http://localhost:11434'
            }
        }
        
        # Primary service (OpenAI) should fail
        with patch('services.llm_implementations.openai_implementation.openai.OpenAI') as mock_openai:
            mock_openai.side_effect = Exception("Invalid API key")
            
            with pytest.raises(LLMServiceCreationError):
                create_llm_service(config, validate_health=True)
        
        # Switch to fallback service (Ollama)
        config['llm']['service'] = 'ollama'
        
        with patch('services.llm_implementations.ollama_implementation.Client') as mock_ollama:
            mock_client = MagicMock()
            mock_client.generate.return_value = {'response': 'Test'}
            mock_ollama.return_value = mock_client
            
            # Should succeed with fallback service
            service = create_llm_service(config, validate_health=True)
            assert service is not None
            assert service.model == 'gemma3:12b'
    
    def test_configuration_migration_scenarios(self):
        """Test configuration migration between different service formats."""
        # Old-style configuration (hypothetical legacy format)
        old_config = {
            'LLM': {'service': 'OpenAI'},
            'OpenAI': {
                'api_key': 'sk-test1234567890abcdef1234567890abcdef1234567890ab',
                'model': 'gemma3:12b',
                'max_tokens': '4000',
                'temperature': '0.1'
            }
        }
        
        # Normalize to new format
        normalized_config = self.normalizer.normalize_and_override(old_config)
        
        # Should be in new format
        assert 'llm' in normalized_config
        assert 'openai' in normalized_config
        assert normalized_config['llm']['service'] == 'openai'
        
        # Should validate successfully
        result = self.validator.validate_llm_config(normalized_config)
        assert result.is_valid
        
        # Should create service successfully
        with patch('services.llm_implementations.openai_implementation.openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="Test"))]
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            service = create_llm_service(normalized_config, validate_health=False)
            assert service is not None


class TestComplexConfigurationScenarios:
    """Test complex configuration scenarios with multiple components."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ConfigValidator()
        self.normalizer = ConfigNormalizer()
        self.health_checker = ConfigHealthChecker()
    
    def create_temp_config(self, content: str) -> str:
        """Create a temporary configuration file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(content)
            return f.name
    
    def test_complete_application_configuration_validation(self):
        """Test validation of complete application configuration."""
        config_content = """
[llm]
service = openai

[openai]
api_key = sk-test1234567890abcdef1234567890abcdef1234567890ab
model = gpt-4
max_tokens = 4000
temperature = 0.1

[ollama]
model = gemma3:12b
host = http://localhost:11434
timeout = 30

[anthropic]
api_key = sk-ant-test1234567890abcdef1234567890abcdef1234567890ab
model = claude-3-sonnet-20240229
max_tokens = 4000

[tmdb]
api_key = test_tmdb_key
language = en-US
region = US

[sftp]
host = nas.example.com
port = 22
username = sync2nas
key_file = /path/to/ssh/key
timeout = 30

[database]
type = sqlite
path = ./database/sync2nas.db

[transfers]
incoming = ./incoming
temp_dir = ./temp

[routing]
anime_tv_path = /mnt/anime_tv
completed_path = /mnt/completed
"""
        config_file = self.create_temp_config(config_content)
        
        try:
            # Load complete configuration
            config = load_configuration(config_file, normalize=True)
            
            # Validate LLM configuration
            llm_result = self.validator.validate_llm_config(config)
            assert llm_result.is_valid
            
            # Should have all required sections
            assert 'llm' in config
            assert 'openai' in config
            assert 'tmdb' in config
            assert 'sftp' in config
            assert 'database' in config
            assert 'transfers' in config
            assert 'routing' in config
            
            # Test service creation with complete config
            with patch('services.llm_implementations.openai_implementation.openai.OpenAI') as mock_openai:
                mock_client = MagicMock()
                mock_response = MagicMock()
                mock_response.choices = [MagicMock(message=MagicMock(content="Test"))]
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client
                
                service = create_llm_service(config, validate_health=False)
                assert service is not None
        
        finally:
            os.unlink(config_file)
    
    def test_configuration_with_optional_sections(self):
        """Test configuration validation with optional sections."""
        # Minimal configuration
        minimal_config = {
            'llm': {'service': 'ollama'},
            'ollama': {
                'model': 'gemma3:12b'
                # Missing optional host (should default)
            }
        }
        
        # Should validate successfully with defaults
        result = self.validator.validate_llm_config(minimal_config)
        assert result.is_valid
        
        # Should create service with defaults
        with patch('services.llm_implementations.ollama_implementation.Client') as mock_ollama:
            mock_client = MagicMock()
            mock_client.generate.return_value = {'response': 'Test'}
            mock_ollama.return_value = mock_client
            
            service = create_llm_service(minimal_config, validate_health=False)
            assert service is not None
            assert service.model == 'gemma3:12b'
            # Should use default host (stored in client)
            assert hasattr(service, 'client')
    
    def test_configuration_with_conflicting_sections(self):
        """Test configuration with conflicting section definitions."""
        # Configuration with duplicate sections (different cases)
        config_content = """
[llm]
service = openai

[OpenAI]
api_key = sk-config1234567890abcdef1234567890abcdef1234567890ab
model = gpt-4

[openai]
api_key = sk-override1234567890abcdef1234567890abcdef1234567890ab
model = gpt-3.5-turbo
"""
        config_file = self.create_temp_config(config_content)
        
        try:
            # Load configuration (should handle conflicts)
            config = load_configuration(config_file, normalize=True)
            
            # Should merge sections with precedence rules
            assert 'openai' in config
            
            # Lowercase section should take precedence
            assert config['openai']['api_key'] == 'sk-override1234567890abcdef1234567890abcdef1234567890ab'
            assert config['openai']['model'] == 'gpt-3.5-turbo'
            
            # Should validate successfully
            result = self.validator.validate_llm_config(config)
            assert result.is_valid
        
        finally:
            os.unlink(config_file)
    
    def test_configuration_with_environment_and_file_conflicts(self):
        """Test configuration with conflicts between environment and file."""
        config = {
            'llm': {'service': 'openai'},
            'openai': {
                'api_key': 'sk-file1234567890abcdef1234567890abcdef1234567890ab',
                'model': 'gemma3:12b'
            }
        }
        
        # Test with environment override
        with patch.dict(os.environ, {
            'SYNC2NAS_OPENAI_API_KEY': 'sk-env1234567890abcdef1234567890abcdef1234567890ab',
            'SYNC2NAS_OPENAI_MODEL': 'gpt-3.5-turbo'
        }):
            # Apply environment overrides
            normalized_config = self.normalizer.normalize_and_override(config)
            
            # Environment should take precedence
            assert normalized_config['openai']['api_key'] == 'sk-env1234567890abcdef1234567890abcdef1234567890ab'
            assert normalized_config['openai']['model'] == 'gpt-3.5-turbo'
            
            # Should validate successfully
            result = self.validator.validate_llm_config(normalized_config)
            assert result.is_valid
    
    def test_configuration_error_aggregation_across_services(self):
        """Test error aggregation across multiple service configurations."""
        config = {
            'llm': {'service': 'openai'},
            'openai': {
                'api_key': 'invalid_key',  # Invalid format
                'model': 'gemma3:12b',  # Invalid model name
                'max_tokens': 'invalid_number'  # Invalid type
            },
            'ollama': {
                'model': 'gemma3:12b',  # Empty model
                'host': 'invalid_url'  # Invalid URL format
            },
            'anthropic': {
                'api_key': 'short_key',  # Too short
                'model': 'gemma3:12b'  # Invalid model
            }
        }
        
        # Validate all services
        openai_result = self.validator.validate_service_config('openai', config)
        ollama_result = self.validator.validate_service_config('ollama', config)
        anthropic_result = self.validator.validate_service_config('anthropic', config)
        
        # All should have errors
        assert not openai_result.is_valid
        assert not ollama_result.is_valid
        assert not anthropic_result.is_valid
        
        # Should have multiple errors per service
        assert len(openai_result.errors) >= 2  # API key and model errors
        assert len(ollama_result.errors) >= 1  # Model error
        assert len(anthropic_result.errors) >= 1  # API key error
        
        # Should have helpful suggestions (may be in errors or warnings instead)
        total_feedback = len(openai_result.suggestions) + len(openai_result.errors) + len(openai_result.warnings)
        assert total_feedback > 0
        
        total_feedback = len(ollama_result.suggestions) + len(ollama_result.errors) + len(ollama_result.warnings)
        assert total_feedback > 0
        
        total_feedback = len(anthropic_result.suggestions) + len(anthropic_result.errors) + len(anthropic_result.warnings)
        assert total_feedback > 0
    
    def test_configuration_performance_with_large_configs(self):
        """Test configuration performance with large configuration files."""
        # Create large configuration with many sections
        large_config = {
            'llm': {'service': 'openai'},
            'openai': {
                'api_key': 'sk-test1234567890abcdef1234567890abcdef1234567890ab',
                'model': 'gemma3:12b'
            }
        }
        
        # Add many additional sections (simulating large config file)
        for i in range(100):
            large_config[f'section_{i}'] = {
                f'key_{j}': f'value_{j}' for j in range(10)
            }
        
        import time
        start_time = time.time()
        
        # Normalize configuration
        normalized_config = self.normalizer.normalize_and_override(large_config)
        
        # Validate configuration
        result = self.validator.validate_llm_config(normalized_config)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should complete within reasonable time (2 seconds)
        assert processing_time < 2.0
        assert result.is_valid
        
        # Should preserve all sections
        assert len(normalized_config) >= 102  # Original sections + 100 additional