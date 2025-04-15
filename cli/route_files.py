import os
import click
from utils.file_routing import file_routing, parse_filename
from utils.show_adder import add_show_interactively

@click.command("route-files")
@click.option("--dry-run", is_flag=True, default=False, help="Print what would be routed without actually moving files.")
@click.option("--auto-add", is_flag=True, default=False, help="Attempt to add missing shows automatically before routing.")
@click.pass_context
def route_files(ctx, dry_run, auto_add):
    """
    Scan the incoming path and move files to the appropriate show directories.
    """
    db = ctx.obj["db"]
    tmdb = ctx.obj["tmdb"]
    anime_tv_path = ctx.obj["anime_tv_path"]
    incoming_path = ctx.obj["incoming_path"]

    click.secho(f"Scanning: {incoming_path}", fg="cyan")

    ignore_files = {'desktop.ini', 'Thumbs.db', '.DS_Store'}

    if auto_add:
        seen = set()
        for root, _, filenames in os.walk(incoming_path):
            for fname in filenames:
                if fname in ignore_files:
                    continue

                full_path = os.path.join(root, fname)
                if not os.path.isfile(full_path):
                    continue

                show_name, *_ = parse_filename(os.path.basename(fname))
                if not show_name or show_name in seen:
                    continue

                seen.add(show_name)

                if not db.show_exists(show_name):
                    click.secho(f"📥 Auto-adding show: {show_name}", fg="yellow")
                    try:
                        result = add_show_interactively(show_name, None, db, tmdb, anime_tv_path, dry_run=dry_run)
                        click.secho(f"✅ Auto-added: {result['tmdb_name']}", fg="green")
                    except Exception as e:
                        click.secho(f"❌ Failed to add show '{show_name}': {e}", fg="red")

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
