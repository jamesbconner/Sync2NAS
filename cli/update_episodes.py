import click
import logging
from utils.cli_helpers import pass_sync2nas_context
from models.episode import Episode
from models.show import Show
from utils.episode_updater import refresh_episodes_for_show

logger = logging.getLogger(__name__)

"""
CLI command to refresh episodes for a show from TMDB and update the local database.
"""

@click.command("update-episodes", help="Refresh episodes for a show from TMDB and update the local database.")
@click.argument("show_name", required=False)
@click.option("--tmdb-id", type=int, help="TMDB ID of the show (overrides show_name search)")
@pass_sync2nas_context
def update_episodes(ctx: click.Context, show_name: str, tmdb_id: int) -> None:
    """
    Refresh episodes for a show from TMDB and update the local database.

    Args:
        ctx (click.Context): Click context containing shared config and services.
        show_name (str): Name of the show to update (optional if tmdb_id provided).
        tmdb_id (int): TMDB ID of the show (overrides show_name search).
        dry_run (bool): Simulate without writing to database.

    Returns:
        None. Prints results to the console and exits on error.
    """
    if not ctx.obj:
        click.secho("❌ Error: No context object found", fg="red", bold=True)
        return
    
    logger.info("Starting update process")
    dry_run = ctx.obj["dry_run"]
    db = ctx.obj["db"]
    tmdb = ctx.obj["tmdb"]

    if not show_name and not tmdb_id:
        logger.error("Missing show_name and tmdb_id")
        click.secho("❌ You must provide either show_name or --tmdb-id", fg="red")
        return

    logger.debug(f"Inputs show_name={show_name}, tmdb_id={tmdb_id}")

    # Step 1: Resolve show record from DB
    if tmdb_id:
        logger.debug(f"Fetching show by tmdb_id {tmdb_id}")
        show_row = db.get_show_by_tmdb_id(tmdb_id)
        if not show_row:
            logger.warning(f"No show found in DB for tmdb_id={tmdb_id}")
            click.secho(f"❌ No show found in DB for TMDB ID {tmdb_id}", fg="red")
            return
    else:
        logger.debug(f"Fetching show by show_name '{show_name}'")
        show_row = db.get_show_by_name_or_alias(show_name)
        if not show_row:
            logger.warning(f"No show found in DB for show_name='{show_name}'")
            click.secho(f"❌ No show found in DB for show name '{show_name}'", fg="red")
            return

    show = Show.from_db_record(show_row)
    logger.info(f"Found show {show.sys_name} (tmdb_id={show.tmdb_id})")
    click.secho(f"🔎 Found show: {show.sys_name} (TMDB ID {show.tmdb_id})", fg="cyan")

    # Step 2: Fetch fresh episode data from TMDB
    logger.debug(f"Calling refresh_episodes_for_show for {show.sys_name} (tmdb_id={show.tmdb_id})")
    num_episodes = refresh_episodes_for_show(db, tmdb, show, dry_run)
    if num_episodes == 0:
        click.secho(f"❌ Failed to fetch or update episodes for {show.sys_name}", fg="red")
        return
    click.secho(f"🎞️ Fetched {num_episodes} episodes from TMDB", fg="cyan")
    if dry_run:
        click.secho("[DRY RUN] Skipping database update.", fg="yellow")
    else:
        click.secho(f"✅ {num_episodes} episodes added/updated for {show.sys_name}", fg="green")