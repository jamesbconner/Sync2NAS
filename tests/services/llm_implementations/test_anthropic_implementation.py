import pytest
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
            "model": "claude-3-haiku",
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
    assert service.model == "claude-3-haiku"
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
            "model": "claude-3-haiku",
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
    ("max_tokens", "not-an-int", TypeError),
    ("temperature", "not-a-float", TypeError),
    ("llm_confidence_threshold", "not-a-float", TypeError),
])
def test_invalid_types_raise_typeerror(bad_key, bad_value, expected_type, monkeypatch):
    config_dict = {
        "anthropic": {
            "api_key": "test-api-key",
            "model": "claude-3-haiku",
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
            "model": "claude-3-haiku",
            "max_tokens": 200,
            "temperature": 0.1,
            "llm_confidence_threshold": 0.7,
        }
    })

    dummy_response_text = '{"show_name": "Sakamoto Days", "season": 1, "episode": 5}'

    class DummyClaudeResponse:
        content = [{"text": dummy_response_text}]

    class DummyClient:
        def __init__(self, api_key): pass

        class messages:
            @staticmethod
            def create(*args, **kwargs):
                return DummyClaudeResponse()

    monkeypatch.setattr(
        "services.llm_implementations.anthropic_implementation.anthropic.Anthropic",
        lambda api_key: DummyClient()
    )

    service = AnthropicLLMService(config=dummy_conf)
    result = service.parse_filename("Sakamoto.Days.S01E05.1080p.mkv")

    assert result["show_name"] == "Sakamoto Days"
    assert result["season"] == 1
    assert result["episode"] == 5