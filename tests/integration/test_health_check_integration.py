"""
Integration tests for health check system with mock services.

Tests the health check system's integration with various LLM services,
focusing on the sync methods that are actually available.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from utils.config.health_checker import ConfigHealthChecker
from utils.config.validation_models import HealthCheckResult
from services.llm_factory import create_llm_service, LLMServiceCreationError


class TestHealthCheckIntegration:
    """Test health check integration with LLM services."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.health_checker = ConfigHealthChecker()
    
    @patch('httpx.AsyncClient')
    def test_openai_health_check_success(self, mock_client_class):
        """Test successful OpenAI health check integration."""
        # Mock successful HTTP response
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': [{'id': 'gpt-4'}, {'id': 'gpt-3.5-turbo'}]}
        
        # Create async context manager mock
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        config = {
            'llm': {'service': 'openai'},
            'openai': {
                'api_key': 'sk-test1234567890abcdef1234567890abcdef1234567890ab',
                'model': 'gemma3:12b',
                'max_tokens': '100',
                'temperature': '0.1'
            }
        }
        
        # Test health check using sync method
        results = self.health_checker.check_llm_health_sync(config)
        
        assert len(results) > 0
        result = results[0]
        assert result.is_healthy
        assert result.service == 'openai'
        assert result.response_time_ms is not None
        assert result.response_time_ms >= 0  # Mocked responses may have 0 response time
        assert result.error_message is None
        
        # Verify HTTP client was called correctly
        mock_client_class.assert_called_once()
        mock_client.get.assert_called_once()
    
    @patch('httpx.AsyncClient')
    def test_openai_health_check_api_error(self, mock_client_class):
        """Test OpenAI health check with API error."""
        # Mock API error response
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {'error': {'message': 'Invalid API key'}}
        
        # Create async context manager mock
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        config = {
            'llm': {'service': 'openai'},
            'openai': {
                'api_key': 'sk-invalid1234567890abcdef1234567890abcdef1234567890ab',
                'model': 'gemma3:12b'
            }
        }
        
        # Test health check using sync method
        results = self.health_checker.check_llm_health_sync(config)
        
        assert len(results) > 0
        result = results[0]
        assert not result.is_healthy
        assert result.service == 'openai'
        assert "Invalid" in result.error_message and "API key" in result.error_message
        assert result.response_time_ms is not None  # Should still measure time even on error
    
    @patch('httpx.AsyncClient')
    def test_ollama_health_check_success(self, mock_client_class):
        """Test successful Ollama health check integration."""
        # Mock successful HTTP response
        mock_client = AsyncMock()
        
        # Mock GET response for /api/tags
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {'models': [{'name': 'gemma3:12b'}, {'name': 'llama2:7b'}]}
        
        # Mock POST response for /api/generate
        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {'response': 'Hello'}
        
        # Create async context manager mock
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = mock_get_response
        mock_client.post.return_value = mock_post_response
        mock_client_class.return_value = mock_client
        
        config = {
            'llm': {'service': 'ollama'},
            'ollama': {
                'model': 'gemma3:12b',
                'host': 'http://localhost:11434',
                'timeout': '30'
            }
        }
        
        # Test health check using sync method
        results = self.health_checker.check_llm_health_sync(config)
        
        assert len(results) > 0
        result = results[0]
        assert result.is_healthy
        assert result.service == 'ollama'
        assert result.response_time_ms is not None
        assert result.response_time_ms >= 0  # Mocked responses may have 0 response time
        assert result.error_message is None
        
        # Verify HTTP client was called correctly
        mock_client_class.assert_called_once()
        mock_client.get.assert_called_once()
    
    @patch('httpx.AsyncClient')
    def test_ollama_health_check_connection_error(self, mock_client_class):
        """Test Ollama health check with connection error."""
        # Mock connection error
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.side_effect = Exception("Connection refused")
        mock_client_class.return_value = mock_client
        
        config = {
            'llm': {'service': 'ollama'},
            'ollama': {
                'model': 'gemma3:12b',
                'host': 'http://localhost:11434'
            }
        }
        
        # Test health check using sync method
        results = self.health_checker.check_llm_health_sync(config)
        
        assert len(results) > 0
        result = results[0]
        assert not result.is_healthy
        assert result.service == 'ollama'
        assert "Connection refused" in result.error_message
        assert result.response_time_ms >= 0  # Should always have a response time, even for errors
    
    def test_health_check_invalid_service(self):
        """Test health check with invalid service configuration."""
        config = {
            'llm': {'service': 'invalid_service'},
            'invalid_service': {'some_key': 'some_value'}
        }
        
        # Test health check using sync method
        results = self.health_checker.check_llm_health_sync(config)
        
        assert len(results) > 0
        result = results[0]
        assert not result.is_healthy
        assert result.service == 'invalid_service'
        assert "unknown" in result.error_message.lower() or "not supported" in result.error_message.lower()
        assert result.response_time_ms is None
    
    def test_health_check_missing_service_config(self):
        """Test health check with missing service configuration."""
        config = {
            'llm': {'service': 'openai'}
            # Missing [openai] section
        }
        
        # Test health check using sync method
        results = self.health_checker.check_llm_health_sync(config)
        
        assert len(results) > 0
        result = results[0]
        assert not result.is_healthy
        assert result.service == 'openai'
        assert "not configured" in result.error_message.lower() or "missing" in result.error_message.lower()
        assert result.response_time_ms is None
    
    def test_health_check_specific_service(self):
        """Test health check for specific service."""
        config = {
            'llm': {'service': 'ollama'},
            'openai': {
                'api_key': 'sk-test1234567890abcdef1234567890abcdef1234567890ab',
                'model': 'gemma3:12b'
            },
            'ollama': {
                'model': 'gemma3:12b',
                'host': 'http://localhost:11434'
            }
        }
        
        # Test health check for specific service (not the configured one)
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'data': [{'id': 'gpt-4'}]}
            
            # Create async context manager mock
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            result = self.health_checker.check_service_health_sync('openai', config)
            
            assert result.is_healthy
            assert result.service == 'openai'
    
    def test_health_check_response_time_measurement(self):
        """Test that health check accurately measures response time."""
        import time
        
        with patch('httpx.AsyncClient') as mock_client_class:
            # Mock a response that takes some time
            async def slow_get(*args, **kwargs):
                await asyncio.sleep(0.1)  # 100ms delay
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {'data': [{'id': 'gpt-4'}]}
                return mock_response
            
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.side_effect = slow_get
            mock_client_class.return_value = mock_client
            
            config = {
                'llm': {'service': 'openai'},
                'openai': {
                    'api_key': 'sk-test1234567890abcdef1234567890abcdef1234567890ab',
                    'model': 'gemma3:12b'
                }
            }
            
            results = self.health_checker.check_llm_health_sync(config)
            
            assert len(results) > 0
            result = results[0]
            assert result.is_healthy
            assert result.response_time_ms is not None
            assert result.response_time_ms >= 100  # Should be at least 100ms
            assert result.response_time_ms < 1000  # But not too long
    
    def test_health_check_details_information(self):
        """Test that health check provides detailed information."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'data': [{'id': 'gpt-4'}, {'id': 'gpt-3.5-turbo'}]}
            
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            config = {
                'llm': {'service': 'openai'},
                'openai': {
                    'api_key': 'sk-test1234567890abcdef1234567890abcdef1234567890ab',
                    'model': 'gemma3:12b',
                    'max_tokens': '100',
                    'temperature': '0.1'
                }
            }
            
            results = self.health_checker.check_llm_health_sync(config)
            
            assert len(results) > 0
            result = results[0]
            assert result.is_healthy
            assert result.details is not None
            assert isinstance(result.details, dict)
            
            # Should contain configuration details
            assert 'status_code' in result.details or 'available_models' in result.details
            assert 'endpoint' in result.details or 'available_models' in result.details
            # Details should contain useful information about the health check
            assert len(result.details) > 0
            # Verify that details contain meaningful information
            assert 'status_code' in result.details


class TestHealthCheckServiceIntegration:
    """Test health check integration with service creation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.health_checker = ConfigHealthChecker()
    
    @patch('httpx.AsyncClient')
    def test_service_creation_with_health_check_success(self, mock_client_class):
        """Test service creation with successful health check."""
        # Mock successful HTTP response for health check
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': [{'id': 'gpt-4'}]}
        
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        config = {
            'llm': {'service': 'openai'},
            'openai': {
                'api_key': 'sk-test1234567890abcdef1234567890abcdef1234567890ab',
                'model': 'gemma3:12b'
            }
        }
        
        # Create service with health check enabled
        service = create_llm_service(config, validate_health=True)
        
        assert service is not None
        assert service.api_key.startswith('sk-')
        assert service.model == 'gemma3:12b'  # Service uses configured model, not API response model
        
        # Verify health check was performed
        mock_client.get.assert_called()
    
    @patch('services.llm_implementations.openai_implementation.openai.OpenAI')
    def test_service_creation_with_health_check_failure(self, mock_openai):
        """Test service creation with health check failure."""
        # Mock failing OpenAI client
        mock_openai.side_effect = Exception("API connection failed")
        
        config = {
            'llm': {'service': 'openai'},
            'openai': {
                'api_key': 'sk-test1234567890abcdef1234567890abcdef1234567890ab',
                'model': 'gemma3:12b'
            }
        }
        
        # Service creation with health check should fail
        with pytest.raises(LLMServiceCreationError) as exc_info:
            create_llm_service(config, validate_health=True)
        
        # Should contain health check failure information
        assert "health check failed" in str(exc_info.value).lower()
    
    def test_service_creation_without_health_check(self):
        """Test service creation without health check."""
        config = {
            'llm': {'service': 'openai'},
            'openai': {
                'api_key': 'sk-test1234567890abcdef1234567890abcdef1234567890ab',
                'model': 'gemma3:12b'
            }
        }
        
        # Should succeed even if health check would fail
        with patch('services.llm_implementations.openai_implementation.openai.OpenAI'):
            service = create_llm_service(config, validate_health=False)
            assert service is not None
    
    @patch('httpx.AsyncClient')
    def test_multiple_service_health_checks(self, mock_client_class):
        """Test health checks for multiple services."""
        # Mock successful HTTP responses for both services
        mock_client = AsyncMock()
        
        def mock_get_response(url, **kwargs):
            mock_response = MagicMock()
            if 'api/tags' in url:
                # Ollama response
                mock_response.status_code = 200
                mock_response.json.return_value = {'models': [{'name': 'gemma3:12b'}]}
            else:
                # OpenAI response
                mock_response.status_code = 200
                mock_response.json.return_value = {'data': [{'id': 'gpt-4'}]}
            return mock_response
        
        def mock_post_response(url, **kwargs):
            # Ollama generation response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'response': 'Test'}
            return mock_response
        
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.side_effect = mock_get_response
        mock_client.post.side_effect = mock_post_response
        mock_client_class.return_value = mock_client
        
        config = {
            'llm': {'service': 'ollama'},
            'ollama': {
                'model': 'gemma3:12b',
                'host': 'http://localhost:11434'
            },
            'openai': {
                'api_key': 'sk-test1234567890abcdef1234567890abcdef1234567890ab',
                'model': 'gemma3:12b'
            }
        }
        
        # Test health check for configured service (Ollama)
        results1 = self.health_checker.check_llm_health_sync(config)
        assert len(results1) > 0
        assert results1[0].is_healthy
        assert results1[0].service == 'ollama'
        
        # Test health check for specific service (OpenAI)
        result2 = self.health_checker.check_service_health_sync('openai', config)
        assert result2.is_healthy
        assert result2.service == 'openai'


class TestHealthCheckErrorScenarios:
    """Test various error scenarios in health checks."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.health_checker = ConfigHealthChecker()
    
    def test_health_check_with_no_llm_service(self):
        """Test health check when no LLM service is configured."""
        config = {}
        
        results = self.health_checker.check_llm_health_sync(config)
        
        # Should return at least one result indicating no service configured
        assert len(results) > 0
        result = results[0]
        assert not result.is_healthy
        assert "no llm service" in result.error_message.lower() or "not configured" in result.error_message.lower()
    
    def test_health_check_with_empty_config(self):
        """Test health check with completely empty configuration."""
        config = {'llm': {}}
        
        results = self.health_checker.check_llm_health_sync(config)
        
        assert len(results) > 0
        result = results[0]
        assert not result.is_healthy
        assert result.error_message is not None
    
    @patch('httpx.AsyncClient')
    def test_health_check_with_partial_failure(self, mock_client_class):
        """Test health check when service creation succeeds but health check fails."""
        # Mock HTTP client that raises rate limit error
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.side_effect = Exception("Rate limit exceeded")
        mock_client_class.return_value = mock_client
        
        config = {
            'llm': {'service': 'openai'},
            'openai': {
                'api_key': 'sk-test1234567890abcdef1234567890abcdef1234567890ab',
                'model': 'gemma3:12b'
            }
        }
        
        results = self.health_checker.check_llm_health_sync(config)
        
        assert len(results) > 0
        result = results[0]
        assert not result.is_healthy
        assert "rate limit" in result.error_message.lower() or "exceeded" in result.error_message.lower()
    
    def test_health_check_result_string_representation(self):
        """Test that health check results have proper string representation."""
        # Create a mock result
        from utils.config.validation_models import HealthCheckResult
        
        healthy_result = HealthCheckResult(
            service='openai',
            is_healthy=True,
            response_time_ms=150.5,
            error_message=None,
            details={'model': 'gemma3:12b'}
        )
        
        unhealthy_result = HealthCheckResult(
            service='ollama',
            is_healthy=False,
            response_time_ms=None,
            error_message='Connection failed',
            details={}
        )
        
        # Test string representations
        healthy_str = str(healthy_result)
        assert 'openai' in healthy_str
        assert 'Healthy' in healthy_str or '✓' in healthy_str
        assert '150.5' in healthy_str
        
        unhealthy_str = str(unhealthy_result)
        assert 'ollama' in unhealthy_str
        assert 'Unhealthy' in unhealthy_str or '✗' in unhealthy_str
        assert 'Connection failed' in unhealthy_str