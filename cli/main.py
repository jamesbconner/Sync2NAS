"""
Main entry point for the Sync2NAS CLI.
- Sets up the Click command group and context object.
- Dynamically loads all CLI commands from this directory.
- Includes comprehensive configuration validation and health checking.
"""
import os
import sys
import importlib
import click
import logging
import rich_click as rclick
from utils.sync2nas_config import load_configuration
from utils.logging_config import setup_logging
from services.db_factory import create_db_service
from services.sftp_service import SFTPService
from services.tmdb_service import TMDBService
from services.llm_factory import create_llm_service, LLMServiceCreationError

logger = logging.getLogger(__name__)

@rclick.group()
@click.option('--logfile', '-l', type=click.Path(writable=True), help="Log to file")
@click.option('--verbose', '-v', count=True, help="Set verbosity level (-v = INFO, -vv = DEBUG)")
@click.option('--config', '-c', type=click.Path(exists=True), default='./config/sync2nas_config.ini', help="Path to config file")
@click.option('--dry-run', is_flag=True, help="Run in dry-run mode (read-only database, no file system changes)")
@click.option('--skip-validation', is_flag=True, help="Skip configuration validation and health checks (for troubleshooting)")
@click.pass_context
def sync2nas_cli(ctx: click.Context, verbose: int, logfile: str, config: str, dry_run: bool, skip_validation: bool) -> None:
    """
    Main CLI group. Sets up the context object with configuration, database, SFTP, TMDB, and LLM services.
    All subcommands share this context.
    
    Includes comprehensive configuration validation and health checking to ensure
    all services are properly configured before use.

    Args:
        ctx (click.Context): Click context for Click command group.
        verbose (int): Verbosity level (-v = INFO, -vv = DEBUG).
        logfile (str): Path to log file.
        config (str): Path to configuration file.
        dry_run (bool): Run in dry-run mode (read-only operations).
        skip_validation (bool): Skip configuration validation (for troubleshooting).

    Returns:
        None
    """
    # If the context object is already set, return it without reinitializing it
    if ctx.obj and all(k in ctx.obj for k in ("config", "db", "tmdb", "sftp", "anime_tv_path", "incoming_path", "llm_service", "dry_run")):
        return
    else:
        if ctx.obj is not None:
            logger.debug(f"Context object incomplete, reinitializing")
    
    if logfile:
        os.makedirs(os.path.dirname(logfile), exist_ok=True)
        
    setup_logging(verbosity=verbose, logfile=logfile)

    # Check if this is a config-check command - allow it to run with minimal validation
    is_config_check = len(sys.argv) > 1 and 'config-check' in sys.argv

    
    # Load configuration and initialize shared services
    try:
        logger.info("Loading configuration and initializing services")
        cfg = load_configuration(config)
        
        # Initialize services with proper error handling and validation
        llm_service = None
        db_service = None
        sftp_service = None
        tmdb_service = None
        anime_tv_path = None
        incoming_path = None
        
        # LLM Service - Critical for most operations
        try:
            if skip_validation:
                logger.warning("Skipping LLM service validation (--skip-validation flag)")
                from services.llm_factory import create_llm_service_legacy
                llm_service = create_llm_service_legacy(cfg)
            else:
                # Use full validation including health checks for startup
                llm_service = create_llm_service(cfg, validate_health=not is_config_check, startup_mode=not is_config_check)
                logger.info("✓ LLM service initialized and validated successfully")
        
        except LLMServiceCreationError as e:
            if is_config_check:
                # For config-check, we want to capture the error but continue
                logger.debug(f"LLM service validation failed (config-check mode): {e}")
                llm_service = None
            else:
                # For normal startup, LLM service failure is critical
                logger.error(f"❌ LLM service initialization failed: {e}")
                if not skip_validation:
                    # Exit with error code for startup failures
                    sys.exit(1)
        
        except Exception as e:
            logger.error(f"❌ Unexpected error creating LLM service: {e}")
            if not is_config_check and not skip_validation:
                sys.exit(1)
        
        # Database Service
        try:
            db_service = create_db_service(cfg, read_only=dry_run)
            logger.info("✓ Database service initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️  Database service initialization failed: {e}")
            if not is_config_check:
                logger.error("Database service is required for most operations")
        
        # SFTP Service
        try:
            sftp_service = SFTPService(
                cfg["SFTP"]["host"], 
                int(cfg["SFTP"]["port"]), 
                cfg["SFTP"]["username"], 
                cfg["SFTP"]["ssh_key_path"], 
                llm_service=llm_service
            )
            logger.info("✓ SFTP service initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️  SFTP service initialization failed: {e}")
        
        # TMDB Service
        try:
            tmdb_service = TMDBService(cfg["TMDB"]["api_key"])
            logger.info("✓ TMDB service initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️  TMDB service initialization failed: {e}")
        
        # Configuration paths
        try:
            anime_tv_path = cfg["Routing"]["anime_tv_path"]
            incoming_path = cfg["Transfers"]["incoming"]
            logger.debug("✓ Configuration paths loaded successfully")
        except Exception as e:
            logger.warning(f"⚠️  Failed to load configuration paths: {e}")
        
        # Create context object with all services
        ctx.obj = {
            "config": cfg,
            "db": db_service,
            "llm_service": llm_service,
            "sftp": sftp_service,
            "tmdb": tmdb_service,
            "anime_tv_path": anime_tv_path,
            "incoming_path": incoming_path,
            "dry_run": dry_run,
            "skip_validation": skip_validation
        }
        
        # Log successful initialization
        services_status = []
        if llm_service: services_status.append("LLM")
        if db_service: services_status.append("Database")
        if sftp_service: services_status.append("SFTP")
        if tmdb_service: services_status.append("TMDB")
        
        if services_status:
            logger.info(f"✓ Services initialized: {', '.join(services_status)}")
        
    except Exception as e:
        logger.error(f"❌ Critical error during initialization: {e}")
        
        # For config-check command, we still want to proceed with minimal context
        if is_config_check:
            ctx.obj = {
                "config": None,
                "db": None,
                "llm_service": None,
                "sftp": None,
                "tmdb": None,
                "anime_tv_path": None,
                "incoming_path": None,
                "dry_run": dry_run,
                "skip_validation": skip_validation,
                "config_error": str(e),
                "config_path": config
            }
        else:
            # For normal operations, critical initialization failure should exit
            if not skip_validation:
                logger.error("Use --skip-validation flag to bypass validation for troubleshooting")
                sys.exit(1)
            else:
                # Create minimal context for troubleshooting mode
                ctx.obj = {
                    "config": None,
                    "db": None,
                    "llm_service": None,
                    "sftp": None,
                    "tmdb": None,
                    "anime_tv_path": None,
                    "incoming_path": None,
                    "dry_run": dry_run,
                    "skip_validation": skip_validation,
                    "config_error": str(e),
                    "config_path": config
                }

def validate_context_for_command(ctx: click.Context, required_services: list = None) -> bool:
    """
    Validate that the context object has the required services for a command.
    
    Args:
        ctx: Click context object
        required_services: List of required service names (e.g., ['llm_service', 'db'])
        
    Returns:
        bool: True if context is valid, False otherwise
    """
    if not ctx.obj:
        click.secho("❌ Error: No context object found. Configuration may have failed to load.", fg="red", bold=True)
        if ctx.obj and "config_error" in ctx.obj:
            click.secho(f"Configuration error: {ctx.obj['config_error']}", fg="red")
        return False
    
    if required_services:
        missing_services = []
        for service in required_services:
            if not ctx.obj.get(service):
                missing_services.append(service)
        
        if missing_services:
            click.secho(f"❌ Error: Required services not available: {', '.join(missing_services)}", fg="red", bold=True)
            click.secho("This may be due to configuration issues. Try running 'config-check' to diagnose.", fg="yellow")
            return False
    
    return True


def get_service_from_context(ctx: click.Context, service_name: str, required: bool = True):
    """
    Get a service from the context object with proper error handling.
    
    Args:
        ctx: Click context object
        service_name: Name of the service to retrieve
        required: Whether the service is required (raises error if missing)
        
    Returns:
        Service instance or None
    """
    if not ctx.obj:
        if required:
            click.secho("❌ Error: No context object available", fg="red", bold=True)
            sys.exit(1)
        return None
    
    service = ctx.obj.get(service_name)
    if required and not service:
        click.secho(f"❌ Error: {service_name} not available", fg="red", bold=True)
        click.secho("Try running 'config-check' to diagnose configuration issues", fg="yellow")
        sys.exit(1)
    
    return service


# Dynamic discovery loop: auto-register all CLI commands in this directory
COMMAND_DIR = os.path.dirname(__file__)
for filename in os.listdir(COMMAND_DIR):
    # Only import .py files that are not main.py or __init__.py
    if filename.endswith(".py") and filename not in {"main.py", "__init__.py"}:
        command_name = filename[:-3]
        module_name = f"cli.{command_name}"
        try:
            module = importlib.import_module(module_name)
            cli_function = getattr(module, command_name, None)
            if cli_function:
                sync2nas_cli.add_command(cli_function)
            else:
                logger.debug(f"No command function found in {module_name}")
        except Exception as e:
            logger.debug(f"Failed to import {module_name}: {e}")
    else:
        logger.debug(f"Skipping non-Python file: {filename}")

if __name__ == '__main__':
    sync2nas_cli()