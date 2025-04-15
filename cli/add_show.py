import click
from services.db_service import DBService
from services.tmdb_service import TMDBService
from utils.show_adder import add_show_interactively

@click.command("add-show")
@click.argument("show_name", required=False)
@click.option("--tmdb-id", type=int, help="TMDB ID of the show (overrides show_name search)")
@click.option("--override-dir", is_flag=True, help="Use the provided show_name directly for the folder name.")
@click.option("--dry-run", is_flag=True, help="Simulate without writing to database or creating directory")
@click.pass_context
def add_show(ctx, show_name, tmdb_id, dry_run, override_dir):
    """Add a show to the tv_shows table by searching TMDB or using TMDB ID."""
    db: DBService = ctx.obj["db"]
    tmdb: TMDBService = ctx.obj["tmdb"]
    anime_tv_path = ctx.obj["anime_tv_path"]

    try:
        result = add_show_interactively(show_name, tmdb_id, db, tmdb, anime_tv_path, dry_run, override_dir)
    except Exception as e:
        click.secho("❌ Failed to add show", fg="red", bold=True)
        click.secho(f"Reason: {e}", fg="red")
        return

    click.echo()
    click.secho("📦 Show Addition Summary", fg="cyan", bold=True)
    click.secho("-" * 40)

    if dry_run:
        click.secho("✅ DRY RUN successful", fg="green")
    else:
        click.secho(f"✅ Show added: {result['tmdb_name']}", fg="green")
        click.secho(f"📂 Directory created at: {result['sys_path']}", fg="blue")
        click.secho(f"🎞️ Episodes added: {result['episode_count']}", fg="green")
