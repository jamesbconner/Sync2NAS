"""
CLI command to scan the incoming directory and route files to the correct show directories, optionally using LLM and auto-adding missing shows.
"""
import os
import click
import logging
from click.testing import CliRunner
from pathlib import Path
from utils.file_routing import file_routing
from utils.filename_parser import parse_filename
from utils.cli_helpers import pass_sync2nas_context
from cli.add_show import add_show
from utils.file_filters import EXCLUDED_FILENAMES

logger = logging.getLogger(__name__)

@click.command("route-files", help="Scan the incoming path and move files to the appropriate show directories.")
@click.option("--incoming", "-i", type=click.Path(exists=True), help="Incoming directory to scan")
@click.option("--use-llm", "-l", is_flag=True, help="Use LLM for filename parsing")
@click.option("--llm-confidence", type=float, default=0.7, help="Minimum LLM confidence threshold (0.0-1.0)")
@click.option("--auto-add", is_flag=True, default=False, help="Attempt to add missing shows automatically before routing.")
@click.pass_context
@pass_sync2nas_context
def route_files(ctx: click.Context, incoming: str, use_llm: bool, llm_confidence: float, auto_add: bool) -> int:
    """
    Scan the incoming path and move files to the appropriate show directories.
    Optionally uses LLM for filename parsing and can auto-add missing shows.

    Args:
        ctx (click.Context): Click context containing shared config and services.
        incoming (str): Incoming directory to scan.
        dry_run (bool): Simulate without moving files.
        use_llm (bool): Use LLM for filename parsing.
        llm_confidence (float): Minimum LLM confidence threshold (0.0-1.0).
        auto_add (bool): Attempt to add missing shows automatically before routing.

    Returns:
        int: 0 on success, 1 on error.
    """
    if not ctx.obj:
        click.echo("Error: No context object found")
        return 1
    
    dry_run = ctx.obj["dry_run"]
    logger.info(f"Called with incoming={incoming}, dry_run={dry_run}, use_llm={use_llm}, llm_confidence={llm_confidence}, auto_add={auto_add}")

    db = ctx.obj["db"]
    tmdb = ctx.obj["tmdb"]
    anime_tv_path = ctx.obj["anime_tv_path"]
    incoming_path = incoming if incoming else ctx.obj["incoming_path"]

    click.secho(f"Scanning: {incoming_path}", fg="cyan")

    # Initialize LLM service if requested
    llm_service = ctx.obj["llm_service"] if use_llm else None

    # Optionally auto-add missing shows before routing
    if auto_add:
        _auto_add_missing_shows(ctx=ctx, incoming_path=incoming_path, use_llm=use_llm, llm_confidence=llm_confidence)

    try:
        # Route files using the file_routing utility
        logger.info("Calling file_routing")
        routed_files = file_routing(
            incoming_path=incoming_path,
            anime_tv_path=anime_tv_path,
            db=db,
            tmdb=tmdb,
            dry_run=dry_run,
            llm_service=llm_service,
            llm_confidence_threshold=llm_confidence
        )
        logger.info("file_routing completed successfully")

        if dry_run:
            click.echo(f"Dry run: Would route {len(routed_files)} files")
            for file_info in routed_files:
                click.echo(f"  {file_info['original_path']} -> {file_info['routed_path']}")
                if 'confidence' in file_info:
                    click.echo(f"    Confidence: {file_info['confidence']:.2f} - {file_info['reasoning']}")
        else:
            click.echo(f"Successfully routed {len(routed_files)} files")
            for file_info in routed_files:
                click.echo(f"  {file_info['original_path']} -> {file_info['routed_path']}")

        return 0

    except Exception as e:
        logger.exception(f"Error routing files: {str(e)}")
        click.secho(f"Error routing files: {str(e)}", fg="red")
        return 1


def _auto_add_missing_shows(ctx: click.Context, incoming_path: str, ignore_files: set[str] = None, use_llm: bool = False, llm_confidence: float = None) -> None:
    """
    Helper function to scan incoming files and auto-add missing shows to the database.

    Args:
        ctx (click.Context): Click context containing shared config and services.
        incoming_path (str): Path to scan for unrecognized show files.
        ignore_files (set[str], optional): Set of filenames to skip.
        use_llm (bool, optional): If True, use the LLM to parse the filename.
        llm_confidence (float, optional): Minimum confidence threshold for the LLM to parse the filename.

    Returns:
        None
    """
    # Get the database and LLM service from the context object
    # DB is used to check if the show already exists in the database
    # LLM service is used to parse the filename if use_llm is True
    if not ctx.obj:
        logger.error("No context object found in _auto_add_missing_shows")
        return
    
    db = ctx.obj["db"]
    llm_service = ctx.obj["llm_service"] if use_llm else None
    dry_run = ctx.obj["dry_run"]

    # Initialize the CLI runner
    runner = CliRunner()

    # Set the default ignore files
    if ignore_files is None:
        ignore_files = EXCLUDED_FILENAMES

    # Set of show names that have already been processed
    seen = set()

    # Walk through incoming directories and identify candidate shows
    for root, _, filenames in os.walk(incoming_path):
        for fname in filenames:
            # Skip ignored files
            if fname in ignore_files:
                continue

            full_path = os.path.join(root, fname)
            if not os.path.isfile(full_path):
                continue

            # Parse filename to extract show name
            # If use_llm is True, use the LLM to parse the filename, otherwise use the regex parser.
            #   the llm parser will fall back to the regex parser if the confidence answer is 
            #   below the llm_confidence threshold.
            if use_llm:
                logger.info(f"Using LLM to parse filename: {fname}")
                metadata = parse_filename(fname, llm_service=llm_service, llm_confidence_threshold=llm_confidence)
            else:
                logger.info(f"Using regex to parse filename: {fname}")
                metadata = parse_filename(fname)
            
            # This is the object that we'll use to search TMDB to find the show details.
            # Note that we aren't using a TMDB ID because this is an auto-add operation.
            show_name = metadata["show_name"]

            # Skip if parsing failed or already processed (do not duplicate shows)
            if not show_name:
                logger.info(f"Skipping show because there's no show_name value: {show_name}")
                continue
            if show_name in seen:
                logger.info(f"Skipping show because it's already been processed: {show_name}")
                continue
            
            logger.info(f"Adding show to seen set: {show_name}")
            seen.add(show_name)

            # Check if show already exists in DB (either by exact name or as an alias)
            existing_show = db.get_show_by_name_or_alias(show_name)
            if existing_show:
                logger.info(f"Show already exists in DB: {existing_show.get('tmdb_name', show_name)} (matched by: {show_name})")
                # Still update aliases to include the parsed filename for future routing
                try:
                    current_aliases = existing_show.get("tmdb_aliases", "")
                    aliases_list = [a.strip() for a in current_aliases.split(",") if a.strip()]
                    
                    # Add the parsed show name if it's not already in aliases
                    if show_name not in aliases_list:
                        aliases_list.append(show_name)
                        new_aliases = ",".join(aliases_list)
                        
                        # Update the show's aliases in the database
                        db.update_show_aliases(existing_show["id"], new_aliases)
                        logger.info(f"Updated aliases for existing show '{existing_show.get('tmdb_name', show_name)}' to include parsed filename: {new_aliases}")
                    else:
                        logger.info(f"Show '{existing_show.get('tmdb_name', show_name)}' already has parsed filename in aliases")
                except Exception as alias_exc:
                    logger.warning(f"Failed to update aliases for existing show '{existing_show.get('tmdb_name', show_name)}': {alias_exc}")
                continue

            click.secho(f"[AUTO-ADD] Auto-adding show: {show_name}", fg="yellow")

            # Construct CLI args and invoke add-show command
            add_show_args = [show_name]
            if use_llm:
                add_show_args.append("--use-llm")
            if llm_confidence:
                add_show_args.append("--llm-confidence")
                add_show_args.append(str(llm_confidence)) # The CLI runner expects a string, not a float

            logger.info(f"Invoking add-show command with args: {add_show_args}")

            # Invoke the add-show CLI command
            add_show_result = runner.invoke(add_show, add_show_args, obj=ctx.obj)

            # Check the result of the add-show command
            if add_show_result.exit_code == 0:
                # Check if the output indicates the show already exists
                if "Show already exists in database" in add_show_result.output:
                    # This is actually a success - we found an existing show that matches
                    click.secho(f"✅ Show already exists: {show_name} (matched existing show)", fg="green")
                    
                    # Extract the existing show name from the output
                    # The output format is: "Info: Show already exists in DB: {show_name}"
                    output_text = add_show_result.output.strip()
                    if "Show already exists in DB: " in output_text:
                        existing_show_name = output_text.split("Show already exists in DB: ")[1].split("\n")[0].strip()
                        logger.info(f"Extracted existing show name from output: {existing_show_name}")
                        
                        # Now look up the show by its actual database name
                        existing_show = db.get_show_by_name_or_alias(existing_show_name)
                        if existing_show:
                            try:
                                current_aliases = existing_show.get("tmdb_aliases", "")
                                aliases_list = [a.strip() for a in current_aliases.split(",") if a.strip()]
                                
                                # Add the parsed show name if it's not already in aliases
                                if show_name not in aliases_list:
                                    aliases_list.append(show_name)
                                    new_aliases = ",".join(aliases_list)
                                    
                                    # Update the show's aliases in the database
                                    db.update_show_aliases(existing_show["id"], new_aliases)
                                    logger.info(f"Updated aliases for existing show '{existing_show.get('tmdb_name', show_name)}' to include parsed filename: {new_aliases}")
                                else:
                                    logger.info(f"Show '{existing_show.get('tmdb_name', show_name)}' already has parsed filename in aliases")
                            except Exception as alias_exc:
                                logger.warning(f"Failed to update aliases for existing show '{existing_show.get('tmdb_name', show_name)}': {alias_exc}")
                        else:
                            logger.warning(f"Could not retrieve existing show '{existing_show_name}' to update aliases")
                    else:
                        logger.warning(f"Could not parse existing show name from output: {output_text}")
                else:
                    # The show was successfully added
                    click.secho(f"✅ Auto-added: {show_name}", fg="green")
            else:
                # This is a genuine error
                click.secho(f"[ERROR] Failed to add show '{show_name}': {add_show_result.output.strip()}", fg="red")