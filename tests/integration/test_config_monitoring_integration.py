"""
Integration tests for configuration monitoring system.

Tests the complete monitoring pipeline including validation, health checks,
metrics collection, and alerting.
"""

import pytest
import time
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from utils.config.config_monitor import ConfigMonitor, initialize_config_monitor
from utils.config.config_validator import ConfigValidator
from utils.config.config_normalizer import ConfigNormalizer
from utils.config.health_checker import ConfigHealthChecker
from utils.config.alert_handlers import AlertManager, ConsoleAlertHandler, FileAlertHandler
from utils.config.validation_models import ValidationResult, ValidationError, ErrorCode, HealthCheckResult
from services.llm_factory import create_llm_service, LLMServiceCreationError


class TestConfigMonitoringIntegration:
    """Integration tests for the complete monitoring system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Initialize fresh monitor for each test
        self.monitor = initialize_config_monitor(
            enable_metrics=True,
            enable_alerts=True,
            metrics_retention_hours=1,
            alert_threshold_failures=2,
            alert_threshold_window_minutes=1
        )
        
        # Set up alert manager
        self.alert_manager = AlertManager()
        self.alert_callback = Mock()
        self.alert_manager.add_handler(Mock())
        self.monitor.add_alert_callback(self.alert_callback)
    
    def test_complete_validation_monitoring_pipeline(self):
        """Test complete validation monitoring from start to finish."""
        # Create test configuration
        config = {
            'llm': {'service': 'openai'},
            'openai': {'api_key': 'sk-test123', 'model': 'gpt-4'}
        }
        
        # Create validator and validate
        validator = ConfigValidator()
        result = validator.validate_llm_config(config)
        
        # Check that monitoring captured the validation
        events = self.monitor.get_recent_events(limit=10)
        validation_events = [e for e in events if 'validation' in e.event_type]
        
        assert len(validation_events) >= 2  # start and complete events
        
        # Check metrics were recorded
        metrics = self.monitor.get_metrics_summary()
        assert any('config_validation_total' in key for key in metrics['counters'].keys())
        assert any('config_validation_duration_ms' in key for key in metrics['histograms'].keys())
        
        # Verify event details
        complete_event = next(e for e in validation_events if e.event_type == 'validation_complete')
        assert complete_event.service == 'llm'
        assert complete_event.success == result.is_valid
        assert complete_event.duration_ms is not None
    
    @pytest.mark.asyncio
    async def test_complete_health_check_monitoring_pipeline(self):
        """Test complete health check monitoring pipeline."""
        # Create test configuration
        config = {
            'llm': {'service': 'ollama'},
            'ollama': {'host': 'http://localhost:11434', 'model': 'llama2:7b'}
        }
        
        # Mock successful health check
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'models': [{'name': 'llama2:7b'}]
            }
            
            mock_gen_response = Mock()
            mock_gen_response.status_code = 200
            
            mock_http_client = AsyncMock()
            mock_http_client.get.return_value = mock_response
            mock_http_client.post.return_value = mock_gen_response
            mock_client.return_value.__aenter__.return_value = mock_http_client
            
            # Create health checker and check
            health_checker = ConfigHealthChecker(timeout=5.0)
            results = await health_checker.check_llm_health(config)
            
            # Verify health check result
            assert len(results) == 1
            assert results[0].service == 'ollama'
            assert results[0].is_healthy is True
            
            # Check monitoring captured the health check
            events = self.monitor.get_recent_events(limit=10)
            health_events = [e for e in events if 'health_check' in e.event_type]
            
            assert len(health_events) >= 2  # start and complete events
            
            # Check metrics
            metrics = self.monitor.get_metrics_summary()
            assert any('health_check_total' in key for key in metrics['counters'].keys())
            assert any('health_check_response_time_ms' in key for key in metrics['histograms'].keys())
    
    def test_llm_factory_integration_with_monitoring(self):
        """Test LLM factory integration with monitoring system."""
        # Create valid configuration
        config = {
            'llm': {'service': 'ollama'},
            'ollama': {'host': 'http://localhost:11434', 'model': 'llama2:7b'}
        }
        
        # Mock the LLM service creation to avoid actual service calls
        with patch('services.llm_implementations.ollama_implementation.OllamaLLMService') as mock_service:
            with patch('utils.config.health_checker.ConfigHealthChecker.check_llm_health_sync') as mock_health:
                # Mock successful health check
                mock_health.return_value = [HealthCheckResult(
                    service='ollama',
                    is_healthy=True,
                    response_time_ms=150.0,
                    error_message=None,
                    details={}
                )]
                
                # Create LLM service
                service = create_llm_service(config, validate_health=True, startup_mode=False)
                
                # Verify service was created
                assert service is not None
                mock_service.assert_called_once()
                
                # Check monitoring captured the operations
                events = self.monitor.get_recent_events(limit=20)
                
                # Should have config loading, validation, and health check events
                event_types = [e.event_type for e in events]
                assert 'config_loading_start' in event_types
                assert 'config_loading_complete' in event_types
                assert 'validation_start' in event_types
                assert 'validation_complete' in event_types
                assert 'health_check_start' in event_types
                assert 'health_check_complete' in event_types
                
                # Check metrics
                metrics = self.monitor.get_metrics_summary()
                assert len(metrics['counters']) > 0
                assert len(metrics['histograms']) > 0
    
    def test_validation_failure_alerting_integration(self):
        """Test validation failure alerting integration."""
        # Create invalid configuration
        config = {
            'llm': {'service': 'openai'},
            # Missing openai section
        }
        
        validator = ConfigValidator()
        
        # Trigger multiple validation failures to exceed alert threshold
        for _ in range(3):
            result = validator.validate_llm_config(config)
            assert not result.is_valid
            time.sleep(0.1)  # Small delay for different timestamps
        
        # Check that alert was triggered
        assert self.alert_callback.call_count >= 1
        
        # Verify alert details
        call_args = self.alert_callback.call_args
        alert_type, details = call_args[0]
        assert 'validation failures' in alert_type.lower()
        assert details['service'] == 'llm'
        assert details['failure_count'] >= 2
    
    @pytest.mark.asyncio
    async def test_health_check_failure_alerting_integration(self):
        """Test health check failure alerting integration."""
        # Create configuration with unreachable service
        config = {
            'llm': {'service': 'ollama'},
            'ollama': {'host': 'http://unreachable:11434', 'model': 'llama2:7b'}
        }
        
        # Mock connection failure
        with patch('httpx.AsyncClient') as mock_client:
            mock_http_client = AsyncMock()
            mock_http_client.get.side_effect = Exception("Connection failed")
            mock_client.return_value.__aenter__.return_value = mock_http_client
            
            health_checker = ConfigHealthChecker(timeout=1.0)
            
            # Trigger multiple health check failures
            for _ in range(3):
                results = await health_checker.check_service_health('ollama', config)
                assert not results.is_healthy
                time.sleep(0.1)
            
            # Check that alert was triggered
            assert self.alert_callback.call_count >= 1
            
            # Verify alert details
            call_args = self.alert_callback.call_args
            alert_type, details = call_args[0]
            assert 'health check failures' in alert_type.lower()
            assert details['service'] == 'ollama'
    
    def test_environment_override_monitoring_integration(self):
        """Test environment variable override monitoring."""
        config = {
            'llm': {'service': 'openai'},
            'openai': {'model': 'gpt-3.5-turbo'}
        }
        
        # Mock environment variable
        with patch.dict('os.environ', {'SYNC2NAS_OPENAI_API_KEY': 'sk-env-override'}):
            normalizer = ConfigNormalizer()
            normalized_config = normalizer.normalize_and_override(config)
            
            # Verify override was applied
            assert normalized_config['openai']['api_key'] == 'sk-env-override'
            
            # Check monitoring captured the override
            events = self.monitor.get_recent_events(limit=10)
            env_events = [e for e in events if e.event_type == 'env_override']
            
            assert len(env_events) >= 1
            env_event = env_events[0]
            assert env_event.details['env_var'] == 'SYNC2NAS_OPENAI_API_KEY'
            assert env_event.details['section'] == 'openai'
            assert env_event.details['key'] == 'api_key'
            assert env_event.details['new_value'] == 'sk-env-override'
            
            # Check metrics
            metrics = self.monitor.get_metrics_summary()
            assert any('env_overrides_total' in key for key in metrics['counters'].keys())
    
    def test_metrics_collection_and_cleanup_integration(self):
        """Test metrics collection and cleanup integration."""
        # Generate various metrics
        config = {'llm': {'service': 'openai'}, 'openai': {'api_key': 'sk-test'}}
        validator = ConfigValidator()
        
        # Generate multiple validation events
        for i in range(5):
            result = validator.validate_llm_config(config)
            time.sleep(0.01)  # Small delay
        
        # Check metrics were collected
        metrics = self.monitor.get_metrics_summary()
        
        # Should have counters, gauges, and histograms
        assert len(metrics['counters']) > 0
        assert len(metrics['histograms']) > 0
        assert metrics['total_events'] > 0
        
        # Test histogram statistics
        for histogram_name, stats in metrics['histograms'].items():
            assert stats['count'] > 0
            assert stats['min'] >= 0
            assert stats['max'] >= stats['min']
            assert stats['avg'] >= 0
            assert stats['p50'] >= 0
            assert stats['p95'] >= stats['p50']
            assert stats['p99'] >= stats['p95']
    
    def test_file_alert_handler_integration(self):
        """Test file alert handler integration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            alert_file = Path(temp_dir) / "test_alerts.log"
            
            # Create file alert handler
            file_handler = FileAlertHandler(str(alert_file))
            alert_manager = AlertManager()
            alert_manager.add_handler(file_handler)
            
            # Add to monitor
            self.monitor.add_alert_callback(alert_manager.handle_alert)
            
            # Trigger validation failures to generate alert
            config = {'llm': {'service': 'invalid_service'}}
            validator = ConfigValidator()
            
            for _ in range(3):
                validator.validate_llm_config(config)
                time.sleep(0.1)
            
            # Check that alert file was created and contains alert
            assert alert_file.exists()
            
            with open(alert_file, 'r') as f:
                content = f.read()
                assert content.strip()  # File should not be empty
                
                # Parse JSON alert record
                alert_record = json.loads(content.strip().split('\n')[0])
                assert 'alert_type' in alert_record
                assert 'details' in alert_record
                assert alert_record['details']['service'] == 'llm'
    
    def test_concurrent_monitoring_operations(self):
        """Test concurrent monitoring operations for thread safety."""
        import threading
        
        config = {'llm': {'service': 'openai'}, 'openai': {'api_key': 'sk-test'}}
        validator = ConfigValidator()
        
        results = []
        
        def worker(worker_id):
            try:
                for i in range(10):
                    result = validator.validate_llm_config(config)
                    time.sleep(0.001)  # Very small delay
                results.append(f"worker_{worker_id}_success")
            except Exception as e:
                results.append(f"worker_{worker_id}_error: {e}")
        
        # Start multiple worker threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check all workers completed successfully
        assert len(results) == 5
        assert all('success' in result for result in results)
        
        # Check events were recorded correctly
        events = self.monitor.get_recent_events(limit=200)
        validation_events = [e for e in events if 'validation' in e.event_type]
        
        # Should have events from all workers (5 workers * 10 operations * 2 events each)
        assert len(validation_events) == 100
        
        # Check metrics consistency
        metrics = self.monitor.get_metrics_summary()
        validation_counters = [v for k, v in metrics['counters'].items() if 'validation' in k]
        assert sum(validation_counters) == 50  # 5 workers * 10 validations each
    
    def test_monitoring_with_disabled_features(self):
        """Test monitoring system with disabled features."""
        # Create monitor with disabled metrics and alerts
        disabled_monitor = initialize_config_monitor(
            enable_metrics=False,
            enable_alerts=False
        )
        
        config = {'llm': {'service': 'openai'}, 'openai': {'api_key': 'sk-test'}}
        validator = ConfigValidator()
        
        # Perform operations
        for _ in range(3):
            validator.validate_llm_config(config)
        
        # Events should still be recorded
        events = disabled_monitor.get_recent_events(limit=10)
        assert len(events) > 0
        
        # But metrics should not be collected
        metrics = disabled_monitor.get_metrics_summary()
        assert len(metrics['counters']) == 0
        assert len(metrics['gauges']) == 0
        assert len(metrics['histograms']) == 0
    
    def test_error_handling_in_monitoring_pipeline(self):
        """Test error handling throughout the monitoring pipeline."""
        # Test with configuration that causes validation errors
        config = {
            'llm': {'service': 'openai'},
            'openai': {}  # Missing required fields
        }
        
        validator = ConfigValidator()
        
        # This should not raise exceptions despite validation errors
        result = validator.validate_llm_config(config)
        assert not result.is_valid
        assert len(result.errors) > 0
        
        # Monitoring should still capture the events
        events = self.monitor.get_recent_events(limit=10)
        validation_events = [e for e in events if 'validation' in e.event_type]
        assert len(validation_events) >= 2
        
        # Error details should be captured
        complete_event = next(e for e in validation_events if e.event_type == 'validation_complete')
        assert complete_event.success is False
        assert complete_event.details['error_count'] > 0
    
    def test_monitoring_performance_impact(self):
        """Test that monitoring doesn't significantly impact performance."""
        config = {'llm': {'service': 'openai'}, 'openai': {'api_key': 'sk-test'}}
        validator = ConfigValidator()
        
        # Measure time with monitoring
        start_time = time.time()
        for _ in range(100):
            validator.validate_llm_config(config)
        monitoring_time = time.time() - start_time
        
        # Create validator without monitoring integration (mock the monitor)
        with patch('utils.config.config_validator.get_config_monitor') as mock_monitor:
            mock_monitor.return_value = Mock()
            
            start_time = time.time()
            for _ in range(100):
                validator.validate_llm_config(config)
            no_monitoring_time = time.time() - start_time
        
        # Monitoring overhead should be minimal (less than 50% increase)
        overhead_ratio = monitoring_time / no_monitoring_time
        assert overhead_ratio < 1.5, f"Monitoring overhead too high: {overhead_ratio:.2f}x"
        
        # Check that events were actually recorded
        events = self.monitor.get_recent_events(limit=300)
        assert len(events) >= 200  # Should have start and complete events for each validation


if __name__ == "__main__":
    pytest.main([__file__])