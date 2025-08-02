import os
import click
import datetime
from pathlib import Path
from utils.file_filters import is_valid_media_file

@click.command("bootstrap-inventory")
@click.pass_context
def bootstrap_inventory(ctx):
    """
    Populate the inventory table based on files already present in the media path.
    
    Args:
        ctx (click.Context): Click context containing shared config and services.

    Returns:
        None. Prints results to the console and exits on error.
    """
    dry_run = ctx.obj["dry_run"]
    """
    Populate the anime_tv_inventory table based on files already present in the media path.
    """

    dry_run = ctx.obj["dry_run"]
    anime_tv_path = ctx.obj["anime_tv_path"]
    db = ctx.obj["db"]
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    click.secho(f"📁 Scanning existing files in: {anime_tv_path}", fg="cyan")

    collected = []

    for root, _, files in os.walk(anime_tv_path):
        for file in files:
            # Create a posix path from the root and file using Path().as_posix()
            full_path = Path(root, file).as_posix()
            if not is_valid_media_file(full_path): # Exclude certain file extensions and keywords
                continue

            stat = os.stat(full_path)
            record = {
                "name": file,
                "path": full_path,
                "size": stat.st_size,
                "modified_time": datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "is_dir": False,
                "fetched_at": now,
            }
            collected.append(record)

    if dry_run:
        click.secho(f"[DRY RUN] Would insert {len(collected)} entries into anime_tv_inventory table.", fg="yellow")
    else:
        db.add_inventory_files(collected)
        click.secho(f"✅ Inserted {len(collected)} files into anime_tv_inventory.", fg="green")
