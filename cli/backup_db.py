import click
import logging

logger = logging.getLogger(__name__)

@click.command('backup-db', help='Backs up the database.')
@click.option('--dry-run', is_flag=True, help='Simulate the backup without making changes.')
@click.pass_context
def backup_db(ctx, dry_run):
    """Backs up the database."""
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