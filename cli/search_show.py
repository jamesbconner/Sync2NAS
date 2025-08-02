"""
Search Show CLI Command

This module provides a CLI command to search for shows in the database.
It supports searching by show name (default) or TMDB ID (flagged option).
"""

import logging
import click
from rich.console import Console
from rich.table import Table
from services.db_implementations.db_interface import DatabaseInterface
from services.tmdb_service import TMDBService

logger = logging.getLogger(__name__)


def _search_shows_partial(show_name: str, db: DatabaseInterface) -> list:
    """
    Search for shows using partial matching.

    Args:
        show_name (str): Partial name to search for.
        db (DatabaseInterface): Database interface.

    Returns:
        list: List of matching shows.
    """
    logger.info(f"Searching for partial match: {show_name}")
    
    all_shows = db.get_all_shows()
    matches = []
    search_term = show_name.lower()
    
    for show in all_shows:
        # Check if search term appears in any of the name fields
        sys_name = show.get('sys_name', '').lower()
        tmdb_name = show.get('tmdb_name', '').lower()
        aliases = show.get('aliases', '').lower()
        
        if (search_term in sys_name or 
            search_term in tmdb_name or 
            search_term in aliases):
            matches.append(show)
    
    logger.info(f"Found {len(matches)} partial matches")
    return matches


@click.command("search-show")
@click.argument("show_name", required=False)
@click.option("--tmdb-id", type=int, help="TMDB ID of the show to search for")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed show information")
@click.option("--partial", "-p", is_flag=True, help="Enable partial matching (default behavior)")
@click.option("--exact", "-e", is_flag=True, help="Use exact matching only")
@click.pass_context
def search_show(ctx: click.Context, show_name: str, tmdb_id: int, verbose: bool, partial: bool, exact: bool) -> None:
    """
    Search for shows in the database by name or TMDB ID.

    If no arguments are provided, lists all shows in the database.
    By default, partial matching is enabled (e.g., "Piece" will find "One Piece").
    Use --exact for exact matching only.

    Args:
        ctx (click.Context): Click context containing shared config and services.
        show_name (str): Name of the show to search for (optional if tmdb_id provided).
        tmdb_id (int): TMDB ID of the show to search for.
        dry_run (bool): Simulate search without displaying results.
        verbose (bool): Show detailed show information.
        partial (bool): Enable partial matching (default behavior).
        exact (bool): Use exact matching only.

    Returns:
        None. Prints results to the console and exits on error.
    """
    if not ctx.obj:
        click.secho("❌ Error: No context object found", fg="red", bold=True)
        ctx.exit(1)

    db: DatabaseInterface = ctx.obj["db"]
    tmdb: TMDBService = ctx.obj["tmdb"]
    console = Console()

    dry_run = ctx.obj["dry_run"]
    logger.info(f"Starting show search: show_name={show_name}, tmdb_id={tmdb_id}, dry_run={dry_run}, partial={partial}, exact={exact}")

    try:
        if dry_run:
            click.secho("🧪 DRY RUN: Would search for shows", fg="yellow")
            if show_name:
                click.secho(f"  Show name: {show_name}", fg="yellow")
            if tmdb_id:
                click.secho(f"  TMDB ID: {tmdb_id}", fg="yellow")
            return

        # Case 1: Search by TMDB ID (highest priority)
        if tmdb_id:
            logger.info(f"Searching by TMDB ID: {tmdb_id}")
            show = db.get_show_by_tmdb_id(tmdb_id)
            
            if show:
                click.secho(f"✅ Found show with TMDB ID {tmdb_id}:", fg="green", bold=True)
                _display_show_details(show, verbose, console)
            else:
                click.secho(f"❌ No show found with TMDB ID {tmdb_id}", fg="red", bold=True)
                ctx.exit(1)

        # Case 2: Search by show name
        elif show_name:
            logger.info(f"Searching by show name: {show_name}")
            
            # First try exact match
            show = db.get_show_by_name_or_alias(show_name)
            
            if show:
                click.secho(f"✅ Found exact match for '{show_name}':", fg="green", bold=True)
                _display_show_details(show, verbose, console)
            else:
                # If exact match fails and partial matching is enabled (default)
                if not exact:
                    logger.info(f"No exact match found, trying partial match")
                    partial_matches = _search_shows_partial(show_name, db)
                    
                    if partial_matches:
                        if len(partial_matches) == 1:
                            click.secho(f"✅ Found 1 partial match for '{show_name}':", fg="green", bold=True)
                            _display_show_details(partial_matches[0], verbose, console)
                        else:
                            click.secho(f"✅ Found {len(partial_matches)} partial matches for '{show_name}':", fg="green", bold=True)
                            _display_shows_table(partial_matches, console)
                    else:
                        click.secho(f"❌ No shows found matching '{show_name}' (exact or partial)", fg="red", bold=True)
                        
                        # Offer to search TMDB for similar shows
                        click.secho("\n🔍 Would you like to search TMDB for similar shows?", fg="cyan")
                        if click.confirm("Search TMDB?"):
                            _search_tmdb_for_similar_shows(show_name, tmdb, console, dry_run)
                else:
                    click.secho(f"❌ No exact match found for '{show_name}'", fg="red", bold=True)
                    
                    # Offer to search TMDB for similar shows
                    click.secho("\n🔍 Would you like to search TMDB for similar shows?", fg="cyan")
                    if click.confirm("Search TMDB?"):
                        _search_tmdb_for_similar_shows(show_name, tmdb, console, dry_run)

        # Case 3: No arguments - list all shows
        else:
            logger.info("No search criteria provided, listing all shows")
            shows = db.get_all_shows()
            
            if not shows:
                click.secho("📭 No shows found in database", fg="yellow")
                return
            
            click.secho(f"✅ Found {len(shows)} shows in database:", fg="cyan", bold=True)
            _display_shows_table(shows, console)

    except Exception as e:
        logger.exception(f"Error during show search: {e}")
        click.secho(f"❌ Error searching for shows: {e}", fg="red", bold=True)
        ctx.exit(1)


def _display_show_details(show: dict, verbose: bool, console: Console) -> None:
    """
    Display detailed information about a single show.

    Args:
        show (dict): Show dictionary from database.
        verbose (bool): Whether to show detailed information.
        console (Console): Rich console for formatted output.

    Returns:
        None
    """
    logger.debug(f"Displaying show: {show.get('tmdb_name', 'Unknown')}")
    
    # Basic information
    click.secho(f"📺 Name: {show.get('tmdb_name', 'N/A')}", fg="cyan")
    click.secho(f"�� Database ID: {show.get('id', 'N/A')}", fg="blue")
    click.secho(f"�� TMDB ID: {show.get('tmdb_id', 'N/A')}", fg="blue")
    click.secho(f"�� System Name: {show.get('sys_name', 'N/A')}", fg="green")
    click.secho(f"📂 Path: {show.get('sys_path', 'N/A')}", fg="green")
    
    if show.get('aliases'):
        click.secho(f"🏷️ Aliases: {show.get('aliases', 'N/A')}", fg="yellow")
    
    if verbose:
        click.secho("\n📊 Detailed Information:", fg="magenta", bold=True)
        
        # Format first aired date
        first_aired = show.get('tmdb_first_aired')
        if first_aired:
            try:
                # Handle both string and datetime objects
                if isinstance(first_aired, str):
                    # If it's already a date string, extract just the date part
                    if 'T' in first_aired:
                        first_aired = first_aired.split('T')[0]
                    elif ' ' in first_aired:
                        first_aired = first_aired.split(' ')[0]
                else:
                    # If it's a datetime object, format as date
                    first_aired = first_aired.strftime('%Y-%m-%d')
            except Exception:
                first_aired = 'N/A'
        else:
            first_aired = 'N/A'
        
        # Format last aired date
        last_aired = show.get('tmdb_last_aired')
        if last_aired:
            try:
                # Handle both string and datetime objects
                if isinstance(last_aired, str):
                    # If it's already a date string, extract just the date part
                    if 'T' in last_aired:
                        last_aired = last_aired.split('T')[0]
                    elif ' ' in last_aired:
                        last_aired = last_aired.split(' ')[0]
                else:
                    # If it's a datetime object, format as date
                    last_aired = last_aired.strftime('%Y-%m-%d')
            except Exception:
                last_aired = 'N/A'
        else:
            last_aired = 'N/A'
        
        click.secho(f"  First Aired: {first_aired}", fg="white")
        click.secho(f"  Last Aired: {last_aired}", fg="white")
        click.secho(f"  Year: {show.get('tmdb_year', 'N/A')}", fg="white")
        click.secho(f"  Seasons: {show.get('tmdb_season_count', 'N/A')}", fg="white")
        click.secho(f"  Episodes: {show.get('tmdb_episode_count', 'N/A')}", fg="white")
        click.secho(f"  Status: {show.get('tmdb_status', 'N/A')}", fg="white")
        click.secho(f"  Last Updated: {show.get('fetched_at', 'N/A')}", fg="white")
        
        if show.get('tmdb_overview'):
            click.secho(f"\n📝 Overview:", fg="white")
            click.secho(f"  {show.get('tmdb_overview', 'N/A')}", fg="white")


def _display_shows_table(shows: list, console: Console) -> None:
    """
    Display a table of multiple shows.

    Args:
        shows (list): List of show dictionaries from database.
        console (Console): Rich console for formatted output.

    Returns:
        None
    """
    logger.debug(f"Displaying {len(shows)} shows in table")
    
    table = Table(title="Shows in Database", show_lines=True)
    table.add_column("ID", style="bold cyan", justify="right")
    table.add_column("TMDB ID", style="bold blue", justify="right")
    table.add_column("Name", style="bold green")
    table.add_column("System Name", style="yellow")
    table.add_column("Path", style="blue", overflow="fold")
    table.add_column("Status", style="magenta")

    for show in shows:
        table.add_row(
            str(show.get('id', 'N/A')),
            str(show.get('tmdb_id', 'N/A')),
            show.get('tmdb_name', 'N/A'),
            show.get('sys_name', 'N/A'),
            show.get('sys_path', 'N/A'),
            show.get('tmdb_status', 'N/A')
        )

    console.print(table)


def _search_tmdb_for_similar_shows(show_name: str, tmdb: TMDBService, console: Console, dry_run: bool = False):
    """
    Search TMDB for shows similar to the provided name.
    
    Args:
        show_name: Name to search for
        tmdb: TMDB service instance
        console: Rich console for formatted output
        dry_run: Whether to run in dry-run mode
    """
    logger.info(f"Searching TMDB for: {show_name}")
    
    try:
        results = tmdb.search_show(show_name)
        matches = results.get("results", [])
        
        if not matches:
            click.secho("❌ No TMDB results found", fg="red")
            return
        
        click.secho(f"\n✅ Found {len(matches)} similar shows on TMDB:", fg="cyan", bold=True)
        
        table = Table(title="TMDB Search Results", show_lines=True)
        table.add_column("Index", style="bold cyan", justify="right")
        table.add_column("Name", style="bold green")
        table.add_column("Year", style="yellow", justify="center")
        table.add_column("TMDB ID", style="bold blue", justify="right")
        table.add_column("Overview", style="white", overflow="fold")

        for idx, result in enumerate(matches[:10]):  # Limit to first 10 results
            year = result.get("first_air_date", "????")[:4] if result.get("first_air_date") else "????"
            overview = result.get("overview", "")[:100] + "..." if len(result.get("overview", "")) > 100 else result.get("overview", "")
            
            table.add_row(
                str(idx),
                result.get("name", "N/A"),
                year,
                str(result.get("id", "N/A")),
                overview
            )

        console.print(table)
        click.secho("\n✅ Tip: Use 'add-show' command with --tmdb-id to add any of these shows", fg="green")
        
    except Exception as e:
        logger.exception(f"Error searching TMDB: {e}")
        click.secho(f"❌ Error searching TMDB: {e}", fg="red") 