import click

@click.command("list-remote")
@click.option("--path", "-p", type=str, help="Path to list")
@click.option("--recursive", "-r", is_flag=True, help="List recursively")
@click.option("--populate-sftp-temp", "-s", is_flag=True, help="Populate sftp_temp table")
@click.option("--dry-run", "-d", is_flag=True, help="Simulate without listing")
@click.pass_context
def list_remote(ctx, path, recursive, populate_sftp_temp, dry_run):
    """List files on the remote SFTP server."""

    remote_path = ctx.obj["config"]["SFTP"]["path"]

    with ctx.obj["sftp"] as sftp:
        files = sftp.list_remote_dir(remote_path)
        for f in files:
            click.echo(f)
    