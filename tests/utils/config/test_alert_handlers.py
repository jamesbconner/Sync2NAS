"""
Tests for configuration alert handlers.
"""

import pytest
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from utils.config.alert_handlers import (
    AlertHandler, ConsoleAlertHandler, FileAlertHandler, EmailAlertHandler,
    WebhookAlertHandler, AlertManager, create_default_alert_manager,
    create_email_alert_handler_from_env
)


class TestAlertHandler:
    """Test the base AlertHandler class."""
    
    def test_base_handler_not_implemented(self):
        """Test that base handler raises NotImplementedError."""
        handler = AlertHandler("test")
        
        with pytest.raises(NotImplementedError):
            handler._handle_alert_impl("test_alert", {})
    
    def test_handler_enabled_disabled(self):
        """Test enabling/disabling handlers."""
        handler = AlertHandler("test")
        handler._handle_alert_impl = Mock()
        
        # Handler is enabled by default
        assert handler.enabled is True
        
        # Should call implementation when enabled
        handler.handle_alert("test_alert", {"key": "value"})
        handler._handle_alert_impl.assert_called_once_with("test_alert", {"key": "value"})
        
        # Should not call implementation when disabled
        handler._handle_alert_impl.reset_mock()
        handler.enabled = False
        handler.handle_alert("test_alert", {"key": "value"})
        handler._handle_alert_impl.assert_not_called()
    
    def test_handler_error_handling(self):
        """Test error handling in alert handlers."""
        handler = AlertHandler("test")
        handler._handle_alert_impl = Mock(side_effect=Exception("Test error"))
        
        # Should not raise exception, but log error
        with patch('utils.config.alert_handlers.logger') as mock_logger:
            handler.handle_alert("test_alert", {})
            mock_logger.error.assert_called_once()


class TestConsoleAlertHandler:
    """Test the ConsoleAlertHandler class."""
    
    def test_console_handler_creation(self):
        """Test creating console alert handler."""
        handler = ConsoleAlertHandler(use_colors=True)
        assert handler.name == "console"
        assert handler.use_colors is True
        
        handler_no_colors = ConsoleAlertHandler(use_colors=False)
        assert handler_no_colors.use_colors is False
    
    @patch('builtins.print')
    def test_validation_failure_alert(self, mock_print):
        """Test console output for validation failure alerts."""
        handler = ConsoleAlertHandler(use_colors=False)
        
        alert_details = {
            "alert_type": "validation_failure",
            "service": "openai",
            "timestamp": "2024-01-01T12:00:00",
            "failure_count": 3,
            "window_minutes": 5,
            "errors": [
                {"section": "openai", "key": "api_key", "message": "API key is missing"},
                {"section": "openai", "key": "model", "message": "Model is invalid"}
            ]
        }
        
        handler._handle_alert_impl("Configuration validation failures", alert_details)
        
        # Check that print was called multiple times
        assert mock_print.call_count > 5
        
        # Check some expected content
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Configuration validation failures" in call for call in print_calls)
        assert any("openai" in call for call in print_calls)
        assert any("3 in 5 minutes" in call for call in print_calls)
    
    @patch('builtins.print')
    def test_health_check_failure_alert(self, mock_print):
        """Test console output for health check failure alerts."""
        handler = ConsoleAlertHandler(use_colors=False)
        
        alert_details = {
            "alert_type": "health_check_failure",
            "service": "ollama",
            "timestamp": "2024-01-01T12:00:00",
            "failure_count": 2,
            "window_minutes": 3,
            "error_message": "Connection timeout",
            "health_details": {"host": "localhost:11434", "timeout": 10}
        }
        
        handler._handle_alert_impl("LLM service health check failures", alert_details)
        
        # Check that print was called
        assert mock_print.call_count > 3
        
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("health check failures" in call.lower() for call in print_calls)
        assert any("Connection timeout" in call for call in print_calls)
    
    @patch('builtins.print')
    def test_colored_output(self, mock_print):
        """Test colored console output."""
        handler = ConsoleAlertHandler(use_colors=True)
        
        alert_details = {
            "alert_type": "validation_failure",
            "service": "openai",
            "timestamp": "2024-01-01T12:00:00",
            "failure_count": 1,
            "window_minutes": 1,
            "errors": []
        }
        
        handler._handle_alert_impl("Test Alert", alert_details)
        
        # Check that ANSI color codes are used
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("\033[" in call for call in print_calls)  # ANSI escape codes


class TestFileAlertHandler:
    """Test the FileAlertHandler class."""
    
    def test_file_handler_creation(self):
        """Test creating file alert handler."""
        with tempfile.TemporaryDirectory() as temp_dir:
            alert_file = Path(temp_dir) / "alerts.log"
            handler = FileAlertHandler(str(alert_file), max_file_size_mb=5)
            
            assert handler.name == "file"
            assert handler.alert_file == alert_file
            assert handler.max_file_size_bytes == 5 * 1024 * 1024
    
    def test_file_alert_writing(self):
        """Test writing alerts to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            alert_file = Path(temp_dir) / "alerts.log"
            handler = FileAlertHandler(str(alert_file))
            
            alert_details = {
                "alert_type": "validation_failure",
                "service": "openai",
                "timestamp": "2024-01-01T12:00:00",
                "failure_count": 2,
                "window_minutes": 5
            }
            
            handler._handle_alert_impl("Test Alert", alert_details)
            
            # Check file was created and contains alert
            assert alert_file.exists()
            
            with open(alert_file, 'r') as f:
                content = f.read()
                alert_record = json.loads(content.strip())
                
                assert alert_record["alert_type"] == "Test Alert"
                assert alert_record["details"]["service"] == "openai"
                assert alert_record["details"]["failure_count"] == 2
    
    def test_file_rotation(self):
        """Test file rotation when size limit is exceeded."""
        with tempfile.TemporaryDirectory() as temp_dir:
            alert_file = Path(temp_dir) / "alerts.log"
            handler = FileAlertHandler(str(alert_file), max_file_size_mb=0.001)  # Very small limit
            
            # Write initial content to exceed size limit
            with open(alert_file, 'w') as f:
                f.write("x" * 2000)  # Write more than 0.001 MB
            
            alert_details = {"test": "data"}
            handler._handle_alert_impl("Test Alert", alert_details)
            
            # Check that backup file was created
            backup_files = list(Path(temp_dir).glob("alerts.*.log"))
            assert len(backup_files) == 1
            
            # Check that new alert file contains only the new alert
            with open(alert_file, 'r') as f:
                content = f.read()
                assert "Test Alert" in content
                assert len(content) < 1000  # Much smaller than original
    
    def test_directory_creation(self):
        """Test that handler creates directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_dir = Path(temp_dir) / "nested" / "alerts"
            alert_file = nested_dir / "alerts.log"
            
            # Directory doesn't exist initially
            assert not nested_dir.exists()
            
            handler = FileAlertHandler(str(alert_file))
            
            # Directory should be created
            assert nested_dir.exists()


class TestEmailAlertHandler:
    """Test the EmailAlertHandler class."""
    
    def test_email_handler_creation(self):
        """Test creating email alert handler."""
        handler = EmailAlertHandler(
            smtp_host="smtp.example.com",
            smtp_port=587,
            username="user@example.com",
            password="password",
            from_email="alerts@example.com",
            to_emails=["admin@example.com", "dev@example.com"],
            use_tls=True
        )
        
        assert handler.name == "email"
        assert handler.smtp_host == "smtp.example.com"
        assert handler.smtp_port == 587
        assert handler.to_emails == ["admin@example.com", "dev@example.com"]
        assert handler.use_tls is True
    
    @patch('smtplib.SMTP')
    def test_email_sending(self, mock_smtp):
        """Test sending email alerts."""
        # Mock SMTP server
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        handler = EmailAlertHandler(
            smtp_host="smtp.example.com",
            smtp_port=587,
            username="user@example.com",
            password="password",
            from_email="alerts@example.com",
            to_emails=["admin@example.com"],
            use_tls=True
        )
        
        alert_details = {
            "alert_type": "validation_failure",
            "service": "openai",
            "timestamp": "2024-01-01T12:00:00",
            "failure_count": 3,
            "window_minutes": 5,
            "errors": [{"section": "openai", "key": "api_key", "message": "Missing API key"}]
        }
        
        handler._handle_alert_impl("Configuration Alert", alert_details)
        
        # Check SMTP operations
        mock_smtp.assert_called_once_with("smtp.example.com", 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user@example.com", "password")
        mock_server.send_message.assert_called_once()
        
        # Check email content
        sent_message = mock_server.send_message.call_args[0][0]
        assert sent_message["Subject"] == "Sync2NAS Alert: Configuration Alert"
        assert sent_message["From"] == "alerts@example.com"
        assert "admin@example.com" in sent_message["To"]
    
    def test_email_body_formatting(self):
        """Test email body formatting for different alert types."""
        handler = EmailAlertHandler(
            smtp_host="smtp.example.com",
            smtp_port=587,
            username="user@example.com",
            password="password",
            from_email="alerts@example.com",
            to_emails=["admin@example.com"]
        )
        
        # Test validation failure formatting
        validation_details = {
            "alert_type": "validation_failure",
            "service": "openai",
            "timestamp": "2024-01-01T12:00:00",
            "failure_count": 2,
            "window_minutes": 5,
            "errors": [
                {"section": "openai", "key": "api_key", "message": "API key missing"},
                {"section": "openai", "key": None, "message": "Section invalid"}
            ]
        }
        
        body = handler._format_email_body("Validation Alert", validation_details)
        
        assert "Validation Alert" in body
        assert "openai" in body
        assert "2 in 5 minutes" in body
        assert "API key missing" in body
        assert "[openai].api_key" in body
        assert "[openai]:" in body  # For error without key
        
        # Test health check failure formatting
        health_details = {
            "alert_type": "health_check_failure",
            "service": "ollama",
            "timestamp": "2024-01-01T12:00:00",
            "failure_count": 3,
            "window_minutes": 2,
            "error_message": "Connection timeout",
            "health_details": {"host": "localhost:11434", "timeout": 10}
        }
        
        body = handler._format_email_body("Health Check Alert", health_details)
        
        assert "Health Check Alert" in body
        assert "ollama" in body
        assert "3 in 2 minutes" in body
        assert "Connection timeout" in body
        assert "host: localhost:11434" in body


class TestWebhookAlertHandler:
    """Test the WebhookAlertHandler class."""
    
    def test_webhook_handler_creation(self):
        """Test creating webhook alert handler."""
        handler = WebhookAlertHandler("https://hooks.example.com/webhook", timeout=15)
        
        assert handler.name == "webhook"
        assert handler.webhook_url == "https://hooks.example.com/webhook"
        assert handler.timeout == 15
    
    @patch('httpx.Client')
    def test_webhook_sending(self, mock_client):
        """Test sending webhook alerts."""
        # Mock HTTP client
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_http_client = MagicMock()
        mock_http_client.post.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_http_client
        
        handler = WebhookAlertHandler("https://hooks.example.com/webhook")
        
        alert_details = {
            "alert_type": "validation_failure",
            "service": "openai",
            "timestamp": "2024-01-01T12:00:00",
            "failure_count": 2
        }
        
        handler._handle_alert_impl("Test Alert", alert_details)
        
        # Check HTTP request
        mock_http_client.post.assert_called_once()
        call_args = mock_http_client.post.call_args
        
        assert call_args[0][0] == "https://hooks.example.com/webhook"
        
        payload = call_args[1]["json"]
        assert payload["alert_type"] == "Test Alert"
        assert payload["service"] == "openai"
        assert payload["details"]["failure_count"] == 2
    
    @patch('httpx.Client')
    def test_webhook_error_handling(self, mock_client):
        """Test webhook error handling."""
        # Mock HTTP client to raise exception
        mock_http_client = MagicMock()
        mock_http_client.post.side_effect = Exception("Network error")
        mock_client.return_value.__enter__.return_value = mock_http_client
        
        handler = WebhookAlertHandler("https://hooks.example.com/webhook")
        
        # Should not raise exception
        with patch('utils.config.alert_handlers.logger') as mock_logger:
            handler._handle_alert_impl("Test Alert", {})
            mock_logger.error.assert_called_once()


class TestAlertManager:
    """Test the AlertManager class."""
    
    def test_alert_manager_creation(self):
        """Test creating alert manager."""
        manager = AlertManager()
        assert len(manager.handlers) == 0
        assert manager.get_handler_names() == []
    
    def test_adding_handlers(self):
        """Test adding alert handlers."""
        manager = AlertManager()
        
        console_handler = ConsoleAlertHandler()
        file_handler = FileAlertHandler("/tmp/alerts.log")
        
        manager.add_handler(console_handler)
        manager.add_handler(file_handler)
        
        assert len(manager.handlers) == 2
        assert "console" in manager.get_handler_names()
        assert "file" in manager.get_handler_names()
    
    def test_removing_handlers(self):
        """Test removing alert handlers."""
        manager = AlertManager()
        
        console_handler = ConsoleAlertHandler()
        manager.add_handler(console_handler)
        
        assert len(manager.handlers) == 1
        
        # Remove existing handler
        removed = manager.remove_handler("console")
        assert removed is True
        assert len(manager.handlers) == 0
        
        # Try to remove non-existent handler
        removed = manager.remove_handler("nonexistent")
        assert removed is False
    
    def test_handling_alerts(self):
        """Test handling alerts through manager."""
        manager = AlertManager()
        
        # Mock handlers
        handler1 = Mock()
        handler1.name = "handler1"
        handler2 = Mock()
        handler2.name = "handler2"
        
        manager.add_handler(handler1)
        manager.add_handler(handler2)
        
        alert_details = {"test": "data"}
        manager.handle_alert("Test Alert", alert_details)
        
        # Both handlers should be called
        handler1.handle_alert.assert_called_once_with("Test Alert", alert_details)
        handler2.handle_alert.assert_called_once_with("Test Alert", alert_details)
    
    def test_no_handlers_warning(self):
        """Test warning when no handlers are configured."""
        manager = AlertManager()
        
        with patch('utils.config.alert_handlers.logger') as mock_logger:
            manager.handle_alert("Test Alert", {})
            mock_logger.warning.assert_called_once_with("No alert handlers configured")


class TestAlertManagerCreation:
    """Test alert manager creation functions."""
    
    @patch('utils.config.alert_handlers.Path')
    def test_create_default_alert_manager(self, mock_path):
        """Test creating default alert manager."""
        # Mock successful directory creation
        mock_path.return_value.mkdir.return_value = None
        
        manager = create_default_alert_manager()
        
        assert len(manager.handlers) >= 1  # At least console handler
        assert "console" in manager.get_handler_names()
    
    @patch.dict(os.environ, {
        'SYNC2NAS_ALERT_SMTP_HOST': 'smtp.example.com',
        'SYNC2NAS_ALERT_SMTP_PORT': '587',
        'SYNC2NAS_ALERT_SMTP_USERNAME': 'user@example.com',
        'SYNC2NAS_ALERT_SMTP_PASSWORD': 'password',
        'SYNC2NAS_ALERT_FROM_EMAIL': 'alerts@example.com',
        'SYNC2NAS_ALERT_TO_EMAILS': 'admin@example.com,dev@example.com',
        'SYNC2NAS_ALERT_USE_TLS': 'true'
    })
    def test_create_email_handler_from_env(self):
        """Test creating email handler from environment variables."""
        handler = create_email_alert_handler_from_env()
        
        assert handler is not None
        assert isinstance(handler, EmailAlertHandler)
        assert handler.smtp_host == "smtp.example.com"
        assert handler.smtp_port == 587
        assert handler.username == "user@example.com"
        assert handler.from_email == "alerts@example.com"
        assert handler.to_emails == ["admin@example.com", "dev@example.com"]
        assert handler.use_tls is True
    
    def test_create_email_handler_missing_env(self):
        """Test creating email handler with missing environment variables."""
        # Clear any existing environment variables
        env_vars = [
            'SYNC2NAS_ALERT_SMTP_HOST',
            'SYNC2NAS_ALERT_SMTP_PORT',
            'SYNC2NAS_ALERT_SMTP_USERNAME',
            'SYNC2NAS_ALERT_SMTP_PASSWORD',
            'SYNC2NAS_ALERT_FROM_EMAIL',
            'SYNC2NAS_ALERT_TO_EMAILS'
        ]
        
        with patch.dict(os.environ, {}, clear=True):
            handler = create_email_alert_handler_from_env()
            assert handler is None
    
    @patch.dict(os.environ, {
        'SYNC2NAS_ALERT_SMTP_HOST': 'smtp.example.com',
        'SYNC2NAS_ALERT_SMTP_PORT': 'invalid_port',  # Invalid port
        'SYNC2NAS_ALERT_SMTP_USERNAME': 'user@example.com',
        'SYNC2NAS_ALERT_SMTP_PASSWORD': 'password',
        'SYNC2NAS_ALERT_FROM_EMAIL': 'alerts@example.com',
        'SYNC2NAS_ALERT_TO_EMAILS': 'admin@example.com'
    })
    def test_create_email_handler_invalid_env(self):
        """Test creating email handler with invalid environment variables."""
        with patch('utils.config.alert_handlers.logger') as mock_logger:
            handler = create_email_alert_handler_from_env()
            assert handler is None
            mock_logger.error.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])