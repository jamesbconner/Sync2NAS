"""
Configuration Health Check CLI Command

This module provides a CLI command to validate LLM configuration and test
connectivity to configured services. It supports checking all services or
specific services with detailed reporting.
"""

import asyncio
import logging
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from typing import List, Optional

from utils.config.config_validator import ConfigValidator
from utils.config.health_checker import ConfigHealthChecker
from utils.config.validation_models import ValidationResult, HealthCheckResult
from utils.sync2nas_config import load_configuration

logger = logging.getLogger(__name__)


@click.command("config-check")
@click.option("--service", "-s", type=click.Choice(['openai', 'anthropic', 'ollama', 'all']), 
              default='all', help="Specific service to check (default: all configured services)")
@click.option("--timeout", "-t", type=float, default=10.0, 
              help="Timeout for connectivity tests in seconds (default: 10.0)")
@click.option("--skip-connectivity", is_flag=True, 
              help="Skip connectivity tests, only validate configuration")
@click.option("--verbose", "-v", is_flag=True, 
              help="Show detailed configuration and diagnostic information")
@click.pass_context
def config_check(ctx: click.Context, service: str, timeout: float, skip_connectivity: bool, verbose: bool) -> None:
    """
    Validate LLM configuration and test service connectivity.
    
    This command validates your LLM configuration for completeness and correctness,
    then optionally tests connectivity to the configured services. It provides
    detailed error reporting and suggestions for fixing configuration issues.
    
    Examples:
        sync2nas config-check                    # Check all configured services
        sync2nas config-check -s openai          # Check only OpenAI configuration
        sync2nas config-check --skip-connectivity # Only validate config, no network tests
        sync2nas config-check -v                 # Show detailed diagnostic information
    
    Args:
        ctx (click.Context): Click context containing shared config and services.
        service (str): Specific service to check or 'all' for all services.
        timeout (float): Timeout for connectivity tests in seconds.
        skip_connectivity (bool): Skip connectivity tests.
        verbose (bool): Show detailed diagnostic information.
    
    Returns:
        None. Prints results to console and exits with appropriate code.
    """
    console = Console()
    
    # Load configuration directly (don't rely on context for this command)
    try:
        # Try to get config from context first, then fall back to loading directly
        config = None
        config_path = './config/sync2nas_config.ini'
        
        if ctx.obj and ctx.obj.get('config'):
            config = ctx.obj['config']
            logger.info("Using configuration from context")
        else:
            # Get config path from parent context if available
            if ctx.parent and hasattr(ctx.parent, 'params'):
                config_path = ctx.parent.params.get('config', config_path)
            
            config = load_configuration(config_path)
            logger.info(f"Loaded configuration from: {config_path}")
        
    except Exception as e:
        logger.exception(f"Failed to load configuration: {e}")
        console.print(Panel(
            f"❌ [bold red]Failed to load configuration:[/bold red]\n{str(e)}",
            title="Configuration Error",
            border_style="red"
        ))
        ctx.exit(1)
    
    # Initialize validator and health checker
    validator = ConfigValidator()
    health_checker = ConfigHealthChecker(timeout=timeout)
    
    console.print(Panel(
        f"🔍 [bold cyan]LLM Configuration Health Check[/bold cyan]\n"
        f"Service: {service}\n"
        f"Timeout: {timeout}s\n"
        f"Skip Connectivity: {skip_connectivity}",
        title="Configuration Check",
        border_style="cyan"
    ))
    
    # Step 1: Validate configuration
    console.print("\n📋 [bold yellow]Step 1: Configuration Validation[/bold yellow]")
    
    try:
        if service == 'all':
            validation_result = validator.validate_llm_config(config)
        else:
            validation_result = validator.validate_service_config(service, config)
        
        _display_validation_results(validation_result, console, verbose)
        
        if not validation_result.is_valid:
            console.print(Panel(
                "❌ [bold red]Configuration validation failed. Please fix the issues above before proceeding.[/bold red]",
                border_style="red"
            ))
            ctx.exit(1)
        
    except Exception as e:
        logger.exception(f"Configuration validation failed: {e}")
        console.print(Panel(
            f"❌ [bold red]Configuration validation error:[/bold red]\n{str(e)}",
            title="Validation Error",
            border_style="red"
        ))
        ctx.exit(1)
    
    # Step 2: Connectivity tests (if not skipped)
    if not skip_connectivity:
        console.print("\n🌐 [bold yellow]Step 2: Connectivity Tests[/bold yellow]")
        
        try:
            if service == 'all':
                health_results = health_checker.check_llm_health_sync(config)
            else:
                health_result = health_checker.check_service_health_sync(service, config)
                health_results = [health_result]
            
            _display_health_results(health_results, console, verbose)
            
            # Check if any health checks failed
            failed_checks = [r for r in health_results if not r.is_healthy]
            if failed_checks:
                console.print(Panel(
                    f"❌ [bold red]{len(failed_checks)} service(s) failed connectivity tests.[/bold red]",
                    border_style="red"
                ))
                ctx.exit(1)
            
        except Exception as e:
            logger.exception(f"Health check failed: {e}")
            console.print(Panel(
                f"❌ [bold red]Health check error:[/bold red]\n{str(e)}",
                title="Health Check Error",
                border_style="red"
            ))
            ctx.exit(1)
    else:
        console.print("⏭️  [yellow]Skipping connectivity tests as requested[/yellow]")
    
    # Success summary
    console.print(Panel(
        "✅ [bold green]All checks passed! Your LLM configuration is valid and services are reachable.[/bold green]",
        title="Success",
        border_style="green"
    ))


def _display_validation_results(result: ValidationResult, console: Console, verbose: bool) -> None:
    """
    Display configuration validation results.
    
    Args:
        result: ValidationResult object with validation details
        console: Rich console for formatted output
        verbose: Whether to show detailed information
    """
    if result.is_valid:
        console.print("✅ [green]Configuration validation passed[/green]")
        
        if result.warnings and verbose:
            console.print("\n⚠️  [yellow]Warnings:[/yellow]")
            for warning in result.warnings:
                console.print(f"  • {warning}")
        
        if result.suggestions and verbose:
            console.print("\n💡 [cyan]Suggestions:[/cyan]")
            for suggestion in result.suggestions:
                console.print(f"  • {suggestion}")
    else:
        console.print("❌ [red]Configuration validation failed[/red]")
        
        if result.errors:
            console.print("\n🚨 [bold red]Errors:[/bold red]")
            for error in result.errors:
                if error.section and error.key:
                    console.print(f"  • [{error.section}] {error.key}: {error.message}")
                elif error.section:
                    console.print(f"  • [{error.section}]: {error.message}")
                else:
                    console.print(f"  • {error.message}")
                
                if error.suggestion:
                    console.print(f"    💡 [cyan]{error.suggestion}[/cyan]")
        
        if result.warnings:
            console.print("\n⚠️  [yellow]Warnings:[/yellow]")
            for warning in result.warnings:
                console.print(f"  • {warning}")
        
        if result.suggestions:
            console.print("\n💡 [cyan]Suggestions:[/cyan]")
            for suggestion in result.suggestions:
                console.print(f"  • {suggestion}")


def _display_health_results(results: List[HealthCheckResult], console: Console, verbose: bool) -> None:
    """
    Display health check results.
    
    Args:
        results: List of HealthCheckResult objects
        console: Rich console for formatted output
        verbose: Whether to show detailed information
    """
    if not results:
        console.print("⚠️  [yellow]No health check results to display[/yellow]")
        return
    
    # Create summary table
    table = Table(title="Service Health Check Results", show_lines=True)
    table.add_column("Service", style="bold cyan")
    table.add_column("Status", style="bold")
    table.add_column("Response Time", style="yellow", justify="right")
    table.add_column("Details", style="white", overflow="fold")
    
    for result in results:
        # Determine status styling
        if result.is_healthy:
            status = "[green]✅ Healthy[/green]"
        else:
            status = "[red]❌ Unhealthy[/red]"
        
        # Format response time
        if result.response_time_ms is not None:
            response_time = f"{result.response_time_ms:.1f}ms"
        else:
            response_time = "N/A"
        
        # Format details
        if result.is_healthy:
            details = "Service is responding correctly"
            if verbose and result.details:
                detail_items = []
                for key, value in result.details.items():
                    if key not in ['error_code', 'exception_type']:
                        detail_items.append(f"{key}: {value}")
                if detail_items:
                    details = ", ".join(detail_items)
        else:
            details = result.error_message or "Unknown error"
        
        table.add_row(
            result.service.title(),
            status,
            response_time,
            details
        )
    
    console.print(table)
    
    # Show detailed error information for failed checks
    failed_results = [r for r in results if not r.is_healthy]
    if failed_results and verbose:
        console.print("\n🔍 [bold red]Detailed Error Information:[/bold red]")
        
        for result in failed_results:
            console.print(f"\n📍 [bold]{result.service.title()} Service:[/bold]")
            console.print(f"  Error: {result.error_message}")
            
            if result.details:
                for key, value in result.details.items():
                    if key == 'suggestion':
                        console.print(f"  💡 Suggestion: [cyan]{value}[/cyan]")
                    elif key == 'error_code':
                        console.print(f"  🏷️  Error Code: {value}")
                    elif key not in ['exception_type']:
                        console.print(f"  📋 {key.replace('_', ' ').title()}: {value}")
    
    # Show suggestions for failed checks
    failed_with_suggestions = [r for r in failed_results if r.details and r.details.get('suggestion')]
    if failed_with_suggestions and not verbose:
        console.print("\n💡 [cyan]Quick Fixes:[/cyan]")
        for result in failed_with_suggestions:
            suggestion = result.details.get('suggestion')
            if suggestion:
                console.print(f"  • {result.service.title()}: {suggestion}")


if __name__ == "__main__":
    # For testing purposes
    config_check()