import pytest
from unittest.mock import patch, MagicMock
from services.llm_implementations.ollama_implementation import OllamaLLMService

class DummyConfig:
    def get(self, section, option, fallback=None):
        if section == 'ollama' and option == 'model':
            return 'llama3.2'
        return fallback

def test_constructor_sets_model_and_client():
    """Test that OllamaLLMService constructor sets model and client attributes."""
    with patch('services.llm_implementations.ollama_implementation.Client') as mock_client:
        config = DummyConfig()
        service = OllamaLLMService(config)
        assert service.model == 'llama3.2'
        mock_client.assert_called_once()
        assert hasattr(service, 'client')

def test_parse_filename_success():
    """Test that parse_filename returns validated result on successful Ollama response."""
    with patch('services.llm_implementations.ollama_implementation.Client') as mock_client:
        config = DummyConfig()
        service = OllamaLLMService(config)
        mock_response = MagicMock()
        mock_response.response = '{"show_name": "Show", "season": 1, "episode": 2, "confidence": 0.9, "reasoning": "ok"}'
        service.client.generate = MagicMock(return_value=mock_response)
        result = service.parse_filename("Show.Name.S01E02.mkv")
        assert result["show_name"] == "Show"
        assert result["season"] == 1
        assert result["episode"] == 2
        assert result["confidence"] == 0.9
        assert result["reasoning"] == "ok"

def test_parse_filename_json_error_fallback():
    """Test that parse_filename falls back if Ollama returns invalid JSON."""
    with patch('services.llm_implementations.ollama_implementation.Client') as mock_client:
        config = DummyConfig()
        service = OllamaLLMService(config)
        mock_response = MagicMock()
        mock_response.response = 'not json'
        service.client.generate = MagicMock(return_value=mock_response)
        result = service.parse_filename("Show.Name.S01E02.mkv")
        assert result["confidence"] == 0.1 or result["confidence"] == 0.5

def test_parse_filename_api_error_fallback():
    """Test that parse_filename falls back if Ollama API raises an exception."""
    with patch('services.llm_implementations.ollama_implementation.Client') as mock_client:
        config = DummyConfig()
        service = OllamaLLMService(config)
        service.client.generate = MagicMock(side_effect=Exception('fail!'))
        result = service.parse_filename("Show.Name.S01E02.mkv")
        assert result["confidence"] == 0.1 or result["confidence"] == 0.5

def test_ollama_implementation_basic():
    # TODO: Add tests for services/llm_implementations/ollama_implementation.py
    assert True 