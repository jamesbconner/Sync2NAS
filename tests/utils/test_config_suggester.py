"""Tests for configuration error suggestion system."""

import pytest
from utils.config.config_suggester import ConfigSuggester
from utils.config.validation_models import ValidationError, ErrorCode


class TestConfigSuggester:
    """Test cases for ConfigSuggester class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.suggester = ConfigSuggester()
    
    def test_suggest_section_name_exact_match(self):
        """Test suggestion for exact section name matches."""
        # Test case variations
        assert self.suggester.suggest_section_name("OpenAI") == "openai"
        assert self.suggester.suggest_section_name("ANTHROPIC") == "anthropic"
        assert self.suggester.suggest_section_name("Ollama") == "ollama"
        assert self.suggester.suggest_section_name("LLM") == "llm"
    
    def test_suggest_section_name_typos(self):
        """Test suggestion for section name typos."""
        # Common typos
        assert self.suggester.suggest_section_name("openai") == "openai"  # Already correct
        assert self.suggester.suggest_section_name("opena") == "openai"
        assert self.suggester.suggest_section_name("anthropi") == "anthropic"
        assert self.suggester.suggest_section_name("olama") == "ollama"
        assert self.suggester.suggest_section_name("lm") == "llm"
    
    def test_suggest_section_name_no_match(self):
        """Test suggestion when no good match exists."""
        assert self.suggester.suggest_section_name("completely_different") is None
        assert self.suggester.suggest_section_name("xyz") is None
        assert self.suggester.suggest_section_name("") is None
    
    def test_suggest_config_key_exact_match(self):
        """Test suggestion for exact key matches."""
        assert self.suggester.suggest_config_key("openai", "apikey") == "api_key"
        assert self.suggester.suggest_config_key("openai", "api-key") == "api_key"
        assert self.suggester.suggest_config_key("ollama", "hostname") == "host"
        assert self.suggester.suggest_config_key("any", "model_name") == "model"
    
    def test_suggest_config_key_typos(self):
        """Test suggestion for key name typos."""
        assert self.suggester.suggest_config_key("openai", "api_ky") == "api_key"
        assert self.suggester.suggest_config_key("ollama", "mdoel") == "model"
        assert self.suggester.suggest_config_key("any", "servic") == "service"
    
    def test_suggest_config_key_no_match(self):
        """Test key suggestion when no good match exists."""
        assert self.suggester.suggest_config_key("openai", "completely_different") is None
        assert self.suggester.suggest_config_key("openai", "") is None
    
    def test_suggest_missing_config_openai(self):
        """Test missing configuration suggestions for OpenAI."""
        suggestions = self.suggester.suggest_missing_config("openai")
        
        assert len(suggestions) > 0
        assert "Add [openai] section with:" in suggestions[0]
        assert any("api_key" in s for s in suggestions)
        assert any("model" in s for s in suggestions)
        assert any("platform.openai.com" in s for s in suggestions)
    
    def test_suggest_missing_config_anthropic(self):
        """Test missing configuration suggestions for Anthropic."""
        suggestions = self.suggester.suggest_missing_config("anthropic")
        
        assert len(suggestions) > 0
        assert "Add [anthropic] section with:" in suggestions[0]
        assert any("api_key" in s for s in suggestions)
        assert any("console.anthropic.com" in s for s in suggestions)
    
    def test_suggest_missing_config_ollama(self):
        """Test missing configuration suggestions for Ollama."""
        suggestions = self.suggester.suggest_missing_config("ollama")
        
        assert len(suggestions) > 0
        assert "Add [ollama] section with:" in suggestions[0]
        assert any("model" in s for s in suggestions)
        assert any("ollama.ai" in s for s in suggestions)
        assert any("ollama pull" in s for s in suggestions)
    
    def test_suggest_missing_config_invalid_service(self):
        """Test missing configuration suggestions for invalid service."""
        suggestions = self.suggester.suggest_missing_config("invalid_service")
        assert suggestions == []
    
    def test_suggest_env_vars(self):
        """Test environment variable suggestions."""
        result = self.suggester.suggest_env_vars("openai", "api_key")
        assert "SYNC2NAS_OPENAI_API_KEY" in result
        assert "Set environment variable:" in result
        
        result = self.suggester.suggest_env_vars("ollama", "model")
        assert "SYNC2NAS_OLLAMA_MODEL" in result
    
    def test_suggest_value_correction_common_mistakes(self):
        """Test value correction for common mistakes."""
        assert self.suggester.suggest_value_correction("openai", "model", "gpt4") == "gpt-4"
        assert self.suggester.suggest_value_correction("openai", "model", "gpt35") == "gpt-3.5-turbo"
        assert self.suggester.suggest_value_correction("anthropic", "model", "claude3") == "claude-3-sonnet-20240229"
        assert self.suggester.suggest_value_correction("ollama", "host", "localhost") == "http://localhost:11434"
    
    def test_suggest_value_correction_openai_models(self):
        """Test OpenAI model name corrections."""
        assert self.suggester.suggest_value_correction("openai", "model", "gpt-4-turb") == "gpt-4-turbo"
        assert self.suggester.suggest_value_correction("openai", "model", "gpt3.5") == "gpt-3.5-turbo"
        assert self.suggester.suggest_value_correction("openai", "model", "chatgpt") is None  # No good match
    
    def test_suggest_value_correction_anthropic_models(self):
        """Test Anthropic model name corrections."""
        assert "claude-3-sonnet" in self.suggester.suggest_value_correction("anthropic", "model", "claude sonnet")
        assert "claude-3-haiku" in self.suggester.suggest_value_correction("anthropic", "model", "claude haiku")
        assert "claude-3-opus" in self.suggester.suggest_value_correction("anthropic", "model", "claude opus")
    
    def test_suggest_value_correction_ollama_models(self):
        """Test Ollama model name corrections."""
        assert self.suggester.suggest_value_correction("ollama", "model", "llama2") == "llama2:7b"
        assert self.suggester.suggest_value_correction("ollama", "model", "codellama") == "codellama:7b"
        assert self.suggester.suggest_value_correction("ollama", "model", "mistral") == "mistral:7b"
    
    def test_suggest_value_correction_ollama_host(self):
        """Test Ollama host URL corrections."""
        assert self.suggester.suggest_value_correction("ollama", "host", "localhost:11434") == "http://localhost:11434"
        assert self.suggester.suggest_value_correction("ollama", "host", "127.0.0.1") == "http://127.0.0.1"
        assert self.suggester.suggest_value_correction("ollama", "host", "http://localhost:11434") is None  # Already correct
    
    def test_suggest_value_correction_service_names(self):
        """Test service name corrections."""
        assert self.suggester.suggest_value_correction("llm", "service", "opena") == "openai"
        assert self.suggester.suggest_value_correction("llm", "service", "anthropi") == "anthropic"
        assert self.suggester.suggest_value_correction("llm", "service", "olama") == "ollama"
    
    def test_generate_config_template_openai(self):
        """Test configuration template generation for OpenAI."""
        template = self.suggester.generate_config_template("openai")
        
        assert "[llm]" in template
        assert "service = openai" in template
        assert "[openai]" in template
        assert "api_key" in template
        assert "model" in template
        assert "platform.openai.com" in template
    
    def test_generate_config_template_anthropic(self):
        """Test configuration template generation for Anthropic."""
        template = self.suggester.generate_config_template("anthropic")
        
        assert "[llm]" in template
        assert "service = anthropic" in template
        assert "[anthropic]" in template
        assert "api_key" in template
        assert "console.anthropic.com" in template
    
    def test_generate_config_template_ollama(self):
        """Test configuration template generation for Ollama."""
        template = self.suggester.generate_config_template("ollama")
        
        assert "[llm]" in template
        assert "service = ollama" in template
        assert "[ollama]" in template
        assert "model" in template
        assert "host" in template
        assert "ollama.ai" in template
    
    def test_analyze_configuration_errors_missing_sections(self):
        """Test error analysis for missing sections."""
        config = {}
        errors = [
            ValidationError(
                section="openai",
                key=None,
                message="Missing section",
                suggestion=None,
                error_code=ErrorCode.MISSING_SECTION
            )
        ]
        
        suggestions = self.suggester.analyze_configuration_errors(config, errors)
        
        assert len(suggestions) > 0
        assert any("Missing configuration sections:" in s for s in suggestions)
        assert any("openai" in s for s in suggestions)
    
    def test_analyze_configuration_errors_missing_keys(self):
        """Test error analysis for missing keys."""
        config = {"openai": {}}
        errors = [
            ValidationError(
                section="openai",
                key="api_key",
                message="Missing key",
                suggestion=None,
                error_code=ErrorCode.MISSING_KEY
            )
        ]
        
        suggestions = self.suggester.analyze_configuration_errors(config, errors)
        
        assert len(suggestions) > 0
        assert any("Missing configuration keys:" in s for s in suggestions)
        assert any("api_key" in s for s in suggestions)
    
    def test_analyze_configuration_errors_invalid_values(self):
        """Test error analysis for invalid values."""
        config = {"openai": {"model": "qwen3:14b"}}
        errors = [
            ValidationError(
                section="openai",
                key="model",
                message="Invalid value",
                suggestion="Use a valid model name",
                error_code=ErrorCode.INVALID_VALUE
            )
        ]
        
        suggestions = self.suggester.analyze_configuration_errors(config, errors)
        
        assert len(suggestions) > 0
        assert any("Invalid configuration values:" in s for s in suggestions)
        assert any("Use a valid model name" in s for s in suggestions)
    
    def test_analyze_potential_typos(self):
        """Test potential typo detection in configuration."""
        config = {
            "OpenAI": {"api_ky": "test"},  # Typos in section and key
            "olama": {"mdoel": "llama2"}   # More typos
        }
        
        suggestions = []
        self.suggester._analyze_potential_typos(config, suggestions)
        
        # Should detect section name typos
        assert any("OpenAI" in s and "openai" in s for s in suggestions)
        assert any("olama" in s and "ollama" in s for s in suggestions)
        
        # Should detect key name typos
        assert any("api_ky" in s and "api_key" in s for s in suggestions)
        assert any("mdoel" in s and "model" in s for s in suggestions)
    
    def test_analyze_potential_typos_no_typos(self):
        """Test typo detection with correct configuration."""
        config = {
            "openai": {"api_key": "test", "model": "qwen3:14b"},
            "ollama": {"model": "qwen3:14b", "host": "http://localhost:11434"}
        }
        
        suggestions = []
        self.suggester._analyze_potential_typos(config, suggestions)
        
        # Should not detect any typos
        assert len(suggestions) == 0
    
    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        # Empty inputs
        assert self.suggester.suggest_section_name("") is None
        assert self.suggester.suggest_config_key("openai", "") is None
        assert self.suggester.suggest_value_correction("openai", "model", "") is None
        
        # None inputs
        assert self.suggester.suggest_section_name(None) is None
        assert self.suggester.suggest_config_key("openai", None) is None
        assert self.suggester.suggest_value_correction("openai", "model", None) is None
        
        # Invalid service
        assert self.suggester.suggest_missing_config("invalid") == []
        
        # Empty configuration
        suggestions = self.suggester.analyze_configuration_errors({}, [])
        assert isinstance(suggestions, list)


class TestConfigSuggesterIntegration:
    """Integration tests for ConfigSuggester with real configuration scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.suggester = ConfigSuggester()
    
    def test_real_world_typo_scenario(self):
        """Test a real-world scenario with multiple typos."""
        config = {
            "LLM": {"servic": "opena"},  # Typos in section case and keys
            "OpenAI": {"api_ky": "sk-test", "mdoel": "gpt4"}  # More typos
        }
        
        # Test section name suggestions
        assert self.suggester.suggest_section_name("LLM") == "llm"
        assert self.suggester.suggest_section_name("OpenAI") == "openai"
        
        # Test key suggestions
        assert self.suggester.suggest_config_key("llm", "servic") == "service"
        assert self.suggester.suggest_config_key("openai", "api_ky") == "api_key"
        assert self.suggester.suggest_config_key("openai", "mdoel") == "model"
        
        # Test value suggestions
        assert self.suggester.suggest_value_correction("llm", "service", "opena") == "openai"
        assert self.suggester.suggest_value_correction("openai", "model", "gpt4") == "gpt-4"
    
    def test_complete_missing_configuration(self):
        """Test suggestions for completely missing configuration."""
        config = {}
        
        # Test template generation for each service
        for service in ["openai", "anthropic", "ollama"]:
            template = self.suggester.generate_config_template(service)
            assert f"service = {service}" in template
            assert f"[{service}]" in template
    
    def test_partial_configuration_suggestions(self):
        """Test suggestions for partially configured services."""
        config = {
            "llm": {"service": "openai"},
            "openai": {}  # Missing required keys
        }
        
        suggestions = self.suggester.suggest_missing_config("openai")
        assert any("api_key" in s for s in suggestions)
        assert any("platform.openai.com" in s for s in suggestions)
