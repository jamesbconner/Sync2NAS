import click
from utils.sync2nas_config import parse_sftp_paths
from utils.sftp_orchestrator import bootstrap_downloaded_files

"""
CLI command to bootstrap the downloaded_files table from the current SFTP remote listing.
"""

@click.command("bootstrap-downloads")
@click.option("--dry-run", is_flag=True, help="Simulate without writing to DB")
@click.pass_context
def bootstrap_downloads(ctx, dry_run):
    """Bootstrap the downloaded_files table from the current SFTP remote listing."""
    sftp = ctx.obj["sftp"]
    db = ctx.obj["db"]
    remote_paths = parse_sftp_paths(ctx.obj["config"])

    if dry_run:
        click.secho("[DRY RUN] Would baseline downloaded_files from SFTP listing.", fg="yellow")
        return

    with sftp as s:
        for remote_path in remote_paths:
            bootstrap_downloaded_files(s, db, remote_path)
        
    click.secho("✅ Bootstrapped downloaded_files from remote listing", fg="green")
