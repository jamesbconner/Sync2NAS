import click
from utils.sync2nas_config import parse_sftp_paths
from utils.sftp_orchestrator import download_from_remote as downloader
from services.hashing_service import HashingService
from utils.cli_helpers import validate_context_for_command, get_service_from_context

"""
CLI command to download new files or directories from the remote SFTP server and record them in the database.
"""

@click.command("download-from-remote")
@click.option("--max-workers", "-m", default=4, show_default=True, type=int, help="Number of concurrent downloads")
@click.option("--parse/--no-parse", default=True, show_default=True, help="Enable filename parsing to populate show/season/episode")
@click.option("--llm/--no-llm", default=True, show_default=True, help="Use configured LLM for parsing; disable to force regex fallback")
@click.option("--llm-threshold", type=float, default=0.7, show_default=True, help="Minimum LLM confidence to accept parse result")
@click.pass_context
def download_from_remote(ctx, max_workers, parse, llm, llm_threshold):
    """
    Download new files or directories from the remote SFTP server and record them.
    """
    # Validate required services
    if not validate_context_for_command(ctx, required_services=['sftp', 'db', 'config']):
        return

    dry_run = ctx.obj["dry_run"]
    config = ctx.obj["config"]
    sftp = ctx.obj["sftp"]
    db = ctx.obj["db"]
    from utils.sync2nas_config import get_config_value
    incoming_path = get_config_value(config, "transfers", "incoming")
    remote_paths = parse_sftp_paths(config)

    if not remote_paths:
        click.secho("[ERROR] No SFTP paths defined in config [SFTP] section (key: 'paths').", fg="red")
        ctx.exit(1)
        
    click.secho(f"[SFTP] Starting remote scan from: {remote_paths}", fg="cyan")
    click.secho(f"[DOWNLOAD] Incoming destination: {incoming_path}", fg="cyan")
    click.secho(
        f"[PARSING] Enabled={parse} | LLM={llm} | LLM threshold={llm_threshold}",
        fg="cyan",
    )

    # Optional hashing service wiring
    hashing_service = None
    try:
        # Initialize hashing service with configurable chunk size
        chunk_size = None
        try:
            if config.has_section("Hashing"):
                if config.has_option("Hashing", "chunk_size_bytes"):
                    chunk_size = config.getint("Hashing", "chunk_size_bytes")
                elif config.has_option("Hashing", "chunk_size_mib"):
                    chunk_size = config.getint("Hashing", "chunk_size_mib") * 1024 * 1024
        except Exception:
            chunk_size = None
        hashing_service = HashingService(chunk_size=chunk_size or 1_048_576)
    except Exception:
        # Non-fatal: continue without optional integrations
        hashing_service = None

    with sftp as s:
        try:
            llm_available = getattr(s, "llm_service", None) is not None
            click.secho(f"[LLM] Service available: {llm_available}", fg="cyan")
        except Exception:
            click.secho(f"[LLM] Service available: False", fg="cyan")
        downloader(
            sftp=s,
            db=db,
            remote_paths=remote_paths,
            incoming_path=incoming_path,
            dry_run=dry_run,
            max_workers=max_workers,
            hashing_service=hashing_service,
            parse_filenames=parse,
            use_llm=llm,
            llm_confidence_threshold=llm_threshold,
        )

    # ToDo: If dry-run is true without -vv then no file information is printed.  Should always print the files that would be downloaded.
    if dry_run:
        click.secho("[DRY-RUN] Complete. No files were downloaded or recorded.", fg="green")
