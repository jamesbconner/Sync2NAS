import click
from services.db_service import DBService

@click.command()
@click.pass_context
def init_db(ctx):
    """Initialize the SQLite database."""
    db = ctx.obj["db"]
    db.initialize()