"""
CLI command to initialize the SQLite database.
"""
import click
from services.db_implementations.db_interface import DatabaseInterface

@click.command()
@click.pass_context
def init_db(ctx):
    """Initialize the SQLite database."""
    db = ctx.obj["db"]
    db.initialize()