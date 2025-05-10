import os
import click
import logging
from models.show import Show
from models.episode import Episode
from services.db_implementations.db_interface import DatabaseInterface
from services.tmdb_service import TMDBService
from utils.file_filters import sanitize_filename

def add_show_interactively(show_name, tmdb_id, db: DatabaseInterface, tmdb: TMDBService, anime_tv_path: str, dry_run: bool = False, override_dir: bool = False):
    logger = logging.getLogger(__name__)
    if tmdb_id:
        details = tmdb.get_show_details(tmdb_id)
        if not details or "info" not in details:
            raise ValueError("Could not retrieve show details for TMDB ID")
        sys_name = details["info"]["name"]
    elif show_name:
        results = tmdb.search_show(show_name)
        if not results or not results.get("results"):
            raise ValueError(f"No results found for show name: {show_name}")
        first_result = results["results"][0]
        tmdb_id = first_result["id"]
        details = tmdb.get_show_details(tmdb_id)
        if not details or "info" not in details:
            raise ValueError(f"Failed to retrieve full details for TMDB ID {tmdb_id}")
        sys_name = show_name
    else:
        raise ValueError("Either show_name or tmdb_id must be provided")

    if override_dir:
        sys_path = os.path.join(anime_tv_path, sanitize_filename(show_name))
        logger.info(f"Using provided show_name directly for the folder name: {sys_path}")
        sys_name = show_name
        logger.info(f"Using provided show_name directly for the sys_name: {sys_name}")
    else:
        sys_path = os.path.join(anime_tv_path, sanitize_filename(sys_name))
        logger.info(f"Using sanitized derived sys_name for the folder name: {sys_path}")

    # If the show already exists and we're not overriding the directory, raise an error
    #   If we're overriding the directory, assume we know what we're doing and continue
    #   Why does this scenario exist:  Remakes like Rurouni Kenshin and Ranma 1/2
    # TODO:  This is a hack and needs to be refactored with better logic
    if db.show_exists(sys_name):
        if not override_dir:
            raise FileExistsError(f"Show already exists in DB: {sys_name}")
        else:
            logger.info(f"Show already exists in DB: {sys_name}, but overriding directory.  Likely a remake.")
    
    # TODO:  Decisioning about sys_name and sys_path for show instantiation is less than ideal.
    show = Show.from_tmdb(show_details=details, sys_name=sys_name, sys_path=sys_path)
    episode_groups = details.get("episode_groups", {}).get("results", [])
    season_count = details["info"].get("number_of_seasons", 0)
    episodes = Episode.parse_from_tmdb(tmdb_id, tmdb, episode_groups, season_count)

    if dry_run:
        logger.info(f"[DRY RUN] Would create directory: {sys_path}")
        logger.info(f"[DRY RUN] Would insert show: {show.tmdb_name}")
        logger.info(f"[DRY RUN] Would insert {len(episodes)} episodes")
    else:
        os.makedirs(sys_path, exist_ok=True)
        db.add_show(show)
        db.add_episodes(episodes)
        logger.info(f"✅ Created directory and added show '{show.tmdb_name}' with {len(episodes)} episodes")

    return {
        "sys_path": sys_path,
        "tmdb_name": show.tmdb_name,
        "episode_count": len(episodes),
    }
