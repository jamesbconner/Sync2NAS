import os
import sys
import time
import json
import click
import shutil
import logging
import rich_click as rclick
from rich import print as rprint
from rich.table import Table
from rich.console import Console
from utils.sync2nas_config import load_configuration
from utils.logging_config import setup_logging
from services.db_service import DBService
from services.sftp_service import SFTPService
from services.tmdb_service import TMDBService
from utils.file_routing import route_files
from models.show import Show
from models.episode import Episode


@rclick.group()
@click.option( '--logfile', '-l', type=click.Path(writable=True), help="Write logs to specified file (e.g. logs/output.log)", default=None)
@click.option('--verbose', '-v', count=True, help="Set verbosity level (-v = INFO, -vv = DEBUG)")
@click.option('--config', '-c', type=click.Path(exists=True), default='./config/sync2nas_config.ini', help="Path to configuration file (default: ./config/sync2nas_config.ini)")
@click.pass_context
def sync2nas_cli(ctx, verbose, logfile, config):
    # Setup logging
    if logfile:
        try:    
            os.makedirs(os.path.dirname(logfile), exist_ok=True)
        except Exception as e:
            click.echo(f"Error creating log directory: {e}")
            sys.exit(1)
    setup_logging(verbosity=verbose, logfile=logfile)
    
    # Create the various objects for the context
    cfg = load_configuration(config)
    db = DBService(cfg["SQLite"]["db_file"])
    sftp = SFTPService(
        cfg["SFTP"]["host"],
        int(cfg["SFTP"]["port"]),
        cfg["SFTP"]["username"],
        cfg["SFTP"]["ssh_key_path"])
    tmdb = TMDBService(cfg["TMDB"]["api_key"])
    anime_tv_path = cfg["Routing"]["anime_tv_path"]
    incoming_path = cfg["Transfers"]["incoming"]

    # Add the objects to the context
    ctx.obj = {
        "config": cfg,
        "db": db,
        "sftp": sftp,
        "tmdb": tmdb,
        "anime_tv_path": anime_tv_path,
        "incoming_path": incoming_path
    }

@sync2nas_cli.command()
@click.pass_context
def init_db(ctx):
    """Initialize the SQLite database."""
    db = ctx.obj["db"]
    db.initialize()

@sync2nas_cli.command()
@click.pass_context
def list_files(ctx):
    """List files on the remote SFTP server."""
    with ctx.obj["sftp"] as sftp:
        files = sftp.list_files()
        for f in files:
            click.echo(f)
    
@sync2nas_cli.command(name="bootstrap-tv-shows")
@click.option('--dry-run', is_flag=True, help="Simulate population without writing to database")
@click.pass_context
def bootstrap_tv_shows(ctx, dry_run):
    """One-time population of tv_shows table from anime_tv_path."""
    # Setup logging
    logger = logging.getLogger(__name__)
    
    # Setup a rate limit
    # ToDo: Implement a better rate limit function that obeys return codes from TMDB
    RATE_LIMIT_DELAY = 2 # simple delay between requests
    
    # Counter lits for processed shows
    added = []
    skipped = []
    failed = []
    
    # Start timer
    start_time = time.time()

    db: DBService = ctx.obj["db"]
    tmdb: TMDBService = ctx.obj["tmdb"]
    config = ctx.obj["config"]
    anime_tv_path = config["Routing"]["anime_tv_path"]

    logger.info(f"Scanning anime_tv_path for shows: {anime_tv_path}")
    show_dirs = [d for d in os.listdir(anime_tv_path) if os.path.isdir(os.path.join(anime_tv_path, d))]

    for folder_name in sorted(show_dirs):
        sys_name = folder_name.strip()
        sys_path = os.path.join(anime_tv_path, sys_name)

        try:
            # Check if already exists
            if db.show_exists(sys_name):
                logger.info(f"Skipping existing show: {sys_name}")
                skipped.append(sys_name)
                continue

            logger.info(f"Searching TMDB for: {sys_name}")
            results = tmdb.search_show(sys_name)
            if not results or not results.get("results"):
                logger.warning(f"No TMDB results for: {sys_name}")
                continue

            first_match = results["results"][0]
            details = tmdb.get_show_details(first_match["id"])
            if not details or "info" not in details:
                logger.warning(f"Failed to fetch full details for TMDB ID {first_match['id']}")
                continue

            show = Show.from_tmdb(
                show_details=details,
                sys_name=sys_name,
                sys_path=sys_path)

            if dry_run:
                logger.info(f"[DRY RUN] Would add show: {show.tmdb_name}")
                logger.info(f"Show: {show.to_db_tuple()}")
                added.append(sys_name)
            else:
                db.add_show(show)
                logger.info(f"✅ Added show: {show.tmdb_name} (sys_name='{sys_name}')")
                added.append(sys_name)

        except Exception as e:
            logger.exception(f"❌ Error processing show '{sys_name}': {e}")
            failed.append(sys_name)

        finally:
            time.sleep(RATE_LIMIT_DELAY) # simple delay between requests

    end_time = time.time()
    duration = end_time - start_time
    logger.info(f"Total time taken: {duration:.2f} seconds")
    
    click.echo("\n📦 Import Summary\n" + "-" * 40, file=sys.stdout)

    if added:
        click.secho(f"✅ Added: {len(added)}", fg="green", file=sys.stdout)
        for name in added:
            click.secho(f"  - {name}", fg="green", file=sys.stdout)

    if skipped:
        click.secho(f"⏭️ Skipped: {len(skipped)}", fg="yellow", file=sys.stdout)
        for name in skipped:
            click.secho(f"  - {name}", fg="yellow", file=sys.stdout)

    if failed:
        click.secho(f"❌ Failed: {len(failed)}", fg="red", file=sys.stdout)
        for name in failed:
            click.secho(f"  - {name}", fg="red", file=sys.stdout)

    total = len(added) + len(skipped) + len(failed)
    click.secho(f"\n🧾 Total processed: {total}", bold=True, file=sys.stdout)

@sync2nas_cli.command(name="bootstrap-episodes")
@click.option('--dry-run', is_flag=True, help="Simulate episode population without writing to database")
@click.pass_context
def bootstrap_episodes(ctx, dry_run):
    """Populate episodes for all shows in the tv_shows table."""

    logger = logging.getLogger(__name__)
    db: DBService = ctx.obj["db"]
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

@sync2nas_cli.command(name="add-show")
@click.argument("show_name", required=False)
@click.option("--tmdb-id", type=int, help="TMDB ID of the show (overrides show_name search)")
@click.option("--dry-run", is_flag=True, help="Simulate without writing to database or creating directory")
@click.pass_context
def add_show(ctx, show_name, tmdb_id, dry_run):
    """
    Add a show to the tv_shows table by searching TMDB or using TMDB ID.
    
    This command will create the show directory, insert the show into the database,
    and populate episode metadata.
    """
    # ToDo: add a --file option to read the show details from a file

    # Setup logging
    logger = logging.getLogger(__name__)
    
    # Setup the objects
    db: DBService = ctx.obj["db"]
    tmdb: TMDBService = ctx.obj["tmdb"]
    anime_tv_path = ctx.obj["anime_tv_path"]

    # Initialize variables
    success = True
    error = None
    added_episodes = []

    try:
        # Check if TMDB ID is provided
        if tmdb_id:
            # Fetch the details
            logger.info(f"🔍 Fetching details for TMDB ID {tmdb_id}")
            details = tmdb.get_show_details(tmdb_id)
            if not details or "info" not in details:
                raise ValueError(f"Could not retrieve show details for TMDB ID {tmdb_id}")
            sys_name = details["info"]["name"]
        elif show_name:
            # Search TMDB for the show
            logger.info(f"🔍 Searching TMDB for: {show_name}")
            results = tmdb.search_show(show_name)
            if not results or not results.get("results"):
                raise ValueError(f"No results found for show name: {show_name}")
            first_result = results["results"][0]
            tmdb_id = first_result["id"]
            details = tmdb.get_show_details(tmdb_id)
            if not details or "info" not in details:
                raise ValueError(f"Failed to retrieve full details for TMDB ID {tmdb_id}")
            sys_name = show_name
        else:
            # Error if no show name or TMDB ID is provided
            click.secho("❌ Either show_name or --tmdb-id must be provided.", fg="red")
            return

        # Get the system path
        sys_path = os.path.join(anime_tv_path, sys_name)

        # Check if the show already exists
        if db.show_exists(sys_name):
            click.secho(f"⚠️ Show already exists in DB: {sys_name}", fg="yellow")
            return

        # Build the Show object
        show = Show.from_tmdb(show_details=details, sys_name=sys_name, sys_path=sys_path)

        # Prepare episode parsing
        episode_groups = details.get("episode_groups", {}).get("results", [])
        season_count = details["info"].get("number_of_seasons", 0)
        episode_count = details["info"].get("number_of_episodes", 0)
        episodes = Episode.parse_from_tmdb(tmdb_id, tmdb, episode_groups, season_count)
        click.secho(f"[DEBUG] Episodes parsed: {len(episodes)}", fg="yellow")

        # Dry run
        if dry_run:
            logger.info(f"[DRY RUN] Would create directory: {sys_path}")
            logger.info(f"[DRY RUN] Would insert show: {show.tmdb_name}")
            logger.info(f"[DRY RUN] Would insert {len(episodes)} episodes")
        else:
            # Create the directory
            os.makedirs(sys_path, exist_ok=True)
            # Add the show to the database
            db.add_show(show)
            # Add the episodes to the database
            db.add_episodes(episodes)
            # Set the added episodes
            added_episodes = episodes
            logger.info(f"✅ Created directory and added show '{show.tmdb_name}' with {len(episodes)} episodes")

    except Exception as e:
        success = False
        error = str(e)
        logger.exception(f"❌ Error adding show: {e}")

    # Post-Summary
    click.echo()
    click.secho("📦 Show Addition Summary", fg="cyan", bold=True)
    click.secho("-" * 40)

    if success:
        if dry_run:
            click.secho("✅ DRY RUN successful", fg="green")
        else:
            click.secho(f"✅ Show added: {show.tmdb_name}", fg="green")
            click.secho(f"📂 Directory created at: {sys_path}", fg="blue")
            click.secho(f"🎞️ Episodes added: {len(added_episodes)}", fg="green")
    else:
        click.secho("❌ Failed to add show", fg="red", bold=True)
        if error:
            click.secho(f"Reason: {error}", fg="red")

@sync2nas_cli.command(name="fix-show")
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

def print_dry_run_summary(added, skipped, failed):
    total = len(added) + len(skipped) + len(failed)

    rprint("\n[bold cyan]📦 Episode Bootstrap Summary[/bold cyan]")
    rprint("[bold]" + "-" * 40 + "[/bold]")

    if added:
        rprint(f"[green]✅ Added episodes for {len(added)} show(s):[/green]")
        for name in added:
            rprint(f"[green]  - {name}[/green]")

    if skipped:
        rprint(f"[yellow]⏭️ Skipped existing {len(skipped)} show(s):[/yellow]")
        for name in skipped:
            rprint(f"[yellow]  - {name}[/yellow]")

    if failed:
        rprint(f"[red]❌ Failed to process {len(failed)} show(s):[/red]")
        for name in failed:
            rprint(f"[red]  - {name}[/red]")

    rprint(f"\n[bold]🧾 Total shows processed: {total}[/bold]")