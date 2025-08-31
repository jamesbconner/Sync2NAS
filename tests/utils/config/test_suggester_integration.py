"""Integration tests for config suggester with validator."""

import pytest
from utils.config.config_validator import ConfigValidator
from utils.config.validation_models import ErrorCode


class TestSuggesterIntegration:
    """Test integration between ConfigValidator and ConfigSuggester."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ConfigValidator()
    
    def test_typo_suggestions_in_validation(self):
        """Test that typo suggestions are included in validation results."""
        config = {
            "llm": {"servic": "opena"},  # Typos
            "OpenAI": {"api_ky": "sk-test"}  # Case and typo issues
        }
        
        result = self.validator.validate_llm_config(config)
        
        # Should have errors
        assert not result.is_valid
        assert len(result.errors) > 0
        
        # Should have intelligent suggestions
        assert len(result.suggestions) > 0
        
        # Check for specific suggestion content
        suggestion_text = " ".join(result.suggestions)
        assert "typos" in suggestion_text.lower() or "might be" in suggestion_text.lower()
    
    def test_missing_section_suggestions(self):
        """Test suggestions for missing configuration sections."""
        config = {
            "llm": {"service": "openai"}
            # Missing openai section
        }
        
        result = self.validator.validate_llm_config(config)
        
        assert not result.is_valid
        assert len(result.suggestions) > 0
        
        # Should suggest adding openai section
        suggestion_text = " ".join(result.suggestions)
        assert "openai" in suggestion_text.lower()
        assert "section" in suggestion_text.lower()
    
    def test_invalid_service_name_suggestion(self):
        """Test suggestions for invalid service names."""
        config = {
            "llm": {"service": "opena"},  # Typo in service name
            "openai": {"api_key": "sk-test"}
        }
        
        result = self.validator.validate_llm_config(config)
        
        assert not result.is_valid
        
        # Find the invalid service error
        service_errors = [e for e in result.errors if e.error_code == ErrorCode.INVALID_SERVICE]
        assert len(service_errors) > 0
        
        # Should suggest "openai"
        service_error = service_errors[0]
        assert "openai" in service_error.suggestion.lower()
    
    def test_generate_config_template(self):
        """Test configuration template generation."""
        template = self.validator.generate_config_template("openai")
        
        assert "[llm]" in template
        assert "service = openai" in template
        assert "[openai]" in template
        assert "api_key" in template
        assert "platform.openai.com" in template
    
    def test_typo_suggestions_method(self):
        """Test the typo suggestions method."""
        config = {
            "OpenAI": {"api_ky": "test"},
            "olama": {"mdoel": "llama2"}
        }
        
        suggestions = self.validator.get_typo_suggestions(config)
        
        assert len(suggestions) > 0
        suggestion_text = " ".join(suggestions)
        
        # Should detect section name issues
        assert "openai" in suggestion_text.lower()
        assert "ollama" in suggestion_text.lower()
        
        # Should detect key name issues
        assert "api_key" in suggestion_text.lower()
        assert "model" in suggestion_text.lower()
    
    def test_suggest_fix_for_error(self):
        """Test specific error fix suggestions."""
        config = {"openai": {"model": "gpt4"}}
        
        # Create a mock error
        from utils.config.validation_models import ValidationError
        error = ValidationError(
            section="openai",
            key="model",
            message="Invalid value",
            suggestion=None,
            error_code=ErrorCode.INVALID_VALUE
        )
        
        fix_suggestion = self.validator.suggest_fix_for_error(error, config)
        
        assert fix_suggestion is not None
        assert "gpt-4" in fix_suggestion  # Should suggest correct model name
    
    def test_comprehensive_error_analysis(self):
        """Test comprehensive error analysis with multiple issues."""
        config = {
            "LLM": {"servic": "opena"},  # Multiple typos
            "OpenAI": {},  # Missing required keys
            "olama": {"mdoel": "llama"}  # Wrong section, typos
        }
        
        result = self.validator.validate_llm_config(config)
        
        # Should have multiple errors
        assert not result.is_valid
        assert len(result.errors) > 0
        
        # Should have comprehensive suggestions
        assert len(result.suggestions) > 0
        
        # Check that suggestions cover different types of issues
        suggestion_text = " ".join(result.suggestions)
        assert any(keyword in suggestion_text.lower() for keyword in [
            "missing", "typo", "section", "key", "configuration"
        ])
    
    def test_no_suggestions_for_valid_config(self):
        """Test that valid configuration doesn't generate unnecessary suggestions."""
        config = {
            "llm": {"service": "openai"},
            "openai": {"api_key": "sk-test123456789012345678901234567890123456789012345"}
        }
        
        result = self.validator.validate_llm_config(config)
        
        # Should be valid (ignoring API key validation for this test)
        # Focus on structure being correct
        assert len([e for e in result.errors if e.error_code in [
            ErrorCode.MISSING_SECTION, ErrorCode.MISSING_KEY
        ]]) == 0
        
        # Should not have typo-related suggestions
        if result.suggestions:
            suggestion_text = " ".join(result.suggestions)
            assert "typo" not in suggestion_text.lower()
            assert "might be" not in suggestion_text.lower()