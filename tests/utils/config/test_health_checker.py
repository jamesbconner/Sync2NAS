"""Tests for configuration health check system."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import httpx

from utils.config.health_checker import ConfigHealthChecker
from utils.config.validation_models import HealthCheckResult, ErrorCode


class TestConfigHealthChecker:
    """Test cases for ConfigHealthChecker class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.health_checker = ConfigHealthChecker(timeout=5.0)
    
    @pytest.mark.asyncio
    async def test_check_openai_health_success(self):
        """Test successful OpenAI health check."""
        config = {
            'llm': {'service': 'openai'},
            'openai': {'api_key': 'sk-' + 'x' * 48}
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [{'id': 'gpt-4'}, {'id': 'gpt-3.5-turbo'}]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            results = await self.health_checker.check_llm_health(config)
            
            assert len(results) == 1
            result = results[0]
            assert result.service == 'openai'
            assert result.is_healthy
            assert result.response_time_ms is not None
            assert result.error_message is None
            assert result.details['available_models'] == 2
    
    @pytest.mark.asyncio
    async def test_check_openai_health_invalid_key(self):
        """Test OpenAI health check with invalid API key."""
        config = {
            'llm': {'service': 'openai'},
            'openai': {'api_key': 'invalid-key'}
        }
        
        mock_response = Mock()
        mock_response.status_code = 401
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            results = await self.health_checker.check_llm_health(config)
            
            assert len(results) == 1
            result = results[0]
            assert result.service == 'openai'
            assert not result.is_healthy
            assert 'Invalid OpenAI API key' in result.error_message
            assert result.details['error_code'] == ErrorCode.AUTHENTICATION_FAILED.value
    
    @pytest.mark.asyncio
    async def test_check_openai_health_missing_key(self):
        """Test OpenAI health check with missing API key."""
        config = {
            'llm': {'service': 'openai'},
            'openai': {}
        }
        
        results = await self.health_checker.check_llm_health(config)
        
        assert len(results) == 1
        result = results[0]
        assert result.service == 'openai'
        assert not result.is_healthy
        assert 'API key not configured' in result.error_message
        assert result.details['error_code'] == ErrorCode.MISSING_KEY.value
    
    @pytest.mark.asyncio
    async def test_check_openai_health_timeout(self):
        """Test OpenAI health check with timeout."""
        config = {
            'llm': {'service': 'openai'},
            'openai': {'api_key': 'sk-' + 'x' * 48}
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.TimeoutException("Timeout")
            )
            
            results = await self.health_checker.check_llm_health(config)
            
            assert len(results) == 1
            result = results[0]
            assert result.service == 'openai'
            assert not result.is_healthy
            assert 'Timeout' in result.error_message
            assert result.details['error_code'] == ErrorCode.CONNECTIVITY_FAILED.value
    
    @pytest.mark.asyncio
    async def test_check_anthropic_health_success(self):
        """Test successful Anthropic health check."""
        config = {
            'llm': {'service': 'anthropic'},
            'anthropic': {
                'api_key': 'sk-ant-' + 'x' * 35,
                'model': 'claude-3-sonnet-20240229'
            }
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'content': [{'text': 'Hello'}]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            results = await self.health_checker.check_llm_health(config)
            
            assert len(results) == 1
            result = results[0]
            assert result.service == 'anthropic'
            assert result.is_healthy
            assert result.response_time_ms is not None
            assert result.error_message is None
            assert result.details['model'] == 'claude-3-sonnet-20240229'
    
    @pytest.mark.asyncio
    async def test_check_anthropic_health_invalid_key(self):
        """Test Anthropic health check with invalid API key."""
        config = {
            'llm': {'service': 'anthropic'},
            'anthropic': {'api_key': 'invalid-key'}
        }
        
        mock_response = Mock()
        mock_response.status_code = 401
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            results = await self.health_checker.check_llm_health(config)
            
            assert len(results) == 1
            result = results[0]
            assert result.service == 'anthropic'
            assert not result.is_healthy
            assert 'Invalid Anthropic API key' in result.error_message
            assert result.details['error_code'] == ErrorCode.AUTHENTICATION_FAILED.value
    
    @pytest.mark.asyncio
    async def test_check_anthropic_health_model_unavailable(self):
        """Test Anthropic health check with unavailable model."""
        config = {
            'llm': {'service': 'anthropic'},
            'anthropic': {
                'api_key': 'sk-ant-' + 'x' * 35,
                'model': 'invalid-model'
            }
        }
        
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            'error': {'message': 'model not found'}
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            results = await self.health_checker.check_llm_health(config)
            
            assert len(results) == 1
            result = results[0]
            assert result.service == 'anthropic'
            assert not result.is_healthy
            assert 'not available' in result.error_message
            assert result.details['error_code'] == ErrorCode.MODEL_UNAVAILABLE.value
    
    @pytest.mark.asyncio
    async def test_check_ollama_health_success(self):
        """Test successful Ollama health check."""
        config = {
            'llm': {'service': 'ollama'},
            'ollama': {
                'host': 'http://localhost:11434',
                'model': 'llama2:7b'
            }
        }
        
        # Mock the /api/tags response
        mock_tags_response = Mock()
        mock_tags_response.status_code = 200
        mock_tags_response.json.return_value = {
            'models': [
                {'name': 'llama2:7b'},
                {'name': 'mistral:latest'}
            ]
        }
        
        # Mock the /api/generate response
        mock_gen_response = Mock()
        mock_gen_response.status_code = 200
        mock_gen_response.json.return_value = {
            'response': 'Hello'
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client_instance = mock_client.return_value.__aenter__.return_value
            mock_client_instance.get = AsyncMock(return_value=mock_tags_response)
            mock_client_instance.post = AsyncMock(return_value=mock_gen_response)
            
            results = await self.health_checker.check_llm_health(config)
            
            assert len(results) == 1
            result = results[0]
            assert result.service == 'ollama'
            assert result.is_healthy
            assert result.response_time_ms is not None
            assert result.error_message is None
            assert result.details['model'] == 'llama2:7b'
            assert result.details['generation_test'] == 'passed'
    
    @pytest.mark.asyncio
    async def test_check_ollama_health_service_unreachable(self):
        """Test Ollama health check when service is unreachable."""
        config = {
            'llm': {'service': 'ollama'},
            'ollama': {
                'host': 'http://localhost:11434',
                'model': 'llama2:7b'
            }
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            
            results = await self.health_checker.check_llm_health(config)
            
            assert len(results) == 1
            result = results[0]
            assert result.service == 'ollama'
            assert not result.is_healthy
            assert 'Cannot connect to Ollama' in result.error_message
            assert result.details['error_code'] == ErrorCode.SERVICE_UNREACHABLE.value
    
    @pytest.mark.asyncio
    async def test_check_ollama_health_model_not_found(self):
        """Test Ollama health check when model is not available."""
        config = {
            'llm': {'service': 'ollama'},
            'ollama': {
                'host': 'http://localhost:11434',
                'model': 'nonexistent:model'
            }
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'models': [
                {'name': 'llama2:7b'},
                {'name': 'mistral:latest'}
            ]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            results = await self.health_checker.check_llm_health(config)
            
            assert len(results) == 1
            result = results[0]
            assert result.service == 'ollama'
            assert not result.is_healthy
            assert 'not found in Ollama' in result.error_message
            assert result.details['error_code'] == ErrorCode.MODEL_UNAVAILABLE.value
            assert 'ollama pull' in result.details['suggestion']
    
    @pytest.mark.asyncio
    async def test_check_ollama_health_missing_model(self):
        """Test Ollama health check with missing model configuration."""
        config = {
            'llm': {'service': 'ollama'},
            'ollama': {'host': 'http://localhost:11434'}
        }
        
        results = await self.health_checker.check_llm_health(config)
        
        assert len(results) == 1
        result = results[0]
        assert result.service == 'ollama'
        assert not result.is_healthy
        assert 'model not configured' in result.error_message
        assert result.details['error_code'] == ErrorCode.MISSING_KEY.value
    
    @pytest.mark.asyncio
    async def test_check_llm_health_no_service_configured(self):
        """Test health check when no LLM service is configured."""
        config = {}
        
        results = await self.health_checker.check_llm_health(config)
        
        assert len(results) == 1
        result = results[0]
        assert result.service == 'llm'
        assert not result.is_healthy
        assert 'No LLM service configured' in result.error_message
        assert result.details['error_code'] == ErrorCode.MISSING_KEY.value
    
    @pytest.mark.asyncio
    async def test_check_llm_health_invalid_service(self):
        """Test health check with invalid service name."""
        config = {
            'llm': {'service': 'invalid_service'}
        }
        
        results = await self.health_checker.check_llm_health(config)
        
        assert len(results) == 1
        result = results[0]
        assert result.service == 'invalid_service'
        assert not result.is_healthy
        assert 'Unknown LLM service' in result.error_message
        assert result.details['error_code'] == ErrorCode.INVALID_SERVICE.value
    
    @pytest.mark.asyncio
    async def test_check_service_health_specific_service(self):
        """Test health check for a specific service."""
        config = {
            'openai': {'api_key': 'sk-' + 'x' * 48}
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': []}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await self.health_checker.check_service_health('openai', config)
            
            assert result.service == 'openai'
            assert result.is_healthy
    
    @pytest.mark.asyncio
    async def test_check_service_health_unknown_service(self):
        """Test health check for unknown service."""
        config = {}
        
        result = await self.health_checker.check_service_health('unknown', config)
        
        assert result.service == 'unknown'
        assert not result.is_healthy
        assert 'Unknown service' in result.error_message
        assert result.details['error_code'] == ErrorCode.INVALID_SERVICE.value
    
    def test_check_llm_health_sync(self):
        """Test synchronous wrapper for LLM health checks."""
        config = {
            'llm': {'service': 'ollama'},
            'ollama': {'model': 'llama2:7b'}
        }
        
        # Mock the async method
        with patch.object(self.health_checker, 'check_llm_health') as mock_async:
            mock_result = [HealthCheckResult(
                service='ollama',
                is_healthy=True,
                response_time_ms=100.0,
                error_message=None,
                details={}
            )]
            mock_async.return_value = mock_result
            
            results = self.health_checker.check_llm_health_sync(config)
            
            assert len(results) == 1
            assert results[0].service == 'ollama'
            assert results[0].is_healthy
    
    def test_check_service_health_sync(self):
        """Test synchronous wrapper for service health checks."""
        config = {'openai': {'api_key': 'sk-test'}}
        
        # Mock the async method
        with patch.object(self.health_checker, 'check_service_health') as mock_async:
            mock_result = HealthCheckResult(
                service='openai',
                is_healthy=True,
                response_time_ms=50.0,
                error_message=None,
                details={}
            )
            mock_async.return_value = mock_result
            
            result = self.health_checker.check_service_health_sync('openai', config)
            
            assert result.service == 'openai'
            assert result.is_healthy
    
    @pytest.mark.asyncio
    async def test_case_insensitive_configuration(self):
        """Test health check works with case-insensitive configuration."""
        config = {
            'LLM': {'SERVICE': 'OpenAI'},
            'OpenAI': {'API_KEY': 'sk-' + 'x' * 48}
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': []}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            results = await self.health_checker.check_llm_health(config)
            
            assert len(results) == 1
            result = results[0]
            assert result.service == 'openai'
            assert result.is_healthy
    
    def test_health_check_result_string_representation(self):
        """Test string representation of health check results."""
        # Healthy result
        healthy_result = HealthCheckResult(
            service='openai',
            is_healthy=True,
            response_time_ms=123.4,
            error_message=None,
            details={}
        )
        
        result_str = str(healthy_result)
        assert 'openai: ✓ Healthy' in result_str
        assert '123.4ms' in result_str
        
        # Unhealthy result
        unhealthy_result = HealthCheckResult(
            service='ollama',
            is_healthy=False,
            response_time_ms=None,
            error_message='Service unreachable',
            details={}
        )
        
        result_str = str(unhealthy_result)
        assert 'ollama: ✗ Unhealthy' in result_str
        assert 'Service unreachable' in result_str
    
    @pytest.mark.asyncio
    async def test_custom_timeout(self):
        """Test health checker with custom timeout."""
        health_checker = ConfigHealthChecker(timeout=1.0)
        
        config = {
            'llm': {'service': 'openai'},
            'openai': {'api_key': 'sk-' + 'x' * 48}
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.TimeoutException("Timeout")
            )
            
            results = await health_checker.check_llm_health(config)
            
            assert len(results) == 1
            result = results[0]
            assert not result.is_healthy
            assert result.details['timeout_seconds'] == 1.0