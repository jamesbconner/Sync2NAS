"""
CLI commands for configuration monitoring and health checking.

This module provides commands to check configuration health, view metrics,
and manage monitoring settings.
"""

import click
import json
import asyncio
from typing import Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.markup import escape

from utils.config.config_monitor import get_config_monitor, initialize_config_monitor
from utils.config.alert_handlers import create_default_alert_manager, create_email_alert_handler_from_env
from utils.config.health_checker import ConfigHealthChecker
from utils.config.config_validator import ConfigValidator
from utils.sync2nas_config import load_configuration

console = Console()


@click.group(name="config-monitor")
def config_monitor_group():
    """Configuration monitoring and health check commands."""
    pass


@config_monitor_group.command("health")
@click.option("--service", "-s", help="Check specific service (openai, anthropic, ollama)")
@click.option("--timeout", "-t", default=10, help="Health check timeout in seconds")
@click.option("--json-output", "--json", is_flag=True, help="Output results as JSON")
@click.pass_context
def health_check(ctx: click.Context, service: str, timeout: int, json_output: bool):
    """
    Perform health checks on LLM services.
    
    This command validates configuration and tests connectivity to LLM services.
    """
    try:
        # Load configuration
        config = ctx.obj.get("config") if ctx.obj else load_configuration()
        
        # Initialize health checker
        health_checker = ConfigHealthChecker(timeout=timeout)
        
        if service:
            # Check specific service
            if not json_output:
                console.print(f"🔍 Checking health for {service}...")
            result = health_checker.check_service_health_sync(service, config)
            results = [result]
        else:
            # Check all configured services
            if not json_output:
                console.print("🔍 Checking health for all configured LLM services...")
            results = health_checker.check_llm_health_sync(config)
        
        if json_output:
            # Output as JSON
            json_results = []
            for result in results:
                json_results.append({
                    "service": result.service,
                    "healthy": result.is_healthy,
                    "response_time_ms": result.response_time_ms,
                    "error_message": result.error_message,
                    "details": result.details
                })
            click.echo(json.dumps(json_results, indent=2))
        else:
            # Output as formatted table
            _display_health_results(results)
    
    except Exception as e:
        if json_output:
            click.echo(json.dumps({"error": str(e)}, indent=2))
        else:
            console.print(f"❌ Error performing health check: {e}", style="red")
        ctx.exit(1)


@config_monitor_group.command("validate")
@click.option("--service", "-s", help="Validate specific service (openai, anthropic, ollama)")
@click.option("--json-output", "--json", is_flag=True, help="Output results as JSON")
@click.pass_context
def validate_config(ctx: click.Context, service: str, json_output: bool):
    """
    Validate LLM configuration without performing connectivity tests.
    
    This command checks configuration completeness and correctness.
    """
    try:
        # Load configuration
        config = ctx.obj.get("config") if ctx.obj else load_configuration()
        
        # Initialize validator
        validator = ConfigValidator()
        
        if service:
            # Validate specific service
            if not json_output:
                console.print(f"🔍 Validating configuration for {service}...")
            result = validator.validate_service_config(service, config)
        else:
            # Validate all LLM configuration
            if not json_output:
                console.print("🔍 Validating LLM configuration...")
            result = validator.validate_llm_config(config)
        
        if json_output:
            # Output as JSON
            json_result = {
                "valid": result.is_valid,
                "errors": [
                    {
                        "section": error.section,
                        "key": error.key,
                        "message": error.message,
                        "suggestion": error.suggestion,
                        "error_code": error.error_code.value if error.error_code else None
                    }
                    for error in result.errors
                ],
                "warnings": result.warnings,
                "suggestions": result.suggestions
            }
            click.echo(json.dumps(json_result, indent=2))
        else:
            # Output as formatted display
            _display_validation_result(result)
    
    except Exception as e:
        if json_output:
            click.echo(json.dumps({"error": str(e)}, indent=2))
        else:
            console.print(f"❌ Error validating configuration: {e}", style="red")
        ctx.exit(1)


@config_monitor_group.command("metrics")
@click.option("--json-output", "--json", is_flag=True, help="Output metrics as JSON")
@click.option("--reset", is_flag=True, help="Reset metrics after displaying")
def show_metrics(json_output: bool, reset: bool):
    """
    Display configuration monitoring metrics.
    
    Shows collected metrics about configuration loading, validation, and health checks.
    """
    try:
        monitor = get_config_monitor()
        metrics = monitor.get_metrics_summary()
        
        if json_output:
            click.echo(json.dumps(metrics, indent=2))
        else:
            _display_metrics(metrics)
        
        if reset:
            # Reset metrics by reinitializing monitor
            initialize_config_monitor()
            console.print("✅ Metrics reset", style="green")
    
    except Exception as e:
        if json_output:
            click.echo(json.dumps({"error": str(e)}, indent=2))
        else:
            console.print(f"❌ Error retrieving metrics: {e}", style="red")


@config_monitor_group.command("events")
@click.option("--limit", "-l", default=20, help="Number of recent events to show")
@click.option("--type", "-t", "event_type", help="Filter by event type")
@click.option("--json-output", "--json", is_flag=True, help="Output events as JSON")
def show_events(limit: int, event_type: str, json_output: bool):
    """
    Display recent configuration events.
    
    Shows recent configuration loading, validation, and health check events.
    """
    try:
        monitor = get_config_monitor()
        events = monitor.get_recent_events(limit=limit, event_type=event_type)
        
        if json_output:
            json_events = []
            for event in events:
                json_events.append({
                    "event_type": event.event_type,
                    "timestamp": event.timestamp.isoformat(),
                    "service": event.service,
                    "success": event.success,
                    "duration_ms": event.duration_ms,
                    "error_code": event.error_code,
                    "error_message": event.error_message,
                    "details": event.details
                })
            click.echo(json.dumps(json_events, indent=2))
        else:
            _display_events(events)
    
    except Exception as e:
        if json_output:
            click.echo(json.dumps({"error": str(e)}, indent=2))
        else:
            console.print(f"❌ Error retrieving events: {e}", style="red")


@config_monitor_group.command("setup-alerts")
@click.option("--email", is_flag=True, help="Setup email alerts from environment variables")
@click.option("--test", is_flag=True, help="Send test alert")
def setup_alerts(email: bool, test: bool):
    """
    Setup alert handlers for configuration monitoring.
    
    Configure email alerts and other notification methods.
    """
    try:
        monitor = get_config_monitor()
        alert_manager = create_default_alert_manager()
        
        # Setup email alerts if requested
        if email:
            email_handler = create_email_alert_handler_from_env()
            if email_handler:
                alert_manager.add_handler(email_handler)
                console.print("✅ Email alert handler configured", style="green")
            else:
                console.print("❌ Email alert handler not configured - missing environment variables", style="red")
                console.print("Required environment variables:")
                console.print("  - SYNC2NAS_ALERT_SMTP_HOST")
                console.print("  - SYNC2NAS_ALERT_SMTP_PORT")
                console.print("  - SYNC2NAS_ALERT_SMTP_USERNAME")
                console.print("  - SYNC2NAS_ALERT_SMTP_PASSWORD")
                console.print("  - SYNC2NAS_ALERT_FROM_EMAIL")
                console.print("  - SYNC2NAS_ALERT_TO_EMAILS")
        
        # Register alert manager with monitor
        monitor.add_alert_callback(alert_manager.handle_alert)
        
        console.print(f"✅ Alert handlers configured: {', '.join(alert_manager.get_handler_names())}", style="green")
        
        # Send test alert if requested
        if test:
            test_details = {
                "alert_type": "test_alert",
                "service": "test",
                "timestamp": "2024-01-01T12:00:00",
                "message": "This is a test alert from Sync2NAS configuration monitoring"
            }
            alert_manager.handle_alert("Test Alert", test_details)
            console.print("✅ Test alert sent", style="green")
    
    except Exception as e:
        console.print(f"❌ Error setting up alerts: {e}", style="red")


def _display_health_results(results):
    """Display health check results in a formatted table."""
    table = Table(title="LLM Service Health Check Results")
    table.add_column("Service", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Response Time", justify="right")
    table.add_column("Details")
    
    for result in results:
        status = "✅ Healthy" if result.is_healthy else "❌ Unhealthy"
        status_style = "green" if result.is_healthy else "red"
        
        response_time = f"{result.response_time_ms:.1f}ms" if result.response_time_ms else "N/A"
        
        details = result.error_message if result.error_message else "OK"
        if result.details and result.is_healthy:
            detail_items = []
            for key, value in result.details.items():
                if key not in ['error_code', 'status_code']:
                    detail_items.append(f"{key}: {value}")
            if detail_items:
                details = ", ".join(detail_items)
        
        table.add_row(
            result.service,
            Text(status, style=status_style),
            response_time,
            details
        )
    
    console.print(table)


def _display_validation_result(result):
    """Display validation result in a formatted way."""
    if result.is_valid:
        console.print("✅ Configuration validation passed", style="green bold")
    else:
        console.print("❌ Configuration validation failed", style="red bold")
        
        if result.errors:
            console.print("\n🔍 Errors found:", style="red")
            for i, error in enumerate(result.errors, 1):
                error_text = f"{i}. "
                if error.key:
                    error_text += f"[{error.section}].{error.key}: {error.message}"
                else:
                    error_text += f"[{error.section}]: {error.message}"
                
                console.print(f"  {error_text}", style="red")
                
                if error.suggestion:
                    console.print(f"     💡 {error.suggestion}", style="yellow")
    
    if result.warnings:
        console.print("\n⚠️  Warnings:", style="yellow")
        for warning in result.warnings:
            console.print(f"  • {warning}", style="yellow")
    
    if result.suggestions:
        console.print("\n💡 Suggestions:", style="blue")
        for suggestion in result.suggestions:
            # Escape Rich markup to prevent interpretation of square brackets
            escaped_suggestion = escape(suggestion)
            console.print(f"  • {escaped_suggestion}", style="blue")


def _display_metrics(metrics):
    """Display metrics in a formatted way."""
    console.print(Panel.fit("📊 Configuration Monitoring Metrics", style="blue bold"))
    
    # Counters
    if metrics.get("counters"):
        console.print("\n📈 Counters:", style="cyan bold")
        for name, value in metrics["counters"].items():
            console.print(f"  {name}: {value}")
    
    # Gauges
    if metrics.get("gauges"):
        console.print("\n📊 Gauges:", style="green bold")
        for name, value in metrics["gauges"].items():
            console.print(f"  {name}: {value}")
    
    # Histograms
    if metrics.get("histograms"):
        console.print("\n📉 Response Times:", style="magenta bold")
        for name, stats in metrics["histograms"].items():
            console.print(f"  {name}:")
            console.print(f"    Count: {stats['count']}")
            console.print(f"    Min: {stats['min']:.1f}ms")
            console.print(f"    Max: {stats['max']:.1f}ms")
            console.print(f"    Avg: {stats['avg']:.1f}ms")
            console.print(f"    P95: {stats['p95']:.1f}ms")
    
    # Summary
    total_events = metrics.get("total_events", 0)
    retention_hours = metrics.get("collection_period_hours", 24)
    console.print(f"\n📋 Total Events: {total_events} (last {retention_hours} hours)", style="blue")


def _display_events(events):
    """Display events in a formatted table."""
    if not events:
        console.print("No events found", style="yellow")
        return
    
    table = Table(title="Recent Configuration Events")
    table.add_column("Time", style="cyan")
    table.add_column("Event", style="bold")
    table.add_column("Service")
    table.add_column("Status", style="bold")
    table.add_column("Duration", justify="right")
    table.add_column("Details")
    
    for event in events:
        timestamp = event.timestamp.strftime("%H:%M:%S")
        
        status = "✅ Success" if event.success else "❌ Failed"
        status_style = "green" if event.success else "red"
        
        duration = f"{event.duration_ms:.1f}ms" if event.duration_ms else "N/A"
        
        details = event.error_message if event.error_message else ""
        if event.details and not event.error_message:
            detail_items = []
            for key, value in event.details.items():
                if key not in ['operation_id']:
                    detail_items.append(f"{key}: {value}")
            details = ", ".join(detail_items[:2])  # Limit to first 2 items
        
        table.add_row(
            timestamp,
            event.event_type,
            event.service or "N/A",
            Text(status, style=status_style),
            duration,
            details
        )
    
    console.print(table)


# Export the command group for dynamic discovery
config_monitor = config_monitor_group

# Register the command group
if __name__ == "__main__":
    config_monitor_group()