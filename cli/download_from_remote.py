import click
from utils.sync2nas_config import parse_sftp_paths
from utils.sftp_orchestrator import download_from_remote as downloader

@click.command("download-from-remote")
@click.option("--dry-run", "-d", is_flag=True, help="Simulate downloads without writing files or updating the DB.")
@click.pass_context
def download_from_remote(ctx, dry_run):
    """
    Download new files or directories from the remote SFTP server and record them.
    """

    config = ctx.obj["config"]
    sftp = ctx.obj["sftp"]
    db = ctx.obj["db"]
    incoming_path = config["Transfers"]["incoming"]

    remote_paths = parse_sftp_paths(config)

    if not remote_paths:
        click.secho("❌ No SFTP paths defined in config [SFTP] section (key: 'paths').", fg="red")
        ctx.exit(1)
        
    click.secho(f"📡 Starting remote scan from: {remote_paths}", fg="cyan")
    click.secho(f"📥 Incoming destination: {incoming_path}", fg="cyan")

    with sftp as s:
        downloader(
            sftp=s,
            db=db,
            remote_paths=remote_paths,
            incoming_path=incoming_path,
            dry_run=dry_run)

    # ToDo: If dry-run is true without -vv then no file information is printed.  Should always print the files that would be downloaded.
    if dry_run:
        click.secho("✔️ Dry run complete. No files were downloaded or recorded.", fg="green")
