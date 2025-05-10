import click
import logging
from utils.cli_helpers import pass_sync2nas_context
from models.episode import Episode
from models.show import Show

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
    logger.debug(f"cli/update_episodes.py::update_episodes - Calling tmdb.get_show_details({show.tmdb_id})")
    details = tmdb.get_show_details(show.tmdb_id)
    if not details or "info" not in details:
        logger.error(f"cli/update_episodes.py::update_episodes - Failed to get TMDB details for {show.tmdb_id}")
        click.secho(f"❌ Failed to get TMDB details for {show.tmdb_id}", fg="red")
        return

    episode_groups = details.get("episode_groups", {}).get("results", [])
    season_count = details["info"].get("number_of_seasons", 0)
    logger.debug(f"cli/update_episodes.py::update_episodes - TMDB returned season_count={season_count}")

    episodes = Episode.parse_from_tmdb(show.tmdb_id, tmdb, episode_groups, season_count)

    logger.info(f"cli/update_episodes.py::update_episodes - Parsed {len(episodes)} episodes from TMDB")
    click.secho(f"🎞️ Fetched {len(episodes)} episodes from TMDB", fg="cyan")

    # Step 3: Update DB
    if dry_run:
        logger.info("cli/update_episodes.py::update_episodes - Dry run: skipping db.add_episodes()")
        click.secho("[DRY RUN] Skipping database update.", fg="yellow")
    else:
        logger.debug(f"cli/update_episodes.py::update_episodes - Writing {len(episodes)} episodes to database")
        db.add_episodes(episodes)
        logger.info(f"cli/update_episodes.py::update_episodes - Completed update for {show.sys_name}")
        click.secho(f"✅ {len(episodes)} episodes added/updated for {show.sys_name}", fg="green")