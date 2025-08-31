import pytest
from unittest.mock import patch, MagicMock, Mock
from services.llm_factory import (
    create_llm_service, 
    create_llm_service_legacy,
    validate_llm_config_only,
    LLMServiceCreationError
)
from utils.config.validation_models import ValidationResult, ValidationError, HealthCheckResult, ErrorCode

class DummyConfig:
    def __init__(self, service=None):
        self._service = service
        self._data = {
            'llm': {'service': service} if service else {},
            'ollama': {'model': 'gemma3:12b', 'host': 'http://localhost:11434'},
            'openai': {'api_key': 'sk-test123', 'model': 'gemma3:12b'},
            'anthropic': {'api_key': 'sk-ant-test123', 'model': 'gemma3:12b'}
        }
    
    def get(self, section, option, fallback=None):
        if section == 'llm' and option == 'service':
            return self._service if self._service is not None else fallback
        return fallback
    
    def copy(self):
        """Return a copy of the configuration data for normalizer compatibility."""
        return self._data.copy()
    
    def __getitem__(self, key):
        """Support dict-like access for normalizer compatibility."""
        return self._data[key]
    
    def __contains__(self, key):
        """Support 'in' operator for normalizer compatibility."""
        return key in self._data
    
    def keys(self):
        """Support keys() method for normalizer compatibility."""
        return self._data.keys()
    
    def items(self):
        """Support items() method for normalizer compatibility."""
        return self._data.items()

def test_create_llm_service_ollama(monkeypatch):
    """Test that create_llm_service returns OllamaLLMService for ollama config."""
    with patch('services.llm_factory.OllamaLLMService') as mock_ollama:
        config = DummyConfig('ollama')
        instance = MagicMock()
        mock_ollama.return_value = instance
        # Use legacy function to test backward compatibility
        result = create_llm_service_legacy(config)
        assert result is instance
        mock_ollama.assert_called_once_with(config)

def test_create_llm_service_openai(monkeypatch):
    """Test that create_llm_service returns OpenAILLMService for openai config."""
    with patch('services.llm_factory.OpenAILLMService') as mock_openai:
        config = DummyConfig('openai')
        instance = MagicMock()
        mock_openai.return_value = instance
        # Use legacy function to test backward compatibility
        result = create_llm_service_legacy(config)
        assert result is instance
        mock_openai.assert_called_once_with(config)

def test_create_llm_service_unsupported():
    """Test that create_llm_service raises ValueError for unsupported service type."""
    config = DummyConfig('unsupported')
    with pytest.raises(ValueError):
        # Use legacy function to test backward compatibility
        create_llm_service_legacy(config)

def test_create_llm_service_case_insensitive(monkeypatch):
    """Test that create_llm_service is case-insensitive for service type."""
    with patch('services.llm_factory.OllamaLLMService') as mock_ollama:
        config = DummyConfig('OlLaMa')
        instance = MagicMock()
        mock_ollama.return_value = instance
        # Use legacy function to test backward compatibility
        result = create_llm_service_legacy(config)
        assert result is instance
        mock_ollama.assert_called_once_with(config)

def test_create_llm_service_fallback(monkeypatch):
    """Test that create_llm_service defaults to ollama if service is not specified."""
    with patch('services.llm_factory.OllamaLLMService') as mock_ollama:
        config = DummyConfig(None)
        instance = MagicMock()
        mock_ollama.return_value = instance
        # Use legacy function to test backward compatibility
        result = create_llm_service_legacy(config)
        assert result is instance
        mock_ollama.assert_called_once_with(config)

def test_create_llm_service_with_validation_success():
    """Test successful LLM service creation with validation."""
    config = DummyConfig('ollama')
    
    # Mock validation components
    with patch('services.llm_factory.ConfigValidator') as mock_validator_class, \
         patch('services.llm_factory.ConfigNormalizer') as mock_normalizer_class, \
         patch('services.llm_factory.ConfigHealthChecker') as mock_health_checker_class, \
         patch('services.llm_factory.OllamaLLMService') as mock_ollama:
        
        # Setup mocks
        mock_validator = Mock()
        mock_normalizer = Mock()
        mock_health_checker = Mock()
        
        mock_validator_class.return_value = mock_validator
        mock_normalizer_class.return_value = mock_normalizer
        mock_health_checker_class.return_value = mock_health_checker
        
        # Mock successful validation
        validation_result = ValidationResult(is_valid=True, errors=[], warnings=[], suggestions=[])
        mock_validator.validate_llm_config.return_value = validation_result
        
        # Mock successful normalization
        normalized_config = {'llm': {'service': 'ollama'}, 'ollama': {'model': 'gemma3:12b'}}
        mock_normalizer.normalize_and_override.return_value = normalized_config
        
        # Mock successful health check
        health_result = HealthCheckResult(
            service='ollama',
            is_healthy=True,
            response_time_ms=100.0,
            error_message=None,
            details={}
        )
        mock_health_checker.check_llm_health_sync.return_value = [health_result]
        
        # Mock service creation
        service_instance = Mock()
        mock_ollama.return_value = service_instance
        
        # Test
        result = create_llm_service(config)
        
        # Assertions
        assert result is service_instance
        mock_validator.validate_llm_config.assert_called_once()
        mock_normalizer.normalize_and_override.assert_called_once_with(config)
        mock_health_checker.check_llm_health_sync.assert_called_once()
        mock_ollama.assert_called_once_with(normalized_config)


def test_create_llm_service_validation_failure():
    """Test LLM service creation failure due to validation errors."""
    config = DummyConfig('ollama')
    
    with patch('services.llm_factory.ConfigValidator') as mock_validator_class, \
         patch('services.llm_factory.ConfigNormalizer') as mock_normalizer_class:
        
        # Setup mocks
        mock_validator = Mock()
        mock_normalizer = Mock()
        
        mock_validator_class.return_value = mock_validator
        mock_normalizer_class.return_value = mock_normalizer
        
        # Mock validation failure
        validation_error = ValidationError(
            section='ollama',
            key='model',
            message='Model is required',
            suggestion='Add model = llama2',
            error_code=ErrorCode.MISSING_KEY
        )
        validation_result = ValidationResult(
            is_valid=False, 
            errors=[validation_error], 
            warnings=[], 
            suggestions=[]
        )
        mock_validator.validate_llm_config.return_value = validation_result
        
        # Mock normalization
        normalized_config = {'llm': {'service': 'ollama'}}
        mock_normalizer.normalize_and_override.return_value = normalized_config
        
        # Test
        with pytest.raises(LLMServiceCreationError) as exc_info:
            create_llm_service(config)
        
        assert "validation failed" in str(exc_info.value).lower()
        assert exc_info.value.validation_result is validation_result


def test_create_llm_service_health_check_failure():
    """Test LLM service creation failure due to health check failure."""
    config = DummyConfig('ollama')
    
    with patch('services.llm_factory.ConfigValidator') as mock_validator_class, \
         patch('services.llm_factory.ConfigNormalizer') as mock_normalizer_class, \
         patch('services.llm_factory.ConfigHealthChecker') as mock_health_checker_class:
        
        # Setup mocks
        mock_validator = Mock()
        mock_normalizer = Mock()
        mock_health_checker = Mock()
        
        mock_validator_class.return_value = mock_validator
        mock_normalizer_class.return_value = mock_normalizer
        mock_health_checker_class.return_value = mock_health_checker
        
        # Mock successful validation
        validation_result = ValidationResult(is_valid=True, errors=[], warnings=[], suggestions=[])
        mock_validator.validate_llm_config.return_value = validation_result
        
        # Mock normalization
        normalized_config = {'llm': {'service': 'ollama'}, 'ollama': {'model': 'gemma3:12b'}}
        mock_normalizer.normalize_and_override.return_value = normalized_config
        
        # Mock health check failure
        health_result = HealthCheckResult(
            service='ollama',
            is_healthy=False,
            response_time_ms=None,
            error_message='Cannot connect to Ollama',
            details={'error_code': ErrorCode.SERVICE_UNREACHABLE.value}
        )
        mock_health_checker.check_llm_health_sync.return_value = [health_result]
        
        # Test
        with pytest.raises(LLMServiceCreationError) as exc_info:
            create_llm_service(config)
        
        assert "health check failed" in str(exc_info.value).lower()


def test_create_llm_service_without_health_check():
    """Test LLM service creation without health check."""
    config = DummyConfig('ollama')
    
    with patch('services.llm_factory.ConfigValidator') as mock_validator_class, \
         patch('services.llm_factory.ConfigNormalizer') as mock_normalizer_class, \
         patch('services.llm_factory.OllamaLLMService') as mock_ollama:
        
        # Setup mocks
        mock_validator = Mock()
        mock_normalizer = Mock()
        
        mock_validator_class.return_value = mock_validator
        mock_normalizer_class.return_value = mock_normalizer
        
        # Mock successful validation
        validation_result = ValidationResult(is_valid=True, errors=[], warnings=[], suggestions=[])
        mock_validator.validate_llm_config.return_value = validation_result
        
        # Mock normalization
        normalized_config = {'llm': {'service': 'ollama'}, 'ollama': {'model': 'gemma3:12b'}}
        mock_normalizer.normalize_and_override.return_value = normalized_config
        
        # Mock service creation
        service_instance = Mock()
        mock_ollama.return_value = service_instance
        
        # Test without health check
        result = create_llm_service(config, validate_health=False)
        
        # Assertions
        assert result is service_instance
        mock_validator.validate_llm_config.assert_called_once()
        mock_normalizer.normalize_and_override.assert_called_once_with(config)
        mock_ollama.assert_called_once_with(normalized_config)


def test_create_llm_service_legacy():
    """Test legacy LLM service creation without validation."""
    with patch('services.llm_factory.OllamaLLMService') as mock_ollama:
        config = DummyConfig('ollama')
        instance = MagicMock()
        mock_ollama.return_value = instance
        
        result = create_llm_service_legacy(config)
        
        assert result is instance
        mock_ollama.assert_called_once_with(config)


def test_validate_llm_config_only():
    """Test configuration validation without service creation."""
    config = DummyConfig('ollama')
    
    with patch('services.llm_factory.ConfigValidator') as mock_validator_class, \
         patch('services.llm_factory.ConfigNormalizer') as mock_normalizer_class:
        
        # Setup mocks
        mock_validator = Mock()
        mock_normalizer = Mock()
        
        mock_validator_class.return_value = mock_validator
        mock_normalizer_class.return_value = mock_normalizer
        
        # Mock validation result
        validation_result = ValidationResult(is_valid=True, errors=[], warnings=[], suggestions=[])
        mock_validator.validate_llm_config.return_value = validation_result
        
        # Mock normalization
        normalized_config = {'llm': {'service': 'ollama'}}
        mock_normalizer.normalize_and_override.return_value = normalized_config
        
        # Test
        result = validate_llm_config_only(config)
        
        # Assertions
        assert result is validation_result
        mock_validator.validate_llm_config.assert_called_once()
        mock_normalizer.normalize_and_override.assert_called_once_with(config)


def test_create_llm_service_with_warnings():
    """Test LLM service creation with validation warnings."""
    config = DummyConfig('ollama')
    
    with patch('services.llm_factory.ConfigValidator') as mock_validator_class, \
         patch('services.llm_factory.ConfigNormalizer') as mock_normalizer_class, \
         patch('services.llm_factory.ConfigHealthChecker') as mock_health_checker_class, \
         patch('services.llm_factory.OllamaLLMService') as mock_ollama:
        
        # Setup mocks
        mock_validator = Mock()
        mock_normalizer = Mock()
        mock_health_checker = Mock()
        
        mock_validator_class.return_value = mock_validator
        mock_normalizer_class.return_value = mock_normalizer
        mock_health_checker_class.return_value = mock_health_checker
        
        # Mock validation with warnings
        validation_result = ValidationResult(
            is_valid=True, 
            errors=[], 
            warnings=['Model may not be available'], 
            suggestions=['Consider using llama2:7b']
        )
        mock_validator.validate_llm_config.return_value = validation_result
        
        # Mock normalization
        normalized_config = {'llm': {'service': 'ollama'}, 'ollama': {'model': 'gemma3:12b'}}
        mock_normalizer.normalize_and_override.return_value = normalized_config
        
        # Mock successful health check
        health_result = HealthCheckResult(
            service='ollama',
            is_healthy=True,
            response_time_ms=100.0,
            error_message=None,
            details={}
        )
        mock_health_checker.check_llm_health_sync.return_value = [health_result]
        
        # Mock service creation
        service_instance = Mock()
        mock_ollama.return_value = service_instance
        
        # Test
        result = create_llm_service(config)
        
        # Should succeed despite warnings
        assert result is service_instance


def test_create_llm_service_unsupported_service():
    """Test LLM service creation with unsupported service type."""
    config = DummyConfig('unsupported')
    
    with patch('services.llm_factory.ConfigValidator') as mock_validator_class, \
         patch('services.llm_factory.ConfigNormalizer') as mock_normalizer_class, \
         patch('services.llm_factory.ConfigHealthChecker') as mock_health_checker_class:
        
        # Setup mocks
        mock_validator = Mock()
        mock_normalizer = Mock()
        mock_health_checker = Mock()
        
        mock_validator_class.return_value = mock_validator
        mock_normalizer_class.return_value = mock_normalizer
        mock_health_checker_class.return_value = mock_health_checker
        
        # Mock successful validation (validator should catch this, but testing factory logic)
        validation_result = ValidationResult(is_valid=True, errors=[], warnings=[], suggestions=[])
        mock_validator.validate_llm_config.return_value = validation_result
        
        # Mock normalization
        normalized_config = {'llm': {'service': 'unsupported'}}
        mock_normalizer.normalize_and_override.return_value = normalized_config
        
        # Mock successful health check
        health_result = HealthCheckResult(
            service='unsupported',
            is_healthy=True,
            response_time_ms=100.0,
            error_message=None,
            details={}
        )
        mock_health_checker.check_llm_health_sync.return_value = [health_result]
        
        # Test
        with pytest.raises(ValueError) as exc_info:
            create_llm_service(config)
        
        assert "Unsupported LLM service: unsupported" in str(exc_info.value) 