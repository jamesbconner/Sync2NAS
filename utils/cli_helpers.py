#!/usr/bin/env python3
"""
CLI helper utilities for consistent error handling and service validation.
"""

import click
from rich.console import Console
from typing import List, Optional, Dict, Any

console = Console()


def validate_context_for_command(ctx: click.Context, required_services: Optional[List[str]] = None) -> bool:
    """
    Validate context has required services with helpful error messages.
    
    Args:
        ctx: Click context object
        required_services: List of required service names (e.g., ['sftp', 'db', 'tmdb'])
    
    Returns:
        bool: True if validation passes, False otherwise
    """
    if not ctx.obj:
        console.print("❌ No context available. Configuration may not be loaded properly.", style="red")
        console.print("💡 Try running: python sync2nas.py config-monitor validate", style="yellow")
        return False
    
    if required_services:
        missing = [s for s in required_services if not ctx.obj.get(s)]
        if missing:
            console.print(f"❌ Required services unavailable: {', '.join(missing)}", style="red")
            _suggest_service_fixes(missing)
            return False
    
    return True


def get_service_from_context(ctx: click.Context, service_name: str, required: bool = True) -> Optional[Any]:
    """
    Get a service from context with proper error handling.
    
    Args:
        ctx: Click context object
        service_name: Name of the service to retrieve
        required: Whether the service is required (affects error handling)
    
    Returns:
        Service instance or None if not available
    """
    if not ctx.obj:
        if required:
            console.print("❌ No context available. Configuration may not be loaded properly.", style="red")
            console.print("💡 Try running: python sync2nas.py config-monitor validate", style="yellow")
            raise click.Abort()
        return None
    
    service = ctx.obj.get(service_name)
    if not service and required:
        console.print(f"❌ {service_name.upper()} service not available. Please check your configuration.", style="red")
        _suggest_service_fixes([service_name])
        raise click.Abort()
    
    return service


def _suggest_service_fixes(missing_services: List[str]) -> None:
    """Provide specific suggestions for fixing missing services."""
    suggestions = {
        'sftp': [
            "Check your configuration file for the [sftp] section",
            "Required: host, username, ssh_key_path",
            "Optional: port (defaults to 22)",
            "Run 'python sync2nas.py config-monitor validate --service sftp' for detailed diagnosis"
        ],
        'tmdb': [
            "Check your configuration file for the [tmdb] section", 
            "Required: api_key (get from https://www.themoviedb.org/settings/api)",
            "Run 'python sync2nas.py config-monitor validate --service tmdb' for detailed diagnosis"
        ],
        'db': [
            "Check your configuration file for the [database] section",
            "Supported types: sqlite, postgresql, milvus", 
            "Run 'python sync2nas.py config-monitor validate' for detailed diagnosis"
        ],
        'llm_service': [
            "Check your configuration file for the [llm] section",
            "Ensure the selected service (ollama/openai/anthropic) is properly configured",
            "Run 'python sync2nas.py config-monitor validate' for detailed diagnosis",
            "Run 'python sync2nas.py config-monitor health-check' to test connectivity"
        ]
    }
    
    console.print("💡 Configuration suggestions:", style="yellow")
    for service in missing_services:
        if service in suggestions:
            for suggestion in suggestions[service]:
                console.print(f"   - {suggestion}", style="yellow")
        else:
            console.print(f"   - Check configuration for {service} service", style="yellow")
    
    console.print("   - Run 'python sync2nas.py config-monitor validate' for comprehensive diagnosis", style="yellow")


def display_configuration_error(error_message: str, service_name: Optional[str] = None) -> None:
    """
    Display a configuration error with helpful suggestions.
    
    Args:
        error_message: The error message to display
        service_name: Optional service name for specific suggestions
    """
    console.print(f"❌ Configuration Error: {error_message}", style="red")
    
    if service_name:
        _suggest_service_fixes([service_name])
    else:
        console.print("💡 Try running: python sync2nas.py config-monitor validate", style="yellow")


def pass_sync2nas_context(f):
    """
    Decorator that validates sync2nas context is available before executing command.
    
    This decorator ensures that the context object is properly initialized
    and provides helpful error messages if not.
    
    Note: This should be used AFTER @click.pass_context decorator.
    """
    import functools
    
    @functools.wraps(f)
    def wrapper(ctx: click.Context, *args, **kwargs):
        if not validate_context_for_command(ctx):
            raise click.Abort()
        return f(ctx, *args, **kwargs)
    
    return wrapper