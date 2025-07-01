import os
import re
import shutil
from typing import Optional, Tuple, List, Dict
from services.db_implementations.db_interface import DatabaseInterface
from models.episode import Episode
from models.show import Show
import logging
from utils.episode_updater import refresh_episodes_for_show
from services.llm_implementations.llm_interface import LLMInterface
from utils.filename_parser import parse_filename

logger = logging.getLogger(__name__)

def file_routing(incoming_path: str, anime_tv_path: str, db: DatabaseInterface, tmdb, 
                dry_run: bool = False, llm_service: Optional[LLMInterface] = None, llm_confidence_threshold: float = 0.7) -> List[Dict[str, str]]:
    """
    Scan the incoming directory, identify files to route, and move them to their destination paths.

    Args:
        incoming_path: The directory to scan for files
        anime_tv_path: Base directory where shows should be routed
        db: Database interface for show and episode lookup
        tmdb: TMDB object for episode refreshing
        dry_run: If True, simulate actions without moving files
        llm_service: Optional LLM service for intelligent filename parsing
        llm_confidence_threshold: Minimum confidence to accept LLM result

    Returns:
        List of dicts describing routed files
    """
    logger.info("utils/file_routing.py::file_routing - Starting file routing")
    routed_files = []

    # Walk the incoming directory tree
    for root, _, files in os.walk(incoming_path):
        for filename in files:
            # Build the full source path
            source_path = os.path.join(root, filename)

            # Parse metadata from the filename (now with LLM support)
            metadata = parse_filename(filename, llm_service, llm_confidence_threshold)
            show_name = metadata["show_name"]
            season = metadata["season"]
            episode = metadata["episode"]
            confidence = metadata.get("confidence", 0.0)
            reasoning = metadata.get("reasoning", "Unknown")

            # Log parsing details
            logger.info(f"utils/file_routing.py::file_routing - Parsed '{filename}': {show_name} S{season}E{episode} (confidence: {confidence})")

            # Skip files that don't contain a usable show name
            if not show_name:
                logger.debug(f"utils/file_routing.py::file_routing - Skipping file due to missing show name: {filename}")
                continue

            # Lookup the show in the database by sys_name or aliases
            matched_show_row = db.get_show_by_name_or_alias(show_name)
            if not matched_show_row:
                logger.debug(f"utils/file_routing.py::file_routing - No matching show in DB for: {show_name}")
                continue

            # Convert DB record into Show object
            show = Show.from_db_record(matched_show_row)

            # If season and episode are both found, format them
            if season is not None and episode is not None:
                season_str = f"{season:02}"
                episode_str = f"{episode:02}"
                season_int = season
                episode_int = episode

            # If only episode is found, use absolute episode lookup
            elif episode is not None:
                matched_ep = db.get_episode_by_absolute_number(show.tmdb_id, episode)
                if not matched_ep:
                    logger.debug(f"utils/file_routing.py::file_routing - No episode match in DB for TMDB ID {show.tmdb_id}, absolute {episode}. Attempting to refresh episodes from TMDB.")
                    refresh_episodes_for_show(db, tmdb, show, dry_run)
                    matched_ep = db.get_episode_by_absolute_number(show.tmdb_id, episode)
                    if not matched_ep:
                        logger.error(f"utils/file_routing.py::file_routing - No episode info found for show '{show.sys_name}' (TMDB ID {show.tmdb_id}), absolute episode {episode} after TMDB refresh.")
                        # Continue routing, but leave season/episode as None
                        season_str = None
                        episode_str = None
                        season_int = None
                        episode_int = None
                    else:
                        season_str = f"{int(matched_ep['season']):02}"
                        episode_str = f"{int(matched_ep['episode']):02}"
                        season_int = int(matched_ep['season'])
                        episode_int = int(matched_ep['episode'])
                else:
                    season_str = f"{int(matched_ep['season']):02}"
                    episode_str = f"{int(matched_ep['episode']):02}"
                    season_int = int(matched_ep['season'])
                    episode_int = int(matched_ep['episode'])

            # If neither is available, skip this file
            else:
                logger.debug(f"utils/file_routing.py::file_routing - Insufficient episode metadata for file: {filename}")
                continue

            # Construct destination path using the show's sys_path and season folder
            if season_str is not None:
                season_dir = os.path.join(show.sys_path, f"Season {season_str}")
            else:
                season_dir = show.sys_path
            target_path = os.path.join(season_dir, filename)

            # Perform or simulate the move operation
            if dry_run:
                logger.info(f"utils/file_routing.py::file_routing - [DRY RUN] Would move {source_path} to {target_path}")
            else:
                os.makedirs(season_dir, exist_ok=True)
                shutil.move(source_path, target_path)
                logger.info(f"utils/file_routing.py::file_routing - Moved {source_path} to {target_path}")

            # Track successful routing operation
            routed_files.append({
                "original_path": source_path,
                "routed_path": target_path,
                "show_name": show.sys_name,
                "season": season_str, # Changed from season_int to season_str
                "episode": episode_str, # Changed from episode_int to episode_str
                "confidence": confidence,
                "reasoning": reasoning
            })

    return routed_files