import pytest
from unittest.mock import patch, MagicMock
from services.llm_implementations.openai_implementation import OpenAILLMService

class DummyConfig:
    def __init__(self, api_key=None):
        self._api_key = api_key
    def get(self, section, option, fallback=None):
        if section == 'openai' and option == 'model':
            return 'gpt-3.5-turbo'
        if section == 'openai' and option == 'api_key':
            return self._api_key
        return fallback

def test_constructor_sets_model_and_client():
    """Test that OpenAILLMService constructor sets model, api_key, and client attributes."""
    with patch('services.llm_implementations.openai_implementation.openai.OpenAI') as mock_openai:
        config = DummyConfig(api_key='testkey')
        service = OpenAILLMService(config)
        assert service.model == 'gpt-3.5-turbo'
        assert service.api_key == 'testkey'
        mock_openai.assert_called_once_with(api_key='testkey')
        assert hasattr(service, 'client')

def test_constructor_raises_without_api_key():
    """Test that OpenAILLMService constructor raises ValueError if no API key is provided."""
    with patch('services.llm_implementations.openai_implementation.openai.OpenAI'):
        config = DummyConfig(api_key=None)
        with pytest.raises(ValueError):
            OpenAILLMService(config)

def test_parse_filename_success():
    """Test that parse_filename returns validated result on successful OpenAI response."""
    with patch('services.llm_implementations.openai_implementation.openai.OpenAI') as mock_openai:
        config = DummyConfig(api_key='testkey')
        service = OpenAILLMService(config)
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"show_name": "Show", "season": 1, "episode": 2, "confidence": 0.9, "reasoning": "ok"}'
        service.client.chat.completions.create = MagicMock(return_value=mock_response)
        result = service.parse_filename("Show.Name.S01E02.mkv")
        assert result["show_name"] == "Show"
        assert result["season"] == 1
        assert result["episode"] == 2
        assert result["confidence"] == 0.9
        assert result["reasoning"] == "ok"

def test_parse_filename_json_error_fallback():
    """Test that parse_filename falls back if OpenAI returns invalid JSON."""
    with patch('services.llm_implementations.openai_implementation.openai.OpenAI') as mock_openai:
        config = DummyConfig(api_key='testkey')
        service = OpenAILLMService(config)
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = 'not json'
        service.client.chat.completions.create = MagicMock(return_value=mock_response)
        result = service.parse_filename("Show.Name.S01E02.mkv")
        assert result["confidence"] == 0.1 or result["confidence"] == 0.5

def test_parse_filename_api_error_fallback():
    """Test that parse_filename falls back if OpenAI API raises an exception."""
    with patch('services.llm_implementations.openai_implementation.openai.OpenAI') as mock_openai:
        config = DummyConfig(api_key='testkey')
        service = OpenAILLMService(config)
        service.client.chat.completions.create = MagicMock(side_effect=Exception('fail!'))
        result = service.parse_filename("Show.Name.S01E02.mkv")
        assert result["confidence"] == 0.1 or result["confidence"] == 0.5