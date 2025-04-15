import click
from utils.sftp_orchestrator import bootstrap_downloaded_files

@click.command("bootstrap-downloads")
@click.option("--dry-run", is_flag=True, help="Simulate without writing to DB")
@click.pass_context
def bootstrap_downloads(ctx, dry_run):
    """Bootstrap the downloaded_files table from the current SFTP remote listing."""
    sftp = ctx.obj["sftp"]
    db = ctx.obj["db"]
    remote_path = ctx.obj["config"]["SFTP"]["path"]

    if dry_run:
        click.secho("[DRY RUN] Would baseline downloaded_files from SFTP listing.", fg="yellow")
        return

    with sftp as s:
        bootstrap_downloaded_files(s, db, remote_path)
        
    click.secho("✅ Bootstrapped downloaded_files from remote listing", fg="green")
