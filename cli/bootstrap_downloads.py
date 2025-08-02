import click
from utils.sync2nas_config import parse_sftp_paths
from utils.sftp_orchestrator import bootstrap_downloaded_files

@click.command("bootstrap-downloads")
@click.pass_context
def bootstrap_downloads(ctx):
    """
    Bootstrap the downloaded_files table from the current SFTP remote listing.

    Args:
        ctx (click.Context): Click context containing shared config and services.

    Returns:
        None. Prints results to the console and exits on error.
    """
    if not ctx.obj:
        click.secho("❌ Error: No context object found", fg="red", bold=True)
        return
    
    dry_run = ctx.obj["dry_run"]
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
