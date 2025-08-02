import pytest
import json
from unittest.mock import patch, MagicMock
from pydantic import ValidationError
from services.llm_implementations.ollama_implementation import OllamaLLMService, ParsedFilename, SuggestedShowName

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

def test_parse_filename_api_error_fallback(monkeypatch):
    from services.llm_implementations.ollama_implementation import OllamaLLMService
    class DummyConfig:
        def get(self, *a, **k): return ""
        def getint(self, *a, **k): return 1
        def getfloat(self, *a, **k): return 0.1
    service = OllamaLLMService(DummyConfig())
    # Patch the client.generate method to raise an exception
    monkeypatch.setattr(service.client, "generate", lambda *a, **k: (_ for _ in ()).throw(Exception("API Error")))
    result = service.parse_filename("badfile.mkv")
    assert isinstance(result, dict)
    assert "show_name" in result
    assert result["show_name"] == "badfile"

def test_ollama_implementation_basic():
    # TODO: Add tests for services/llm_implementations/ollama_implementation.py
    assert True

# ─────────────────────────────────────────────────────────
# Response Extraction Tests
# ─────────────────────────────────────────────────────────

def test_parse_filename_response_dict_format():
    """Test parse_filename handles response as dict format."""
    with patch('services.llm_implementations.ollama_implementation.Client') as mock_client:
        config = DummyConfig()
        service = OllamaLLMService(config)
        mock_response = {'response': '{"show_name": "Show", "season": 1, "episode": 2, "confidence": 0.9, "reasoning": "ok"}'}
        service.client.generate = MagicMock(return_value=mock_response)
        result = service.parse_filename("Show.Name.S01E02.mkv")
        # The result might be processed through _validate_and_clean_result, so check for the processed name
        assert "show_name" in result
        assert result["season"] == 1

def test_parse_filename_response_string_format():
    """Test parse_filename handles response as string format."""
    with patch('services.llm_implementations.ollama_implementation.Client') as mock_client:
        config = DummyConfig()
        service = OllamaLLMService(config)
        mock_response = '{"show_name": "Show", "season": 1, "episode": 2, "confidence": 0.9, "reasoning": "ok"}'
        service.client.generate = MagicMock(return_value=mock_response)
        result = service.parse_filename("Show.Name.S01E02.mkv")
        # The result might be processed through _validate_and_clean_result, so check for the processed name
        assert "show_name" in result
        assert result["season"] == 1

def test_parse_filename_validation_error_fallback():
    """Test parse_filename falls back when validation fails."""
    with patch('services.llm_implementations.ollama_implementation.Client') as mock_client:
        config = DummyConfig()
        service = OllamaLLMService(config)
        # Mock response that will fail validation (missing required fields)
        mock_response = MagicMock()
        mock_response.response = '{"show_name": "Show"}'  # Missing required fields
        service.client.generate = MagicMock(return_value=mock_response)
        result = service.parse_filename("Show.Name.S01E02.mkv")
        # Should fall back to _fallback_parse
        assert isinstance(result, dict)
        assert "show_name" in result

# ─────────────────────────────────────────────────────────
# Suggest Short Dirname Tests
# ─────────────────────────────────────────────────────────

def test_suggest_short_dirname_success():
    """Test successful short dirname suggestion."""
    with patch('services.llm_implementations.ollama_implementation.Client') as mock_client:
        config = DummyConfig()
        service = OllamaLLMService(config)
        mock_response = MagicMock()
        mock_response.response = "Short Name\n"
        service.client.generate = MagicMock(return_value=mock_response)
        
        # Mock the load_prompt method
        with patch.object(service, 'load_prompt', return_value="Suggest a short name for {long_name} (max {max_length} chars)"):
            result = service.suggest_short_dirname("Very Long Directory Name", 10)
            assert result == "Short Name"

def test_suggest_short_dirname_dict_response():
    """Test short dirname suggestion with dict response format."""
    with patch('services.llm_implementations.ollama_implementation.Client') as mock_client:
        config = DummyConfig()
        service = OllamaLLMService(config)
        mock_response = {'response': "Short Name\n"}
        service.client.generate = MagicMock(return_value=mock_response)
        
        # Mock the load_prompt method
        with patch.object(service, 'load_prompt', return_value="Suggest a short name for {long_name} (max {max_length} chars)"):
            result = service.suggest_short_dirname("Very Long Directory Name", 10)
            assert result == "Short Name"

def test_suggest_short_dirname_string_response():
    """Test short dirname suggestion with string response format."""
    with patch('services.llm_implementations.ollama_implementation.Client') as mock_client:
        config = DummyConfig()
        service = OllamaLLMService(config)
        mock_response = "Short Name\n"
        service.client.generate = MagicMock(return_value=mock_response)
        
        # Mock the load_prompt method
        with patch.object(service, 'load_prompt', return_value="Suggest a short name for {long_name} (max {max_length} chars)"):
            result = service.suggest_short_dirname("Very Long Directory Name", 10)
            assert result == "Short Name"

def test_suggest_short_dirname_with_special_characters():
    """Test short dirname suggestion removes special characters."""
    with patch('services.llm_implementations.ollama_implementation.Client') as mock_client:
        config = DummyConfig()
        service = OllamaLLMService(config)
        mock_response = MagicMock()
        mock_response.response = "Short@Name#123\n"
        service.client.generate = MagicMock(return_value=mock_response)
        
        # Mock the load_prompt method
        with patch.object(service, 'load_prompt', return_value="Suggest a short name for {long_name} (max {max_length} chars)"):
            result = service.suggest_short_dirname("Very Long Directory Name", 10)
            # Special characters should be removed
            assert result == "ShortName"

def test_suggest_short_dirname_exception_handling():
    """Test short dirname suggestion handles exceptions gracefully."""
    with patch('services.llm_implementations.ollama_implementation.Client') as mock_client:
        config = DummyConfig()
        service = OllamaLLMService(config)
        service.client.generate = MagicMock(side_effect=Exception("API Error"))
        
        # Mock the load_prompt method
        with patch.object(service, 'load_prompt', return_value="Suggest a short name for {long_name} (max {max_length} chars)"):
            result = service.suggest_short_dirname("Very Long Directory Name", 10)
            # Should return truncated original name when exception occurs
            assert result == "Very Long "

def test_suggest_short_dirname_empty_response():
    """Test short dirname suggestion handles empty response."""
    with patch('services.llm_implementations.ollama_implementation.Client') as mock_client:
        config = DummyConfig()
        service = OllamaLLMService(config)
        mock_response = MagicMock()
        mock_response.response = ""
        service.client.generate = MagicMock(return_value=mock_response)
        
        # Mock the load_prompt method
        with patch.object(service, 'load_prompt', return_value="Suggest a short name for {long_name} (max {max_length} chars)"):
            result = service.suggest_short_dirname("Very Long Directory Name", 10)
            # Should return truncated original name when response is empty
            assert result == "Very Long "

# ─────────────────────────────────────────────────────────
# Suggest Short Filename Tests
# ─────────────────────────────────────────────────────────

def test_suggest_short_filename_success():
    """Test successful short filename suggestion."""
    with patch('services.llm_implementations.ollama_implementation.Client') as mock_client:
        config = DummyConfig()
        service = OllamaLLMService(config)
        mock_response = MagicMock()
        mock_response.response = "Short Name.mkv\n"
        service.client.generate = MagicMock(return_value=mock_response)
        
        # Mock the load_prompt method
        with patch.object(service, 'load_prompt', return_value="Suggest a short name for {long_name} (max {max_length} chars)"):
            result = service.suggest_short_filename("Very Long Filename.mkv", 15)
            assert result == "Short Name.mkv"

def test_suggest_short_filename_dict_response():
    """Test short filename suggestion with dict response format."""
    with patch('services.llm_implementations.ollama_implementation.Client') as mock_client:
        config = DummyConfig()
        service = OllamaLLMService(config)
        mock_response = {'response': "Short Name.mkv\n"}
        service.client.generate = MagicMock(return_value=mock_response)
        
        # Mock the load_prompt method
        with patch.object(service, 'load_prompt', return_value="Suggest a short name for {long_name} (max {max_length} chars)"):
            result = service.suggest_short_filename("Very Long Filename.mkv", 15)
            assert result == "Short Name.mkv"

def test_suggest_short_filename_string_response():
    """Test short filename suggestion with string response format."""
    with patch('services.llm_implementations.ollama_implementation.Client') as mock_client:
        config = DummyConfig()
        service = OllamaLLMService(config)
        mock_response = "Short Name.mkv\n"
        service.client.generate = MagicMock(return_value=mock_response)
        
        # Mock the load_prompt method
        with patch.object(service, 'load_prompt', return_value="Suggest a short name for {long_name} (max {max_length} chars)"):
            result = service.suggest_short_filename("Very Long Filename.mkv", 15)
            assert result == "Short Name.mkv"

def test_suggest_short_filename_with_special_characters():
    """Test short filename suggestion removes special characters but keeps dots."""
    with patch('services.llm_implementations.ollama_implementation.Client') as mock_client:
        config = DummyConfig()
        service = OllamaLLMService(config)
        mock_response = MagicMock()
        mock_response.response = "Short@Name#123.mkv\n"
        service.client.generate = MagicMock(return_value=mock_response)
        
        # Mock the load_prompt method
        with patch.object(service, 'load_prompt', return_value="Suggest a short name for {long_name} (max {max_length} chars)"):
            result = service.suggest_short_filename("Very Long Filename.mkv", 15)
            # Special characters should be removed but dots kept
            assert result == "ShortName123."

def test_suggest_short_filename_exception_handling():
    """Test short filename suggestion handles exceptions gracefully."""
    with patch('services.llm_implementations.ollama_implementation.Client') as mock_client:
        config = DummyConfig()
        service = OllamaLLMService(config)
        service.client.generate = MagicMock(side_effect=Exception("API Error"))
        
        # Mock the load_prompt method
        with patch.object(service, 'load_prompt', return_value="Suggest a short name for {long_name} (max {max_length} chars)"):
            result = service.suggest_short_filename("Very Long Filename.mkv", 10)
            # Should return truncated original name when exception occurs
            assert result == "Very Long "

def test_suggest_short_filename_empty_response():
    """Test short filename suggestion handles empty response."""
    with patch('services.llm_implementations.ollama_implementation.Client') as mock_client:
        config = DummyConfig()
        service = OllamaLLMService(config)
        mock_response = MagicMock()
        mock_response.response = ""
        service.client.generate = MagicMock(return_value=mock_response)
        
        # Mock the load_prompt method
        with patch.object(service, 'load_prompt', return_value="Suggest a short name for {long_name} (max {max_length} chars)"):
            result = service.suggest_short_filename("Very Long Filename.mkv", 10)
            # Should return truncated original name when response is empty
            assert result == "Very Long "

# ─────────────────────────────────────────────────────────
# Suggest Show Name Tests
# ─────────────────────────────────────────────────────────

def test_suggest_show_name_success():
    """Test successful show name suggestion."""
    with patch('services.llm_implementations.ollama_implementation.Client') as mock_client:
        config = DummyConfig()
        service = OllamaLLMService(config)
        mock_response = MagicMock()
        mock_response.response = '{"tmdb_id": 123, "show_name": "Test Show", "confidence": 0.9, "reasoning": "good match"}'
        service.client.generate = MagicMock(return_value=mock_response)
        
        detailed_results = [
            {
                'info': {
                    'id': 123,
                    'name': 'Test Show',
                    'original_name': 'Test Show Original',
                    'first_air_date': '2020-01-01',
                    'overview': 'A test show'
                },
                'alternative_titles': {'results': []}
            }
        ]
        
        # Mock the load_prompt method
        with patch.object(service, 'load_prompt', return_value="Select the best match for {show_name} from: {candidates}"):
            result = service.suggest_show_name("Test Show", detailed_results)
            assert result['tmdb_id'] == 123
            assert result['show_name'] == "Test Show"

def test_suggest_show_name_string_response():
    """Test show name suggestion with string response format."""
    with patch('services.llm_implementations.ollama_implementation.Client') as mock_client:
        config = DummyConfig()
        service = OllamaLLMService(config)
        mock_response = '{"tmdb_id": 123, "show_name": "Test Show", "confidence": 0.9, "reasoning": "good match"}'
        service.client.generate = MagicMock(return_value=mock_response)
        
        detailed_results = [
            {
                'info': {
                    'id': 123,
                    'name': 'Test Show',
                    'original_name': 'Test Show Original',
                    'first_air_date': '2020-01-01',
                    'overview': 'A test show'
                },
                'alternative_titles': {'results': []}
            }
        ]
        
        # Mock the load_prompt method
        with patch.object(service, 'load_prompt', return_value="Select the best match for {show_name} from: {candidates}"):
            result = service.suggest_show_name("Test Show", detailed_results)
            assert result['tmdb_id'] == 123
            assert result['show_name'] == "Test Show"

def test_suggest_show_name_missing_required_fields():
    """Test show name suggestion handles missing required fields gracefully."""
    with patch('services.llm_implementations.ollama_implementation.Client') as mock_client:
        config = DummyConfig()
        service = OllamaLLMService(config)
        # Create a proper mock response that has the response attribute
        mock_response = MagicMock()
        mock_response.response = '{"show_name": "Test Show"}'  # Missing tmdb_id
        service.client.generate = MagicMock(return_value=mock_response)
        
        detailed_results = [
            {
                'info': {
                    'id': 123,
                    'name': 'Test Show',
                    'original_name': 'Test Show Original',
                    'first_air_date': '2020-01-01',
                    'overview': 'A test show'
                },
                'alternative_titles': {'results': []}
            }
        ]
        
        # Mock the load_prompt method
        with patch.object(service, 'load_prompt', return_value="Select the best match for {show_name} from: {candidates}"):
            result = service.suggest_show_name("Test Show", detailed_results)
            # Should return first candidate when required fields are missing
            assert result['tmdb_id'] == 123
            assert result['show_name'] == "Test Show"

def test_suggest_show_name_json_decode_error():
    """Test show name suggestion handles JSON decode errors gracefully."""
    with patch('services.llm_implementations.ollama_implementation.Client') as mock_client:
        config = DummyConfig()
        service = OllamaLLMService(config)
        mock_response = MagicMock()
        mock_response.response = "invalid json response"
        service.client.generate = MagicMock(return_value=mock_response)
        
        detailed_results = [
            {
                'info': {
                    'id': 123,
                    'name': 'Test Show',
                    'original_name': 'Test Show Original',
                    'first_air_date': '2020-01-01',
                    'overview': 'A test show'
                },
                'alternative_titles': {'results': []}
            }
        ]
        
        # Mock the load_prompt method
        with patch.object(service, 'load_prompt', return_value="Select the best match for {show_name} from: {candidates}"):
            result = service.suggest_show_name("Test Show", detailed_results)
            # Should return first candidate when JSON parsing fails
            assert result['tmdb_id'] == 123
            assert result['show_name'] == "Test Show"

def test_suggest_show_name_exception_handling():
    """Test show name suggestion handles exceptions gracefully."""
    with patch('services.llm_implementations.ollama_implementation.Client') as mock_client:
        config = DummyConfig()
        service = OllamaLLMService(config)
        service.client.generate = MagicMock(side_effect=Exception("API Error"))
        
        detailed_results = [
            {
                'info': {
                    'id': 123,
                    'name': 'Test Show',
                    'original_name': 'Test Show Original',
                    'first_air_date': '2020-01-01',
                    'overview': 'A test show'
                },
                'alternative_titles': {'results': []}
            }
        ]
        
        # Mock the load_prompt method
        with patch.object(service, 'load_prompt', return_value="Select the best match for {show_name} from: {candidates}"):
            result = service.suggest_show_name("Test Show", detailed_results)
            # Should return first candidate when exception occurs
            assert result['tmdb_id'] == 123
            assert result['show_name'] == "Test Show"

def test_suggest_show_name_empty_candidates():
    """Test show name suggestion handles empty candidates list."""
    with patch('services.llm_implementations.ollama_implementation.Client') as mock_client:
        config = DummyConfig()
        service = OllamaLLMService(config)
        service.client.generate = MagicMock(return_value=None)
        
        detailed_results = []
        
        # Mock the load_prompt method
        with patch.object(service, 'load_prompt', return_value="Select the best match for {show_name} from: {candidates}"):
            # Should handle empty candidates list gracefully
            with pytest.raises(ValueError, match="No candidates available for fallback"):
                service.suggest_show_name("Test Show", detailed_results)

def test_suggest_show_name_with_alternative_titles():
    """Test show name suggestion handles alternative titles correctly."""
    with patch('services.llm_implementations.ollama_implementation.Client') as mock_client:
        config = DummyConfig()
        service = OllamaLLMService(config)
        mock_response = MagicMock()
        mock_response.response = '{"tmdb_id": 123, "show_name": "Test Show", "confidence": 0.9, "reasoning": "good match"}'
        service.client.generate = MagicMock(return_value=mock_response)
        
        detailed_results = [
            {
                'info': {
                    'id': 123,
                    'name': 'Test Show',
                    'original_name': 'Test Show Original',
                    'first_air_date': '2020-01-01',
                    'overview': 'A test show'
                },
                'alternative_titles': {
                    'results': [
                        {'name': 'Alternative Title 1'},
                        {'name': 'Alternative Title 2'}
                    ]
                }
            }
        ]
        
        # Mock the load_prompt method
        with patch.object(service, 'load_prompt', return_value="Select the best match for {show_name} from: {candidates}"):
            result = service.suggest_show_name("Test Show", detailed_results)
            assert result['tmdb_id'] == 123
            assert result['show_name'] == "Test Show"

# ─────────────────────────────────────────────────────────
# Pydantic Model Tests
# ─────────────────────────────────────────────────────────

def test_parsed_filename_model():
    """Test ParsedFilename model validation."""
    valid_data = {
        "show_name": "Test Show",
        "season": 1,
        "episode": 2,
        "confidence": 0.9,
        "reasoning": "Good match"
    }
    parsed = ParsedFilename(**valid_data)
    assert parsed.show_name == "Test Show"
    assert parsed.season == 1
    assert parsed.episode == 2
    assert parsed.confidence == 0.9
    assert parsed.reasoning == "Good match"

def test_parsed_filename_model_validation_error():
    """Test ParsedFilename model validation error."""
    invalid_data = {
        "show_name": "Test Show",
        # Missing required fields
    }
    with pytest.raises(ValidationError):
        ParsedFilename(**invalid_data)

def test_suggested_show_name_model():
    """Test SuggestedShowName model validation."""
    valid_data = {
        "tmdb_id": 123,
        "show_name": "Test Show",
        "confidence": 0.9,
        "reasoning": "Good match"
    }
    suggested = SuggestedShowName(**valid_data)
    assert suggested.tmdb_id == 123
    assert suggested.show_name == "Test Show"
    assert suggested.confidence == 0.9
    assert suggested.reasoning == "Good match"

def test_suggested_show_name_model_validation_error():
    """Test SuggestedShowName model validation error."""
    invalid_data = {
        "show_name": "Test Show",
        # Missing required fields
    }
    with pytest.raises(ValidationError):
        SuggestedShowName(**invalid_data) 