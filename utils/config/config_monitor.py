"""
Configuration monitoring and metrics collection system.

This module provides comprehensive monitoring capabilities for configuration
loading, validation, and health checking operations. It includes structured
logging, metrics collection, and alerting functionality.
"""

import time
import logging
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum

from .validation_models import ValidationResult, HealthCheckResult, ErrorCode

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics that can be collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class ConfigMetric:
    """Represents a configuration-related metric."""
    name: str
    metric_type: MetricType
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    description: str = ""


@dataclass
class ConfigEvent:
    """Represents a configuration-related event for logging."""
    event_type: str
    timestamp: datetime
    service: Optional[str] = None
    success: bool = True
    duration_ms: Optional[float] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


class ConfigMonitor:
    """
    Configuration monitoring and metrics collection system.
    
    Provides structured logging, metrics collection, and alerting for
    configuration operations including loading, validation, and health checks.
    """
    
    def __init__(self, 
                 enable_metrics: bool = True,
                 enable_alerts: bool = True,
                 metrics_retention_hours: int = 24,
                 alert_threshold_failures: int = 3,
                 alert_threshold_window_minutes: int = 5):
        """
        Initialize the configuration monitor.
        
        Args:
            enable_metrics: Whether to collect metrics
            enable_alerts: Whether to enable alerting
            metrics_retention_hours: How long to retain metrics in memory
            alert_threshold_failures: Number of failures to trigger alert
            alert_threshold_window_minutes: Time window for failure counting
        """
        self.enable_metrics = enable_metrics
        self.enable_alerts = enable_alerts
        self.metrics_retention_hours = metrics_retention_hours
        self.alert_threshold_failures = alert_threshold_failures
        self.alert_threshold_window_minutes = alert_threshold_window_minutes
        
        # Thread-safe storage for metrics and events
        self._lock = threading.RLock()
        self._metrics: List[ConfigMetric] = []
        self._events: deque = deque(maxlen=1000)  # Keep last 1000 events
        
        # Counters for different metric types
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        
        # Alert callbacks
        self._alert_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
        
        # Failure tracking for alerting
        self._failure_history: deque = deque(maxlen=100)
        
        logger.info("Configuration monitor initialized", extra={
            "enable_metrics": enable_metrics,
            "enable_alerts": enable_alerts,
            "retention_hours": metrics_retention_hours
        })
    
    def log_config_loading_start(self, config_source: str) -> str:
        """
        Log the start of configuration loading.
        
        Args:
            config_source: Source of configuration (file path, etc.)
            
        Returns:
            Operation ID for tracking
        """
        operation_id = f"config_load_{int(time.time() * 1000)}"
        
        logger.info("Configuration loading started", extra={
            "operation_id": operation_id,
            "config_source": config_source,
            "event_type": "config_loading_start"
        })
        
        event = ConfigEvent(
            event_type="config_loading_start",
            timestamp=datetime.now(),
            details={
                "operation_id": operation_id,
                "config_source": config_source
            }
        )
        self._record_event(event)
        
        return operation_id
    
    def log_config_loading_complete(self, 
                                   operation_id: str,
                                   success: bool,
                                   duration_ms: float,
                                   sections_loaded: int,
                                   error_message: Optional[str] = None) -> None:
        """
        Log the completion of configuration loading.
        
        Args:
            operation_id: Operation ID from start
            success: Whether loading was successful
            duration_ms: Duration in milliseconds
            sections_loaded: Number of configuration sections loaded
            error_message: Error message if failed
        """
        logger.info("Configuration loading completed", extra={
            "operation_id": operation_id,
            "success": success,
            "duration_ms": duration_ms,
            "sections_loaded": sections_loaded,
            "error_message": error_message,
            "event_type": "config_loading_complete"
        })
        
        event = ConfigEvent(
            event_type="config_loading_complete",
            timestamp=datetime.now(),
            success=success,
            duration_ms=duration_ms,
            error_message=error_message,
            details={
                "operation_id": operation_id,
                "sections_loaded": sections_loaded
            }
        )
        self._record_event(event)
        
        # Record metrics
        if self.enable_metrics:
            self._record_counter("config_loading_total", 1, {"success": str(success)})
            self._record_histogram("config_loading_duration_ms", duration_ms)
            self._record_gauge("config_sections_loaded", sections_loaded)
    
    def log_validation_start(self, service: str) -> str:
        """
        Log the start of configuration validation.
        
        Args:
            service: LLM service being validated
            
        Returns:
            Operation ID for tracking
        """
        operation_id = f"validation_{service}_{int(time.time() * 1000)}"
        
        logger.info("Configuration validation started", extra={
            "operation_id": operation_id,
            "service": service,
            "event_type": "validation_start"
        })
        
        event = ConfigEvent(
            event_type="validation_start",
            timestamp=datetime.now(),
            service=service,
            details={"operation_id": operation_id}
        )
        self._record_event(event)
        
        return operation_id
    
    def log_validation_complete(self,
                               operation_id: str,
                               service: str,
                               validation_result: ValidationResult,
                               duration_ms: float) -> None:
        """
        Log the completion of configuration validation.
        
        Args:
            operation_id: Operation ID from start
            service: LLM service that was validated
            validation_result: Validation result
            duration_ms: Duration in milliseconds
        """
        success = validation_result.is_valid
        error_count = len(validation_result.errors)
        warning_count = len(validation_result.warnings)
        
        logger.info("Configuration validation completed", extra={
            "operation_id": operation_id,
            "service": service,
            "success": success,
            "duration_ms": duration_ms,
            "error_count": error_count,
            "warning_count": warning_count,
            "event_type": "validation_complete"
        })
        
        # Log individual errors at warning level for visibility
        for error in validation_result.errors:
            logger.warning("Validation error", extra={
                "operation_id": operation_id,
                "service": service,
                "section": error.section,
                "key": error.key,
                "error_code": error.error_code.value if error.error_code else None,
                "error_message": error.message,
                "event_type": "validation_error"
            })
        
        event = ConfigEvent(
            event_type="validation_complete",
            timestamp=datetime.now(),
            service=service,
            success=success,
            duration_ms=duration_ms,
            details={
                "operation_id": operation_id,
                "error_count": error_count,
                "warning_count": warning_count,
                "errors": [{"section": e.section, "key": e.key, "message": e.message} 
                          for e in validation_result.errors]
            }
        )
        self._record_event(event)
        
        # Record metrics
        if self.enable_metrics:
            self._record_counter("config_validation_total", 1, {
                "service": service,
                "success": str(success)
            })
            self._record_histogram("config_validation_duration_ms", duration_ms)
            self._record_gauge("config_validation_errors", error_count)
            self._record_gauge("config_validation_warnings", warning_count)
        
        # Check for alerting
        if not success and self.enable_alerts:
            self._check_validation_failure_alert(service, validation_result)
    
    def log_health_check_start(self, service: str) -> str:
        """
        Log the start of a health check.
        
        Args:
            service: LLM service being checked
            
        Returns:
            Operation ID for tracking
        """
        operation_id = f"health_check_{service}_{int(time.time() * 1000)}"
        
        logger.info("Health check started", extra={
            "operation_id": operation_id,
            "service": service,
            "event_type": "health_check_start"
        })
        
        event = ConfigEvent(
            event_type="health_check_start",
            timestamp=datetime.now(),
            service=service,
            details={"operation_id": operation_id}
        )
        self._record_event(event)
        
        return operation_id
    
    def log_health_check_complete(self,
                                 operation_id: str,
                                 service: str,
                                 health_result: HealthCheckResult) -> None:
        """
        Log the completion of a health check.
        
        Args:
            operation_id: Operation ID from start
            service: LLM service that was checked
            health_result: Health check result
        """
        success = health_result.is_healthy
        response_time_ms = health_result.response_time_ms or 0
        
        logger.info("Health check completed", extra={
            "operation_id": operation_id,
            "service": service,
            "success": success,
            "response_time_ms": response_time_ms,
            "error_message": health_result.error_message,
            "event_type": "health_check_complete"
        })
        
        event = ConfigEvent(
            event_type="health_check_complete",
            timestamp=datetime.now(),
            service=service,
            success=success,
            duration_ms=response_time_ms,
            error_message=health_result.error_message,
            details={
                "operation_id": operation_id,
                "health_details": health_result.details or {}
            }
        )
        self._record_event(event)
        
        # Record metrics
        if self.enable_metrics:
            self._record_counter("health_check_total", 1, {
                "service": service,
                "success": str(success)
            })
            if response_time_ms > 0:
                self._record_histogram("health_check_response_time_ms", response_time_ms)
        
        # Check for alerting
        if not success and self.enable_alerts:
            self._check_health_failure_alert(service, health_result)
    
    def log_environment_override(self, env_var: str, section: str, key: str, old_value: str, new_value: str) -> None:
        """
        Log an environment variable override.
        
        Args:
            env_var: Environment variable name
            section: Configuration section
            key: Configuration key
            old_value: Previous value
            new_value: New value from environment
        """
        logger.info("Environment variable override applied", extra={
            "env_var": env_var,
            "section": section,
            "key": key,
            "old_value": old_value,
            "new_value": new_value,
            "event_type": "env_override"
        })
        
        event = ConfigEvent(
            event_type="env_override",
            timestamp=datetime.now(),
            details={
                "env_var": env_var,
                "section": section,
                "key": key,
                "old_value": old_value,
                "new_value": new_value
            }
        )
        self._record_event(event)
        
        if self.enable_metrics:
            self._record_counter("env_overrides_total", 1, {
                "section": section,
                "key": key
            })
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get a summary of collected metrics.
        
        Returns:
            Dictionary containing metrics summary
        """
        with self._lock:
            # Clean up old metrics
            self._cleanup_old_metrics()
            
            summary = {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {},
                "total_events": len(self._events),
                "collection_period_hours": self.metrics_retention_hours
            }
            
            # Calculate histogram statistics
            for name, values in self._histograms.items():
                if values:
                    summary["histograms"][name] = {
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "avg": sum(values) / len(values),
                        "p50": self._percentile(values, 50),
                        "p95": self._percentile(values, 95),
                        "p99": self._percentile(values, 99)
                    }
            
            return summary
    
    def get_recent_events(self, limit: int = 50, event_type: Optional[str] = None) -> List[ConfigEvent]:
        """
        Get recent configuration events.
        
        Args:
            limit: Maximum number of events to return
            event_type: Filter by event type (optional)
            
        Returns:
            List of recent events
        """
        with self._lock:
            events = list(self._events)
            
            if event_type:
                events = [e for e in events if e.event_type == event_type]
            
            # Return most recent events first
            return list(reversed(events))[:limit]
    
    def add_alert_callback(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """
        Add a callback function for alerts.
        
        Args:
            callback: Function to call when alert is triggered
                     Signature: callback(alert_type: str, details: Dict[str, Any])
        """
        self._alert_callbacks.append(callback)
        callback_name = getattr(callback, '__name__', str(callback))
        logger.info(f"Added alert callback: {callback_name}")
    
    def _record_event(self, event: ConfigEvent) -> None:
        """Record an event in the event history."""
        with self._lock:
            self._events.append(event)
    
    def _record_counter(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record a counter metric."""
        if not self.enable_metrics:
            return
        
        with self._lock:
            # Create a unique key for labeled metrics
            key = name
            if labels:
                label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
                key = f"{name}[{label_str}]"
            
            self._counters[key] += value
            
            # Also store as a metric with timestamp
            metric = ConfigMetric(
                name=name,
                metric_type=MetricType.COUNTER,
                value=value,
                timestamp=datetime.now(),
                labels=labels or {}
            )
            self._metrics.append(metric)
    
    def _record_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record a gauge metric."""
        if not self.enable_metrics:
            return
        
        with self._lock:
            key = name
            if labels:
                label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
                key = f"{name}[{label_str}]"
            
            self._gauges[key] = value
            
            metric = ConfigMetric(
                name=name,
                metric_type=MetricType.GAUGE,
                value=value,
                timestamp=datetime.now(),
                labels=labels or {}
            )
            self._metrics.append(metric)
    
    def _record_histogram(self, name: str, value: float) -> None:
        """Record a histogram metric."""
        if not self.enable_metrics:
            return
        
        with self._lock:
            self._histograms[name].append(value)
            
            # Keep only recent values to prevent memory growth
            if len(self._histograms[name]) > 1000:
                self._histograms[name] = self._histograms[name][-500:]
            
            metric = ConfigMetric(
                name=name,
                metric_type=MetricType.HISTOGRAM,
                value=value,
                timestamp=datetime.now()
            )
            self._metrics.append(metric)
    
    def _cleanup_old_metrics(self) -> None:
        """Remove metrics older than retention period."""
        cutoff_time = datetime.now() - timedelta(hours=self.metrics_retention_hours)
        self._metrics = [m for m in self._metrics if m.timestamp > cutoff_time]
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile of values."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int((percentile / 100.0) * (len(sorted_values) - 1))
        return sorted_values[index]
    
    def _check_validation_failure_alert(self, service: str, validation_result: ValidationResult) -> None:
        """Check if validation failures warrant an alert."""
        now = datetime.now()
        self._failure_history.append(("validation", service, now))
        
        # Count recent validation failures for this service
        cutoff_time = now - timedelta(minutes=self.alert_threshold_window_minutes)
        recent_failures = [
            f for f in self._failure_history 
            if f[0] == "validation" and f[1] == service and f[2] > cutoff_time
        ]
        
        if len(recent_failures) >= self.alert_threshold_failures:
            alert_details = {
                "alert_type": "validation_failure",
                "service": service,
                "failure_count": len(recent_failures),
                "window_minutes": self.alert_threshold_window_minutes,
                "errors": [{"section": e.section, "key": e.key, "message": e.message} 
                          for e in validation_result.errors],
                "timestamp": now.isoformat()
            }
            
            self._trigger_alert("Configuration validation failures", alert_details)
    
    def _check_health_failure_alert(self, service: str, health_result: HealthCheckResult) -> None:
        """Check if health check failures warrant an alert."""
        now = datetime.now()
        self._failure_history.append(("health_check", service, now))
        
        # Count recent health check failures for this service
        cutoff_time = now - timedelta(minutes=self.alert_threshold_window_minutes)
        recent_failures = [
            f for f in self._failure_history 
            if f[0] == "health_check" and f[1] == service and f[2] > cutoff_time
        ]
        
        if len(recent_failures) >= self.alert_threshold_failures:
            alert_details = {
                "alert_type": "health_check_failure",
                "service": service,
                "failure_count": len(recent_failures),
                "window_minutes": self.alert_threshold_window_minutes,
                "error_message": health_result.error_message,
                "health_details": health_result.details or {},
                "timestamp": now.isoformat()
            }
            
            self._trigger_alert("LLM service health check failures", alert_details)
    
    def _trigger_alert(self, alert_type: str, details: Dict[str, Any]) -> None:
        """Trigger an alert by calling all registered callbacks."""
        logger.error(f"ALERT: {alert_type}", extra=details)
        
        for callback in self._alert_callbacks:
            try:
                callback(alert_type, details)
            except Exception as e:
                logger.error(f"Error in alert callback {callback.__name__}: {e}")


# Global monitor instance
_global_monitor: Optional[ConfigMonitor] = None


def get_config_monitor() -> ConfigMonitor:
    """
    Get the global configuration monitor instance.
    
    Returns:
        ConfigMonitor instance
    """
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = ConfigMonitor()
    return _global_monitor


def initialize_config_monitor(**kwargs) -> ConfigMonitor:
    """
    Initialize the global configuration monitor with custom settings.
    
    Args:
        **kwargs: Arguments to pass to ConfigMonitor constructor
        
    Returns:
        ConfigMonitor instance
    """
    global _global_monitor
    _global_monitor = ConfigMonitor(**kwargs)
    return _global_monitor


def log_config_operation(operation_type: str, **kwargs) -> None:
    """
    Convenience function to log configuration operations.
    
    Args:
        operation_type: Type of operation (loading, validation, health_check)
        **kwargs: Additional details to log
    """
    monitor = get_config_monitor()
    
    logger.info(f"Configuration operation: {operation_type}", extra={
        "operation_type": operation_type,
        "event_type": "config_operation",
        **kwargs
    })