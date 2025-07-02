import pytest
from services.llm_factory import create_llm_service
from unittest.mock import patch, MagicMock

class DummyConfig:
    def __init__(self, service=None):
        self._service = service
    def get(self, section, option, fallback=None):
        if section == 'llm' and option == 'service':
            return self._service if self._service is not None else fallback
        return fallback

def test_create_llm_service_ollama(monkeypatch):
    """Test that create_llm_service returns OllamaLLMService for ollama config."""
    with patch('services.llm_factory.OllamaLLMService') as mock_ollama:
        config = DummyConfig('ollama')
        instance = MagicMock()
        mock_ollama.return_value = instance
        result = create_llm_service(config)
        assert result is instance
        mock_ollama.assert_called_once_with(config)

def test_create_llm_service_openai(monkeypatch):
    """Test that create_llm_service returns OpenAILLMService for openai config."""
    with patch('services.llm_factory.OpenAILLMService') as mock_openai:
        config = DummyConfig('openai')
        instance = MagicMock()
        mock_openai.return_value = instance
        result = create_llm_service(config)
        assert result is instance
        mock_openai.assert_called_once_with(config)

def test_create_llm_service_unsupported():
    """Test that create_llm_service raises ValueError for unsupported service type."""
    config = DummyConfig('unsupported')
    with pytest.raises(ValueError):
        create_llm_service(config)

def test_create_llm_service_case_insensitive(monkeypatch):
    """Test that create_llm_service is case-insensitive for service type."""
    with patch('services.llm_factory.OllamaLLMService') as mock_ollama:
        config = DummyConfig('OlLaMa')
        instance = MagicMock()
        mock_ollama.return_value = instance
        result = create_llm_service(config)
        assert result is instance
        mock_ollama.assert_called_once_with(config)

def test_create_llm_service_fallback(monkeypatch):
    """Test that create_llm_service defaults to ollama if service is not specified."""
    with patch('services.llm_factory.OllamaLLMService') as mock_ollama:
        config = DummyConfig(None)
        instance = MagicMock()
        mock_ollama.return_value = instance
        result = create_llm_service(config)
        assert result is instance
        mock_ollama.assert_called_once_with(config)

def test_llm_factory_basic():
    """Basic placeholder test for services/llm_factory.py functionality."""
    # TODO: Add tests for services/llm_factory.py
    assert True 