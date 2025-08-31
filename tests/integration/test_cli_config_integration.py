"""
Integration tests for CLI configuration commands and startup validation.

Tests the complete CLI integration including the config-check command,
startup validation, and error handling in CLI context.
"""

import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock, AsyncMock
from click.testing import CliRunner

from cli.main import sync2nas_cli
from cli.config_check import config_check
from services.llm_factory import LLMServiceCreationError


class TestCLIConfigIntegration:
    """Test CLI integration with configuration validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def create_temp_config(self, content: str) -> str:
        """Create a temporary configuration file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(content)
            return f.name
    
    def test_config_check_command_valid_openai(self):
        """Test config-check command with valid OpenAI configuration."""
        config_content = """
[llm]
service = openai

[openai]
api_key = sk-test1234567890abcdef1234567890abcdef1234567890ab
model = gpt-4
max_tokens = 4000
temperature = 0.1

[tmdb]
api_key = test_tmdb_key

[sftp]
host = test.example.com
username = testuser
key_file = /path/to/key

[database]
type = sqlite
path = test.db

[transfers]
incoming = /path/to/incoming

[routing]
anime_tv_path = /path/to/anime
"""
        config_file = self.create_temp_config(config_content)
        
        try:
            with patch('httpx.AsyncClient') as mock_client_class, \
                 patch('services.db_implementations.sqlite_implementation.sqlite3'), \
                 patch('services.sftp_service.paramiko'), \
                 patch('services.tmdb_service.requests'):
                
                # Mock successful HTTP response for health check
                mock_client = AsyncMock()
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {'data': [{'id': 'gpt-4'}]}
                
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.get.return_value = mock_response
                mock_client_class.return_value = mock_client
                
                # Run config-check command via main CLI
                result = self.runner.invoke(sync2nas_cli, [
                    '--config', config_file,
                    'config-check',
                    '--service', 'openai',
                    '--verbose'
                ])
                
                print(f"Exit code: {result.exit_code}")
                print(f"Output: {result.output}")
                if result.exception:
                    print(f"Exception: {result.exception}")
                
                assert result.exit_code == 0
                assert "Configuration Check" in result.output
                assert "✅" in result.output or "All checks passed" in result.output
                
                # Verify HTTP client was called for health check
                mock_client.get.assert_called()
        
        finally:
            os.unlink(config_file)
    
    def test_config_check_command_invalid_config(self):
        """Test config-check command with invalid configuration."""
        config_content = """
[llm]
service = openai

[openai]
api_key = invalid_key_format
model = gpt4

[tmdb]
api_key = test_tmdb_key
"""
        config_file = self.create_temp_config(config_content)
        
        try:
            # Run config-check command via main CLI
            result = self.runner.invoke(sync2nas_cli, [
                '--config', config_file,
                'config-check',
                '--service', 'openai'
            ])
            
            # Should exit with error code
            assert result.exit_code != 0
            assert "❌" in result.output or "error" in result.output.lower()
            assert "api_key" in result.output.lower() or "invalid" in result.output.lower()
        
        finally:
            os.unlink(config_file)
    
    def test_config_check_command_connectivity_failure(self):
        """Test config-check command with connectivity failure."""
        config_content = """
[llm]
service = openai

[openai]
api_key = sk-test1234567890abcdef1234567890abcdef1234567890ab
model = gpt-4

[tmdb]
api_key = test_tmdb_key
"""
        config_file = self.create_temp_config(config_content)
        
        try:
            with patch('httpx.AsyncClient') as mock_client_class:
                # Mock connection failure
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.get.side_effect = Exception("Connection timeout")
                mock_client_class.return_value = mock_client
                
                # Run config-check command via main CLI
                result = self.runner.invoke(sync2nas_cli, [
                    '--config', config_file,
                    'config-check',
                    '--service', 'openai'
                ])
                
                # Should exit with error code
                assert result.exit_code != 0
                assert "❌" in result.output or "error" in result.output.lower()
                assert "connection" in result.output.lower() or "timeout" in result.output.lower()
        
        finally:
            os.unlink(config_file)
    
    def test_config_check_command_skip_connectivity(self):
        """Test config-check command with --skip-connectivity flag."""
        config_content = """
[llm]
service = openai

[openai]
api_key = sk-test1234567890abcdef1234567890abcdef1234567890ab
model = gpt-4

[tmdb]
api_key = test_tmdb_key
"""
        config_file = self.create_temp_config(config_content)
        
        try:
            # Mock the health check to avoid actual network calls
            with patch('utils.config.health_checker.httpx.AsyncClient') as mock_httpx:
                # Mock successful response
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {'data': [{'id': 'gpt-4'}]}
                
                async def mock_get(*args, **kwargs):
                    return mock_response
                
                mock_client = MagicMock()
                mock_client.get = mock_get
                mock_httpx.return_value.__aenter__.return_value = mock_client
                
                # Run config-check command with skip connectivity via main CLI
                result = self.runner.invoke(sync2nas_cli, [
                    '--config', config_file,
                    'config-check',
                    '--service', 'openai',
                    '--skip-connectivity'
                ])
            
            # Debug output
            print(f"Exit code: {result.exit_code}")
            print(f"Output: {result.output}")
            if result.exception:
                print(f"Exception: {result.exception}")
            
            # Should succeed even without network access
            assert result.exit_code == 0
            assert "Configuration Check" in result.output
            # Should not attempt connectivity tests
            assert "connectivity" in result.output.lower() or "skip" in result.output.lower()
        
        finally:
            os.unlink(config_file)
    
    def test_config_check_command_all_services(self):
        """Test config-check command checking all services."""
        config_content = """
[llm]
service = ollama

[openai]
api_key = sk-test1234567890abcdef1234567890abcdef1234567890ab
model = gpt-4

[ollama]
model = gemma3:12b
host = http://localhost:11434

[anthropic]
api_key = sk-ant-test1234567890abcdef1234567890abcdef1234567890ab
model = claude-3-sonnet-20240229

[tmdb]
api_key = test_tmdb_key
"""
        config_file = self.create_temp_config(config_content)
        
        try:
            with patch('services.llm_implementations.ollama_implementation.Client') as mock_ollama, \
                 patch('services.llm_implementations.openai_implementation.openai.OpenAI') as mock_openai, \
                 patch('services.llm_implementations.anthropic_implementation.anthropic.Anthropic') as mock_anthropic:
                
                # Mock successful responses for all services
                mock_ollama_client = MagicMock()
                mock_ollama_client.generate.return_value = {'response': 'Test'}
                mock_ollama.return_value = mock_ollama_client
                
                mock_openai_client = MagicMock()
                mock_openai_response = MagicMock()
                mock_openai_response.choices = [MagicMock(message=MagicMock(content="Test"))]
                mock_openai_client.chat.completions.create.return_value = mock_openai_response
                mock_openai.return_value = mock_openai_client
                
                mock_anthropic_client = MagicMock()
                mock_anthropic_response = MagicMock()
                mock_anthropic_response.content = [MagicMock(text="Test")]
                mock_anthropic_client.messages.create.return_value = mock_anthropic_response
                mock_anthropic.return_value = mock_anthropic_client
                
                # Run config-check for all services via main CLI
                result = self.runner.invoke(sync2nas_cli, [
                    '--config', config_file,
                    'config-check',
                    '--service', 'all'
                ])
                
                assert result.exit_code == 0
                assert "Configuration Check" in result.output
                
                # Should check multiple services
                output_lower = result.output.lower()
                assert "ollama" in output_lower or "openai" in output_lower or "anthropic" in output_lower
        
        finally:
            os.unlink(config_file)
    
    def test_cli_startup_validation_success(self):
        """Test CLI startup validation with valid configuration."""
        config_content = """
[llm]
service = openai

[openai]
api_key = sk-test1234567890abcdef1234567890abcdef1234567890ab
model = gpt-4

[tmdb]
api_key = test_tmdb_key

[sftp]
host = test.example.com
username = testuser
key_file = /path/to/key

[database]
type = sqlite
path = test.db

[transfers]
incoming = /path/to/incoming

[routing]
anime_tv_path = /path/to/anime
"""
        config_file = self.create_temp_config(config_content)
        
        try:
            with patch('services.llm_implementations.openai_implementation.openai.OpenAI') as mock_openai, \
                 patch('services.db_implementations.sqlite_implementation.sqlite3'), \
                 patch('services.sftp_service.paramiko'), \
                 patch('services.tmdb_service.requests'):
                
                # Mock successful OpenAI response
                mock_client = MagicMock()
                mock_response = MagicMock()
                mock_response.choices = [MagicMock(message=MagicMock(content="Test"))]
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client
                
                # Test CLI initialization (should not exit)
                result = self.runner.invoke(sync2nas_cli, [
                    '--config', config_file,
                    '--help'  # Use help to avoid running actual commands
                ])
                
                # Should succeed without errors
                assert result.exit_code == 0
                assert "Usage:" in result.output
        
        finally:
            os.unlink(config_file)
    
    def test_cli_startup_validation_failure(self):
        """Test CLI startup validation with invalid configuration."""
        config_content = """
[llm]
service = openai

[openai]
api_key = invalid_key_format

[tmdb]
api_key = test_tmdb_key
"""
        config_file = self.create_temp_config(config_content)
        
        try:
            with patch('services.llm_implementations.openai_implementation.openai.OpenAI') as mock_openai:
                # Mock OpenAI failure
                mock_openai.side_effect = Exception("Invalid API key")
                
                # Test CLI initialization (should exit with error)
                result = self.runner.invoke(sync2nas_cli, [
                    '--config', config_file,
                    'config-check'  # Use a command that requires full initialization
                ])
                
                # Should fail with error
                assert result.exit_code != 0
                assert "❌" in result.output or "error" in result.output.lower()
        
        finally:
            os.unlink(config_file)
    
    def test_cli_skip_validation_flag(self):
        """Test CLI --skip-validation flag."""
        config_content = """
[llm]
service = openai

[openai]
api_key = invalid_key_format

[tmdb]
api_key = test_tmdb_key
"""
        config_file = self.create_temp_config(config_content)
        
        try:
            # Test CLI with skip validation (should succeed even with invalid config)
            result = self.runner.invoke(sync2nas_cli, [
                '--config', config_file,
                '--skip-validation',
                '--help'
            ])
            
            # Should succeed despite invalid configuration
            assert result.exit_code == 0
            assert "Usage:" in result.output
        
        finally:
            os.unlink(config_file)
    
    @patch.dict(os.environ, {
        'SYNC2NAS_LLM_SERVICE': 'openai',
        'SYNC2NAS_OPENAI_API_KEY': 'sk-env1234567890abcdef1234567890abcdef1234567890ab'
    })
    def test_cli_environment_variable_integration(self):
        """Test CLI integration with environment variables."""
        config_content = """
[llm]
service = ollama

[ollama]
model = gemma3:12b

[tmdb]
api_key = test_tmdb_key
"""
        config_file = self.create_temp_config(config_content)
        
        try:
            with patch('services.llm_implementations.openai_implementation.openai.OpenAI') as mock_openai, \
                 patch('utils.config.health_checker.httpx.AsyncClient') as mock_httpx, \
                 patch('services.db_implementations.sqlite_implementation.sqlite3'), \
                 patch('services.sftp_service.paramiko'), \
                 patch('services.tmdb_service.requests'):
                
                # Mock successful OpenAI response
                mock_client = MagicMock()
                mock_response = MagicMock()
                mock_response.choices = [MagicMock(message=MagicMock(content="Test"))]
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client
                
                # Mock health check response
                mock_health_response = MagicMock()
                mock_health_response.status_code = 200
                mock_health_response.json.return_value = {'data': [{'id': 'gpt-4'}]}
                
                async def mock_get(*args, **kwargs):
                    return mock_health_response
                
                mock_health_client = MagicMock()
                mock_health_client.get = mock_get
                mock_httpx.return_value.__aenter__.return_value = mock_health_client
                
                # Environment variables should override config file
                # Use config-check to trigger service initialization
                result = self.runner.invoke(sync2nas_cli, [
                    '--config', config_file,
                    'config-check',
                    '--service', 'openai'
                ])
                
                # Should succeed using environment variables
                assert result.exit_code == 0
                assert "Configuration Check" in result.output
                
                # Verify OpenAI was used (from environment) instead of Ollama (from config)
                mock_openai.assert_called()
        
        finally:
            os.unlink(config_file)
    
    def test_config_check_timeout_handling(self):
        """Test config-check command timeout handling."""
        config_content = """
[llm]
service = openai

[openai]
api_key = sk-test1234567890abcdef1234567890abcdef1234567890ab
model = gpt-4

[tmdb]
api_key = test_tmdb_key
"""
        config_file = self.create_temp_config(config_content)
        
        try:
            with patch('services.llm_implementations.openai_implementation.openai.OpenAI') as mock_openai:
                # Mock slow response that should timeout
                import time
                def slow_create(*args, **kwargs):
                    time.sleep(2)  # 2 second delay
                    return MagicMock(choices=[MagicMock(message=MagicMock(content="Test"))])
                
                mock_client = MagicMock()
                mock_client.chat.completions.create.side_effect = slow_create
                mock_openai.return_value = mock_client
                
                # Run config-check with short timeout via main CLI
                result = self.runner.invoke(sync2nas_cli, [
                    '--config', config_file,
                    'config-check',
                    '--service', 'openai',
                    '--timeout', '1.0'  # 1 second timeout
                ])
                
                # Should handle timeout gracefully
                assert result.exit_code != 0
                assert "timeout" in result.output.lower() or "❌" in result.output
        
        finally:
            os.unlink(config_file)


class TestCLIErrorHandlingIntegration:
    """Test CLI error handling integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_cli_missing_config_file(self):
        """Test CLI behavior with missing configuration file."""
        # Run CLI with non-existent config file
        result = self.runner.invoke(sync2nas_cli, [
            '--config', '/nonexistent/config.ini',
            'config-check'
        ])
        
        # Should fail gracefully
        assert result.exit_code != 0
        assert "not exist" in result.output.lower() or "not found" in result.output.lower()
    
    def test_cli_malformed_config_file(self):
        """Test CLI behavior with malformed configuration file."""
        config_content = """
[llm
service = openai  # Missing closing bracket

[openai]
api_key = sk-test1234567890abcdef1234567890abcdef1234567890ab
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(config_content)
            config_file = f.name
        
        try:
            # Run CLI with malformed config
            result = self.runner.invoke(sync2nas_cli, [
                '--config', config_file,
                'config-check'
            ])
            
            # Should fail with parsing error
            assert result.exit_code != 0
        
        finally:
            os.unlink(config_file)
    
    def test_config_check_error_reporting_accuracy(self):
        """Test that config-check provides accurate error reporting."""
        config_content = """
[LLM]
servic = invalid_service

[OpenAI]
api_ky = invalid_key
mdoel = gpt4

[olama]
mdoel = invalid_model
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(config_content)
            config_file = f.name
        
        try:
            # Run config-check command via main CLI
            result = self.runner.invoke(sync2nas_cli, [
                '--config', config_file,
                'config-check',
                '--verbose'
            ])
            
            # Should provide detailed error information
            assert result.exit_code != 0
            output_lower = result.output.lower()
            
            # Should detect typos and provide suggestions
            assert "service" in output_lower or "llm" in output_lower
            assert "ollama" in output_lower or "api_key" in output_lower
        
        finally:
            os.unlink(config_file)
    
    def test_cli_context_object_validation(self):
        """Test CLI context object validation and error handling."""
        config_content = """
[llm]
service = openai

[openai]
api_key = sk-test1234567890abcdef1234567890abcdef1234567890ab
model = gpt-4

[tmdb]
api_key = test_tmdb_key
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(config_content)
            config_file = f.name
        
        try:
            with patch('services.llm_implementations.openai_implementation.openai.OpenAI') as mock_openai, \
                 patch('services.db_implementations.sqlite_implementation.sqlite3') as mock_sqlite:
                
                # Mock successful services
                mock_client = MagicMock()
                mock_response = MagicMock()
                mock_response.choices = [MagicMock(message=MagicMock(content="Test"))]
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client
                
                # Test that context object is properly created
                result = self.runner.invoke(sync2nas_cli, [
                    '--config', config_file,
                    '--help'
                ])
                
                # Should succeed and create proper context
                assert result.exit_code == 0
                assert "Usage:" in result.output
        
        finally:
            os.unlink(config_file)


class TestCLIPerformanceIntegration:
    """Test CLI performance and resource usage integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_cli_startup_performance(self):
        """Test CLI startup performance with various configurations."""
        config_content = """
[llm]
service = openai

[openai]
api_key = sk-test1234567890abcdef1234567890abcdef1234567890ab
model = gpt-4

[tmdb]
api_key = test_tmdb_key
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(config_content)
            config_file = f.name
        
        try:
            with patch('services.llm_implementations.openai_implementation.openai.OpenAI') as mock_openai:
                # Mock fast response
                mock_client = MagicMock()
                mock_response = MagicMock()
                mock_response.choices = [MagicMock(message=MagicMock(content="Test"))]
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client
                
                import time
                start_time = time.time()
                
                # Run CLI command
                result = self.runner.invoke(sync2nas_cli, [
                    '--config', config_file,
                    '--help'
                ])
                
                end_time = time.time()
                startup_time = end_time - start_time
                
                # Should complete within reasonable time (5 seconds)
                assert startup_time < 5.0
                assert result.exit_code == 0
        
        finally:
            os.unlink(config_file)
    
    def test_config_check_performance_multiple_services(self):
        """Test config-check performance with multiple services."""
        config_content = """
[llm]
service = ollama

[openai]
api_key = sk-test1234567890abcdef1234567890abcdef1234567890ab
model = gpt-4

[ollama]
model = gemma3:12b
host = http://localhost:11434

[anthropic]
api_key = sk-ant-test1234567890abcdef1234567890abcdef1234567890ab
model = claude-3-sonnet-20240229

[tmdb]
api_key = test_tmdb_key
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(config_content)
            config_file = f.name
        
        try:
            with patch('services.llm_implementations.ollama_implementation.Client') as mock_ollama, \
                 patch('services.llm_implementations.openai_implementation.openai.OpenAI') as mock_openai, \
                 patch('services.llm_implementations.anthropic_implementation.anthropic.Anthropic') as mock_anthropic:
                
                # Mock fast responses for all services
                mock_ollama_client = MagicMock()
                mock_ollama_client.generate.return_value = {'response': 'Test'}
                mock_ollama.return_value = mock_ollama_client
                
                mock_openai_client = MagicMock()
                mock_openai_response = MagicMock()
                mock_openai_response.choices = [MagicMock(message=MagicMock(content="Test"))]
                mock_openai_client.chat.completions.create.return_value = mock_openai_response
                mock_openai.return_value = mock_openai_client
                
                mock_anthropic_client = MagicMock()
                mock_anthropic_response = MagicMock()
                mock_anthropic_response.content = [MagicMock(text="Test")]
                mock_anthropic_client.messages.create.return_value = mock_anthropic_response
                mock_anthropic.return_value = mock_anthropic_client
                
                import time
                start_time = time.time()
                
                # Run config-check for all services via main CLI
                result = self.runner.invoke(sync2nas_cli, [
                    '--config', config_file,
                    'config-check',
                    '--service', 'all'
                ])
                
                end_time = time.time()
                check_time = end_time - start_time
                
                # Should complete within reasonable time (10 seconds for all services)
                assert check_time < 10.0
                assert result.exit_code == 0
        
        finally:
            os.unlink(config_file)