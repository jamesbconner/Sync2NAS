"""Configuration health check system for LLM services."""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, List
import httpx
import json

from .validation_models import HealthCheckResult, ErrorCode
from .config_normalizer import ConfigNormalizer

logger = logging.getLogger(__name__)


class ConfigHealthChecker:
    """Health checker for LLM service configuration and connectivity."""
    
    def __init__(self, timeout: float = 10.0):
        """
        Initialize the health checker.
        
        Args:
            timeout: Default timeout for health checks in seconds
        """
        self.timeout = timeout
        self.normalizer = ConfigNormalizer()
    
    async def check_llm_health(self, config: Dict[str, Any]) -> List[HealthCheckResult]:
        """
        Check health of all configured LLM services.
        
        Args:
            config: Configuration dictionary (can be ConfigParser or dict)
            
        Returns:
            List of HealthCheckResult for each configured service
        """
        logger.info("Starting LLM health checks")
        
        # Normalize configuration
        normalized_config = self.normalizer.normalize_and_override(config)
        
        results = []
        
        # Get selected LLM service
        llm_service = normalized_config.get('llm', {}).get('service', '').lower()
        
        if not llm_service:
            results.append(HealthCheckResult(
                service='llm',
                is_healthy=False,
                response_time_ms=None,
                error_message="No LLM service configured",
                details={'error_code': ErrorCode.MISSING_KEY.value}
            ))
            return results
        
        # Check the configured service
        if llm_service == 'openai':
            result = await self._check_openai_health(normalized_config.get('openai', {}))
        elif llm_service == 'anthropic':
            result = await self._check_anthropic_health(normalized_config.get('anthropic', {}))
        elif llm_service == 'ollama':
            result = await self._check_ollama_health(normalized_config.get('ollama', {}))
        else:
            result = HealthCheckResult(
                service=llm_service,
                is_healthy=False,
                response_time_ms=None,
                error_message=f"Unknown LLM service: {llm_service}",
                details={'error_code': ErrorCode.INVALID_SERVICE.value}
            )
        
        results.append(result)
        
        logger.info(f"Health check complete for {llm_service}: {'healthy' if result.is_healthy else 'unhealthy'}")
        return results
    
    async def check_service_health(self, service: str, config: Dict[str, Any]) -> HealthCheckResult:
        """
        Check health of a specific LLM service.
        
        Args:
            service: Service name (openai, anthropic, ollama)
            config: Configuration dictionary
            
        Returns:
            HealthCheckResult for the service
        """
        logger.info(f"Checking health for {service}")
        
        # Normalize configuration
        normalized_config = self.normalizer.normalize_and_override(config)
        service_config = normalized_config.get(service.lower(), {})
        
        if service.lower() == 'openai':
            return await self._check_openai_health(service_config)
        elif service.lower() == 'anthropic':
            return await self._check_anthropic_health(service_config)
        elif service.lower() == 'ollama':
            return await self._check_ollama_health(service_config)
        else:
            return HealthCheckResult(
                service=service,
                is_healthy=False,
                response_time_ms=None,
                error_message=f"Unknown service: {service}",
                details={'error_code': ErrorCode.INVALID_SERVICE.value}
            )
    
    async def _check_openai_health(self, config: Dict[str, Any]) -> HealthCheckResult:
        """Check OpenAI service health."""
        service = 'openai'
        start_time = time.time()
        
        try:
            api_key = config.get('api_key')
            if not api_key:
                return HealthCheckResult(
                    service=service,
                    is_healthy=False,
                    response_time_ms=None,
                    error_message="OpenAI API key not configured",
                    details={'error_code': ErrorCode.MISSING_KEY.value}
                )
            
            # Make a minimal API call to check connectivity and authentication
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "User-Agent": "Sync2NAS-HealthCheck/1.0"
                    }
                )
                
                response_time_ms = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    data = response.json()
                    model_count = len(data.get('data', []))
                    
                    return HealthCheckResult(
                        service=service,
                        is_healthy=True,
                        response_time_ms=response_time_ms,
                        error_message=None,
                        details={
                            'status_code': response.status_code,
                            'available_models': model_count,
                            'endpoint': 'https://api.openai.com/v1/models'
                        }
                    )
                elif response.status_code == 401:
                    return HealthCheckResult(
                        service=service,
                        is_healthy=False,
                        response_time_ms=response_time_ms,
                        error_message="Invalid OpenAI API key",
                        details={
                            'status_code': response.status_code,
                            'error_code': ErrorCode.AUTHENTICATION_FAILED.value,
                            'suggestion': 'Check your API key at https://platform.openai.com/api-keys'
                        }
                    )
                else:
                    return HealthCheckResult(
                        service=service,
                        is_healthy=False,
                        response_time_ms=response_time_ms,
                        error_message=f"OpenAI API returned status {response.status_code}",
                        details={
                            'status_code': response.status_code,
                            'error_code': ErrorCode.CONNECTIVITY_FAILED.value
                        }
                    )
        
        except httpx.TimeoutException:
            return HealthCheckResult(
                service=service,
                is_healthy=False,
                response_time_ms=(time.time() - start_time) * 1000,
                error_message="Timeout connecting to OpenAI API",
                details={
                    'error_code': ErrorCode.CONNECTIVITY_FAILED.value,
                    'timeout_seconds': self.timeout
                }
            )
        except Exception as e:
            return HealthCheckResult(
                service=service,
                is_healthy=False,
                response_time_ms=(time.time() - start_time) * 1000,
                error_message=f"Error connecting to OpenAI: {str(e)}",
                details={
                    'error_code': ErrorCode.CONNECTIVITY_FAILED.value,
                    'exception_type': type(e).__name__
                }
            )
    
    async def _check_anthropic_health(self, config: Dict[str, Any]) -> HealthCheckResult:
        """Check Anthropic service health."""
        service = 'anthropic'
        start_time = time.time()
        
        try:
            api_key = config.get('api_key')
            if not api_key:
                return HealthCheckResult(
                    service=service,
                    is_healthy=False,
                    response_time_ms=None,
                    error_message="Anthropic API key not configured",
                    details={'error_code': ErrorCode.MISSING_KEY.value}
                )
            
            # Make a minimal API call to check connectivity and authentication
            # Anthropic doesn't have a models endpoint, so we'll make a small completion request
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                        "User-Agent": "Sync2NAS-HealthCheck/1.0"
                    },
                    json={
                        "model": config.get('model', 'claude-3-haiku-20240307'),
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "Hi"}]
                    }
                )
                
                response_time_ms = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    return HealthCheckResult(
                        service=service,
                        is_healthy=True,
                        response_time_ms=response_time_ms,
                        error_message=None,
                        details={
                            'status_code': response.status_code,
                            'model': config.get('model', 'claude-3-haiku-20240307'),
                            'endpoint': 'https://api.anthropic.com/v1/messages'
                        }
                    )
                elif response.status_code == 401:
                    return HealthCheckResult(
                        service=service,
                        is_healthy=False,
                        response_time_ms=response_time_ms,
                        error_message="Invalid Anthropic API key",
                        details={
                            'status_code': response.status_code,
                            'error_code': ErrorCode.AUTHENTICATION_FAILED.value,
                            'suggestion': 'Check your API key at https://console.anthropic.com/'
                        }
                    )
                elif response.status_code == 400:
                    # Check if it's a model availability issue
                    try:
                        error_data = response.json()
                        if 'model' in str(error_data).lower():
                            return HealthCheckResult(
                                service=service,
                                is_healthy=False,
                                response_time_ms=response_time_ms,
                                error_message=f"Model '{config.get('model')}' not available",
                                details={
                                    'status_code': response.status_code,
                                    'error_code': ErrorCode.MODEL_UNAVAILABLE.value,
                                    'suggestion': 'Check available models in Anthropic console'
                                }
                            )
                    except:
                        pass
                    
                    return HealthCheckResult(
                        service=service,
                        is_healthy=False,
                        response_time_ms=response_time_ms,
                        error_message=f"Anthropic API returned status {response.status_code}",
                        details={
                            'status_code': response.status_code,
                            'error_code': ErrorCode.CONNECTIVITY_FAILED.value
                        }
                    )
                else:
                    return HealthCheckResult(
                        service=service,
                        is_healthy=False,
                        response_time_ms=response_time_ms,
                        error_message=f"Anthropic API returned status {response.status_code}",
                        details={
                            'status_code': response.status_code,
                            'error_code': ErrorCode.CONNECTIVITY_FAILED.value
                        }
                    )
        
        except httpx.TimeoutException:
            return HealthCheckResult(
                service=service,
                is_healthy=False,
                response_time_ms=(time.time() - start_time) * 1000,
                error_message="Timeout connecting to Anthropic API",
                details={
                    'error_code': ErrorCode.CONNECTIVITY_FAILED.value,
                    'timeout_seconds': self.timeout
                }
            )
        except Exception as e:
            return HealthCheckResult(
                service=service,
                is_healthy=False,
                response_time_ms=(time.time() - start_time) * 1000,
                error_message=f"Error connecting to Anthropic: {str(e)}",
                details={
                    'error_code': ErrorCode.CONNECTIVITY_FAILED.value,
                    'exception_type': type(e).__name__
                }
            )
    
    async def _check_ollama_health(self, config: Dict[str, Any]) -> HealthCheckResult:
        """Check Ollama service health."""
        service = 'ollama'
        start_time = time.time()
        
        try:
            host = config.get('host', 'http://localhost:11434')
            model = config.get('model')
            
            if not model:
                return HealthCheckResult(
                    service=service,
                    is_healthy=False,
                    response_time_ms=None,
                    error_message="Ollama model not configured",
                    details={'error_code': ErrorCode.MISSING_KEY.value}
                )
            
            # First check if Ollama service is running
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Check service availability
                try:
                    response = await client.get(f"{host}/api/tags")
                    response_time_ms = (time.time() - start_time) * 1000
                    
                    if response.status_code != 200:
                        return HealthCheckResult(
                            service=service,
                            is_healthy=False,
                            response_time_ms=response_time_ms,
                            error_message=f"Ollama service returned status {response.status_code}",
                            details={
                                'status_code': response.status_code,
                                'error_code': ErrorCode.SERVICE_UNREACHABLE.value,
                                'host': host
                            }
                        )
                    
                    # Check if the specified model is available
                    data = response.json()
                    available_models = [m.get('name', '') for m in data.get('models', [])]
                    
                    model_available = any(model in available_model for available_model in available_models)
                    
                    if not model_available:
                        return HealthCheckResult(
                            service=service,
                            is_healthy=False,
                            response_time_ms=response_time_ms,
                            error_message=f"Model '{model}' not found in Ollama",
                            details={
                                'error_code': ErrorCode.MODEL_UNAVAILABLE.value,
                                'available_models': available_models,
                                'requested_model': model,
                                'suggestion': f'Install model with: ollama pull {model}'
                            }
                        )
                    
                    # Test model with a simple generation request
                    start_time = time.time()  # Reset timer for generation test
                    gen_response = await client.post(
                        f"{host}/api/generate",
                        json={
                            "model": model,
                            "prompt": "Hi",
                            "stream": False,
                            "options": {"num_predict": 1}
                        }
                    )
                    
                    generation_time_ms = (time.time() - start_time) * 1000
                    
                    if gen_response.status_code == 200:
                        return HealthCheckResult(
                            service=service,
                            is_healthy=True,
                            response_time_ms=generation_time_ms,
                            error_message=None,
                            details={
                                'status_code': gen_response.status_code,
                                'model': model,
                                'host': host,
                                'available_models': len(available_models),
                                'generation_test': 'passed'
                            }
                        )
                    else:
                        return HealthCheckResult(
                            service=service,
                            is_healthy=False,
                            response_time_ms=generation_time_ms,
                            error_message=f"Model generation test failed with status {gen_response.status_code}",
                            details={
                                'status_code': gen_response.status_code,
                                'error_code': ErrorCode.MODEL_UNAVAILABLE.value,
                                'model': model
                            }
                        )
                
                except httpx.ConnectError:
                    return HealthCheckResult(
                        service=service,
                        is_healthy=False,
                        response_time_ms=(time.time() - start_time) * 1000,
                        error_message=f"Cannot connect to Ollama at {host}",
                        details={
                            'error_code': ErrorCode.SERVICE_UNREACHABLE.value,
                            'host': host,
                            'suggestion': 'Ensure Ollama is running: ollama serve'
                        }
                    )
        
        except httpx.TimeoutException:
            return HealthCheckResult(
                service=service,
                is_healthy=False,
                response_time_ms=(time.time() - start_time) * 1000,
                error_message="Timeout connecting to Ollama",
                details={
                    'error_code': ErrorCode.CONNECTIVITY_FAILED.value,
                    'timeout_seconds': self.timeout,
                    'host': config.get('host', 'http://localhost:11434')
                }
            )
        except Exception as e:
            return HealthCheckResult(
                service=service,
                is_healthy=False,
                response_time_ms=(time.time() - start_time) * 1000,
                error_message=f"Error connecting to Ollama: {str(e)}",
                details={
                    'error_code': ErrorCode.CONNECTIVITY_FAILED.value,
                    'exception_type': type(e).__name__,
                    'host': config.get('host', 'http://localhost:11434')
                }
            )
    
    def check_llm_health_sync(self, config: Dict[str, Any]) -> List[HealthCheckResult]:
        """
        Synchronous wrapper for LLM health checks.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            List of HealthCheckResult
        """
        try:
            # Try to get existing event loop
            loop = asyncio.get_running_loop()
            # If we're in an async context, we can't use run_until_complete
            raise RuntimeError("Cannot run sync method from async context")
        except RuntimeError:
            # No running loop, create a new one
            return asyncio.run(self.check_llm_health(config))
    
    def check_service_health_sync(self, service: str, config: Dict[str, Any]) -> HealthCheckResult:
        """
        Synchronous wrapper for service health checks.
        
        Args:
            service: Service name
            config: Configuration dictionary
            
        Returns:
            HealthCheckResult
        """
        try:
            # Try to get existing event loop
            loop = asyncio.get_running_loop()
            # If we're in an async context, we can't use run_until_complete
            raise RuntimeError("Cannot run sync method from async context")
        except RuntimeError:
            # No running loop, create a new one
            return asyncio.run(self.check_service_health(service, config))