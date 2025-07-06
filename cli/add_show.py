"""
CLI command to add a new show to the database by searching TMDB or using a TMDB ID.
"""
import click
import logging
from services.db_implementations.db_interface import DatabaseInterface
from services.tmdb_service import TMDBService
from utils.show_adder import add_show_interactively

logger = logging.getLogger(__name__)

@click.command("add-show")
@click.argument("show_name", required=False)
@click.option("--use-llm", is_flag=True, help="Use the LLM to suggest the show name and directory name.")
@click.option("--llm-confidence", default=0.7, type=float, help="Confidence threshold for LLM suggestions (0.0-1.0)")
@click.option("--tmdb-id", default=None, type=int, help="TMDB ID of the show (overrides show_name search)")
@click.option("--override-dir", is_flag=True, help="Use the provided show_name directly for the folder name.")
@click.option("--dry-run", is_flag=True, help="Simulate without writing to database or creating directory")
@click.pass_context
def add_show(ctx, show_name, override_dir, dry_run, use_llm, llm_confidence, tmdb_id):
    logger.info(f"cli/add_show.py::add_show - Called with show_name={show_name}, tmdb_id={tmdb_id}, override_dir={override_dir}, dry_run={dry_run}, use_llm={use_llm}")
    """
    Add a show to the tv_shows table by searching TMDB or using TMDB ID.
    If --dry-run is set, no changes are made to the database or filesystem.
    """
    db: DatabaseInterface = ctx.obj["db"]
    tmdb: TMDBService = ctx.obj["tmdb"]
    anime_tv_path = ctx.obj["anime_tv_path"]
    llm_service = ctx.obj.get("llm_service")

    # Require at least a show name or TMDB ID
    if not show_name and not tmdb_id:
        click.secho("\u274c You must provide either a SHOW_NAME or TMDB_ID if using --tmdb-id.", fg="red", bold=True)
        ctx.exit(1)

    try:
        logger.debug("cli/add_show.py::add_show - Calling add_show_interactively")
        # Use the interactive show adder utility to handle TMDB search and DB insert
        # The ctx is not passed to the add_show_interactively function, so pass the service objects directly
        result = add_show_interactively(
            show_name=show_name,
            tmdb_id=tmdb_id,
            db=db,
            tmdb=tmdb,
            anime_tv_path=anime_tv_path,
            dry_run=dry_run,
            override_dir=override_dir,
            llm_service=llm_service,
            use_llm=use_llm,
            llm_confidence=llm_confidence
        )
        logger.debug("cli/add_show.py::add_show - add_show_interactively completed successfully")
    except Exception as e:
        logger.error(f"cli/add_show.py::add_show - Exception: {e}", exc_info=True)
        click.secho("\u274c Failed to add show", fg="red", bold=True)
        click.secho(f"Reason: {e}", fg="red")
        ctx.exit(1)

    click.echo()
    click.secho("📦 Show Addition Summary", fg="cyan", bold=True)
    click.secho("-" * 40)

    if dry_run:
        click.secho("✅ DRY RUN successful", fg="green")
    else:
        click.secho(f"✅ Show added: {result['tmdb_name']}", fg="green")
        click.secho(f"📂 Directory created at: {result['sys_path']}", fg="blue")
        click.secho(f"🎞️ Episodes added: {result['episode_count']}", fg="green")

