import os
import click
from click.testing import CliRunner
from pathlib import Path
from utils.file_routing import file_routing, parse_filename
from cli.add_show import add_show

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
        runner = CliRunner()

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

                    add_show_args = [show_name]
                    if dry_run:
                        add_show_args.append("--dry-run")

                    add_show_result = runner.invoke(add_show, add_show_args, obj=ctx.obj)

                    if add_show_result.exit_code == 0:
                        click.secho(f"✅ Auto-added: {show_name}", fg="green")
                    else:
                        click.secho(f"❌ Failed to add show '{show_name}': {add_show_result.output.strip()}", fg="red")

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
