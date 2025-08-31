"""
Tests for configuration monitoring CLI commands.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner
from datetime import datetime

from cli.config_monitor import (
    config_monitor_group, health_check, validate_config, 
    show_metrics, show_events, setup_alerts
)
from utils.config.validation_models import ValidationResult, ValidationError, ErrorCode, HealthCheckResult
from utils.config.config_monitor import ConfigEvent


class TestHealthCheckCommand:
    """Test the health check CLI command."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    @patch('cli.config_monitor.ConfigHealthChecker')
    @patch('cli.config_monitor.load_configuration')
    def test_health_check_all_services(self, mock_load_config, mock_health_checker):
        """Test health check for all services."""
        # Mock configuration
        mock_config = {"llm": {"service": "openai"}}
        mock_load_config.return_value = mock_config
        
        # Mock health checker
        mock_checker_instance = Mock()
        mock_health_checker.return_value = mock_checker_instance
        
        # Mock health check results
        health_results = [
            HealthCheckResult(
                service="openai",
                is_healthy=True,
                response_time_ms=150.0,
                error_message=None,
                details={"model": "gpt-4", "status_code": 200}
            )
        ]
        mock_checker_instance.check_llm_health_sync.return_value = health_results
        
        # Run command
        result = self.runner.invoke(health_check, [])
        
        assert result.exit_code == 0
        assert "Checking health for all configured LLM services" in result.output
        mock_checker_instance.check_llm_health_sync.assert_called_once_with(mock_config)
    
    @patch('cli.config_monitor.ConfigHealthChecker')
    @patch('cli.config_monitor.load_configuration')
    def test_health_check_specific_service(self, mock_load_config, mock_health_checker):
        """Test health check for specific service."""
        mock_config = {"openai": {"api_key": "test-key"}}
        mock_load_config.return_value = mock_config
        
        mock_checker_instance = Mock()
        mock_health_checker.return_value = mock_checker_instance
        
        health_result = HealthCheckResult(
            service="openai",
            is_healthy=False,
            response_time_ms=None,
            error_message="Invalid API key",
            details={"error_code": "AUTHENTICATION_FAILED"}
        )
        mock_checker_instance.check_service_health_sync.return_value = health_result
        
        # Run command with specific service
        result = self.runner.invoke(health_check, ["--service", "openai"])
        
        assert result.exit_code == 0
        assert "Checking health for openai" in result.output
        mock_checker_instance.check_service_health_sync.assert_called_once_with("openai", mock_config)
    
    @patch('cli.config_monitor.ConfigHealthChecker')
    @patch('cli.config_monitor.load_configuration')
    def test_health_check_json_output(self, mock_load_config, mock_health_checker):
        """Test health check with JSON output."""
        mock_config = {}
        mock_load_config.return_value = mock_config
        
        mock_checker_instance = Mock()
        mock_health_checker.return_value = mock_checker_instance
        
        health_results = [
            HealthCheckResult(
                service="ollama",
                is_healthy=True,
                response_time_ms=250.0,
                error_message=None,
                details={"host": "localhost:11434"}
            )
        ]
        mock_checker_instance.check_llm_health_sync.return_value = health_results
        
        # Run command with JSON output
        result = self.runner.invoke(health_check, ["--json"])
        
        assert result.exit_code == 0
        
        # Parse JSON output
        output_data = json.loads(result.output)
        assert len(output_data) == 1
        assert output_data[0]["service"] == "ollama"
        assert output_data[0]["healthy"] is True
        assert output_data[0]["response_time_ms"] == 250.0
    
    @patch('cli.config_monitor.ConfigHealthChecker')
    @patch('cli.config_monitor.load_configuration')
    def test_health_check_error(self, mock_load_config, mock_health_checker):
        """Test health check with error."""
        mock_load_config.side_effect = Exception("Configuration error")
        
        # Run command
        result = self.runner.invoke(health_check, [])
        
        assert result.exit_code == 1
        assert "Error performing health check" in result.output
    
    @patch('cli.config_monitor.ConfigHealthChecker')
    @patch('cli.config_monitor.load_configuration')
    def test_health_check_error_json(self, mock_load_config, mock_health_checker):
        """Test health check error with JSON output."""
        mock_load_config.side_effect = Exception("Configuration error")
        
        # Run command with JSON output
        result = self.runner.invoke(health_check, ["--json"])
        
        assert result.exit_code == 1
        
        # Parse JSON error output
        output_data = json.loads(result.output)
        assert "error" in output_data
        assert "Configuration error" in output_data["error"]


class TestValidateConfigCommand:
    """Test the validate config CLI command."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    @patch('cli.config_monitor.ConfigValidator')
    @patch('cli.config_monitor.load_configuration')
    def test_validate_all_config(self, mock_load_config, mock_validator):
        """Test validating all configuration."""
        mock_config = {"llm": {"service": "openai"}}
        mock_load_config.return_value = mock_config
        
        mock_validator_instance = Mock()
        mock_validator.return_value = mock_validator_instance
        
        # Mock successful validation
        validation_result = ValidationResult(is_valid=True, errors=[], warnings=[], suggestions=[])
        mock_validator_instance.validate_llm_config.return_value = validation_result
        
        # Run command
        result = self.runner.invoke(validate_config, [])
        
        assert result.exit_code == 0
        assert "Validating LLM configuration" in result.output
        assert "Configuration validation passed" in result.output
        mock_validator_instance.validate_llm_config.assert_called_once_with(mock_config)
    
    @patch('cli.config_monitor.ConfigValidator')
    @patch('cli.config_monitor.load_configuration')
    def test_validate_specific_service(self, mock_load_config, mock_validator):
        """Test validating specific service."""
        mock_config = {"openai": {"api_key": "test-key"}}
        mock_load_config.return_value = mock_config
        
        mock_validator_instance = Mock()
        mock_validator.return_value = mock_validator_instance
        
        # Mock validation with errors
        validation_result = ValidationResult(is_valid=False, errors=[], warnings=[], suggestions=[])
        validation_result.add_error(ValidationError(
            section="openai",
            key="model",
            message="Model is required",
            suggestion="Add model configuration",
            error_code=ErrorCode.MISSING_KEY
        ))
        mock_validator_instance.validate_service_config.return_value = validation_result
        
        # Run command
        result = self.runner.invoke(validate_config, ["--service", "openai"])
        
        assert result.exit_code == 0
        assert "Validating configuration for openai" in result.output
        assert "Configuration validation failed" in result.output
        assert "Model is required" in result.output
        mock_validator_instance.validate_service_config.assert_called_once_with("openai", mock_config)
    
    @patch('cli.config_monitor.ConfigValidator')
    @patch('cli.config_monitor.load_configuration')
    def test_validate_json_output(self, mock_load_config, mock_validator):
        """Test validation with JSON output."""
        mock_config = {}
        mock_load_config.return_value = mock_config
        
        mock_validator_instance = Mock()
        mock_validator.return_value = mock_validator_instance
        
        validation_result = ValidationResult(is_valid=False, errors=[], warnings=["Test warning"], suggestions=["Test suggestion"])
        validation_result.add_error(ValidationError(
            section="llm",
            key="service",
            message="Service is required",
            error_code=ErrorCode.MISSING_KEY
        ))
        mock_validator_instance.validate_llm_config.return_value = validation_result
        
        # Run command with JSON output
        result = self.runner.invoke(validate_config, ["--json"])
        
        assert result.exit_code == 0
        
        # Parse JSON output
        output_data = json.loads(result.output)
        assert output_data["valid"] is False
        assert len(output_data["errors"]) == 1
        assert output_data["errors"][0]["section"] == "llm"
        assert output_data["errors"][0]["key"] == "service"
        assert output_data["errors"][0]["message"] == "Service is required"
        assert output_data["warnings"] == ["Test warning"]
        assert output_data["suggestions"] == ["Test suggestion"]


class TestShowMetricsCommand:
    """Test the show metrics CLI command."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    @patch('cli.config_monitor.get_config_monitor')
    def test_show_metrics(self, mock_get_monitor):
        """Test showing metrics."""
        mock_monitor = Mock()
        mock_get_monitor.return_value = mock_monitor
        
        # Mock metrics summary
        metrics_summary = {
            "counters": {
                "config_loading_total[success=True]": 5,
                "config_validation_total[service=openai,success=False]": 2
            },
            "gauges": {
                "config_sections_loaded": 8,
                "config_validation_errors": 3
            },
            "histograms": {
                "config_loading_duration_ms": {
                    "count": 5,
                    "min": 50.0,
                    "max": 200.0,
                    "avg": 125.0,
                    "p50": 120.0,
                    "p95": 180.0,
                    "p99": 195.0
                }
            },
            "total_events": 25,
            "collection_period_hours": 24
        }
        mock_monitor.get_metrics_summary.return_value = metrics_summary
        
        # Run command
        result = self.runner.invoke(show_metrics, [])
        
        assert result.exit_code == 0
        assert "Configuration Monitoring Metrics" in result.output
        assert "config_loading_total" in result.output
        assert "Total Events: 25" in result.output
    
    @patch('cli.config_monitor.get_config_monitor')
    def test_show_metrics_json(self, mock_get_monitor):
        """Test showing metrics with JSON output."""
        mock_monitor = Mock()
        mock_get_monitor.return_value = mock_monitor
        
        metrics_summary = {
            "counters": {"test_counter": 10},
            "gauges": {"test_gauge": 42},
            "histograms": {},
            "total_events": 5,
            "collection_period_hours": 24
        }
        mock_monitor.get_metrics_summary.return_value = metrics_summary
        
        # Run command with JSON output
        result = self.runner.invoke(show_metrics, ["--json"])
        
        assert result.exit_code == 0
        
        # Parse JSON output
        output_data = json.loads(result.output)
        assert output_data["counters"]["test_counter"] == 10
        assert output_data["gauges"]["test_gauge"] == 42
        assert output_data["total_events"] == 5
    
    @patch('cli.config_monitor.initialize_config_monitor')
    @patch('cli.config_monitor.get_config_monitor')
    def test_show_metrics_with_reset(self, mock_get_monitor, mock_initialize):
        """Test showing metrics with reset."""
        mock_monitor = Mock()
        mock_get_monitor.return_value = mock_monitor
        mock_monitor.get_metrics_summary.return_value = {"counters": {}, "gauges": {}, "histograms": {}}
        
        # Run command with reset
        result = self.runner.invoke(show_metrics, ["--reset"])
        
        assert result.exit_code == 0
        assert "Metrics reset" in result.output
        mock_initialize.assert_called_once()


class TestShowEventsCommand:
    """Test the show events CLI command."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    @patch('cli.config_monitor.get_config_monitor')
    def test_show_events(self, mock_get_monitor):
        """Test showing events."""
        mock_monitor = Mock()
        mock_get_monitor.return_value = mock_monitor
        
        # Mock events
        events = [
            ConfigEvent(
                event_type="config_loading_complete",
                timestamp=datetime(2024, 1, 1, 12, 0, 0),
                service=None,
                success=True,
                duration_ms=150.0,
                details={"sections_loaded": 5}
            ),
            ConfigEvent(
                event_type="validation_complete",
                timestamp=datetime(2024, 1, 1, 12, 1, 0),
                service="openai",
                success=False,
                duration_ms=75.0,
                error_message="API key missing"
            )
        ]
        mock_monitor.get_recent_events.return_value = events
        
        # Run command
        result = self.runner.invoke(show_events, [])
        
        assert result.exit_code == 0
        assert "Recent Configuration Events" in result.output
        mock_monitor.get_recent_events.assert_called_once_with(limit=20, event_type=None)
    
    @patch('cli.config_monitor.get_config_monitor')
    def test_show_events_filtered(self, mock_get_monitor):
        """Test showing filtered events."""
        mock_monitor = Mock()
        mock_get_monitor.return_value = mock_monitor
        mock_monitor.get_recent_events.return_value = []
        
        # Run command with filters
        result = self.runner.invoke(show_events, ["--limit", "10", "--type", "validation_complete"])
        
        assert result.exit_code == 0
        mock_monitor.get_recent_events.assert_called_once_with(limit=10, event_type="validation_complete")
    
    @patch('cli.config_monitor.get_config_monitor')
    def test_show_events_json(self, mock_get_monitor):
        """Test showing events with JSON output."""
        mock_monitor = Mock()
        mock_get_monitor.return_value = mock_monitor
        
        events = [
            ConfigEvent(
                event_type="health_check_complete",
                timestamp=datetime(2024, 1, 1, 12, 0, 0),
                service="ollama",
                success=True,
                duration_ms=200.0,
                details={"model": "llama2:7b"}
            )
        ]
        mock_monitor.get_recent_events.return_value = events
        
        # Run command with JSON output
        result = self.runner.invoke(show_events, ["--json"])
        
        assert result.exit_code == 0
        
        # Parse JSON output
        output_data = json.loads(result.output)
        assert len(output_data) == 1
        assert output_data[0]["event_type"] == "health_check_complete"
        assert output_data[0]["service"] == "ollama"
        assert output_data[0]["success"] is True
        assert output_data[0]["duration_ms"] == 200.0
    
    @patch('cli.config_monitor.get_config_monitor')
    def test_show_events_empty(self, mock_get_monitor):
        """Test showing events when none exist."""
        mock_monitor = Mock()
        mock_get_monitor.return_value = mock_monitor
        mock_monitor.get_recent_events.return_value = []
        
        # Run command
        result = self.runner.invoke(show_events, [])
        
        assert result.exit_code == 0
        assert "No events found" in result.output


class TestSetupAlertsCommand:
    """Test the setup alerts CLI command."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    @patch('cli.config_monitor.create_email_alert_handler_from_env')
    @patch('cli.config_monitor.create_default_alert_manager')
    @patch('cli.config_monitor.get_config_monitor')
    def test_setup_alerts_basic(self, mock_get_monitor, mock_create_manager, mock_create_email):
        """Test basic alert setup."""
        mock_monitor = Mock()
        mock_get_monitor.return_value = mock_monitor
        
        mock_manager = Mock()
        mock_manager.get_handler_names.return_value = ["console", "file"]
        mock_create_manager.return_value = mock_manager
        
        mock_create_email.return_value = None  # No email handler
        
        # Run command
        result = self.runner.invoke(setup_alerts, [])
        
        assert result.exit_code == 0
        assert "Alert handlers configured: console, file" in result.output
        mock_monitor.add_alert_callback.assert_called_once_with(mock_manager.handle_alert)
    
    @patch('cli.config_monitor.create_email_alert_handler_from_env')
    @patch('cli.config_monitor.create_default_alert_manager')
    @patch('cli.config_monitor.get_config_monitor')
    def test_setup_alerts_with_email(self, mock_get_monitor, mock_create_manager, mock_create_email):
        """Test alert setup with email handler."""
        mock_monitor = Mock()
        mock_get_monitor.return_value = mock_monitor
        
        mock_manager = Mock()
        mock_manager.get_handler_names.return_value = ["console", "file", "email"]
        mock_create_manager.return_value = mock_manager
        
        # Mock email handler
        mock_email_handler = Mock()
        mock_create_email.return_value = mock_email_handler
        
        # Run command with email flag
        result = self.runner.invoke(setup_alerts, ["--email"])
        
        assert result.exit_code == 0
        assert "Email alert handler configured" in result.output
        mock_manager.add_handler.assert_called_once_with(mock_email_handler)
    
    @patch('cli.config_monitor.create_email_alert_handler_from_env')
    @patch('cli.config_monitor.create_default_alert_manager')
    @patch('cli.config_monitor.get_config_monitor')
    def test_setup_alerts_email_missing_env(self, mock_get_monitor, mock_create_manager, mock_create_email):
        """Test alert setup with missing email environment variables."""
        mock_monitor = Mock()
        mock_get_monitor.return_value = mock_monitor
        
        mock_manager = Mock()
        mock_create_manager.return_value = mock_manager
        
        mock_create_email.return_value = None  # No email handler due to missing env vars
        
        # Run command with email flag
        result = self.runner.invoke(setup_alerts, ["--email"])
        
        assert result.exit_code == 0
        assert "Email alert handler not configured" in result.output
        assert "SYNC2NAS_ALERT_SMTP_HOST" in result.output
    
    @patch('cli.config_monitor.create_email_alert_handler_from_env')
    @patch('cli.config_monitor.create_default_alert_manager')
    @patch('cli.config_monitor.get_config_monitor')
    def test_setup_alerts_with_test(self, mock_get_monitor, mock_create_manager, mock_create_email):
        """Test alert setup with test alert."""
        mock_monitor = Mock()
        mock_get_monitor.return_value = mock_monitor
        
        mock_manager = Mock()
        mock_manager.get_handler_names.return_value = ["console"]
        mock_create_manager.return_value = mock_manager
        
        mock_create_email.return_value = None
        
        # Run command with test flag
        result = self.runner.invoke(setup_alerts, ["--test"])
        
        assert result.exit_code == 0
        assert "Test alert sent" in result.output
        mock_manager.handle_alert.assert_called_once()
        
        # Check test alert details
        call_args = mock_manager.handle_alert.call_args
        alert_type, details = call_args[0]
        assert alert_type == "Test Alert"
        assert details["alert_type"] == "test_alert"


class TestConfigMonitorGroup:
    """Test the config monitor command group."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_config_monitor_group_help(self):
        """Test config monitor group help."""
        result = self.runner.invoke(config_monitor_group, ["--help"])
        
        assert result.exit_code == 0
        assert "Configuration monitoring and health check commands" in result.output
        assert "health" in result.output
        assert "validate" in result.output
        assert "metrics" in result.output
        assert "events" in result.output
        assert "setup-alerts" in result.output
    
    def test_individual_command_help(self):
        """Test individual command help."""
        # Test health command help
        result = self.runner.invoke(config_monitor_group, ["health", "--help"])
        assert result.exit_code == 0
        assert "Perform health checks on LLM services" in result.output
        
        # Test validate command help
        result = self.runner.invoke(config_monitor_group, ["validate", "--help"])
        assert result.exit_code == 0
        assert "Validate LLM configuration" in result.output
        
        # Test metrics command help
        result = self.runner.invoke(config_monitor_group, ["metrics", "--help"])
        assert result.exit_code == 0
        assert "Display configuration monitoring metrics" in result.output


if __name__ == "__main__":
    pytest.main([__file__])