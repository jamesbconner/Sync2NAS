import click
import logging
from utils.cli_helpers import pass_sync2nas_context
from models.episode import Episode
from models.show import Show
from utils.episode_updater import refresh_episodes_for_show

logger = logging.getLogger(__name__)

@click.command("update-episodes", help="Refresh episodes for a show from TMDB and update the local database.")
@click.argument("show_name", required=False)
@click.option("--tmdb-id", type=int, help="TMDB ID of the show (overrides show_name search)")
@click.option("--dry-run", is_flag=True, help="Simulate without writing to database")
@pass_sync2nas_context
def update_episodes(ctx, show_name, tmdb_id, dry_run):
    """
    Refresh episodes for a show from TMDB and update the local database.

    You can provide either a SHOW_NAME (matched against sys_name or aliases) or a --tmdb-id.
    """
    logger.info("cli/update_episodes.py::update_episodes - Starting update process")
    db = ctx.obj["db"]
    tmdb = ctx.obj["tmdb"]

    if not show_name and not tmdb_id:
        logger.error("cli/update_episodes.py::update_episodes - Missing show_name and tmdb_id")
        click.secho("❌ You must provide either show_name or --tmdb-id", fg="red")
        return

    logger.debug(f"cli/update_episodes.py::update_episodes - Inputs show_name={show_name}, tmdb_id={tmdb_id}")

    # Step 1: Resolve show record from DB
    if tmdb_id:
        logger.debug(f"cli/update_episodes.py::update_episodes - Fetching show by tmdb_id {tmdb_id}")
        show_row = db.get_show_by_tmdb_id(tmdb_id)
        if not show_row:
            logger.warning(f"cli/update_episodes.py::update_episodes - No show found in DB for tmdb_id={tmdb_id}")
            click.secho(f"❌ No show found in DB for TMDB ID {tmdb_id}", fg="red")
            return
    else:
        logger.debug(f"cli/update_episodes.py::update_episodes - Fetching show by show_name '{show_name}'")
        show_row = db.get_show_by_name_or_alias(show_name)
        if not show_row:
            logger.warning(f"cli/update_episodes.py::update_episodes - No show found in DB for show_name='{show_name}'")
            click.secho(f"❌ No show found in DB for show name '{show_name}'", fg="red")
            return

    show = Show.from_db_record(show_row)
    logger.info(f"cli/update_episodes.py::update_episodes - Found show {show.sys_name} (tmdb_id={show.tmdb_id})")
    click.secho(f"🔎 Found show: {show.sys_name} (TMDB ID {show.tmdb_id})", fg="cyan")

    # Step 2: Fetch fresh episode data from TMDB
    logger.debug(f"cli/update_episodes.py::update_episodes - Calling refresh_episodes_for_show for {show.sys_name} (tmdb_id={show.tmdb_id})")
    num_episodes = refresh_episodes_for_show(db, tmdb, show, dry_run)
    if num_episodes == 0:
        click.secho(f"❌ Failed to fetch or update episodes for {show.sys_name}", fg="red")
        return
    click.secho(f"🎞️ Fetched {num_episodes} episodes from TMDB", fg="cyan")
    if dry_run:
        click.secho("[DRY RUN] Skipping database update.", fg="yellow")
    else:
        click.secho(f"✅ {num_episodes} episodes added/updated for {show.sys_name}", fg="green")