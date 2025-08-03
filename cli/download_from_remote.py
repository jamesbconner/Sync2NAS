import click
from utils.sync2nas_config import parse_sftp_paths
from utils.sftp_orchestrator import download_from_remote as downloader

"""
CLI command to download new files or directories from the remote SFTP server and record them in the database.
"""

@click.command("download-from-remote")
@click.option("--max-workers", "-m", default=4, show_default=True, type=int, help="Number of concurrent downloads")
@click.pass_context
def download_from_remote(ctx, max_workers):
    """
    Download new files or directories from the remote SFTP server and record them.
    """
    if not ctx.obj:
        click.secho("[ERROR] No context object found", fg="red", bold=True)
        return

    dry_run = ctx.obj["dry_run"]
    config = ctx.obj["config"]
    sftp = ctx.obj["sftp"]
    db = ctx.obj["db"]
    incoming_path = config["Transfers"]["incoming"]
    remote_paths = parse_sftp_paths(config)

    if not remote_paths:
        click.secho("[ERROR] No SFTP paths defined in config [SFTP] section (key: 'paths').", fg="red")
        ctx.exit(1)
        
    click.secho(f"[SFTP] Starting remote scan from: {remote_paths}", fg="cyan")
    click.secho(f"[DOWNLOAD] Incoming destination: {incoming_path}", fg="cyan")

    with sftp as s:
        downloader(
            sftp=s,
            db=db,
            remote_paths=remote_paths,
            incoming_path=incoming_path,
            dry_run=dry_run,
            max_workers=max_workers)

    # ToDo: If dry-run is true without -vv then no file information is printed.  Should always print the files that would be downloaded.
    if dry_run:
        click.secho("[DRY-RUN] Complete. No files were downloaded or recorded.", fg="green")
