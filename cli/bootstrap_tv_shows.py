import os
import time
import click
import logging
from services.db_implementations.db_interface import DatabaseInterface
from services.tmdb_service import TMDBService
from models.show import Show

"""
CLI command for one-time population of the tv_shows table from the anime_tv_path directory, using TMDB for metadata.
"""

@click.command(name="bootstrap-tv-shows")
@click.pass_context
def bootstrap_tv_shows(ctx):
    """One-time population of tv_shows table from anime_tv_path."""
    if not ctx.obj:
        click.secho("❌ Error: No context object found", fg="red", bold=True)
        return
    
    dry_run = ctx.obj["dry_run"]
    logger = logging.getLogger(__name__)
    db: DatabaseInterface = ctx.obj["db"]
    tmdb: TMDBService = ctx.obj["tmdb"]
    anime_tv_path = ctx.obj["anime_tv_path"]

    added, skipped, failed = [], [], []
    start_time = time.time()

    for folder_name in sorted(os.listdir(anime_tv_path)):
        sys_name = folder_name.strip()
        sys_path = os.path.join(anime_tv_path, sys_name)
        if not os.path.isdir(sys_path):
            continue

        try:
            if db.show_exists(sys_name):
                logger.info(f"⏭️ Skipping: {sys_name}")
                skipped.append(sys_name)
                continue

            results = tmdb.search_show(sys_name)
            if not results or not results.get("results"):
                logger.warning(f"No TMDB results for: {sys_name}")
                failed.append(sys_name)
                continue

            details = tmdb.get_show_details(results["results"][0]["id"])
            if not details or "info" not in details:
                failed.append(sys_name)
                continue

            show = Show.from_tmdb(details, sys_name=sys_name, sys_path=sys_path)
            if dry_run:
                logger.info(f"[DRY RUN] Would add show: {sys_name}")
            else:
                db.add_show(show)
                logger.info(f"✅ Added: {show.tmdb_name}")
            added.append(sys_name)

        except Exception as e:
            logger.exception(f"❌ Failed to process: {sys_name}")
            failed.append(sys_name)

    duration = time.time() - start_time
    if dry_run:
        click.echo(f"\n📦 [DRY RUN] Summary (Duration: {duration:.2f}s)")
    click.echo(f"\n📦 Summary (Duration: {duration:.2f}s)")
    click.secho(f"✅ Added: {len(added)}", fg="green")
    click.secho(f"⏭️ Skipped: {len(skipped)}", fg="yellow")
    click.secho(f"❌ Failed: {len(failed)}", fg="red")
