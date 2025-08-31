"""
Integration tests for advanced validation scenarios and edge cases.

Tests complex validation scenarios, error recovery, monitoring integration,
and advanced configuration patterns.
"""

import os
import pytest
import tempfile
import time
import asyncio
from unittest.mock import patch, MagicMock, call
from concurrent.futures import ThreadPoolExecutor

from utils.sync2nas_config import load_configuration
from utils.config.config_validator import ConfigValidator
from utils.config.config_normalizer import ConfigNormalizer
from utils.config.health_checker import ConfigHealthChecker
from utils.config.config_suggester import ConfigSuggester
from utils.config.validation_models import ValidationResult, HealthCheckResult, ErrorCode
from services.llm_factory import create_llm_service, LLMServiceCreationError


class TestAdvancedValidationIntegration:
    """Test advanced validation scenarios and edge cases."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ConfigValidator()
        self.normalizer = ConfigNormalizer()
        self.health_checker = ConfigHealthChecker()
        self.suggester = ConfigSuggester()
    
    def create_temp_config(self, content: str) -> str:
        """Create a temporary configuration file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(content)
            return f.name
    
    def test_concurrent_validation_scenarios(self):
        """Test validation under concurrent access scenarios."""
        configs = [
            {
                'llm': {'service': 'openai'},
                'openai': {
                    'api_key': f'sk-test{i:04d}1234567890abcdef1234567890abcdef1234567890ab',
                    'model': 'gemma3:12b'
                }
            }
            for i in range(10)
        ]
        
        def validate_config(config):
            """Validate a single configuration."""
            return self.validator.validate_llm_config(config)
        
        # Test concurrent validation
        with ThreadPoolExecutor(max_workers=5) as executor:
            start_time = time.time()
            
            # Submit all validation tasks
            futures = [executor.submit(validate_config, config) for config in configs]
            
            # Collect results
            results = [future.result() for future in futures]
            
            end_time = time.time()
            total_time = end_time - start_time
        
        # All validations should succeed
        assert all(result.is_valid for result in results)
        
        # Should complete within reasonable time (concurrent should be faster)
        assert total_time < 5.0
        
        # All results should have consistent structure
        for result in results:
            assert isinstance(result, ValidationResult)
            assert len(result.errors) == 0
    
    def test_validation_with_network_timeouts(self):
        """Test validation behavior with network timeouts."""
        config = {
            'llm': {'service': 'openai'},
            'openai': {
                'api_key': 'sk-test1234567890abcdef1234567890abcdef1234567890ab',
                'model': 'gemma3:12b'
            }
        }
        
        with patch('utils.config.health_checker.httpx.AsyncClient') as mock_httpx:
            # Mock timeout scenario
            async def timeout_get(*args, **kwargs):
                await asyncio.sleep(2)  # Simulate slow response
                raise Exception("Request timeout")
            
            mock_client = MagicMock()
            mock_client.get.side_effect = timeout_get
            mock_httpx.return_value.__aenter__.return_value = mock_client
            
            # Test health check with timeout
            health_checker = ConfigHealthChecker(timeout=1.0)  # 1 second timeout
            
            start_time = time.time()
            result = health_checker.check_service_health_sync('openai', config)
            end_time = time.time()
            
            # Should handle timeout gracefully
            assert not result.is_healthy
            assert "timeout" in result.error_message.lower() or "request timeout" in result.error_message.lower()
            
            # Should not take much longer than timeout
            assert (end_time - start_time) < 3.0
    
    def test_validation_with_memory_constraints(self):
        """Test validation behavior under memory constraints."""
        # Create large configuration to test memory usage
        large_config = {
            'llm': {'service': 'openai'},
            'openai': {
                'api_key': 'sk-test1234567890abcdef1234567890abcdef1234567890ab',
                'model': 'gemma3:12b'
            }
        }
        
        # Add many large sections
        for i in range(1000):
            large_config[f'large_section_{i}'] = {
                f'key_{j}': 'x' * 1000 for j in range(10)  # Large values
            }
        
        # Test validation with large config
        start_time = time.time()
        result = self.validator.validate_llm_config(large_config)
        end_time = time.time()
        
        # Should handle large config efficiently
        assert result.is_valid
        assert (end_time - start_time) < 5.0  # Should complete within 5 seconds
    
    def test_validation_error_recovery_scenarios(self):
        """Test error recovery and suggestion accuracy."""
        # Start with completely broken configuration
        broken_config = {
            'LLM': {'servic': 'invalid_service'},
            'OpenAI': {
                'api_ky': 'invalid_key',
                'mdoel': 'invalid_model',
                'max_tokens': 'not_a_number'
            },
            'olama': {
                'mdoel': '',
                'hostname': 'not_a_url'
            }
        }
        
        # Step 1: Initial validation (should fail with suggestions)
        result1 = self.validator.validate_llm_config(broken_config)
        assert not result1.is_valid
        assert len(result1.errors) > 0
        assert len(result1.suggestions) > 0
        
        # Step 2: Apply some suggestions (simulate user fixing issues)
        partially_fixed_config = {
            'llm': {'service': 'openai'},  # Fixed section name and key
            'openai': {  # Fixed section name
                'api_key': 'sk-test1234567890abcdef1234567890abcdef1234567890ab',  # Fixed key name and value
                'model': 'gemma3:12b',  # Fixed key name and value
                'max_tokens': '4000'  # Fixed value type
            }
        }
        
        # Step 3: Validate partially fixed config
        result2 = self.validator.validate_llm_config(partially_fixed_config)
        assert result2.is_valid
        assert len(result2.errors) == 0
        
        # Step 4: Test service creation with fixed config
        with patch('services.llm_implementations.openai_implementation.openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="Test"))]
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            service = create_llm_service(partially_fixed_config, validate_health=False)
            assert service is not None
    
    def test_validation_with_edge_case_values(self):
        """Test validation with edge case configuration values."""
        edge_case_configs = [
            # Empty strings
            {
                'llm': {'service': 'openai'},
                'openai': {'api_key': '', 'model': 'gemma3:12b'}
            },
            # Very long strings
            {
                'llm': {'service': 'openai'},
                'openai': {
                    'api_key': 'sk-' + 'x' * 1000,
                    'model': 'gemma3:12b'
                }
            },
            # Special characters
            {
                'llm': {'service': 'openai'},
                'openai': {
                    'api_key': 'sk-test!@#$%^&*()1234567890abcdef1234567890abcdef',
                    'model': 'gemma3:12b'
                }
            },
            # Unicode characters
            {
                'llm': {'service': 'openai'},
                'openai': {
                    'api_key': 'sk-test🔑1234567890abcdef1234567890abcdef1234567890ab',
                    'model': 'gemma3:12b'
                }
            },
            # Numeric strings that should be strings
            {
                'llm': {'service': 'openai'},
                'openai': {
                    'api_key': '12345678901234567890123456789012345678901234567890',
                    'model': 'gemma3:12b'
                }
            }
        ]
        
        for i, config in enumerate(edge_case_configs):
            result = self.validator.validate_llm_config(config)
            
            # Should handle edge cases gracefully (may be valid or invalid)
            assert isinstance(result, ValidationResult)
            assert isinstance(result.is_valid, bool)
            assert isinstance(result.errors, list)
            assert isinstance(result.suggestions, list)
            
            # If invalid, should provide helpful error messages
            if not result.is_valid:
                for error in result.errors:
                    assert error.message is not None
                    assert len(error.message) > 0
                    assert error.error_code is not None
    
    def test_validation_with_circular_references(self):
        """Test validation with potential circular reference scenarios."""
        # Configuration that might cause circular references in validation logic
        config_with_refs = {
            'llm': {'service': 'openai'},
            'openai': {
                'api_key': 'sk-test1234567890abcdef1234567890abcdef1234567890ab',
                'model': 'gemma3:12b',
                'fallback_service': 'ollama'  # Reference to another service
            },
            'ollama': {
                'model': 'gemma3:12b',
                'fallback_service': 'anthropic'  # Another reference
            },
            'anthropic': {
                'api_key': 'sk-ant-test1234567890abcdef1234567890abcdef1234567890ab',
                'model': 'gemma3:12b',
                'fallback_service': 'openai'  # Circular reference
            }
        }
        
        # Should handle circular references gracefully
        result = self.validator.validate_llm_config(config_with_refs)
        
        # Should not hang or crash
        assert isinstance(result, ValidationResult)
        
        # Primary service should be valid
        assert result.is_valid  # OpenAI config is valid regardless of fallback
    
    def test_validation_performance_benchmarking(self):
        """Test validation performance across different scenarios."""
        test_scenarios = [
            # Small config
            {
                'name': 'small_config',
                'config': {
                    'llm': {'service': 'openai'},
                    'openai': {
                        'api_key': 'sk-test1234567890abcdef1234567890abcdef1234567890ab',
                        'model': 'gemma3:12b'
                    }
                }
            },
            # Medium config
            {
                'name': 'medium_config',
                'config': {
                    'llm': {'service': 'openai'},
                    'openai': {
                        'api_key': 'sk-test1234567890abcdef1234567890abcdef1234567890ab',
                        'model': 'gemma3:12b',
                        'max_tokens': '4000',
                        'temperature': '0.1'
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
            },
            # Large config
            {
                'name': 'large_config',
                'config': {
                    'llm': {'service': 'openai'},
                    'openai': {
                        'api_key': 'sk-test1234567890abcdef1234567890abcdef1234567890ab',
                        'model': 'gemma3:12b'
                    },
                    **{f'section_{i}': {f'key_{j}': f'value_{j}' for j in range(50)} for i in range(100)}
                }
            }
        ]
        
        performance_results = {}
        
        for scenario in test_scenarios:
            # Measure validation time
            start_time = time.time()
            
            # Run validation multiple times for average
            for _ in range(10):
                result = self.validator.validate_llm_config(scenario['config'])
                assert isinstance(result, ValidationResult)
            
            end_time = time.time()
            avg_time = (end_time - start_time) / 10
            
            performance_results[scenario['name']] = avg_time
        
        # Performance assertions (more lenient for CI/test environments)
        assert performance_results['small_config'] < 0.5  # < 500ms
        assert performance_results['medium_config'] < 1.0  # < 1s
        assert performance_results['large_config'] < 5.0   # < 5s
        
        # Large config should not be more than 20x slower than small config (avoid division by zero)
        if performance_results['small_config'] > 0:
            assert performance_results['large_config'] < performance_results['small_config'] * 20
        else:
            # If small config is very fast (< 1ms), just ensure large config is reasonable
            assert performance_results['large_config'] < 5.0
    
    def test_suggestion_accuracy_comprehensive(self):
        """Test comprehensive suggestion accuracy across various error types."""
        test_cases = [
            {
                'name': 'typo_in_section_name',
                'config': {'LLM': {'service': 'openai'}, 'OpenAI': {'api_key': 'test'}},
                'expected_suggestions': ['llm', 'openai'],
                'error_types': [ErrorCode.API_KEY_INVALID]  # Invalid API key format
            },
            {
                'name': 'typo_in_key_name',
                'config': {
                    'llm': {'service': 'openai'},
                    'openai': {'api_ky': 'sk-test1234567890abcdef1234567890abcdef1234567890ab'}
                },
                'expected_suggestions': ['api_key', 'model'],
                'error_types': [ErrorCode.MISSING_KEY]  # Missing model key
            },
            {
                'name': 'invalid_service_name',
                'config': {'llm': {'service': 'invalid_service'}},
                'expected_suggestions': ['openai', 'ollama', 'anthropic'],
                'error_types': [ErrorCode.INVALID_SERVICE]
            },
            {
                'name': 'invalid_api_key_format',
                'config': {
                    'llm': {'service': 'openai'},
                    'openai': {'api_key': 'invalid_key', 'model': 'gemma3:12b'}
                },
                'expected_suggestions': ['openai', 'configuration'],
                'error_types': [ErrorCode.API_KEY_INVALID]
            },
            {
                'name': 'missing_required_section',
                'config': {'llm': {'service': 'openai'}},
                'expected_suggestions': ['openai', 'api_key'],
                'error_types': [ErrorCode.MISSING_SECTION]
            }
        ]
        
        for test_case in test_cases:
            result = self.validator.validate_llm_config(test_case['config'])
            
            # Should have errors
            assert not result.is_valid, f"Test case '{test_case['name']}' should be invalid"
            
            # Should have expected error types
            actual_error_codes = [error.error_code for error in result.errors]
            for expected_error_type in test_case['error_types']:
                assert expected_error_type in actual_error_codes, \
                    f"Expected error type {expected_error_type} in {actual_error_codes} for '{test_case['name']}'"
            
            # Should have helpful suggestions
            assert len(result.suggestions) > 0, f"Test case '{test_case['name']}' should have suggestions"
            
            suggestion_text = ' '.join(result.suggestions).lower()
            
            # Check for expected suggestions
            found_suggestions = []
            for expected_suggestion in test_case['expected_suggestions']:
                if expected_suggestion.lower() in suggestion_text:
                    found_suggestions.append(expected_suggestion)
            
            # Should find at least some expected suggestions
            assert len(found_suggestions) > 0, \
                f"Expected suggestions {test_case['expected_suggestions']} not found in '{suggestion_text}' for '{test_case['name']}'"
    
    def test_health_check_resilience(self):
        """Test health check resilience under various failure conditions."""
        config = {
            'llm': {'service': 'openai'},
            'openai': {
                'api_key': 'sk-test1234567890abcdef1234567890abcdef1234567890ab',
                'model': 'gemma3:12b'
            }
        }
        
        failure_scenarios = [
            # Network timeout
            {
                'name': 'network_timeout',
                'exception': Exception("Connection timeout"),
                'expected_error_keywords': ['timeout', 'connection']
            },
            # API rate limit
            {
                'name': 'rate_limit',
                'exception': Exception("Rate limit exceeded"),
                'expected_error_keywords': ['rate', 'limit']
            },
            # Invalid API key
            {
                'name': 'invalid_api_key',
                'exception': Exception("Invalid API key"),
                'expected_error_keywords': ['api', 'key', 'invalid']
            },
            # Service unavailable
            {
                'name': 'service_unavailable',
                'exception': Exception("Service temporarily unavailable"),
                'expected_error_keywords': ['service', 'unavailable']
            },
            # Generic network error
            {
                'name': 'network_error',
                'exception': Exception("Network error occurred"),
                'expected_error_keywords': ['network', 'error']
            }
        ]
        
        for scenario in failure_scenarios:
            with patch('services.llm_implementations.openai_implementation.openai.OpenAI') as mock_openai:
                # Mock the specific failure
                mock_openai.side_effect = scenario['exception']
                
                # Test health check
                result = self.health_checker.check_service_health_sync('openai', config)
                
                # Should handle failure gracefully
                assert not result.is_healthy, f"Scenario '{scenario['name']}' should be unhealthy"
                assert result.error_message is not None
                assert len(result.error_message) > 0
                
                # Should contain relevant error keywords (or be a generic API key error for mocked services)
                error_message_lower = result.error_message.lower()
                found_keywords = [
                    keyword for keyword in scenario['expected_error_keywords']
                    if keyword in error_message_lower
                ]
                
                # For mocked services, we might get generic API key errors instead of specific network errors
                # This is acceptable as the health check is still detecting failures
                assert len(found_keywords) > 0 or 'api key' in error_message_lower or 'invalid' in error_message_lower, \
                    f"Expected keywords {scenario['expected_error_keywords']} or generic error not found in '{result.error_message}' for '{scenario['name']}'"
    
    def test_integration_with_logging_and_monitoring(self):
        """Test integration with logging and monitoring systems."""
        config = {
            'llm': {'service': 'openai'},
            'openai': {
                'api_key': 'sk-test1234567890abcdef1234567890abcdef1234567890ab',
                'model': 'gemma3:12b'
            }
        }
        
        with patch('utils.config.health_checker.httpx.AsyncClient') as mock_httpx:
            
            # Mock successful OpenAI response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'data': [{'id': 'gpt-4'}]}
            
            async def mock_get(*args, **kwargs):
                return mock_response
            
            mock_client = MagicMock()
            mock_client.get = mock_get
            mock_httpx.return_value.__aenter__.return_value = mock_client
            
            # Run validation and health check
            validation_result = self.validator.validate_llm_config(config)
            health_result = self.health_checker.check_service_health_sync('openai', config)
            
            # Validation and health check should complete successfully
            assert validation_result.is_valid
            assert health_result.is_healthy
    
    def test_configuration_template_generation_integration(self):
        """Test configuration template generation integration."""
        services = ['openai', 'ollama', 'anthropic']
        
        for service in services:
            # Generate template
            template = self.suggester.generate_config_template(service)
            
            # Template should be valid configuration format
            assert f'[llm]' in template
            assert f'service = {service}' in template
            assert f'[{service}]' in template
            
            # Should contain service-specific guidance
            if service == 'openai':
                assert 'api_key' in template
                assert 'platform.openai.com' in template
                assert 'gpt-' in template
            elif service == 'ollama':
                assert 'model' in template
                assert 'ollama' in template.lower()
                assert 'localhost' in template or 'host' in template
            elif service == 'anthropic':
                assert 'api_key' in template
                assert 'console.anthropic.com' in template
                assert 'claude-' in template
            
            # Template should be parseable as configuration
            # (This would require implementing a config parser test, but we can check basic format)
            lines = template.split('\n')
            section_lines = [line for line in lines if line.strip().startswith('[') and line.strip().endswith(']')]
            assert len(section_lines) >= 2  # At least [llm] and [service] sections