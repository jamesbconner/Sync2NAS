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
@click.pass_context
def sync2nas_cli(ctx, verbose, logfile, config):
    # If the context object is already set, return it without reinitializing it
    if ctx.obj and all(k in ctx.obj for k in ("config", "db", "tmdb", "sftp", "anime_tv_path", "incoming_path", "llm_service")):
        return
    else:
        print(f"ctx.obj does not contain all required keys")
        print(f"ctx.obj: {ctx.obj}")
    
    if logfile:
        os.makedirs(os.path.dirname(logfile), exist_ok=True)
        
    setup_logging(verbosity=verbose, logfile=logfile)

    cfg = load_configuration(config)
    ctx.obj = {
        "config": cfg,
        "db": create_db_service(cfg),
        "sftp": SFTPService(cfg["SFTP"]["host"], int(cfg["SFTP"]["port"]), cfg["SFTP"]["username"], cfg["SFTP"]["ssh_key_path"]),
        "tmdb": TMDBService(cfg["TMDB"]["api_key"]),
        "anime_tv_path": cfg["Routing"]["anime_tv_path"],
        "incoming_path": cfg["Transfers"]["incoming"],
        "llm_service": create_llm_service(cfg)
    }

# Dynamic discovery loop
COMMAND_DIR = os.path.dirname(__file__)
for filename in os.listdir(COMMAND_DIR):
    if filename.endswith(".py") and filename not in {"main.py", "__init__.py"}:
        command_name = filename[:-3]
        module_name = f"cli.{command_name}"
        try:
            module = importlib.import_module(module_name)
            cli_function = getattr(module, command_name, None)
            if cli_function:
                sync2nas_cli.add_command(cli_function)
            else:
                pass
        except Exception as e:
            print(f"Failed to import {module_name}: {e}")
            pass
    else:
        pass

if __name__ == '__main__':
    sync2nas_cli()