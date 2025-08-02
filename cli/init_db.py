"""
CLI command to initialize the SQLite database.
"""
import click
from services.db_implementations.db_interface import DatabaseInterface

@click.command()
@click.pass_context
def init_db(ctx):
    """Initialize the SQLite database."""
    if not ctx.obj:
        click.secho("❌ Error: No context object found", fg="red", bold=True)
        return
    
    dry_run = ctx.obj["dry_run"]
    
    if dry_run:
        print("DRY RUN: Would initialize the database (read-only mode)")
        return
    
    db = ctx.obj["db"]
    db.initialize()
    print("Database initialized successfully.")