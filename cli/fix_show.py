import logging
import click
from rich.console import Console
from rich.table import Table
from models.show import Show
from models.episode import Episode
from services.db_service import DBService
from services.tmdb_service import TMDBService


@click.command(name="fix-show")
@click.argument("show_name", required=True)
@click.option("--tmdb-id", type=int, help="TMDB ID to override the search results.")
@click.option("--dry-run", is_flag=True, help="Simulate correction without writing to database")
@click.pass_context
def fix_show(ctx, show_name, tmdb_id, dry_run):
    """Correct a misclassified show in the database."""
    # ToDo: add a --file option to read the show details from a file
    # ToDo: add an audit log for show corrections

    logger = logging.getLogger(__name__)
    db: DBService = ctx.obj["db"]
    tmdb: TMDBService = ctx.obj["tmdb"]
    anime_tv_path = ctx.obj["anime_tv_path"]
    console = Console()

    try:
        # Step 1: Get existing show metadata
        shows = db.get_all_shows()
        existing = next((s for s in shows if s["sys_name"].lower() == show_name.lower()), None)
        if not existing:
            click.secho(f"❌ No show found in database with sys_name: {show_name}", fg="red")
            return

        original_tmdb_id = existing["tmdb_id"]
        sys_name = existing["sys_name"]
        sys_path = existing["sys_path"]

        # Step 2: Either use override or do an interactive TMDB search
        if tmdb_id:
            logger.info(f"🔍 Using TMDB ID override: {tmdb_id}")
            details = tmdb.get_show_details(tmdb_id)
            if not details or "info" not in details:
                raise ValueError("Could not fetch details for TMDB ID")
        else:
            logger.info(f"🔍 Searching TMDB for: {show_name}")
            results = tmdb.search_show(show_name)
            matches = results.get("results", [])
            if not matches:
                click.secho(f"❌ No TMDB results found for: {show_name}", fg="red")
                return

            # Step 3: Show interactive options
            table = Table(title="Select Correct Show", show_lines=True)
            table.add_column("Index", style="bold cyan")
            table.add_column("Name")
            table.add_column("Year")
            table.add_column("Overview", overflow="fold")

            for idx, result in enumerate(matches):
                year = result.get("first_air_date", "????")[:4] if result.get("first_air_date") else "????"
                table.add_row(str(idx), result.get("name", "N/A"), year, result.get("overview", "")[:200])

            console.print(table)
            index = click.prompt("Enter index of correct show", type=int)

            try:
                selected = matches[index]
            except IndexError:
                click.secho("❌ Invalid index selected", fg="red")
                return

            tmdb_id = selected["id"]
            details = tmdb.get_show_details(tmdb_id)
            if not details or "info" not in details:
                click.secho("❌ Could not fetch selected show details", fg="red")
                return

        # Step 4: Build updated Show object with preserved path
        updated_show = Show.from_tmdb(show_details=details, sys_name=sys_name, sys_path=sys_path)

        # Step 5: Prepare episode list
        episode_groups = details.get("episode_groups", {}).get("results", [])
        season_count = details["info"].get("number_of_seasons", 0)
        episodes = Episode.parse_from_tmdb(tmdb_id, tmdb, episode_groups, season_count)

        if dry_run:
            click.echo()
            click.secho("🧪 DRY RUN: Would delete and reinsert metadata for:", fg="yellow")
            click.secho(f"  Show: {updated_show.tmdb_name}", fg="yellow")
            click.secho(f"  Episodes: {len(episodes)}", fg="yellow")
            return

        # Step 6: Delete and replace metadata
        db.delete_show_and_episodes(original_tmdb_id)
        db.add_show(updated_show)
        db.add_episodes(episodes)
        logger.info(f"✅ Corrected metadata for '{updated_show.tmdb_name}'")

        # Step 7: Summary
        click.echo()
        click.secho("✅ Show corrected successfully!", fg="green", bold=True)
        click.secho(f"🆕 TMDB: {updated_show.tmdb_name}", fg="cyan")
        click.secho(f"📂 Directory: {updated_show.sys_path}", fg="blue")
        click.secho(f"🎞️ Episodes added: {len(episodes)}", fg="green")

    except Exception as e:
        logger.exception(f"Error correcting show '{show_name}': {e}")
        click.secho(f"❌ Error correcting show: {e}", fg="red", bold=True)
