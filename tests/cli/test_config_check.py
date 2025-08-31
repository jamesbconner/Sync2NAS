"""
Tests for the config-check CLI command.

This module tests the configuration health check CLI command functionality,
including validation, connectivity tests, error handling, and output formatting.
"""

import pytest
from click.testing import CliRunner
from unittest.mock import MagicMock, patch, Mock
from cli.config_check import config_check
from utils.config.validation_models import ValidationResult, ValidationError, HealthCheckResult, ErrorCode


@pytest.fixture
def runner():
    """Fixture providing a Click CliRunner instance."""
    return CliRunner()


@pytest.fixture
def mock_config():
    """Fixture providing a mock configuration dictionary."""
    return {
        'llm': {'service': 'ollama'},
        'ollama': {'model': 'llama2', 'host': 'http://localhost:11434'},
        'openai': {'api_key': 'test-key', 'model': 'gpt-3.5-turbo'},
        'anthropic': {'api_key': 'test-key', 'model': 'claude-3-haiku-20240307'}
    }


@pytest.fixture
def valid_validation_result():
    """Fixture providing a valid ValidationResult."""
    return ValidationResult(
        is_valid=True,
        errors=[],
        warnings=[],
        suggestions=[]
    )


@pytest.fixture
def invalid_validation_result():
    """Fixture providing an invalid ValidationResult with errors."""
    return ValidationResult(
        is_valid=False,
        errors=[
            ValidationError(
                section='ollama',
                key='model',
                message='Model not configured',
                suggestion='Add model = llama2 to [ollama] section',
                error_code=ErrorCode.MISSING_KEY.value
            )
        ],
        warnings=['Consider upgrading to a newer model'],
        suggestions=['Use environment variables for sensitive configuration']
    )


@pytest.fixture
def healthy_result():
    """Fixture providing a healthy HealthCheckResult."""
    return HealthCheckResult(
        service='ollama',
        is_healthy=True,
        response_time_ms=150.5,
        error_message=None,
        details={
            'status_code': 200,
            'model': 'llama2',
            'host': 'http://localhost:11434',
            'available_models': 5,
            'generation_test': 'passed'
        }
    )


@pytest.fixture
def unhealthy_result():
    """Fixture providing an unhealthy HealthCheckResult."""
    return HealthCheckResult(
        service='ollama',
        is_healthy=False,
        response_time_ms=None,
        error_message='Cannot connect to Ollama at http://localhost:11434',
        details={
            'error_code': ErrorCode.SERVICE_UNREACHABLE.value,
            'host': 'http://localhost:11434',
            'suggestion': 'Ensure Ollama is running: ollama serve'
        }
    )


class TestConfigCheckBasic:
    """Test basic config-check command functionality."""
    
    @patch('cli.config_check.load_configuration')
    @patch('cli.config_check.ConfigValidator')
    @patch('cli.config_check.ConfigHealthChecker')
    def test_config_check_all_services_success(self, mock_health_checker_class, mock_validator_class, 
                                             mock_load_config, runner, mock_config, 
                                             valid_validation_result, healthy_result, mock_llm_service_patch):
        """Test successful config check for all services."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_validator = Mock()
        mock_validator.validate_llm_config.return_value = valid_validation_result
        mock_validator_class.return_value = mock_validator
        
        mock_health_checker = Mock()
        mock_health_checker.check_llm_health_sync.return_value = [healthy_result]
        mock_health_checker_class.return_value = mock_health_checker
        
        # Run command
        result = runner.invoke(config_check, [])
        
        # Assertions
        assert result.exit_code == 0
        assert "Configuration validation passed" in result.output
        assert "All checks passed!" in result.output
        assert "Service is responding correctly" in result.output
        
        # Verify method calls
        mock_validator.validate_llm_config.assert_called_once_with(mock_config)
        mock_health_checker.check_llm_health_sync.assert_called_once_with(mock_config)
    
    @patch('cli.config_check.load_configuration')
    @patch('cli.config_check.ConfigValidator')
    def test_config_check_validation_failure(self, mock_validator_class, mock_load_config, 
                                           runner, mock_config, invalid_validation_result, mock_llm_service_patch):
        """Test config check with validation failure."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_validator = Mock()
        mock_validator.validate_llm_config.return_value = invalid_validation_result
        mock_validator_class.return_value = mock_validator
        
        # Run command
        result = runner.invoke(config_check, [])
        
        # Assertions
        assert result.exit_code == 1
        assert "Configuration validation failed" in result.output
        assert "Model not configured" in result.output
        assert "Add model = llama2 to" in result.output
        assert "Configuration validation failed. Please fix the issues above" in result.output
    
    @patch('cli.config_check.load_configuration')
    def test_config_check_load_config_failure(self, mock_load_config, runner, mock_llm_service_patch):
        """Test config check with configuration loading failure."""
        # Setup mock to raise exception
        mock_load_config.side_effect = Exception("Config file not found")
        
        # Run command
        result = runner.invoke(config_check, [])
        
        # Assertions
        assert result.exit_code == 1
        assert "Failed to load configuration" in result.output
        assert "Config file not found" in result.output


class TestConfigCheckSpecificService:
    """Test config-check command with specific service selection."""
    
    @patch('cli.config_check.load_configuration')
    @patch('cli.config_check.ConfigValidator')
    @patch('cli.config_check.ConfigHealthChecker')
    def test_config_check_specific_service(self, mock_health_checker_class, mock_validator_class, 
                                         mock_load_config, runner, mock_config, 
                                         valid_validation_result, healthy_result, mock_llm_service_patch):
        """Test config check for a specific service."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_validator = Mock()
        mock_validator.validate_service_config.return_value = valid_validation_result
        mock_validator_class.return_value = mock_validator
        
        mock_health_checker = Mock()
        mock_health_checker.check_service_health_sync.return_value = healthy_result
        mock_health_checker_class.return_value = mock_health_checker
        
        # Run command
        result = runner.invoke(config_check, ['-s', 'ollama'])
        
        # Assertions
        assert result.exit_code == 0
        assert "Service: ollama" in result.output
        assert "Configuration validation passed" in result.output
        assert "All checks passed!" in result.output
        
        # Verify method calls
        mock_validator.validate_service_config.assert_called_once_with('ollama', mock_config)
        mock_health_checker.check_service_health_sync.assert_called_once_with('ollama', mock_config)
    
    @patch('cli.config_check.load_configuration')
    @patch('cli.config_check.ConfigValidator')
    @patch('cli.config_check.ConfigHealthChecker')
    def test_config_check_openai_service(self, mock_health_checker_class, mock_validator_class, 
                                       mock_load_config, runner, mock_config, 
                                       valid_validation_result, mock_llm_service_patch):
        """Test config check for OpenAI service."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_validator = Mock()
        mock_validator.validate_service_config.return_value = valid_validation_result
        mock_validator_class.return_value = mock_validator
        
        openai_result = HealthCheckResult(
            service='openai',
            is_healthy=True,
            response_time_ms=250.0,
            error_message=None,
            details={
                'status_code': 200,
                'available_models': 10,
                'endpoint': 'https://api.openai.com/v1/models'
            }
        )
        
        mock_health_checker = Mock()
        mock_health_checker.check_service_health_sync.return_value = openai_result
        mock_health_checker_class.return_value = mock_health_checker
        
        # Run command
        result = runner.invoke(config_check, ['-s', 'openai'])
        
        # Assertions
        assert result.exit_code == 0
        assert "Service: openai" in result.output
        assert "All checks passed!" in result.output
        
        # Verify method calls
        mock_validator.validate_service_config.assert_called_once_with('openai', mock_config)
        mock_health_checker.check_service_health_sync.assert_called_once_with('openai', mock_config)


class TestConfigCheckOptions:
    """Test config-check command options and flags."""
    
    @patch('cli.config_check.load_configuration')
    @patch('cli.config_check.ConfigValidator')
    def test_config_check_skip_connectivity(self, mock_validator_class, mock_load_config, 
                                          runner, mock_config, valid_validation_result, mock_llm_service_patch):
        """Test config check with --skip-connectivity flag."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_validator = Mock()
        mock_validator.validate_llm_config.return_value = valid_validation_result
        mock_validator_class.return_value = mock_validator
        
        # Run command
        result = runner.invoke(config_check, ['--skip-connectivity'])
        
        # Assertions
        assert result.exit_code == 0
        assert "Configuration validation passed" in result.output
        assert "Skipping connectivity tests as requested" in result.output
        assert "All checks passed!" in result.output
        
        # Verify validation was called but health check was not
        mock_validator.validate_llm_config.assert_called_once_with(mock_config)
    
    @patch('cli.config_check.load_configuration')
    @patch('cli.config_check.ConfigValidator')
    @patch('cli.config_check.ConfigHealthChecker')
    def test_config_check_custom_timeout(self, mock_health_checker_class, mock_validator_class, 
                                       mock_load_config, runner, mock_config, 
                                       valid_validation_result, healthy_result, mock_llm_service_patch):
        """Test config check with custom timeout."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_validator = Mock()
        mock_validator.validate_llm_config.return_value = valid_validation_result
        mock_validator_class.return_value = mock_validator
        
        mock_health_checker = Mock()
        mock_health_checker.check_llm_health_sync.return_value = [healthy_result]
        mock_health_checker_class.return_value = mock_health_checker
        
        # Run command
        result = runner.invoke(config_check, ['-t', '5.0'])
        
        # Assertions
        assert result.exit_code == 0
        assert "Timeout: 5.0s" in result.output
        
        # Verify health checker was initialized with custom timeout
        mock_health_checker_class.assert_called_once_with(timeout=5.0)
    
    @patch('cli.config_check.load_configuration')
    @patch('cli.config_check.ConfigValidator')
    @patch('cli.config_check.ConfigHealthChecker')
    def test_config_check_verbose_mode(self, mock_health_checker_class, mock_validator_class, 
                                     mock_load_config, runner, mock_config, unhealthy_result, mock_llm_service_patch):
        """Test config check with verbose output."""
        # Setup mocks with validation warnings and suggestions
        validation_result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=['Consider upgrading to a newer model'],
            suggestions=['Use environment variables for sensitive configuration']
        )
        
        mock_load_config.return_value = mock_config
        mock_validator = Mock()
        mock_validator.validate_llm_config.return_value = validation_result
        mock_validator_class.return_value = mock_validator
        
        mock_health_checker = Mock()
        mock_health_checker.check_llm_health_sync.return_value = [unhealthy_result]
        mock_health_checker_class.return_value = mock_health_checker
        
        # Run command
        result = runner.invoke(config_check, ['-v'])
        
        # Assertions
        assert result.exit_code == 1  # Should fail due to unhealthy service
        assert "Consider upgrading to a newer model" in result.output
        assert "Use environment variables for sensitive configuration" in result.output
        assert "Detailed Error Information" in result.output
        assert "Ensure Ollama is running: ollama serve" in result.output


class TestConfigCheckHealthResults:
    """Test config-check command health check result handling."""
    
    @patch('cli.config_check.load_configuration')
    @patch('cli.config_check.ConfigValidator')
    @patch('cli.config_check.ConfigHealthChecker')
    def test_config_check_connectivity_failure(self, mock_health_checker_class, mock_validator_class, 
                                             mock_load_config, runner, mock_config, 
                                             valid_validation_result, unhealthy_result, mock_llm_service_patch):
        """Test config check with connectivity failure."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_validator = Mock()
        mock_validator.validate_llm_config.return_value = valid_validation_result
        mock_validator_class.return_value = mock_validator
        
        mock_health_checker = Mock()
        mock_health_checker.check_llm_health_sync.return_value = [unhealthy_result]
        mock_health_checker_class.return_value = mock_health_checker
        
        # Run command
        result = runner.invoke(config_check, [])
        
        # Assertions
        assert result.exit_code == 1
        assert "Configuration validation passed" in result.output
        assert "❌ Unhealthy" in result.output
        assert "Cannot connect to Ollama" in result.output
        assert "1 service(s) failed connectivity tests" in result.output
    
    @patch('cli.config_check.load_configuration')
    @patch('cli.config_check.ConfigValidator')
    @patch('cli.config_check.ConfigHealthChecker')
    def test_config_check_multiple_services_mixed_results(self, mock_health_checker_class, 
                                                        mock_validator_class, mock_load_config, 
                                                        runner, mock_config, valid_validation_result, mock_llm_service_patch):
        """Test config check with multiple services having mixed results."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_validator = Mock()
        mock_validator.validate_llm_config.return_value = valid_validation_result
        mock_validator_class.return_value = mock_validator
        
        # Create mixed health results
        healthy_ollama = HealthCheckResult(
            service='ollama',
            is_healthy=True,
            response_time_ms=150.5,
            error_message=None,
            details={'status_code': 200, 'model': 'llama2'}
        )
        
        unhealthy_openai = HealthCheckResult(
            service='openai',
            is_healthy=False,
            response_time_ms=5000.0,
            error_message='Invalid OpenAI API key',
            details={
                'error_code': ErrorCode.AUTHENTICATION_FAILED.value,
                'suggestion': 'Check your API key at https://platform.openai.com/api-keys'
            }
        )
        
        mock_health_checker = Mock()
        mock_health_checker.check_llm_health_sync.return_value = [healthy_ollama, unhealthy_openai]
        mock_health_checker_class.return_value = mock_health_checker
        
        # Run command
        result = runner.invoke(config_check, [])
        
        # Assertions
        assert result.exit_code == 1
        assert "✅ Healthy" in result.output  # Ollama
        assert "❌ Unhealthy" in result.output  # OpenAI
        assert "Invalid OpenAI API key" in result.output
        assert "1 service(s) failed connectivity tests" in result.output
    
    @patch('cli.config_check.load_configuration')
    @patch('cli.config_check.ConfigValidator')
    @patch('cli.config_check.ConfigHealthChecker')
    def test_config_check_health_check_exception(self, mock_health_checker_class, mock_validator_class, 
                                                mock_load_config, runner, mock_config, 
                                                valid_validation_result, mock_llm_service_patch):
        """Test config check with health check exception."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_validator = Mock()
        mock_validator.validate_llm_config.return_value = valid_validation_result
        mock_validator_class.return_value = mock_validator
        
        mock_health_checker = Mock()
        mock_health_checker.check_llm_health_sync.side_effect = Exception("Network error")
        mock_health_checker_class.return_value = mock_health_checker
        
        # Run command
        result = runner.invoke(config_check, [])
        
        # Assertions
        assert result.exit_code == 1
        assert "Configuration validation passed" in result.output
        assert "Health check error" in result.output
        assert "Network error" in result.output


class TestConfigCheckValidationException:
    """Test config-check command validation exception handling."""
    
    @patch('cli.config_check.load_configuration')
    @patch('cli.config_check.ConfigValidator')
    def test_config_check_validation_exception(self, mock_validator_class, mock_load_config, 
                                             runner, mock_config, mock_llm_service_patch):
        """Test config check with validation exception."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_validator = Mock()
        mock_validator.validate_llm_config.side_effect = Exception("Validation error")
        mock_validator_class.return_value = mock_validator
        
        # Run command
        result = runner.invoke(config_check, [])
        
        # Assertions
        assert result.exit_code == 1
        assert "Configuration validation error" in result.output
        assert "Validation error" in result.output


class TestConfigCheckDisplayFunctions:
    """Test config-check command display helper functions."""
    
    @patch('cli.config_check.load_configuration')
    @patch('cli.config_check.ConfigValidator')
    def test_config_check_validation_with_warnings_and_suggestions(self, mock_validator_class, 
                                                                 mock_load_config, runner, mock_config, mock_llm_service_patch):
        """Test display of validation results with warnings and suggestions."""
        # Setup validation result with warnings and suggestions
        validation_result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=['Model version is outdated', 'API rate limits may apply'],
            suggestions=['Consider upgrading model', 'Use caching for better performance']
        )
        
        mock_load_config.return_value = mock_config
        mock_validator = Mock()
        mock_validator.validate_llm_config.return_value = validation_result
        mock_validator_class.return_value = mock_validator
        
        # Run command with verbose flag
        result = runner.invoke(config_check, ['--skip-connectivity', '-v'])
        
        # Assertions
        assert result.exit_code == 0
        assert "Configuration validation passed" in result.output
        assert "Model version is outdated" in result.output
        assert "API rate limits may apply" in result.output
        assert "Consider upgrading model" in result.output
        assert "Use caching for better performance" in result.output
    
    @patch('cli.config_check.load_configuration')
    @patch('cli.config_check.ConfigValidator')
    @patch('cli.config_check.ConfigHealthChecker')
    def test_config_check_health_results_no_response_time(self, mock_health_checker_class, 
                                                        mock_validator_class, mock_load_config, 
                                                        runner, mock_config, valid_validation_result, mock_llm_service_patch):
        """Test display of health results with no response time."""
        # Setup health result with no response time
        health_result = HealthCheckResult(
            service='ollama',
            is_healthy=False,
            response_time_ms=None,
            error_message='Service not configured',
            details={'error_code': ErrorCode.MISSING_KEY.value}
        )
        
        mock_load_config.return_value = mock_config
        mock_validator = Mock()
        mock_validator.validate_llm_config.return_value = valid_validation_result
        mock_validator_class.return_value = mock_validator
        
        mock_health_checker = Mock()
        mock_health_checker.check_llm_health_sync.return_value = [health_result]
        mock_health_checker_class.return_value = mock_health_checker
        
        # Run command
        result = runner.invoke(config_check, [])
        
        # Assertions
        assert result.exit_code == 1
        assert "N/A" in result.output  # Response time should show as N/A
        assert "Service not configured" in result.output
    
    @patch('cli.config_check.load_configuration')
    @patch('cli.config_check.ConfigValidator')
    @patch('cli.config_check.ConfigHealthChecker')
    def test_config_check_no_health_results(self, mock_health_checker_class, mock_validator_class, 
                                          mock_load_config, runner, mock_config, valid_validation_result, mock_llm_service_patch):
        """Test display when no health results are returned."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_validator = Mock()
        mock_validator.validate_llm_config.return_value = valid_validation_result
        mock_validator_class.return_value = mock_validator
        
        mock_health_checker = Mock()
        mock_health_checker.check_llm_health_sync.return_value = []
        mock_health_checker_class.return_value = mock_health_checker
        
        # Run command
        result = runner.invoke(config_check, [])
        
        # Assertions
        assert result.exit_code == 0  # Should succeed if validation passes
        assert "No health check results to display" in result.output


class TestConfigCheckContextHandling:
    """Test config-check command context and parameter handling."""
    
    @patch('cli.config_check.load_configuration')
    def test_config_check_with_custom_config_path(self, mock_load_config, runner, mock_llm_service_patch):
        """Test config check with default configuration file path."""
        # Setup mock to verify the config path is used
        mock_load_config.side_effect = Exception("Config not found")
        
        # Run command - it should use the default config path
        result = runner.invoke(config_check, [])
        
        # The command should attempt to load the default config
        assert result.exit_code == 1
        assert "Failed to load configuration" in result.output
        assert "Config not found" in result.output
    
    def test_config_check_help_message(self, runner, mock_llm_service_patch):
        """Test config check help message."""
        result = runner.invoke(config_check, ['--help'])
        
        # Assertions
        assert result.exit_code == 0
        assert "Validate LLM configuration and test service connectivity" in result.output
        assert "--service" in result.output
        assert "--timeout" in result.output
        assert "--skip-connectivity" in result.output
        assert "--verbose" in result.output
        assert "Examples:" in result.output