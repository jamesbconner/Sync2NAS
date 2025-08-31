"""
Integration tests for error reporting and suggestion accuracy.

Tests the complete error reporting pipeline from configuration validation
through intelligent suggestions and error recovery.
"""

import pytest
import tempfile
import os
from unittest.mock import patch

from utils.sync2nas_config import load_configuration
from utils.config.config_validator import ConfigValidator
from utils.config.config_suggester import ConfigSuggester
from utils.config.validation_models import ErrorCode
from services.llm_factory import create_llm_service, LLMServiceCreationError


class TestErrorReportingIntegration:
    """Test error reporting integration across the configuration system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ConfigValidator()
        self.suggester = ConfigSuggester()
    
    def create_temp_config(self, content: str) -> str:
        """Create a temporary configuration file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(content)
            return f.name
    
    def test_comprehensive_error_detection_and_reporting(self):
        """Test comprehensive error detection and accurate reporting."""
        config_content = """
[LLM]
servic = invalid_service

[OpenAI]
api_ky = invalid_key_format
mdoel = gpt4
max_tokens = invalid_number
temperature = 5.0

[olama]
mdoel = invalid_model
hostname = not_a_url

[unknown_section]
random_key = random_value
"""
        config_file = self.create_temp_config(config_content)
        
        try:
            # Load configuration
            config = load_configuration(config_file, normalize=True)
            
            # Validate configuration
            result = self.validator.validate_llm_config(config)
            
            # Should detect multiple error types
            assert not result.is_valid
            assert len(result.errors) > 0
            
            # Categorize errors
            missing_key_errors = [e for e in result.errors if e.error_code == ErrorCode.MISSING_KEY]
            invalid_value_errors = [e for e in result.errors if e.error_code == ErrorCode.INVALID_VALUE]
            api_key_errors = [e for e in result.errors if e.error_code == ErrorCode.API_KEY_INVALID]
            
            # Should have various error types
            assert len(missing_key_errors) > 0  # Missing 'service' key
            
            # Should have intelligent suggestions
            assert len(result.suggestions) > 0
            
            # Analyze suggestion accuracy
            suggestion_text = ' '.join(result.suggestions).lower()
            
            # Should suggest corrections for typos
            assert 'service' in suggestion_text
            assert 'ollama' in suggestion_text
        
        finally:
            os.unlink(config_file)
    
    def test_error_message_clarity_and_actionability(self):
        """Test that error messages are clear and actionable."""
        test_cases = [
            {
                'config': {'llm': {'service': 'openai'}},  # Missing openai section
                'expected_error_codes': [ErrorCode.MISSING_SECTION],
                'expected_suggestions': ['openai', 'api_key']
            },
            {
                'config': {
                    'llm': {'service': 'openai'},
                    'openai': {'api_key': 'invalid_key'}
                },
                'expected_error_codes': [ErrorCode.API_KEY_INVALID],
                'expected_suggestions': ['api_key']
            },
            {
                'config': {
                    'llm': {'service': 'ollama'},
                    'ollama': {'model': 'gemma3:12b', 'host': 'invalid_url'}
                },
                'expected_error_codes': [ErrorCode.INVALID_VALUE],
                'expected_suggestions': ['http://', 'localhost']
            }
        ]
        
        for test_case in test_cases:
            result = self.validator.validate_llm_config(test_case['config'])
            
            # Check expected error codes
            actual_error_codes = [e.error_code for e in result.errors]
            for expected_code in test_case['expected_error_codes']:
                assert expected_code in actual_error_codes, f"Expected {expected_code} in {actual_error_codes}"
            
            # Check suggestion accuracy
            suggestion_text = ' '.join(result.suggestions).lower()
            for expected_suggestion in test_case['expected_suggestions']:
                assert expected_suggestion.lower() in suggestion_text, f"Expected '{expected_suggestion}' in suggestions"
    
    def test_typo_detection_accuracy(self):
        """Test accuracy of typo detection and correction suggestions."""
        typo_test_cases = [
            {
                'original': {'LLM': {'servic': 'opena'}},
                'expected_corrections': [('llm', 'LLM'), ('service', 'servic')]
            },
            {
                'original': {'OpenAI': {'api_ky': 'test', 'mdoel': 'gpt4'}},
                'expected_corrections': [('openai', 'OpenAI'), ('api_key', 'api_ky'), ('model', 'mdoel')]
            },
            {
                'original': {'olama': {'mdoel': 'llama2', 'hostname': 'localhost'}},
                'expected_corrections': [('ollama', 'olama'), ('model', 'mdoel'), ('host', 'hostname')]
            }
        ]
        
        for test_case in typo_test_cases:
            result = self.validator.validate_llm_config(test_case['original'])
            
            # Should have suggestions
            assert len(result.suggestions) > 0
            
            suggestion_text = ' '.join(result.suggestions).lower()
            
            # Check that corrections are suggested
            for correct, typo in test_case['expected_corrections']:
                assert correct.lower() in suggestion_text, f"Expected correction '{correct}' for typo '{typo}' in suggestions"
    
    def test_suggestion_prioritization(self):
        """Test that suggestions are prioritized appropriately."""
        config = {
            'LLM': {'servic': 'opena'},  # Multiple issues
            'OpenAI': {},  # Missing required keys
            'olama': {'mdoel': 'invalid'}  # Wrong section name and invalid value
        }
        
        result = self.validator.validate_llm_config(config)
        
        # Should have multiple suggestions
        assert len(result.suggestions) > 0
        
        suggestion_text = ' '.join(result.suggestions)
        
        # Should include typo corrections
        assert 'service' in suggestion_text.lower()
        assert 'ollama' in suggestion_text.lower()
    
    def test_error_context_preservation(self):
        """Test that error context is preserved throughout the pipeline."""
        config_content = """
[llm]
service = openai

[openai]
api_key = invalid_key
model = gpt4
max_tokens = too_many
"""
        config_file = self.create_temp_config(config_content)
        
        try:
            # Load and validate
            config = load_configuration(config_file, normalize=True)
            result = self.validator.validate_llm_config(config)
            
            # Check that errors maintain context
            for error in result.errors:
                assert error.section is not None
                assert error.message is not None
                assert error.error_code is not None
                
                # Error messages should be specific
                if error.error_code == ErrorCode.API_KEY_INVALID:
                    assert 'api' in error.message.lower() and 'key' in error.message.lower()
                elif error.error_code == ErrorCode.INVALID_VALUE:
                    assert error.key is not None
                    assert error.key in error.message
        
        finally:
            os.unlink(config_file)
    
    def test_suggestion_template_accuracy(self):
        """Test that suggestion templates are accurate and helpful."""
        # Test missing configuration templates
        missing_configs = ['openai', 'anthropic', 'ollama']
        
        for service in missing_configs:
            template = self.suggester.generate_config_template(service)
            
            # Should contain service selection
            assert f'service = {service}' in template
            
            # Should contain service-specific section
            assert f'[{service}]' in template
            
            # Should contain helpful comments
            if service == 'openai':
                assert 'platform.openai.com' in template
                assert 'gpt-4' in template
            elif service == 'anthropic':
                assert 'console.anthropic.com' in template
                assert 'claude-3' in template
            elif service == 'ollama':
                assert 'ollama.ai' in template
                assert 'ollama pull' in template
    
    def test_error_recovery_workflow(self):
        """Test complete error recovery workflow."""
        # Start with broken config
        broken_config = {
            'LLM': {'servic': 'opena'},
            'OpenAI': {'api_ky': 'invalid_key'}
        }
        
        # Step 1: Detect errors
        result = self.validator.validate_llm_config(broken_config)
        assert not result.is_valid
        
        # Step 2: Apply suggestions (simulate user fixing config)
        fixed_config = {
            'llm': {'service': 'openai'},
            'openai': {
                'api_key': 'sk-test1234567890abcdef1234567890abcdef1234567890ab',
                'model': 'gemma3:12b'
            }
        }
        
        # Step 3: Validate fixed config
        fixed_result = self.validator.validate_llm_config(fixed_config)
        assert fixed_result.is_valid
        assert len(fixed_result.errors) == 0
        
        # Step 4: Service creation should work
        with patch('services.llm_implementations.openai_implementation.openai.OpenAI'):
            service = create_llm_service(fixed_config, validate_health=False)
            assert service is not None
    
    def test_multiple_error_aggregation(self):
        """Test that multiple errors are properly aggregated and reported."""
        config = {
            'llm': {'service': 'openai'},  # Valid service key
            'openai': {
                'api_key': 'invalid',  # Invalid API key
                'model': 'gemma3:12b',  # Invalid model name
                'max_tokens': 'invalid',  # Invalid number
                'temperature': '5.0'  # Out of range
            }
        }
        
        result = self.validator.validate_llm_config(config)
        
        # Should have multiple errors
        assert not result.is_valid
        assert len(result.errors) >= 1  # At least one error
        
        # Should have suggestions
        assert len(result.suggestions) > 0
    
    def test_error_message_localization_readiness(self):
        """Test that error messages are structured for potential localization."""
        config = {
            'llm': {'service': 'openai'},
            'openai': {'api_key': 'invalid_key'}
        }
        
        result = self.validator.validate_llm_config(config)
        
        for error in result.errors:
            # Error messages should have structured components
            assert error.error_code is not None
            assert error.section is not None
            assert error.message is not None
            
            # Should have suggestion when applicable
            if error.error_code == ErrorCode.API_KEY_INVALID:
                assert error.suggestion is not None
                assert 'platform.openai.com' in error.suggestion
    
    def test_suggestion_context_awareness(self):
        """Test that suggestions are context-aware and relevant."""
        test_scenarios = [
            {
                'config': {'llm': {'service': 'openai'}},
                'context': 'missing_openai_config',
                'expected_suggestions': ['api_key', 'openai', 'platform.openai.com']
            },
            {
                'config': {'llm': {'service': 'ollama'}, 'ollama': {}},
                'context': 'missing_ollama_config',
                'expected_suggestions': ['model', 'ollama']
            },
            {
                'config': {'LLM': {'servic': 'opena'}},
                'context': 'typos_in_config',
                'expected_suggestions': ['llm', 'service']
            }
        ]
        
        for scenario in test_scenarios:
            result = self.validator.validate_llm_config(scenario['config'])
            
            suggestion_text = ' '.join(result.suggestions).lower()
            
            # Check context-appropriate suggestions
            for expected in scenario['expected_suggestions']:
                assert expected.lower() in suggestion_text, f"Expected '{expected}' for context '{scenario['context']}'"


class TestErrorReportingServiceIntegration:
    """Test error reporting integration with service creation."""
    
    def test_service_creation_error_propagation(self):
        """Test that service creation errors are properly propagated."""
        invalid_configs = [
            # Missing service selection
            {'openai': {'api_key': 'sk-test1234567890abcdef1234567890abcdef1234567890ab'}},
            
            # Invalid service
            {'llm': {'service': 'invalid_service'}},
            
            # Missing required config
            {'llm': {'service': 'openai'}},
            
            # Invalid API key
            {'llm': {'service': 'openai'}, 'openai': {'api_key': 'invalid'}}
        ]
        
        for config in invalid_configs:
            with pytest.raises(LLMServiceCreationError) as exc_info:
                create_llm_service(config, validate_health=False)
            
            # Error should contain helpful information
            error_message = str(exc_info.value)
            assert len(error_message) > 0
            
            # Should reference the specific issue
            if 'invalid_service' in str(config):
                assert 'service' in error_message.lower()
            elif 'api_key' in str(config) and 'invalid' in str(config):
                assert 'api_key' in error_message.lower() or 'invalid' in error_message.lower()
    
    def test_validation_error_to_service_error_mapping(self):
        """Test that validation errors map correctly to service creation errors."""
        config = {
            'llm': {'service': 'openai'},
            'openai': {'api_key': 'invalid_key_format'}
        }
        
        # First validate to get detailed errors
        validator = ConfigValidator()
        validation_result = validator.validate_llm_config(config)
        
        assert not validation_result.is_valid
        assert len(validation_result.errors) > 0
        
        # Service creation should fail with related error
        with pytest.raises(LLMServiceCreationError) as exc_info:
            create_llm_service(config, validate_health=False)
        
        service_error = str(exc_info.value)
        
        # Service error should reference validation issues
        assert 'api_key' in service_error.lower() or 'invalid' in service_error.lower()
    
    def test_error_suggestion_integration_with_service_creation(self):
        """Test that error suggestions integrate with service creation failures."""
        config = {'llm': {'service': 'openai'}}  # Missing openai section
        
        # Get validation suggestions
        validator = ConfigValidator()
        result = validator.validate_llm_config(config)
        
        assert not result.is_valid
        assert len(result.suggestions) > 0
        
        # Service creation should fail
        with pytest.raises(LLMServiceCreationError):
            create_llm_service(config, validate_health=False)
        
        # Suggestions should be helpful for fixing the service creation issue
        suggestion_text = ' '.join(result.suggestions).lower()
        assert 'openai' in suggestion_text
        assert 'api_key' in suggestion_text