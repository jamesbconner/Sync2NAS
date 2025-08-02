import click
from pathlib import Path
from datetime import datetime

"""
CLI command to list files on the remote SFTP server, with options for recursion, dry-run, and populating the sftp_temp table.
"""

@click.command("list-remote")
@click.option("--path", "-p", type=str, help="Path to list")
@click.option("--recursive", "-r", is_flag=True, help="List recursively")
@click.option("--populate-sftp-temp", "-s", is_flag=True, help="Populate sftp_temp table")
@click.pass_context
def list_remote(ctx, path, recursive, populate_sftp_temp):
    """List files on the remote SFTP server."""
    if not ctx.obj:
        click.echo("Error: No context object found")
        return 1
    
    dry_run = ctx.obj["dry_run"]

    remote_path = path if path else ctx.obj["config"]["SFTP"]["path"]

    with ctx.obj["sftp"] as sftp:
        if recursive:
            files = sftp.list_remote_files_recursive(remote_path)
        else:
            files = sftp.list_remote_dir(remote_path)

        if dry_run:
            click.echo(f"Dry run: Would list {len(files)} files in {remote_path}")
            for f in files:
                click.echo(f"Dry run: Would list {f['name']}")
        else:
            for f in files:
                click.echo(f"{f['name']}")

        if populate_sftp_temp and not dry_run:
            # Convert timestamps to strings for database storage
            files_for_db = []
            for f in files:
                file_copy = f.copy()
                # Handle modified_time
                if isinstance(file_copy['modified_time'], datetime):
                    file_copy['modified_time'] = file_copy['modified_time'].isoformat()
                elif isinstance(file_copy['modified_time'], str):
                    # If it's already a string, try to parse and reformat it
                    try:
                        dt = datetime.strptime(file_copy['modified_time'], "%Y-%m-%d %H:%M:%S")
                        file_copy['modified_time'] = dt.isoformat()
                    except ValueError:
                        # If parsing fails, leave it as is
                        pass
                # Handle fetched_at
                if isinstance(file_copy['fetched_at'], datetime):
                    file_copy['fetched_at'] = file_copy['fetched_at'].isoformat()
                elif isinstance(file_copy['fetched_at'], str):
                    # If it's already a string, try to parse and reformat it
                    try:
                        dt = datetime.strptime(file_copy['fetched_at'], "%Y-%m-%d %H:%M:%S")
                        file_copy['fetched_at'] = dt.isoformat()
                    except ValueError:
                        # If parsing fails, leave it as is
                        pass
                files_for_db.append(file_copy)
            
            try:
                ctx.obj["db"].insert_sftp_temp_files(files_for_db)
                click.echo(f"Populated sftp_temp table with {len(files)} files")
            except Exception as e:
                click.echo(f"Error populating sftp_temp table: {str(e)}")
                return 1
    