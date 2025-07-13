"""
Search TMDB CLI Command

This module provides a CLI command to search for shows directly on TMDB.
It supports searching by show name (default) or TMDB ID (flagged option).
"""

import logging
import click
from rich.console import Console
from rich.table import Table
from services.tmdb_service import TMDBService

logger = logging.getLogger(__name__)


@click.command("search-tmdb")
@click.argument("show_name", required=False)
@click.option("--tmdb-id", type=int, help="TMDB ID of the show to search for")
@click.option("--dry-run", is_flag=True, help="Simulate search without displaying results")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed show information")
@click.option("--limit", "-l", type=int, default=10, help="Limit number of search results (default: 10)")
@click.option("--year", "-y", type=int, help="Filter results by year")
@click.pass_context
def search_tmdb(ctx: click.Context, show_name: str, tmdb_id: int, dry_run: bool, verbose: bool, limit: int, year: int) -> None:
    """
    Search for shows directly on TMDB by name or TMDB ID.

    Args:
        ctx (click.Context): Click context containing shared config and services.
        show_name (str): Name of the show to search for (optional if tmdb_id provided).
        tmdb_id (int): TMDB ID of the show to search for.
        dry_run (bool): Simulate search without displaying results.
        verbose (bool): Show detailed show information.
        limit (int): Limit number of search results (default: 10).
        year (int): Filter results by year.

    Returns:
        None. Prints results to the console and exits on error.
    """
    if not ctx.obj:
        click.secho("❌ Error: No context object found", fg="red", bold=True)
        ctx.exit(1)

    tmdb: TMDBService = ctx.obj["tmdb"]
    console = Console()

    logger.info(f"Starting TMDB search: show_name={show_name}, tmdb_id={tmdb_id}, dry_run={dry_run}, limit={limit}, year={year}")

    try:
        if dry_run:
            click.secho("🧪 DRY RUN: Would search TMDB for shows", fg="yellow")
            if show_name:
                click.secho(f"  Show name: {show_name}", fg="yellow")
            if tmdb_id:
                click.secho(f"  TMDB ID: {tmdb_id}", fg="yellow")
            if year:
                click.secho(f"  Year filter: {year}", fg="yellow")
            click.secho(f"  Result limit: {limit}", fg="yellow")
            return

        # Case 1: Search by TMDB ID (highest priority)
        if tmdb_id:
            logger.info(f"Searching by TMDB ID: {tmdb_id}")
            _search_by_tmdb_id(tmdb_id, tmdb, verbose, console, ctx)

        # Case 2: Search by show name
        elif show_name:
            logger.info(f"Searching by show name: {show_name}")
            _search_by_show_name(show_name, tmdb, verbose, console, limit, year, ctx)

        # Case 3: No arguments - show usage
        else:
            click.secho("❌ Please provide either a show name or --tmdb-id", fg="red", bold=True)
            click.secho("\n📖 Usage Examples:", fg="cyan")
            click.secho("  python sync2nas.py search-tmdb \"One Piece\"", fg="white")
            click.secho("  python sync2nas.py search-tmdb --tmdb-id 37854", fg="white")
            click.secho("  python sync2nas.py search-tmdb \"One Piece\" --limit 5 --verbose", fg="white")
            ctx.exit(1)

    except Exception as e:
        logger.exception(f"Error during TMDB search: {e}")
        click.secho(f"❌ Error searching TMDB: {e}", fg="red", bold=True)
        ctx.exit(1)


def _search_by_tmdb_id(tmdb_id: int, tmdb: TMDBService, verbose: bool, console: Console, ctx: click.Context) -> None:
    """
    Search for a show by TMDB ID and display details.

    Args:
        tmdb_id (int): TMDB ID to search for.
        tmdb (TMDBService): TMDB service instance.
        verbose (bool): Whether to show detailed information.
        console (Console): Rich console for formatted output.
        ctx (click.Context): Click context for error handling.

    Returns:
        None. Prints results to the console and exits on error.
    """
    logger.info(f"Searching TMDB ID: {tmdb_id}")
    
    try:
        details = tmdb.get_show_details(tmdb_id)
        
        if not details or "info" not in details:
            click.secho(f"❌ No show found with TMDB ID {tmdb_id}", fg="red", bold=True)
            return
        
        show_info = details["info"]
        click.secho(f"✅ Found show with TMDB ID {tmdb_id}:", fg="green", bold=True)
        _display_tmdb_show_details(show_info, details, verbose, console)
        
    except Exception as e:
        logger.exception(f"Error fetching show details: {e}")
        click.secho(f"❌ Error fetching show details: {e}", fg="red", bold=True)
        ctx.exit(1)


def _search_by_show_name(show_name: str, tmdb: TMDBService, verbose: bool, console: Console, limit: int, year: int, ctx: click.Context) -> None:
    """
    Search for shows by name and display results.

    Args:
        show_name (str): Name to search for.
        tmdb (TMDBService): TMDB service instance.
        verbose (bool): Whether to show detailed information.
        console (Console): Rich console for formatted output.
        limit (int): Maximum number of results to display.
        year (int): Optional year filter.
        ctx (click.Context): Click context for error handling.

    Returns:
        None. Prints results to the console and exits on error.
    """
    logger.info(f"Searching for: {show_name}")
    
    try:
        results = tmdb.search_show(show_name)
        matches = results.get("results", [])
        
        if not matches:
            click.secho(f"❌ No shows found on TMDB matching '{show_name}'", fg="red", bold=True)
            return
        
        # Apply year filter if specified
        if year:
            original_count = len(matches)
            matches = [m for m in matches if m.get("first_air_date", "")[:4] == str(year)]
            logger.info(f"Year filter applied: {original_count} -> {len(matches)} results")
        
        # Limit results
        matches = matches[:limit]
        
        if len(matches) == 1 and verbose:
            # Show detailed info for single result
            click.secho(f"✅ Found 1 show matching '{show_name}':", fg="green", bold=True)
            _display_tmdb_show_details(matches[0], None, verbose, console)
        else:
            # Show table for multiple results
            click.secho(f"✅ Found {len(matches)} shows matching '{show_name}':", fg="green", bold=True)
            _display_tmdb_search_results(matches, console, verbose)
            
            if len(matches) == limit:
                click.secho(f"\n📝 Showing first {limit} results. Use --limit to see more.", fg="yellow")
        
    except Exception as e:
        logger.exception(f"Error searching TMDB: {e}")
        click.secho(f"❌ Error searching TMDB: {e}", fg="red", bold=True)
        ctx.exit(1)


def _display_tmdb_show_details(show_info: dict, full_details: dict, verbose: bool, console: Console) -> None:
    """
    Display detailed information about a TMDB show.

    Args:
        show_info (dict): Basic show information from TMDB.
        full_details (dict): Full show details (optional).
        verbose (bool): Whether to show detailed information.
        console (Console): Rich console for formatted output.

    Returns:
        None
    """
    logger.debug(f"Displaying show: {show_info.get('name', 'Unknown')}")
    
    # Basic information
    click.secho(f"📺 Name: {show_info.get('name', 'N/A')}", fg="cyan")
    click.secho(f" TMDB ID: {show_info.get('id', 'N/A')}", fg="blue")
    click.secho(f" Original Name: {show_info.get('original_name', 'N/A')}", fg="green")
    click.secho(f" Type: {show_info.get('media_type', 'N/A')}", fg="green")
    
    # Format dates
    first_aired = show_info.get('first_air_date')
    if first_aired:
        try:
            if 'T' in first_aired:
                first_aired = first_aired.split('T')[0]
            elif ' ' in first_aired:
                first_aired = first_aired.split(' ')[0]
        except Exception:
            first_aired = 'N/A'
    else:
        first_aired = 'N/A'
    
    last_aired = show_info.get('last_air_date')
    if last_aired:
        try:
            if 'T' in last_aired:
                last_aired = last_aired.split('T')[0]
            elif ' ' in last_aired:
                last_aired = last_aired.split(' ')[0]
        except Exception:
            last_aired = 'N/A'
    else:
        last_aired = 'N/A'
    
    click.secho(f"📅 First Aired: {first_aired}", fg="yellow")
    click.secho(f"📅 Last Aired: {last_aired}", fg="yellow")
    
    if verbose:
        click.secho("\n📊 Detailed Information:", fg="magenta", bold=True)
        click.secho(f"  Status: {show_info.get('status', 'N/A')}", fg="white")
        click.secho(f"  Seasons: {show_info.get('number_of_seasons', 'N/A')}", fg="white")
        click.secho(f"  Episodes: {show_info.get('number_of_episodes', 'N/A')}", fg="white")
        click.secho(f"  Runtime: {show_info.get('episode_run_time', ['N/A'])[0] if show_info.get('episode_run_time') else 'N/A'} min", fg="white")
        click.secho(f"  Language: {show_info.get('original_language', 'N/A')}", fg="white")
        click.secho(f"  Popularity: {show_info.get('popularity', 'N/A')}", fg="white")
        click.secho(f"  Vote Average: {show_info.get('vote_average', 'N/A')}", fg="white")
        click.secho(f"  Vote Count: {show_info.get('vote_count', 'N/A')}", fg="white")
        
        # Genres
        genres = show_info.get('genres', [])
        if genres:
            genre_names = [g.get('name', '') for g in genres]
            click.secho(f"  Genres: {', '.join(genre_names)}", fg="white")
        
        # Networks
        networks = show_info.get('networks', [])
        if networks:
            network_names = [n.get('name', '') for n in networks]
            click.secho(f"  Networks: {', '.join(network_names)}", fg="white")
        
        # Overview
        if show_info.get('overview'):
            click.secho(f"\n📝 Overview:", fg="white")
            click.secho(f"  {show_info.get('overview', 'N/A')}", fg="white")
        
        # External IDs (if available)
        if full_details and 'external_ids' in full_details:
            external_ids = full_details['external_ids']
            click.secho(f"\n External IDs:", fg="white")
            if external_ids.get('imdb_id'):
                click.secho(f"  IMDb: {external_ids['imdb_id']}", fg="white")
            if external_ids.get('tvdb_id'):
                click.secho(f"  TVDB: {external_ids['tvdb_id']}", fg="white")
            if external_ids.get('tvrage_id'):
                click.secho(f"  TVRage: {external_ids['tvrage_id']}", fg="white")


def _display_tmdb_search_results(matches: list, console: Console, verbose: bool) -> None:
    """
    Display a table of TMDB search results.

    Args:
        matches (list): List of show dictionaries from TMDB.
        console (Console): Rich console for formatted output.
        verbose (bool): Whether to show additional columns.

    Returns:
        None
    """
    logger.debug(f"Displaying {len(matches)} search results")
    
    table = Table(title="TMDB Search Results", show_lines=True)
    table.add_column("Index", style="bold cyan", justify="right")
    table.add_column("Name", style="bold green")
    table.add_column("Year", style="yellow", justify="center")
    table.add_column("TMDB ID", style="bold blue", justify="right")
    table.add_column("Status", style="magenta")
    
    if verbose:
        table.add_column("Overview", style="white", overflow="fold")

    for idx, result in enumerate(matches):
        year = result.get("first_air_date", "????")[:4] if result.get("first_air_date") else "????"
        status = result.get("status", "N/A")
        
        if verbose:
            overview = result.get("overview", "")[:100] + "..." if len(result.get("overview", "")) > 100 else result.get("overview", "")
            table.add_row(
                str(idx),
                result.get("name", "N/A"),
                year,
                str(result.get("id", "N/A")),
                status,
                overview
            )
        else:
            table.add_row(
                str(idx),
                result.get("name", "N/A"),
                year,
                str(result.get("id", "N/A")),
                status
            )

    console.print(table)
    
    if not verbose:
        click.secho("\n💡 Use --verbose for detailed information about each show", fg="cyan")
    
    click.secho("\n💡 Use 'add-show' command with --tmdb-id to add any of these shows to your database", fg="green") 