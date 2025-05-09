import os
import click
from click.testing import CliRunner
from pathlib import Path
from utils.file_routing import file_routing, parse_filename
from utils.cli_helpers import pass_sync2nas_context
from cli.add_show import add_show
from utils.file_filters import EXCLUDED_FILENAMES


@click.command("route-files", help="Scan the incoming path and move files to the appropriate show directories.")
@click.option("--dry-run", is_flag=True, default=False, help="Print what would be routed without actually moving files.")
@click.option("--auto-add", is_flag=True, default=False, help="Attempt to add missing shows automatically before routing.")
@pass_sync2nas_context
def route_files(ctx, dry_run, auto_add):
    """
    Scan the incoming path and move files to the appropriate show directories.
    """
    db = ctx.obj["db"]
    tmdb = ctx.obj["tmdb"]
    anime_tv_path = ctx.obj["anime_tv_path"]
    incoming_path = ctx.obj["incoming_path"]

    click.secho(f"Scanning: {incoming_path}", fg="cyan")

    if auto_add:
        _auto_add_missing_shows(ctx, incoming_path, dry_run)

    routed = file_routing(incoming_path, anime_tv_path, db, dry_run=dry_run)

    if dry_run:
        click.secho("\n[DRY RUN] No files will be moved.", fg="green")

    if not routed:
        click.secho("No files routed.", fg="yellow")
        return

    click.secho(f"{len(routed)} file(s) routed:", fg="green")
    for item in routed:
        click.echo(
            f"- {item['original_path']} → {item['routed_path']}, "
            f"{item['show_name']}, {item['season']}, {item['episode']}"
        )


def _auto_add_missing_shows(ctx, incoming_path: str, dry_run: bool, ignore_files: set[str] = None):
    """
    Helper function to scan incoming files and auto-add missing shows to the database.

    Args:
        ctx: Click context containing shared config and services
        incoming_path: Path to scan for unrecognized show files
        dry_run: If True, simulate add-show operations
        ignore_files: Optional set of filenames to skip
    """
    db = ctx.obj["db"]
    runner = CliRunner()

    if ignore_files is None:
        ignore_files = EXCLUDED_FILENAMES

    seen = set()

    # Walk through incoming directories and identify candidate shows
    for root, _, filenames in os.walk(incoming_path):
        for fname in filenames:
            # Skip ignored files
            if fname in ignore_files:
                continue

            full_path = os.path.join(root, fname)
            if not os.path.isfile(full_path):
                continue

            # Parse filename to extract show name
            metadata = parse_filename(fname)
            show_name = metadata["show_name"]

            # Skip if parsing failed or already processed
            if not show_name or show_name in seen:
                continue
            seen.add(show_name)

            # Skip if show already exists in DB
            if db.show_exists(show_name):
                continue

            click.secho(f"📥 Auto-adding show: {show_name}", fg="yellow")

            # Construct CLI args and invoke add-show command
            add_show_args = [show_name]
            if dry_run:
                add_show_args.append("--dry-run")

            add_show_result = runner.invoke(add_show, add_show_args, obj=ctx.obj)

            if add_show_result.exit_code == 0:
                click.secho(f"✅ Auto-added: {show_name}", fg="green")
            else:
                click.secho(f"❌ Failed to add show '{show_name}': {add_show_result.output.strip()}", fg="red")