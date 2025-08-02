import click
import logging

logger = logging.getLogger(__name__)

"""
CLI command to back up the database, with dry-run support.
"""

@click.command('backup-db', help='Backs up the database.')
@click.pass_context
def backup_db(ctx):
    """Backs up the database."""
    dry_run = ctx.obj["dry_run"]
    db_service = ctx.obj['db']
    db_config = ctx.obj['config']['Database']

    if dry_run:
        logger.info("[DRY RUN] Simulating database backup.")
        logger.info(f"[DRY RUN] Would attempt to back up the {db_config['type']} database.")
        logger.info("[DRY RUN] No actual changes will be made.")
        return

    try:
        backup_path = db_service.backup_database()
        logger.info(f"Database backup created successfully: {backup_path}")
    except Exception as e:
        logger.error(f"Database backup failed: {e}") 