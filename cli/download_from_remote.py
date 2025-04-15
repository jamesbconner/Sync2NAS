import click
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
    remote_path = config["SFTP"]["path"]
    incoming_path = config["Transfers"]["incoming"]

    click.secho(f"📡 Starting remote scan from: {remote_path}", fg="cyan")
    click.secho(f"📥 Incoming destination: {incoming_path}", fg="cyan")

    with sftp as s:
        downloader(
            sftp=s,
            db=db,
            remote_path=remote_path,
            incoming_path=incoming_path,
            dry_run=dry_run)

    if dry_run:
        click.secho("✔️ Dry run complete. No files were downloaded or recorded.", fg="green")
