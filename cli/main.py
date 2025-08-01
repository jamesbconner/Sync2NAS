"""
Main entry point for the Sync2NAS CLI.
- Sets up the Click command group and context object.
- Dynamically loads all CLI commands from this directory.
"""
import os
import importlib
import click
import logging
import rich_click as rclick
from utils.sync2nas_config import load_configuration
from utils.logging_config import setup_logging
from services.db_factory import create_db_service
from services.sftp_service import SFTPService
from services.tmdb_service import TMDBService
from services.llm_factory import create_llm_service

@rclick.group()
@click.option('--logfile', '-l', type=click.Path(writable=True), help="Log to file")
@click.option('--verbose', '-v', count=True, help="Set verbosity level (-v = INFO, -vv = DEBUG)")
@click.option('--config', '-c', type=click.Path(exists=True), default='./config/sync2nas_config.ini', help="Path to config file")
@click.option('--dry-run', is_flag=True, help="Run in dry-run mode (read-only database, no file system changes)")
@click.pass_context
def sync2nas_cli(ctx: click.Context, verbose: int, logfile: str, config: str, dry_run: bool) -> None:
    """
    Main CLI group. Sets up the context object with configuration, database, SFTP, TMDB, and LLM services.
    All subcommands share this context.

    Args:
        ctx (click.Context): Click context for Click command group.
        verbose (int): Verbosity level (-v = INFO, -vv = DEBUG).
        logfile (str): Path to log file.
        config (str): Path to configuration file.

    Returns:
        None
    """
    # If the context object is already set, return it without reinitializing it
    if ctx.obj and all(k in ctx.obj for k in ("config", "db", "tmdb", "sftp", "anime_tv_path", "incoming_path", "llm_service", "dry_run")):
        return
    else:
        if ctx.obj is not None:
            print(f"ctx.obj: {ctx.obj}")
            print(f"ctx.obj does not contain all required keys")
    
    if logfile:
        os.makedirs(os.path.dirname(logfile), exist_ok=True)
        
    setup_logging(verbosity=verbose, logfile=logfile)

    # Load configuration and initialize shared services
    cfg = load_configuration(config)
    llm_service = create_llm_service(cfg)
    db_service = create_db_service(cfg, read_only=dry_run)
    ctx.obj = {
        "config": cfg,
        "db": db_service,
        "llm_service": llm_service,
        "sftp": SFTPService(cfg["SFTP"]["host"], int(cfg["SFTP"]["port"]), cfg["SFTP"]["username"], cfg["SFTP"]["ssh_key_path"], llm_service=llm_service),
        "tmdb": TMDBService(cfg["TMDB"]["api_key"]),
        "anime_tv_path": cfg["Routing"]["anime_tv_path"],
        "incoming_path": cfg["Transfers"]["incoming"],
        "dry_run": dry_run
    }

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
                pass  # No command function found in module
        except Exception as e:
            print(f"Failed to import {module_name}: {e}")
            pass
    else:
        pass

if __name__ == '__main__':
    sync2nas_cli()