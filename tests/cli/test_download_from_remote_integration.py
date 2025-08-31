"""
Integration tests for the download-from-remote CLI command.

This module tests the download-from-remote command with various service
availability scenarios to ensure proper error handling and user guidance.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import click
from click.testing import CliRunner

from cli.download_from_remote import download_from_remote


class TestDownloadFromRemoteIntegration:
    """Integration tests for download-from-remote command."""
    
    def test_command_with_all_services_available(self):
        """Test download-from-remote command with all required services available."""
        # Create mock context with all required services
        mock_ctx = Mock()
        mock_ctx.obj = {
            'sftp': Mock(),
            'db': Mock(),
            'config': {
                'sftp': {'paths': '/test/path'},
                'transfers': {'incoming': '/test/incoming'}
            },
            'dry_run': True
        }
        
        # Mock the SFTP context manager
        mock_sftp = mock_ctx.obj['sftp']
        mock_sftp.__enter__ = Mock(return_value=mock_sftp)
        mock_sftp.__exit__ = Mock(return_value=None)
        
        with patch('utils.sync2nas_config.parse_sftp_paths', return_value=['/test/path']), \
             patch('utils.sync2nas_config.get_config_value') as mock_get_config, \
             patch('services.hashing_service.HashingService'), \
             patch('cli.download_from_remote.downloader') as mock_downloader:
            
            # Configure get_config_value to return appropriate values
            def get_config_side_effect(config, section, key, fallback=None, value_type=str):
                if section == 'transfers' and key == 'incoming':
                    return '/test/incoming'
                return fallback
            
            mock_get_config.side_effect = get_config_side_effect
            
            runner = CliRunner()
            result = runner.invoke(download_from_remote, ['--max-workers', '1'], obj=mock_ctx.obj)
            
            assert result.exit_code == 0
            mock_downloader.assert_called_once()
    
    def test_command_with_missing_sftp_service(self):
        """Test download-from-remote command with missing SFTP service."""
        mock_ctx = Mock()
        mock_ctx.obj = {
            'sftp': None,  # Missing SFTP service
            'db': Mock(),
            'config': {},
            'dry_run': True
        }
        
        runner = CliRunner()
        result = runner.invoke(download_from_remote, ['--max-workers', '1'], obj=mock_ctx.obj)
        
        # Should exit with error
        assert result.exit_code == 0  # Command returns normally but prints error
        assert 'Required services unavailable' in result.output
        assert 'config-monitor validate' in result.output
    
    def test_command_with_missing_database_service(self):
        """Test download-from-remote command with missing database service."""
        mock_ctx = Mock()
        mock_ctx.obj = {
            'sftp': Mock(),
            'db': None,  # Missing database service
            'config': {},
            'dry_run': True
        }
        
        runner = CliRunner()
        result = runner.invoke(download_from_remote, ['--max-workers', '1'], obj=mock_ctx.obj)
        
        # Should exit with error
        assert result.exit_code == 0  # Command returns normally but prints error
        assert 'Required services unavailable' in result.output
        assert 'config-monitor validate' in result.output
    
    def test_command_with_no_context_object(self):
        """Test download-from-remote command with no context object."""
        runner = CliRunner()
        result = runner.invoke(download_from_remote, ['--max-workers', '1'])
        
        # Should exit with error
        assert result.exit_code == 0  # Command returns normally but prints error
        assert 'No context available' in result.output
        assert 'config-monitor validate' in result.output
    
    def test_command_with_configuration_error(self):
        """Test download-from-remote command with configuration error in context."""
        mock_ctx = Mock()
        mock_ctx.obj = {
            'config_error': 'Test configuration error',
            'sftp': None,
            'db': None,
            'config': None
        }
        
        runner = CliRunner()
        result = runner.invoke(download_from_remote, ['--max-workers', '1'], obj=mock_ctx.obj)
        
        # Should exit with error
        assert result.exit_code == 0  # Command returns normally but prints error
        assert ('Configuration error' in result.output or 
                'No context available' in result.output or 
                'Required services unavailable' in result.output)
    
    def test_command_help_works_without_services(self):
        """Test that command help works even without services initialized."""
        runner = CliRunner()
        result = runner.invoke(download_from_remote, ['--help'])
        
        # Help should always work
        assert result.exit_code == 0
        assert 'Download new files or directories' in result.output
        assert '--max-workers' in result.output
    
    def test_command_with_sftp_connection_failure(self):
        """Test download-from-remote command when SFTP connection fails."""
        mock_ctx = Mock()
        mock_sftp = Mock()
        mock_sftp.__enter__ = Mock(side_effect=Exception("Connection failed"))
        mock_sftp.__exit__ = Mock(return_value=None)
        
        mock_ctx.obj = {
            'sftp': mock_sftp,
            'db': Mock(),
            'config': {
                'sftp': {'paths': '/test/path'},
                'transfers': {'incoming': '/test/incoming'}
            },
            'dry_run': True
        }
        
        with patch('utils.sync2nas_config.parse_sftp_paths', return_value=['/test/path']), \
             patch('utils.sync2nas_config.get_config_value', return_value='/test/incoming'), \
             patch('services.hashing_service.HashingService'):
            
            runner = CliRunner()
            result = runner.invoke(download_from_remote, ['--max-workers', '1'], obj=mock_ctx.obj)
            
            # Should handle the connection error gracefully
            # The exact behavior depends on how the SFTP context manager handles errors
            assert result.exit_code != 0 or 'Connection failed' in result.output
    
    def test_command_with_missing_sftp_paths_config(self):
        """Test download-from-remote command with missing SFTP paths configuration."""
        mock_ctx = Mock()
        mock_ctx.obj = {
            'sftp': Mock(),
            'db': Mock(),
            'config': {
                # Missing SFTP paths configuration
                'transfers': {'incoming': '/test/incoming'}
            },
            'dry_run': True
        }
        
        with patch('utils.sync2nas_config.parse_sftp_paths', return_value=[]), \
             patch('utils.sync2nas_config.get_config_value', return_value='/test/incoming'):
            
            runner = CliRunner()
            result = runner.invoke(download_from_remote, ['--max-workers', '1'], obj=mock_ctx.obj)
            
            # Should exit with error about missing SFTP paths
            assert result.exit_code == 1
            assert 'No SFTP paths defined' in result.output


class TestCommandValidationHelpers:
    """Test the validation helper functions used by CLI commands."""
    
    def test_validate_context_integration(self):
        """Test context validation integration with actual CLI command."""
        from cli.main import validate_context_for_command
        
        # Test with valid context
        mock_ctx = Mock()
        mock_ctx.obj = {
            'sftp': Mock(),
            'db': Mock(),
            'config': {}
        }
        
        result = validate_context_for_command(mock_ctx, required_services=['sftp', 'db'])
        assert result is True
        
        # Test with invalid context
        mock_ctx.obj = {
            'sftp': None,
            'db': Mock(),
            'config': {}
        }
        
        with patch('click.secho'):
            result = validate_context_for_command(mock_ctx, required_services=['sftp', 'db'])
            assert result is False
    
    def test_service_validation_error_messages(self):
        """Test that service validation provides helpful error messages."""
        from cli.main import validate_context_for_command
        
        mock_ctx = Mock()
        mock_ctx.obj = {
            'db': Mock(),
            'config': {}
            # Missing SFTP service
        }
        
        with patch('click.secho') as mock_secho:
            validate_context_for_command(mock_ctx, required_services=['sftp', 'db'])
            
            # Check that helpful error messages were displayed
            error_calls = [str(call) for call in mock_secho.call_args_list]
            
            # Should mention missing services
            assert any('Required services not available' in call for call in error_calls)
            
            # Should suggest running config validation
            assert any('config-monitor validate' in call for call in error_calls)


class TestServiceInitializationRegression:
    """Regression tests to ensure service initialization doesn't break."""
    
    def test_normalized_config_access_regression(self):
        """Test that normalized configuration access doesn't regress."""
        # This test ensures that the fix for uppercase/lowercase config access
        # doesn't break in the future
        
        mock_config = {
            'sftp': {  # lowercase section (normalized)
                'host': 'test.example.com',
                'port': '22',
                'username': 'testuser',
                'ssh_key_path': '/path/to/key'
            }
        }
        
        from utils.sync2nas_config import get_config_value
        
        # These should all work with normalized config
        assert get_config_value(mock_config, 'sftp', 'host') == 'test.example.com'
        assert get_config_value(mock_config, 'sftp', 'port', value_type=int) == 22
        assert get_config_value(mock_config, 'sftp', 'username') == 'testuser'
        assert get_config_value(mock_config, 'sftp', 'ssh_key_path') == '/path/to/key'
        
        # Test with fallback values
        assert get_config_value(mock_config, 'sftp', 'timeout', fallback=30, value_type=int) == 30
    
    def test_service_initialization_with_missing_sections(self):
        """Test service initialization gracefully handles missing config sections."""
        mock_config = {}  # Empty configuration
        
        from utils.sync2nas_config import get_config_value
        
        # Should not crash, should return fallback values
        assert get_config_value(mock_config, 'sftp', 'host', fallback='localhost') == 'localhost'
        assert get_config_value(mock_config, 'sftp', 'port', fallback=22, value_type=int) == 22
    
    def test_cli_command_discovery_still_works(self):
        """Test that CLI command discovery still works after changes."""
        from cli.main import sync2nas_cli
        
        # The main CLI should have commands registered
        assert len(sync2nas_cli.commands) > 0
        
        # download-from-remote should be one of them
        assert 'download-from-remote' in sync2nas_cli.commands