import time
import json
import click
import logging
from models.episode import Episode
from services.db_implementations.db_interface import DatabaseInterface
from services.tmdb_service import TMDBService
from rich import print as rprint


@click.command(name="bootstrap-episodes")
@click.option('--dry-run', is_flag=True, help="Simulate episode population without writing to database")
@click.pass_context
def bootstrap_episodes(ctx, dry_run):
    """
    CLI command to populate episodes for all shows in the tv_shows table from TMDB.
    """

    logger = logging.getLogger(__name__)
    db: DatabaseInterface = ctx.obj["db"]
    tmdb: TMDBService = ctx.obj["tmdb"]

    added, skipped, failed = [], [], []
    start = time.time()

    shows = db.get_all_shows()

    for show in shows:
        tmdb_id = show["tmdb_id"]
        tmdb_name = show["tmdb_name"]

        if db.episodes_exist(tmdb_id):
            logger.info(f"⏭️ Skipping {tmdb_name}: already has episodes.")
            skipped.append(tmdb_name)
            continue

        logger.info(f"🔍 Parsing episodes for: {tmdb_name}")
        try:
            episode_groups = json.loads(show["tmdb_episode_groups"]) if show["tmdb_episode_groups"] else []
            season_count = show["tmdb_season_count"] or 0
            episode_count = show["tmdb_episode_count"] or 0

            episodes = Episode.parse_from_tmdb(
                tmdb_id=tmdb_id,
                tmdb_service=tmdb,
                episode_groups=episode_groups,
                season_count=season_count
            )

            if dry_run:
                logger.info(f"[DRY RUN] Would add {len(episodes)} episodes for {tmdb_name}")
            else:
                db.add_episodes(episodes)
                logger.info(f"✅ Added {len(episodes)} episodes for {tmdb_name}")
            added.append(tmdb_name)

        except Exception as e:
            logger.exception(f"❌ Failed to process {tmdb_name}: {e}")
            failed.append(tmdb_name)

        time.sleep(2)

    duration = time.time() - start
    logger.info(f"Episode bootstrap complete in {duration:.2f} seconds")

    click.echo("\n📦 Episode Import Summary")
    if added:
        click.secho(f"✅ Added: {len(added)}", fg="green")
    if skipped:
        click.secho(f"⏭️ Skipped: {len(skipped)}", fg="yellow")
    if failed:
        click.secho(f"❌ Failed: {len(failed)}", fg="red")
    click.secho(f"🧾 Total processed: {len(shows)}", bold=True)
