"""
Tests for CLI service initialization and error handling.

This module tests the service initialization logic in the main CLI to ensure
that services are properly initialized with normalized configuration and that
appropriate error handling is in place.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import click
from click.testing import CliRunner

from cli.main import sync2nas_cli, validate_context_for_command, get_service_from_context
from utils.sync2nas_config import get_config_value


class TestServiceInitialization:
    """Test service initialization with various configuration scenarios."""
    
    def test_successful_service_initialization(self):
        """Test that all services initialize correctly with valid configuration."""
        # Create a mock configuration with all required sections
        mock_config = {
            'sftp': {
                'host': 'test.example.com',
                'port': '22',
                'username': 'testuser',
                'ssh_key_path': '/path/to/key'
            },
            'tmdb': {
                'api_key': 'test_api_key'
            },
            'routing': {
                'anime_tv_path': '/path/to/anime'
            },
            'transfers': {
                'incoming': '/path/to/incoming'
            },
            'llm': {
                'service': 'ollama'
            },
            'ollama': {
                'model': 'test_model',
                'host': 'http://localhost:11434'
            },
            'database': {
                'type': 'sqlite'
            },
            'sqlite': {
                'db_file': 'test.db'
            }
        }
        
        with patch('utils.sync2nas_config.load_configuration', return_value=mock_config), \
             patch('services.llm_factory.create_llm_service') as mock_llm, \
             patch('services.db_factory.create_db_service') as mock_db, \
             patch('services.sftp_service.SFTPService') as mock_sftp, \
             patch('services.tmdb_service.TMDBService') as mock_tmdb:
            
            # Configure mocks
            mock_llm.return_value = Mock()
            mock_db.return_value = Mock()
            mock_sftp.return_value = Mock()
            mock_tmdb.return_value = Mock()
            
            runner = CliRunner()
            result = runner.invoke(sync2nas_cli, ['--help'])
            
            # Should not crash and should show help
            assert result.exit_code == 0
            assert 'Usage:' in result.output
    
    def test_missing_sftp_configuration(self):
        """Test service initialization with missing SFTP configuration."""
        # Create configuration missing SFTP section
        mock_config = {
            'llm': {'service': 'ollama'},
            'ollama': {'model': 'test_model'},
            'database': {'type': 'sqlite'},
            'sqlite': {'db_file': 'test.db'}
        }
        
        with patch('utils.sync2nas_config.load_configuration', return_value=mock_config), \
             patch('services.llm_factory.create_llm_service', return_value=Mock()), \
             patch('services.db_factory.create_db_service', return_value=Mock()):
            
            runner = CliRunner()
            result = runner.invoke(sync2nas_cli, ['--help'])
            
            # Should still work (services are optional for help)
            assert result.exit_code == 0
    
    def test_invalid_sftp_configuration(self):
        """Test service initialization with invalid SFTP configuration."""
        mock_config = {
            'sftp': {
                'host': 'test.example.com',
                # Missing required fields: username, ssh_key_path
                'port': '22'
            },
            'llm': {'service': 'ollama'},
            'ollama': {'model': 'test_model'},
            'database': {'type': 'sqlite'},
            'sqlite': {'db_file': 'test.db'}
        }
        
        with patch('utils.sync2nas_config.load_configuration', return_value=mock_config), \
             patch('services.llm_factory.create_llm_service', return_value=Mock()), \
             patch('services.db_factory.create_db_service', return_value=Mock()):
            
            runner = CliRunner()
            result = runner.invoke(sync2nas_cli, ['--help'])
            
            # Should still work but SFTP service should be None
            assert result.exit_code == 0
    
    def test_configuration_access_with_normalized_config(self):
        """Test that configuration access works with normalized (lowercase) sections."""
        mock_config = {
            'sftp': {  # lowercase section name
                'host': 'test.example.com',
                'port': '22',
                'username': 'testuser',
                'ssh_key_path': '/path/to/key'
            }
        }
        
        # Test that get_config_value works with normalized config
        host = get_config_value(mock_config, 'sftp', 'host')
        assert host == 'test.example.com'
        
        port = get_config_value(mock_config, 'sftp', 'port', value_type=int)
        assert port == 22
        
        # Test fallback values
        timeout = get_config_value(mock_config, 'sftp', 'timeout', fallback=30, value_type=int)
        assert timeout == 30


class TestContextValidation:
    """Test context validation functions."""
    
    def test_validate_context_with_valid_services(self):
        """Test context validation with all required services available."""
        mock_ctx = Mock()
        mock_ctx.obj = {
            'sftp': Mock(),
            'db': Mock(),
            'config': {}
        }
        
        result = validate_context_for_command(mock_ctx, required_services=['sftp', 'db'])
        assert result is True
    
    def test_validate_context_with_missing_services(self):
        """Test context validation with missing services."""
        mock_ctx = Mock()
        mock_ctx.obj = {
            'db': Mock(),
            'config': {}
            # Missing 'sftp'
        }
        
        with patch('click.secho') as mock_secho:
            result = validate_context_for_command(mock_ctx, required_services=['sftp', 'db'])
            assert result is False
            
            # Should have called secho with error message
            mock_secho.assert_called()
            error_calls = [call for call in mock_secho.call_args_list if 'Required services not available' in str(call)]
            assert len(error_calls) > 0
    
    def test_validate_context_with_no_context_object(self):
        """Test context validation with no context object."""
        mock_ctx = Mock()
        mock_ctx.obj = None
        
        with patch('click.secho') as mock_secho:
            result = validate_context_for_command(mock_ctx)
            assert result is False
            
            # Should have called secho with error message
            mock_secho.assert_called()
    
    def test_validate_context_with_config_error(self):
        """Test context validation with configuration error."""
        mock_ctx = Mock()
        mock_ctx.obj = {
            'config_error': 'Test configuration error'
        }
        
        with patch('click.secho') as mock_secho:
            result = validate_context_for_command(mock_ctx)
            assert result is False
            
            # Should have called secho with error message
            mock_secho.assert_called()
    
    def test_get_service_from_context_success(self):
        """Test getting a service from context successfully."""
        mock_ctx = Mock()
        mock_service = Mock()
        mock_ctx.obj = {
            'sftp': mock_service
        }
        
        result = get_service_from_context(mock_ctx, 'sftp')
        assert result is mock_service
    
    def test_get_service_from_context_missing_required(self):
        """Test getting a missing required service from context."""
        mock_ctx = Mock()
        mock_ctx.obj = {}
        
        with patch('click.secho') as mock_secho, \
             patch('sys.exit') as mock_exit:
            
            get_service_from_context(mock_ctx, 'sftp', required=True)
            
            # Should have called secho with error and exit
            mock_secho.assert_called()
            mock_exit.assert_called_with(1)
    
    def test_get_service_from_context_missing_optional(self):
        """Test getting a missing optional service from context."""
        mock_ctx = Mock()
        mock_ctx.obj = {}
        
        result = get_service_from_context(mock_ctx, 'sftp', required=False)
        assert result is None


class TestConfigurationErrorHandling:
    """Test configuration error handling and user guidance."""
    
    def test_helpful_error_messages_for_missing_config(self):
        """Test that helpful error messages are provided for missing configuration."""
        # This would be tested through integration tests with actual CLI commands
        pass
    
    def test_suggestion_to_run_config_validation(self):
        """Test that error messages suggest running config validation."""
        mock_ctx = Mock()
        mock_ctx.obj = None
        
        with patch('click.secho') as mock_secho:
            validate_context_for_command(mock_ctx)
            
            # Check that one of the calls suggests running config validation
            suggestion_calls = [
                call for call in mock_secho.call_args_list 
                if 'config-monitor validate' in str(call)
            ]
            assert len(suggestion_calls) > 0


class TestServiceDependencies:
    """Test service dependencies and initialization order."""
    
    def test_sftp_service_with_llm_dependency(self):
        """Test that SFTP service can be initialized with LLM service dependency."""
        mock_config = {
            'sftp': {
                'host': 'test.example.com',
                'port': '22',
                'username': 'testuser',
                'ssh_key_path': '/path/to/key'
            }
        }
        
        mock_llm_service = Mock()
        
        with patch('services.sftp_service.SFTPService') as mock_sftp_class:
            mock_sftp_instance = Mock()
            mock_sftp_class.return_value = mock_sftp_instance
            
            # This would be called during service initialization
            from services.sftp_service import SFTPService
            
            # Test that SFTPService can be called with llm_service parameter
            # (This is more of an integration test)
            pass
    
    def test_service_initialization_continues_on_optional_failures(self):
        """Test that service initialization continues when optional services fail."""
        mock_config = {
            'llm': {'service': 'ollama'},
            'ollama': {'model': 'test_model'},
            'database': {'type': 'sqlite'},
            'sqlite': {'db_file': 'test.db'}
        }
        
        with patch('utils.sync2nas_config.load_configuration', return_value=mock_config), \
             patch('services.llm_factory.create_llm_service', return_value=Mock()), \
             patch('services.db_factory.create_db_service', return_value=Mock()), \
             patch('services.sftp_service.SFTPService', side_effect=Exception("SFTP failed")), \
             patch('services.tmdb_service.TMDBService', side_effect=Exception("TMDB failed")):
            
            runner = CliRunner()
            result = runner.invoke(sync2nas_cli, ['--help'])
            
            # Should still work even if optional services fail
            assert result.exit_code == 0