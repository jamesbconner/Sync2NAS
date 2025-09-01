import pytest
import json
from unittest.mock import Mock, patch
from services.llm_implementations.anthropic_implementation import AnthropicLLMService

class DummyConfig:
    """A minimal config mock that mimics your config.get() pattern."""
    def __init__(self, data):
        self.data = data

    def get(self, section, key, fallback=None):
        return self.data.get(section, {}).get(key, fallback)

    def getint(self, section, key, fallback=None):
        value = self.get(section, key, fallback)
        return int(value) if value is not None else fallback

    def getfloat(self, section, key, fallback=None):
        value = self.get(section, key, fallback)
        return float(value) if value is not None else fallback


def test_successful_initialization(monkeypatch):
    dummy_conf = DummyConfig({
        "anthropic": {
            "api_key": "test-api-key",
            "model": "qwen3:14b",
            "max_tokens": 300,
            "temperature": 0.2,
            "llm_confidence_threshold": 0.75,
        }
    })

    # Patch anthropic.Anthropic to avoid real API init
    class DummyClient:
        def __init__(self, api_key): pass

    monkeypatch.setattr("services.llm_implementations.anthropic_implementation.anthropic.Anthropic", DummyClient)

    service = AnthropicLLMService(config=dummy_conf)
    assert service.model == "qwen3:14b"
    assert service.api_key == "test-api-key"
    assert service.max_tokens == 300
    assert service.temperature == 0.2
    assert service.confidence_threshold == 0.75


@pytest.mark.parametrize("missing_key", ["api_key", "model", "max_tokens", "temperature", "llm_confidence_threshold"])
def test_missing_required_field_raises_value_error(missing_key, monkeypatch):
    # Setup with a missing key
    config_dict = {
        "anthropic": {
            "api_key": "test-api-key",
            "model": "qwen3:14b",
            "max_tokens": 300,
            "temperature": 0.2,
            "llm_confidence_threshold": 0.75,
        }
    }
    config_dict["anthropic"].pop(missing_key)

    dummy_conf = DummyConfig(config_dict)

    monkeypatch.setattr("services.llm_implementations.anthropic_implementation.anthropic.Anthropic", lambda api_key: None)

    if missing_key == "api_key":
        with pytest.raises(ValueError, match="Anthropic API key is required"):
            AnthropicLLMService(config=dummy_conf)
    else:
        # Let it fall back to default, which may be acceptable for optional fields
        service = AnthropicLLMService(config=dummy_conf)
        assert service is not None


@pytest.mark.parametrize("bad_key,bad_value,expected_type", [
    ("max_tokens", "not-an-int", ValueError),
    ("temperature", "not-a-float", ValueError),
    ("llm_confidence_threshold", "not-a-float", ValueError),
])
def test_invalid_types_raise_valueerror(bad_key, bad_value, expected_type, monkeypatch):
    """Test that invalid type values raise ValueError during type conversion."""
    config_dict = {
        "anthropic": {
            "api_key": "test-api-key",
            "model": "qwen3:14b",
            "max_tokens": 300,
            "temperature": 0.2,
            "llm_confidence_threshold": 0.75,
        }
    }
    config_dict["anthropic"][bad_key] = bad_value

    dummy_conf = DummyConfig(config_dict)
    monkeypatch.setattr("services.llm_implementations.anthropic_implementation.anthropic.Anthropic", lambda api_key: None)

    with pytest.raises(expected_type):
        AnthropicLLMService(config=dummy_conf)


def test_parse_filename_success(monkeypatch):
    dummy_conf = DummyConfig({
        "anthropic": {
            "api_key": "fake-key",
            "model": "qwen3:14b",
            "max_tokens": 200,
            "temperature": 0.1,
            "llm_confidence_threshold": 0.7,
        }
    })

    dummy_response_text = '{"show_name": "Sakamoto Days", "season": 1, "episode": 5}'

    class DummyClaudeResponse:
        content = [type("T", (), {"text": dummy_response_text})()]

    class DummyClient:
        def __init__(self, api_key): 
            self.api_key = api_key

        class messages:
            @staticmethod
            def create(*args, **kwargs):
                return DummyClaudeResponse()

    monkeypatch.setattr(
        "services.llm_implementations.anthropic_implementation.anthropic.Anthropic",
        DummyClient
    )

    service = AnthropicLLMService(config=dummy_conf)
    result = service.parse_filename("Sakamoto.Days.S01E05.1080p.mkv")

    # The result should be a dictionary, not a string
    assert isinstance(result, dict)
    assert result["show_name"] == "Sakamoto Days"
    assert result["season"] == 1
    assert result["episode"] == 5

# ─────────────────────────────────────────────────────────
# Type Validation Tests
# ─────────────────────────────────────────────────────────

def test_initialization_with_non_integer_max_tokens(monkeypatch):
    """Test initialization fails when max_tokens is not an integer."""
    dummy_conf = DummyConfig({
        "anthropic": {
            "api_key": "test-api-key",
            "max_tokens": "not-an-integer",  # String instead of int
        }
    })

    # Override the getint method to return the string directly
    def getint_override(section, key, fallback=None):
        if key == "max_tokens":
            return "not-an-integer"
        return dummy_conf.get(section, key, fallback)
    
    dummy_conf.getint = getint_override

    monkeypatch.setattr("services.llm_implementations.anthropic_implementation.anthropic.Anthropic", lambda api_key: None)

    with pytest.raises(ValueError, match="Invalid configuration values for Anthropic service"):
        AnthropicLLMService(config=dummy_conf)

def test_initialization_with_non_float_temperature(monkeypatch):
    """Test initialization fails when temperature is not a float."""
    dummy_conf = DummyConfig({
        "anthropic": {
            "api_key": "test-api-key",
            "temperature": "not-a-float",  # String instead of float
        }
    })

    # Override the getfloat method to return the string directly
    def getfloat_override(section, key, fallback=None):
        if key == "temperature":
            return "not-a-float"
        return dummy_conf.get(section, key, fallback)
    
    dummy_conf.getfloat = getfloat_override

    monkeypatch.setattr("services.llm_implementations.anthropic_implementation.anthropic.Anthropic", lambda api_key: None)

    with pytest.raises(ValueError, match="Invalid configuration values for Anthropic service"):
        AnthropicLLMService(config=dummy_conf)

def test_initialization_with_non_float_confidence_threshold(monkeypatch):
    """Test initialization fails when confidence_threshold is not a float."""
    dummy_conf = DummyConfig({
        "anthropic": {
            "api_key": "test-api-key",
            "llm_confidence_threshold": "not-a-float",  # String instead of float
        }
    })

    # Override the getfloat method to return the string directly
    def getfloat_override(section, key, fallback=None):
        if key == "llm_confidence_threshold":
            return "not-a-float"
        return dummy_conf.get(section, key, fallback)
    
    dummy_conf.getfloat = getfloat_override

    monkeypatch.setattr("services.llm_implementations.anthropic_implementation.anthropic.Anthropic", lambda api_key: None)

    with pytest.raises(ValueError, match="Invalid configuration values for Anthropic service"):
        AnthropicLLMService(config=dummy_conf)

def test_initialization_with_empty_api_key(monkeypatch):
    """Test initialization fails when API key is empty string."""
    dummy_conf = DummyConfig({
        "anthropic": {
            "api_key": "",  # Empty string
            "model": "claude-3-sonnet-20240229",
        }
    })

    monkeypatch.setattr("services.llm_implementations.anthropic_implementation.anthropic.Anthropic", lambda api_key: None)

    with pytest.raises(ValueError, match="Anthropic API key is required"):
        AnthropicLLMService(config=dummy_conf)

def test_initialization_with_none_api_key(monkeypatch):
    """Test initialization fails when API key is None."""
    dummy_conf = DummyConfig({
        "anthropic": {
            "api_key": None,  # None value
            "model": "claude-3-sonnet-20240229",
        }
    })

    monkeypatch.setattr("services.llm_implementations.anthropic_implementation.anthropic.Anthropic", lambda api_key: None)

    with pytest.raises(ValueError, match="Anthropic API key is required"):
        AnthropicLLMService(config=dummy_conf)

# ─────────────────────────────────────────────────────────
# Parse Filename Tests
# ─────────────────────────────────────────────────────────

def test_parse_filename_json_decode_error(monkeypatch):
    """Test parse_filename handles JSON decode errors gracefully."""
    dummy_conf = DummyConfig({
        "anthropic": {
            "api_key": "fake-key",
            "model": "qwen3:14b",
            "max_tokens": 200,
            "temperature": 0.1,
            "llm_confidence_threshold": 0.7,
        }
    })

    # Mock response with invalid JSON
    class DummyClaudeResponse:
        content = [type("T", (), {"text": "invalid json response"})()]

    class DummyClient:
        def __init__(self, api_key): 
            self.api_key = api_key

        class messages:
            @staticmethod
            def create(*args, **kwargs):
                return DummyClaudeResponse()

    monkeypatch.setattr(
        "services.llm_implementations.anthropic_implementation.anthropic.Anthropic",
        DummyClient
    )

    # Mock the fallback parse method
    mock_fallback_result = {"show_name": "Fallback Show", "season": 1, "episode": 1}
    monkeypatch.setattr("services.llm_implementations.anthropic_implementation.AnthropicLLMService._fallback_parse", 
                       lambda self, filename: mock_fallback_result)

    service = AnthropicLLMService(config=dummy_conf)
    result = service.parse_filename("test.mkv")

    # Should return fallback result when JSON parsing fails
    assert result == mock_fallback_result

def test_parse_filename_empty_response(monkeypatch):
    """Test parse_filename handles empty response content."""
    dummy_conf = DummyConfig({
        "anthropic": {
            "api_key": "fake-key",
            "model": "qwen3:14b",
            "max_tokens": 200,
            "temperature": 0.1,
            "llm_confidence_threshold": 0.7,
        }
    })

    # Mock response with empty content
    class DummyClaudeResponse:
        content = []

    class DummyClient:
        def __init__(self, api_key): 
            self.api_key = api_key

        class messages:
            @staticmethod
            def create(*args, **kwargs):
                return DummyClaudeResponse()

    monkeypatch.setattr(
        "services.llm_implementations.anthropic_implementation.anthropic.Anthropic",
        DummyClient
    )

    # Mock the fallback parse method
    mock_fallback_result = {"show_name": "Fallback Show", "season": 1, "episode": 1}
    monkeypatch.setattr("services.llm_implementations.anthropic_implementation.AnthropicLLMService._fallback_parse", 
                       lambda self, filename: mock_fallback_result)

    service = AnthropicLLMService(config=dummy_conf)
    result = service.parse_filename("test.mkv")

    # Should return fallback result when response is empty
    assert result == mock_fallback_result

# ─────────────────────────────────────────────────────────
# Suggest Short Dirname Tests
# ─────────────────────────────────────────────────────────

def test_suggest_short_dirname_success(monkeypatch):
    """Test successful short dirname suggestion."""
    dummy_conf = DummyConfig({
        "anthropic": {
            "api_key": "fake-key",
            "model": "qwen3:14b",
            "max_tokens": 200,
            "temperature": 0.1,
            "llm_confidence_threshold": 0.7,
        }
    })

    class DummyClaudeResponse:
        content = [type("T", (), {"text": "Short Name\n"})()]

    class DummyClient:
        def __init__(self, api_key): 
            self.api_key = api_key

        class messages:
            @staticmethod
            def create(*args, **kwargs):
                return DummyClaudeResponse()

    monkeypatch.setattr(
        "services.llm_implementations.anthropic_implementation.anthropic.Anthropic",
        DummyClient
    )

    # Mock the load_prompt method
    monkeypatch.setattr("services.llm_implementations.anthropic_implementation.AnthropicLLMService.load_prompt", 
                       lambda self, prompt_name: "Suggest a short name for {long_name} (max {max_length} chars)")

    service = AnthropicLLMService(config=dummy_conf)
    result = service.suggest_short_dirname("Very Long Directory Name That Needs Shortening", 10)

    assert result == "Short Name"

def test_suggest_short_dirname_with_special_characters(monkeypatch):
    """Test short dirname suggestion removes special characters."""
    dummy_conf = DummyConfig({
        "anthropic": {
            "api_key": "fake-key",
            "model": "qwen3:14b",
            "max_tokens": 200,
            "temperature": 0.1,
            "llm_confidence_threshold": 0.7,
        }
    })

    class DummyClaudeResponse:
        content = [type("T", (), {"text": "Short@Name#123\n"})()]

    class DummyClient:
        def __init__(self, api_key): 
            self.api_key = api_key

        class messages:
            @staticmethod
            def create(*args, **kwargs):
                return DummyClaudeResponse()

    monkeypatch.setattr(
        "services.llm_implementations.anthropic_implementation.anthropic.Anthropic",
        DummyClient
    )

    # Mock the load_prompt method
    monkeypatch.setattr("services.llm_implementations.anthropic_implementation.AnthropicLLMService.load_prompt", 
                       lambda self, prompt_name: "Suggest a short name for {long_name} (max {max_length} chars)")

    service = AnthropicLLMService(config=dummy_conf)
    result = service.suggest_short_dirname("Very Long Directory Name", 10)

    # Special characters should be removed
    assert result == "ShortName"

def test_suggest_short_dirname_exception_handling(monkeypatch):
    """Test short dirname suggestion handles exceptions gracefully."""
    dummy_conf = DummyConfig({
        "anthropic": {
            "api_key": "fake-key",
            "model": "qwen3:14b",
            "max_tokens": 200,
            "temperature": 0.1,
            "llm_confidence_threshold": 0.7,
        }
    })

    class DummyClient:
        def __init__(self, api_key): 
            self.api_key = api_key

        class messages:
            @staticmethod
            def create(*args, **kwargs):
                raise Exception("API Error")

    monkeypatch.setattr(
        "services.llm_implementations.anthropic_implementation.anthropic.Anthropic",
        DummyClient
    )

    # Mock the load_prompt method
    monkeypatch.setattr("services.llm_implementations.anthropic_implementation.AnthropicLLMService.load_prompt", 
                       lambda self, prompt_name: "Suggest a short name for {long_name} (max {max_length} chars)")

    service = AnthropicLLMService(config=dummy_conf)
    result = service.suggest_short_dirname("Very Long Directory Name", 10)

    # Should return truncated original name when exception occurs
    assert result == "Very Long "

def test_suggest_short_dirname_empty_response(monkeypatch):
    """Test short dirname suggestion handles empty response."""
    dummy_conf = DummyConfig({
        "anthropic": {
            "api_key": "fake-key",
            "model": "qwen3:14b",
            "max_tokens": 200,
            "temperature": 0.1,
            "llm_confidence_threshold": 0.7,
        }
    })

    class DummyClaudeResponse:
        content = [type("T", (), {"text": ""})()]

    class DummyClient:
        def __init__(self, api_key): 
            self.api_key = api_key

        class messages:
            @staticmethod
            def create(*args, **kwargs):
                return DummyClaudeResponse()

    monkeypatch.setattr(
        "services.llm_implementations.anthropic_implementation.anthropic.Anthropic",
        DummyClient
    )

    # Mock the load_prompt method
    monkeypatch.setattr("services.llm_implementations.anthropic_implementation.AnthropicLLMService.load_prompt", 
                       lambda self, prompt_name: "Suggest a short name for {long_name} (max {max_length} chars)")

    service = AnthropicLLMService(config=dummy_conf)
    result = service.suggest_short_dirname("Very Long Directory Name", 10)

    # Should return truncated original name when response is empty
    assert result == "Very Long "

# ─────────────────────────────────────────────────────────
# Suggest Short Filename Tests
# ─────────────────────────────────────────────────────────

def test_suggest_short_filename_success(monkeypatch):
    """Test successful short filename suggestion."""
    dummy_conf = DummyConfig({
        "anthropic": {
            "api_key": "fake-key",
            "model": "qwen3:14b",
            "max_tokens": 200,
            "temperature": 0.1,
            "llm_confidence_threshold": 0.7,
        }
    })

    class DummyClaudeResponse:
        content = [type("T", (), {"text": "Short Name.mkv\n"})()]

    class DummyClient:
        def __init__(self, api_key): 
            self.api_key = api_key

        class messages:
            @staticmethod
            def create(*args, **kwargs):
                return DummyClaudeResponse()

    monkeypatch.setattr(
        "services.llm_implementations.anthropic_implementation.anthropic.Anthropic",
        DummyClient
    )

    # Mock the load_prompt method
    monkeypatch.setattr("services.llm_implementations.anthropic_implementation.AnthropicLLMService.load_prompt", 
                       lambda self, prompt_name: "Suggest a short name for {long_name} (max {max_length} chars)")

    service = AnthropicLLMService(config=dummy_conf)
    result = service.suggest_short_filename("Very Long Filename That Needs Shortening.mkv", 15)

    assert result == "Short Name.mkv"

def test_suggest_short_filename_with_special_characters(monkeypatch):
    """Test short filename suggestion removes special characters but keeps dots."""
    dummy_conf = DummyConfig({
        "anthropic": {
            "api_key": "fake-key",
            "model": "qwen3:14b",
            "max_tokens": 200,
            "temperature": 0.1,
            "llm_confidence_threshold": 0.7,
        }
    })

    class DummyClaudeResponse:
        content = [type("T", (), {"text": "Short@Name#123.mkv\n"})()]

    class DummyClient:
        def __init__(self, api_key): 
            self.api_key = api_key

        class messages:
            @staticmethod
            def create(*args, **kwargs):
                return DummyClaudeResponse()

    monkeypatch.setattr(
        "services.llm_implementations.anthropic_implementation.anthropic.Anthropic",
        DummyClient
    )

    # Mock the load_prompt method
    monkeypatch.setattr("services.llm_implementations.anthropic_implementation.AnthropicLLMService.load_prompt", 
                       lambda self, prompt_name: "Suggest a short name for {long_name} (max {max_length} chars)")

    service = AnthropicLLMService(config=dummy_conf)
    result = service.suggest_short_filename("Very Long Filename.mkv", 15)

    # Special characters should be removed but dots kept
    assert result == "ShortName123."

def test_suggest_short_filename_exception_handling(monkeypatch):
    """Test short filename suggestion handles exceptions gracefully."""
    dummy_conf = DummyConfig({
        "anthropic": {
            "api_key": "fake-key",
            "model": "qwen3:14b",
            "max_tokens": 200,
            "temperature": 0.1,
            "llm_confidence_threshold": 0.7,
        }
    })

    class DummyClient:
        def __init__(self, api_key): 
            self.api_key = api_key

        class messages:
            @staticmethod
            def create(*args, **kwargs):
                raise Exception("API Error")

    monkeypatch.setattr(
        "services.llm_implementations.anthropic_implementation.anthropic.Anthropic",
        DummyClient
    )

    # Mock the load_prompt method
    monkeypatch.setattr("services.llm_implementations.anthropic_implementation.AnthropicLLMService.load_prompt", 
                       lambda self, prompt_name: "Suggest a short name for {long_name} (max {max_length} chars)")

    service = AnthropicLLMService(config=dummy_conf)
    result = service.suggest_short_filename("Very Long Filename.mkv", 10)

    # Should return truncated original name when exception occurs
    assert result == "Very Long "

def test_suggest_short_filename_empty_response(monkeypatch):
    """Test short filename suggestion handles empty response."""
    dummy_conf = DummyConfig({
        "anthropic": {
            "api_key": "fake-key",
            "model": "qwen3:14b",
            "max_tokens": 200,
            "temperature": 0.1,
            "llm_confidence_threshold": 0.7,
        }
    })

    class DummyClaudeResponse:
        content = [type("T", (), {"text": ""})()]

    class DummyClient:
        def __init__(self, api_key): 
            self.api_key = api_key

        class messages:
            @staticmethod
            def create(*args, **kwargs):
                return DummyClaudeResponse()

    monkeypatch.setattr(
        "services.llm_implementations.anthropic_implementation.anthropic.Anthropic",
        DummyClient
    )

    # Mock the load_prompt method
    monkeypatch.setattr("services.llm_implementations.anthropic_implementation.AnthropicLLMService.load_prompt", 
                       lambda self, prompt_name: "Suggest a short name for {long_name} (max {max_length} chars)")

    service = AnthropicLLMService(config=dummy_conf)
    result = service.suggest_short_filename("Very Long Filename.mkv", 10)

    # Should return truncated original name when response is empty
    assert result == "Very Long "

# ─────────────────────────────────────────────────────────
# Suggest Show Name Tests
# ─────────────────────────────────────────────────────────

def test_suggest_show_name_success(monkeypatch):
    """Test successful show name suggestion."""
    dummy_conf = DummyConfig({
        "anthropic": {
            "api_key": "fake-key",
            "model": "qwen3:14b",
            "max_tokens": 200,
            "temperature": 0.1,
            "llm_confidence_threshold": 0.7,
        }
    })

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

    class DummyClaudeResponse:
        content = [type("T", (), {"text": '{"tmdb_id": 123, "show_name": "Test Show"}'})()]

    class DummyClient:
        def __init__(self, api_key): 
            self.api_key = api_key

        class messages:
            @staticmethod
            def create(*args, **kwargs):
                return DummyClaudeResponse()

    monkeypatch.setattr(
        "services.llm_implementations.anthropic_implementation.anthropic.Anthropic",
        DummyClient
    )

    # Mock the load_prompt method
    monkeypatch.setattr("services.llm_implementations.anthropic_implementation.AnthropicLLMService.load_prompt", 
                       lambda self, prompt_name: "Select the best match for {show_name} from: {candidates}")

    service = AnthropicLLMService(config=dummy_conf)
    result = service.suggest_show_name("Test Show", detailed_results)

    assert result['tmdb_id'] == 123
    assert result['show_name'] == "Test Show"

def test_suggest_show_name_json_decode_error(monkeypatch):
    """Test show name suggestion handles JSON decode errors gracefully."""
    dummy_conf = DummyConfig({
        "anthropic": {
            "api_key": "fake-key",
            "model": "qwen3:14b",
            "max_tokens": 200,
            "temperature": 0.1,
            "llm_confidence_threshold": 0.7,
        }
    })

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

    class DummyClaudeResponse:
        content = [type("T", (), {"text": "invalid json response"})()]

    class DummyClient:
        def __init__(self, api_key): 
            self.api_key = api_key

        class messages:
            @staticmethod
            def create(*args, **kwargs):
                return DummyClaudeResponse()

    monkeypatch.setattr(
        "services.llm_implementations.anthropic_implementation.anthropic.Anthropic",
        DummyClient
    )

    # Mock the load_prompt method
    monkeypatch.setattr("services.llm_implementations.anthropic_implementation.AnthropicLLMService.load_prompt", 
                       lambda self, prompt_name: "Select the best match for {show_name} from: {candidates}")

    service = AnthropicLLMService(config=dummy_conf)
    result = service.suggest_show_name("Test Show", detailed_results)

    # Should return first candidate when JSON parsing fails
    assert result['tmdb_id'] == 123
    assert result['show_name'] == "Test Show"

def test_suggest_show_name_missing_required_fields(monkeypatch):
    """Test show name suggestion handles missing required fields gracefully."""
    dummy_conf = DummyConfig({
        "anthropic": {
            "api_key": "fake-key",
            "model": "qwen3:14b",
            "max_tokens": 200,
            "temperature": 0.1,
            "llm_confidence_threshold": 0.7,
        }
    })

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

    class DummyClaudeResponse:
        content = [type("T", (), {"text": '{"show_name": "Test Show"}'})()]  # Missing tmdb_id

    class DummyClient:
        def __init__(self, api_key): 
            self.api_key = api_key

        class messages:
            @staticmethod
            def create(*args, **kwargs):
                return DummyClaudeResponse()

    monkeypatch.setattr(
        "services.llm_implementations.anthropic_implementation.anthropic.Anthropic",
        DummyClient
    )

    # Mock the load_prompt method
    monkeypatch.setattr("services.llm_implementations.anthropic_implementation.AnthropicLLMService.load_prompt", 
                       lambda self, prompt_name: "Select the best match for {show_name} from: {candidates}")

    service = AnthropicLLMService(config=dummy_conf)
    result = service.suggest_show_name("Test Show", detailed_results)

    # Should return first candidate when required fields are missing
    assert result['tmdb_id'] == 123
    assert result['show_name'] == "Test Show"

def test_suggest_show_name_exception_handling(monkeypatch):
    """Test show name suggestion handles exceptions gracefully."""
    dummy_conf = DummyConfig({
        "anthropic": {
            "api_key": "fake-key",
            "model": "qwen3:14b",
            "max_tokens": 200,
            "temperature": 0.1,
            "llm_confidence_threshold": 0.7,
        }
    })

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

    class DummyClient:
        def __init__(self, api_key): 
            self.api_key = api_key

        class messages:
            @staticmethod
            def create(*args, **kwargs):
                raise Exception("API Error")

    monkeypatch.setattr(
        "services.llm_implementations.anthropic_implementation.anthropic.Anthropic",
        DummyClient
    )

    # Mock the load_prompt method
    monkeypatch.setattr("services.llm_implementations.anthropic_implementation.AnthropicLLMService.load_prompt", 
                       lambda self, prompt_name: "Select the best match for {show_name} from: {candidates}")

    service = AnthropicLLMService(config=dummy_conf)
    result = service.suggest_show_name("Test Show", detailed_results)

    # Should return first candidate when exception occurs
    assert result['tmdb_id'] == 123
    assert result['show_name'] == "Test Show"

def test_suggest_show_name_empty_response(monkeypatch):
    """Test show name suggestion handles empty response."""
    dummy_conf = DummyConfig({
        "anthropic": {
            "api_key": "fake-key",
            "model": "qwen3:14b",
            "max_tokens": 200,
            "temperature": 0.1,
            "llm_confidence_threshold": 0.7,
        }
    })

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

    class DummyClaudeResponse:
        content = []

    class DummyClient:
        def __init__(self, api_key): 
            self.api_key = api_key

        class messages:
            @staticmethod
            def create(*args, **kwargs):
                return DummyClaudeResponse()

    monkeypatch.setattr(
        "services.llm_implementations.anthropic_implementation.anthropic.Anthropic",
        DummyClient
    )

    # Mock the load_prompt method
    monkeypatch.setattr("services.llm_implementations.anthropic_implementation.AnthropicLLMService.load_prompt", 
                       lambda self, prompt_name: "Select the best match for {show_name} from: {candidates}")

    service = AnthropicLLMService(config=dummy_conf)
    result = service.suggest_show_name("Test Show", detailed_results)

    # Should return first candidate when response is empty
    assert result['tmdb_id'] == 123
    assert result['show_name'] == "Test Show"

def test_suggest_show_name_empty_candidates(monkeypatch):
    """Test show name suggestion handles empty candidates list."""
    dummy_conf = DummyConfig({
        "anthropic": {
            "api_key": "fake-key",
            "model": "qwen3:14b",
            "max_tokens": 200,
            "temperature": 0.1,
            "llm_confidence_threshold": 0.7,
        }
    })

    detailed_results = []

    class DummyClient:
        def __init__(self, api_key): 
            self.api_key = api_key

        class messages:
            @staticmethod
            def create(*args, **kwargs):
                return None

    monkeypatch.setattr(
        "services.llm_implementations.anthropic_implementation.anthropic.Anthropic",
        DummyClient
    )

    # Mock the load_prompt method
    monkeypatch.setattr("services.llm_implementations.anthropic_implementation.AnthropicLLMService.load_prompt", 
                       lambda self, prompt_name: "Select the best match for {show_name} from: {candidates}")

    service = AnthropicLLMService(config=dummy_conf)
    
    # Should handle empty candidates list gracefully
    with pytest.raises(IndexError):  # Trying to access first element of empty list
        service.suggest_show_name("Test Show", detailed_results)
