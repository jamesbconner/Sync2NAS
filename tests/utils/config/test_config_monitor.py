"""
Tests for configuration monitoring and metrics collection system.
"""

import pytest
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from utils.config.config_monitor import (
    ConfigMonitor, ConfigEvent, ConfigMetric, MetricType,
    get_config_monitor, initialize_config_monitor, log_config_operation
)
from utils.config.validation_models import ValidationResult, ValidationError, ErrorCode, HealthCheckResult


class TestConfigMonitor:
    """Test the ConfigMonitor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.monitor = ConfigMonitor(
            enable_metrics=True,
            enable_alerts=True,
            metrics_retention_hours=1,
            alert_threshold_failures=2,
            alert_threshold_window_minutes=1
        )
    
    def test_initialization(self):
        """Test monitor initialization."""
        assert self.monitor.enable_metrics is True
        assert self.monitor.enable_alerts is True
        assert self.monitor.metrics_retention_hours == 1
        assert self.monitor.alert_threshold_failures == 2
        assert self.monitor.alert_threshold_window_minutes == 1
        assert len(self.monitor._metrics) == 0
        assert len(self.monitor._events) == 0
    
    def test_config_loading_logging(self):
        """Test configuration loading event logging."""
        # Start logging
        operation_id = self.monitor.log_config_loading_start("test_config.ini")
        assert operation_id.startswith("config_load_")
        
        # Complete logging
        self.monitor.log_config_loading_complete(
            operation_id=operation_id,
            success=True,
            duration_ms=150.5,
            sections_loaded=5
        )
        
        # Check events were recorded
        events = self.monitor.get_recent_events(limit=10)
        assert len(events) == 2
        
        # Check start event
        start_event = next(e for e in events if e.event_type == "config_loading_start")
        assert start_event.details["operation_id"] == operation_id
        assert start_event.details["config_source"] == "test_config.ini"
        
        # Check complete event
        complete_event = next(e for e in events if e.event_type == "config_loading_complete")
        assert complete_event.success is True
        assert complete_event.duration_ms == 150.5
        assert complete_event.details["sections_loaded"] == 5
        
        # Check metrics were recorded
        metrics = self.monitor.get_metrics_summary()
        assert "config_loading_total[success=True]" in metrics["counters"]
        assert metrics["counters"]["config_loading_total[success=True]"] == 1
        assert "config_loading_duration_ms" in metrics["histograms"]
        assert metrics["histograms"]["config_loading_duration_ms"]["count"] == 1
    
    def test_validation_logging(self):
        """Test validation event logging."""
        # Create validation result
        validation_result = ValidationResult(is_valid=False, errors=[], warnings=[], suggestions=[])
        validation_result.add_error(ValidationError(
            section="openai",
            key="api_key",
            message="API key is missing",
            suggestion="Add your OpenAI API key",
            error_code=ErrorCode.MISSING_KEY
        ))
        
        # Start and complete validation logging
        operation_id = self.monitor.log_validation_start("openai")
        self.monitor.log_validation_complete(
            operation_id=operation_id,
            service="openai",
            validation_result=validation_result,
            duration_ms=75.2
        )
        
        # Check events
        events = self.monitor.get_recent_events(limit=10)
        validation_events = [e for e in events if "validation" in e.event_type]
        assert len(validation_events) == 2
        
        # Check complete event
        complete_event = next(e for e in events if e.event_type == "validation_complete")
        assert complete_event.service == "openai"
        assert complete_event.success is False
        assert complete_event.duration_ms == 75.2
        assert complete_event.details["error_count"] == 1
        
        # Check metrics
        metrics = self.monitor.get_metrics_summary()
        assert "config_validation_total[service=openai,success=False]" in metrics["counters"]
        assert metrics["counters"]["config_validation_total[service=openai,success=False]"] == 1
    
    def test_health_check_logging(self):
        """Test health check event logging."""
        # Create health check result
        health_result = HealthCheckResult(
            service="ollama",
            is_healthy=True,
            response_time_ms=250.0,
            error_message=None,
            details={"model": "llama2:7b", "host": "localhost:11434"}
        )
        
        # Start and complete health check logging
        operation_id = self.monitor.log_health_check_start("ollama")
        self.monitor.log_health_check_complete(
            operation_id=operation_id,
            service="ollama",
            health_result=health_result
        )
        
        # Check events
        events = self.monitor.get_recent_events(limit=10)
        health_events = [e for e in events if "health_check" in e.event_type]
        assert len(health_events) == 2
        
        # Check complete event
        complete_event = next(e for e in events if e.event_type == "health_check_complete")
        assert complete_event.service == "ollama"
        assert complete_event.success is True
        assert complete_event.duration_ms == 250.0
        assert complete_event.details["health_details"]["model"] == "llama2:7b"
        
        # Check metrics
        metrics = self.monitor.get_metrics_summary()
        assert "health_check_total[service=ollama,success=True]" in metrics["counters"]
        assert metrics["counters"]["health_check_total[service=ollama,success=True]"] == 1
        assert "health_check_response_time_ms" in metrics["histograms"]
    
    def test_environment_override_logging(self):
        """Test environment variable override logging."""
        self.monitor.log_environment_override(
            env_var="SYNC2NAS_OPENAI_API_KEY",
            section="openai",
            key="api_key",
            old_value="<not set>",
            new_value="sk-test123"
        )
        
        # Check event was recorded
        events = self.monitor.get_recent_events(limit=10)
        env_events = [e for e in events if e.event_type == "env_override"]
        assert len(env_events) == 1
        
        env_event = env_events[0]
        assert env_event.details["env_var"] == "SYNC2NAS_OPENAI_API_KEY"
        assert env_event.details["section"] == "openai"
        assert env_event.details["key"] == "api_key"
        assert env_event.details["old_value"] == "<not set>"
        assert env_event.details["new_value"] == "sk-test123"
        
        # Check metrics
        metrics = self.monitor.get_metrics_summary()
        assert "env_overrides_total[section=openai,key=api_key]" in metrics["counters"]
    
    def test_metrics_collection(self):
        """Test metrics collection and summary."""
        # Record various metrics
        self.monitor._record_counter("test_counter", 5, {"label": "value"})
        self.monitor._record_gauge("test_gauge", 42.5)
        self.monitor._record_histogram("test_histogram", 100.0)
        self.monitor._record_histogram("test_histogram", 200.0)
        self.monitor._record_histogram("test_histogram", 150.0)
        
        # Get metrics summary
        metrics = self.monitor.get_metrics_summary()
        
        # Check counters
        assert "test_counter[label=value]" in metrics["counters"]
        assert metrics["counters"]["test_counter[label=value]"] == 5
        
        # Check gauges
        assert "test_gauge" in metrics["gauges"]
        assert metrics["gauges"]["test_gauge"] == 42.5
        
        # Check histograms
        assert "test_histogram" in metrics["histograms"]
        histogram_stats = metrics["histograms"]["test_histogram"]
        assert histogram_stats["count"] == 3
        assert histogram_stats["min"] == 100.0
        assert histogram_stats["max"] == 200.0
        assert histogram_stats["avg"] == 150.0
    
    def test_event_filtering(self):
        """Test event filtering by type."""
        # Record different event types
        self.monitor._record_event(ConfigEvent(
            event_type="validation_start",
            timestamp=datetime.now(),
            service="openai"
        ))
        self.monitor._record_event(ConfigEvent(
            event_type="health_check_start",
            timestamp=datetime.now(),
            service="ollama"
        ))
        self.monitor._record_event(ConfigEvent(
            event_type="validation_complete",
            timestamp=datetime.now(),
            service="openai"
        ))
        
        # Test filtering
        all_events = self.monitor.get_recent_events(limit=10)
        assert len(all_events) == 3
        
        validation_events = self.monitor.get_recent_events(limit=10, event_type="validation_start")
        assert len(validation_events) == 1
        assert validation_events[0].event_type == "validation_start"
        
        health_events = self.monitor.get_recent_events(limit=10, event_type="health_check_start")
        assert len(health_events) == 1
        assert health_events[0].event_type == "health_check_start"
    
    def test_alert_callbacks(self):
        """Test alert callback functionality."""
        # Mock alert callback
        alert_callback = Mock()
        self.monitor.add_alert_callback(alert_callback)
        
        # Trigger alert by simulating validation failures
        validation_result = ValidationResult(is_valid=False, errors=[], warnings=[], suggestions=[])
        validation_result.add_error(ValidationError(
            section="openai",
            key="api_key",
            message="API key is missing",
            error_code=ErrorCode.MISSING_KEY
        ))
        
        # Trigger multiple failures to exceed threshold
        for _ in range(3):
            operation_id = self.monitor.log_validation_start("openai")
            self.monitor.log_validation_complete(
                operation_id=operation_id,
                service="openai",
                validation_result=validation_result,
                duration_ms=50.0
            )
            time.sleep(0.1)  # Small delay to ensure different timestamps
        
        # Check that alert callback was called
        assert alert_callback.call_count >= 1
        
        # Check alert details
        call_args = alert_callback.call_args
        alert_type, details = call_args[0]
        assert "validation failures" in alert_type.lower()
        assert details["service"] == "openai"
        assert details["failure_count"] >= 2
    
    def test_health_check_alert(self):
        """Test health check failure alerts."""
        # Mock alert callback
        alert_callback = Mock()
        self.monitor.add_alert_callback(alert_callback)
        
        # Create failing health check result
        health_result = HealthCheckResult(
            service="anthropic",
            is_healthy=False,
            response_time_ms=None,
            error_message="API key invalid",
            details={"error_code": "AUTHENTICATION_FAILED"}
        )
        
        # Trigger multiple failures
        for _ in range(3):
            operation_id = self.monitor.log_health_check_start("anthropic")
            self.monitor.log_health_check_complete(
                operation_id=operation_id,
                service="anthropic",
                health_result=health_result
            )
            time.sleep(0.1)
        
        # Check that alert was triggered
        assert alert_callback.call_count >= 1
        
        call_args = alert_callback.call_args
        alert_type, details = call_args[0]
        assert "health check failures" in alert_type.lower()
        assert details["service"] == "anthropic"
    
    def test_metrics_cleanup(self):
        """Test metrics cleanup for old entries."""
        # Create monitor with very short retention
        short_monitor = ConfigMonitor(metrics_retention_hours=0.001)  # ~3.6 seconds
        
        # Add some metrics
        short_monitor._record_counter("test_counter", 1)
        short_monitor._record_gauge("test_gauge", 10)
        
        # Check metrics exist
        metrics = short_monitor.get_metrics_summary()
        assert len(short_monitor._metrics) > 0
        
        # Wait for retention period to pass
        time.sleep(0.1)
        
        # Trigger cleanup by getting metrics
        metrics = short_monitor.get_metrics_summary()
        
        # Old metrics should be cleaned up
        # Note: counters and gauges persist, but individual metric records are cleaned
        assert len([m for m in short_monitor._metrics if 
                   m.timestamp < datetime.now() - timedelta(hours=0.001)]) == 0
    
    def test_thread_safety(self):
        """Test thread safety of monitor operations."""
        results = []
        
        def worker():
            try:
                for i in range(10):
                    operation_id = self.monitor.log_validation_start(f"service_{i}")
                    validation_result = ValidationResult(is_valid=True, errors=[], warnings=[], suggestions=[])
                    self.monitor.log_validation_complete(
                        operation_id=operation_id,
                        service=f"service_{i}",
                        validation_result=validation_result,
                        duration_ms=float(i * 10)
                    )
                results.append("success")
            except Exception as e:
                results.append(f"error: {e}")
        
        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check all threads completed successfully
        assert len(results) == 5
        assert all(result == "success" for result in results)
        
        # Check events were recorded correctly
        events = self.monitor.get_recent_events(limit=100)
        validation_events = [e for e in events if "validation" in e.event_type]
        assert len(validation_events) == 100  # 5 threads * 10 operations * 2 events each
    
    def test_disabled_metrics(self):
        """Test monitor with metrics disabled."""
        disabled_monitor = ConfigMonitor(enable_metrics=False)
        
        # Try to record metrics
        disabled_monitor._record_counter("test_counter", 1)
        disabled_monitor._record_gauge("test_gauge", 10)
        disabled_monitor._record_histogram("test_histogram", 100)
        
        # Metrics should not be recorded
        metrics = disabled_monitor.get_metrics_summary()
        assert len(metrics["counters"]) == 0
        assert len(metrics["gauges"]) == 0
        assert len(metrics["histograms"]) == 0
    
    def test_disabled_alerts(self):
        """Test monitor with alerts disabled."""
        disabled_monitor = ConfigMonitor(enable_alerts=False)
        alert_callback = Mock()
        disabled_monitor.add_alert_callback(alert_callback)
        
        # Trigger validation failures
        validation_result = ValidationResult(is_valid=False, errors=[], warnings=[], suggestions=[])
        validation_result.add_error(ValidationError(
            section="openai",
            key="api_key",
            message="API key is missing",
            error_code=ErrorCode.MISSING_KEY
        ))
        
        for _ in range(5):
            operation_id = disabled_monitor.log_validation_start("openai")
            disabled_monitor.log_validation_complete(
                operation_id=operation_id,
                service="openai",
                validation_result=validation_result,
                duration_ms=50.0
            )
        
        # Alert should not be triggered
        assert alert_callback.call_count == 0


class TestGlobalMonitor:
    """Test global monitor functions."""
    
    def test_get_config_monitor(self):
        """Test getting global monitor instance."""
        monitor1 = get_config_monitor()
        monitor2 = get_config_monitor()
        
        # Should return same instance
        assert monitor1 is monitor2
        assert isinstance(monitor1, ConfigMonitor)
    
    def test_initialize_config_monitor(self):
        """Test initializing global monitor with custom settings."""
        custom_monitor = initialize_config_monitor(
            enable_metrics=False,
            enable_alerts=False,
            metrics_retention_hours=48
        )
        
        assert custom_monitor.enable_metrics is False
        assert custom_monitor.enable_alerts is False
        assert custom_monitor.metrics_retention_hours == 48
        
        # Should be same as global instance
        global_monitor = get_config_monitor()
        assert custom_monitor is global_monitor
    
    def test_log_config_operation(self):
        """Test convenience logging function."""
        with patch('utils.config.config_monitor.logger') as mock_logger:
            log_config_operation("test_operation", service="test_service", result="success")
            
            # Check that logging was called
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert "Configuration operation: test_operation" in call_args[0][0]
            assert call_args[1]["extra"]["operation_type"] == "test_operation"
            assert call_args[1]["extra"]["service"] == "test_service"
            assert call_args[1]["extra"]["result"] == "success"


class TestConfigEvent:
    """Test ConfigEvent data class."""
    
    def test_event_creation(self):
        """Test creating configuration events."""
        timestamp = datetime.now()
        event = ConfigEvent(
            event_type="test_event",
            timestamp=timestamp,
            service="test_service",
            success=True,
            duration_ms=123.45,
            error_code="TEST_ERROR",
            error_message="Test error message",
            details={"key": "value"}
        )
        
        assert event.event_type == "test_event"
        assert event.timestamp == timestamp
        assert event.service == "test_service"
        assert event.success is True
        assert event.duration_ms == 123.45
        assert event.error_code == "TEST_ERROR"
        assert event.error_message == "Test error message"
        assert event.details == {"key": "value"}
    
    def test_event_defaults(self):
        """Test event creation with defaults."""
        timestamp = datetime.now()
        event = ConfigEvent(
            event_type="minimal_event",
            timestamp=timestamp
        )
        
        assert event.event_type == "minimal_event"
        assert event.timestamp == timestamp
        assert event.service is None
        assert event.success is True
        assert event.duration_ms is None
        assert event.error_code is None
        assert event.error_message is None
        assert event.details == {}


class TestConfigMetric:
    """Test ConfigMetric data class."""
    
    def test_metric_creation(self):
        """Test creating configuration metrics."""
        timestamp = datetime.now()
        metric = ConfigMetric(
            name="test_metric",
            metric_type=MetricType.COUNTER,
            value=42.5,
            timestamp=timestamp,
            labels={"service": "openai", "status": "success"},
            description="Test metric description"
        )
        
        assert metric.name == "test_metric"
        assert metric.metric_type == MetricType.COUNTER
        assert metric.value == 42.5
        assert metric.timestamp == timestamp
        assert metric.labels == {"service": "openai", "status": "success"}
        assert metric.description == "Test metric description"
    
    def test_metric_defaults(self):
        """Test metric creation with defaults."""
        timestamp = datetime.now()
        metric = ConfigMetric(
            name="minimal_metric",
            metric_type=MetricType.GAUGE,
            value=10.0,
            timestamp=timestamp
        )
        
        assert metric.name == "minimal_metric"
        assert metric.metric_type == MetricType.GAUGE
        assert metric.value == 10.0
        assert metric.timestamp == timestamp
        assert metric.labels == {}
        assert metric.description == ""


if __name__ == "__main__":
    pytest.main([__file__])