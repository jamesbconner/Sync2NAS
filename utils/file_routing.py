import os
import re
import shutil
from typing import Optional, Tuple, List, Dict
from services.db_implementations.db_interface import DatabaseInterface
from models.episode import Episode
from models.show import Show
import logging
from utils.episode_updater import refresh_episodes_for_show

logger = logging.getLogger(__name__)

def parse_filename(filename: str) -> dict:
    """
    Extract show metadata from a filename.

    Args:
        filename (str): Raw filename (e.g., "Show.Name.S01E01.1080p.mkv")

    Returns:
        dict: {
            "show_name": str,
            "season": int | None,
            "episode": int | None
        }
    """
    logger.debug(f"Parsing filename: {filename}")

    # Remove file extension
    base = re.sub(r"\.[a-z0-9]{2,4}$", "", filename, flags=re.IGNORECASE)

    # Remove all [tags] and (metadata)
    cleaned = re.sub(r"[\[\(].*?[\]\)]", "", base)

    # Normalize delimiters
    cleaned = re.sub(r"[_.]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Patterns to match the show name, season, and episode
    patterns = [
        r"(?P<name>.*?)[\s\-]+(?P<season>\d{1,2})(?:st|nd|rd|th)?[\s\-]+Season[\s\-]+(?P<episode>\d{1,3})",
        r"(?P<name>.*?)[\s\-]+[Ss](?P<season>\d{1,2})[Ee](?P<episode>\d{1,3})",
        r"(?P<name>.*?)[\s\-]+[Ss](?P<season>\d{1,2})[\s\-]+(?P<episode>\d{1,3})",
        r"(?P<name>.*?)(?:[\s\-]+[Ss](?P<season>\d{1,2}).*)?[\s\-]+[Ee](?P<episode>\d{1,3})",
        r"(?P<name>.*?)[\s\-]+(?P<episode>\d{1,3})(?:v\d)?\b",
        r"(?P<name>.*?)[\s\-]+(?P<episode>\d{1,3})$",
        r"(?P<name>.*?)\s+[Ss](?P<season>\d{1,2})[Ee](?P<episode>\d{1,3})"
    ]

    for index, pattern in enumerate(patterns):
        match = re.search(pattern, cleaned, re.IGNORECASE)
        if match:
            groups = match.groupdict()
            show_name = groups.get("name", "").strip(" -_")
            season = int(groups["season"]) if groups.get("season") else None
            episode = int(groups["episode"]) if groups.get("episode") else None
            logger.debug(f"Parsed: Show={show_name}, Season={season}, Episode={episode} - Pattern {index}")
            return {"show_name": show_name, "season": season, "episode": episode}

    logger.debug(f"No match found; fallback name: {cleaned}")
    return {"show_name": cleaned, "season": None, "episode": None}


def file_routing(incoming_path: str, anime_tv_path: str, db: DatabaseInterface, tmdb, dry_run: bool = False) -> List[Dict[str, str]]:
    """
    Scan the incoming directory, identify files to route, and move them to their destination paths.

    Args:
        incoming_path: The directory to scan for files
        anime_tv_path: Base directory where shows should be routed
        db: Database interface for show and episode lookup
        tmdb: TMDB object for episode refreshing
        dry_run: If True, simulate actions without moving files

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

            # Parse metadata from the filename
            metadata = parse_filename(filename)
            show_name = metadata["show_name"]
            season = metadata["season"]
            episode = metadata["episode"]

            # Skip files that don't contain a usable show name
            if not show_name:
                logger.debug(f"Skipping file due to missing show name: {filename}")
                continue

            # Lookup the show in the database by sys_name or aliases
            matched_show_row = db.get_show_by_name_or_alias(show_name)
            if not matched_show_row:
                logger.debug(f"No matching show in DB for: {show_name}")
                continue

            # Convert DB record into Show object
            show = Show.from_db_record(matched_show_row)

            # If season and episode are both found, format them
            if season is not None and episode is not None:
                season_str = f"{season:02}"
                episode_str = f"{episode:02}"

            # If only episode is found, use absolute episode lookup
            elif episode is not None:
                matched_ep = db.get_episode_by_absolute_number(show.tmdb_id, episode)
                if not matched_ep:
                    logger.debug(f"No episode match in DB for TMDB ID {show.tmdb_id}, absolute {episode}. Attempting to refresh episodes from TMDB.")
                    refresh_episodes_for_show(db, tmdb, show, dry_run)
                    matched_ep = db.get_episode_by_absolute_number(show.tmdb_id, episode)
                    if not matched_ep:
                        logger.error(f"No episode info found for show '{show.sys_name}' (TMDB ID {show.tmdb_id}), absolute episode {episode} after TMDB refresh.")
                        # Continue routing, but leave season/episode as None
                        season_str = None
                        episode_str = None
                    else:
                        season_str = f"{int(matched_ep['season']):02}"
                        episode_str = f"{int(matched_ep['episode']):02}"
                else:
                    season_str = f"{int(matched_ep['season']):02}"
                    episode_str = f"{int(matched_ep['episode']):02}"

            # If neither is available, skip this file
            else:
                logger.debug(f"Insufficient episode metadata for file: {filename}")
                continue

            # Construct destination path using the show's sys_path and season folder
            if season_str is not None:
                season_dir = os.path.join(show.sys_path, f"Season {season_str}")
            else:
                season_dir = show.sys_path
            target_path = os.path.join(season_dir, filename)

            # Perform or simulate the move operation
            if dry_run:
                logger.info(f"[DRY RUN] Would move {source_path} to {target_path}")
            else:
                os.makedirs(season_dir, exist_ok=True)
                shutil.move(source_path, target_path)
                logger.info(f"Moved {source_path} to {target_path}")

            # Track successful routing operation
            routed_files.append({
                "original_path": source_path,
                "routed_path": target_path,
                "show_name": show.sys_name,
                "season": season_str,
                "episode": episode_str
            })

    return routed_files