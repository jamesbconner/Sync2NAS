import os
import re
import shutil
from typing import Optional, Tuple, List, Dict
from services.db_service import DBService
from models.episode import Episode
from models.show import Show
import logging

logger = logging.getLogger(__name__)

def parse_filename(filename: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Parse a filename to extract show metadata.

    Args:
        filename: The filename to parse

    Returns:
        A tuple of:
            - show_name: Name of the show (str or None)
            - episode: Episode number (str or None)
            - season: Season number (str or None)
            - year: Year (str or None)
    """
    filename = os.path.basename(filename)

    # Regex patterns:
    # 1. [Group] Show Name (Year) - Episode
    # 2. [Group] Show Name S01 - 01
    # 3. Show.Name.2000.S01E01
    # 4. Show Name - 101 [abc123]
    pattern = re.compile(
        r'(?:\[.*?\]\s*(?!.*\bS\d+\b)(.*?)(?:\s*\((\d{4})\))?\s*-\s*(\d+))|'     # group 1: [Group] Name (Year) - 12
        r'(?:\[.*?\]\s*(.*?)\s*-\s*S(\d{2})E(\d{2}))|'                           # group 2: [Group] Name - SxxEyy
        r'(?:^(.*?)(?:[.\-\s](\d{4}))?[.\-\s]S(\d{2})[.\-\s]?E(\d{2}))|'         # group 3: Name.SxxEyy
        r'(?:^(.*?)\s*-\s*(\d{1,4})(?:\s*\[.*?\])?)|'                            # group 4: Name - 12
        r'(?:^\[.*?\]_(.*?)-_(\d{2})-_)|'                                        # group 5: underscore -_01_- separator
        r'(?:^\[.*?\]\s*(.*?)\s+(\d{1,3})\s*\[.*)|'                              # group 6: Name 12 [something]
        r'(?:^\[.*?\]_(.*?)_(\d{1,3})_\()'                                       # group 7: underscore + number + (
    )                                                       

    match = pattern.search(filename)
    if not match:
        return None, None, None, None

    groups = match.groups()

    # Match group 1: [Group] Show Name (Year) - Episode
    if groups[0]:
        show_name = groups[0].strip()
        year = groups[1].strip() if groups[1] else None
        episode = groups[2].strip() if groups[2] else None
        season = None  # Do not default season, will fall back to absolute lookup
        logger.debug(f"Method 1: Parsed filename: Show:{show_name}, Episode:{episode}, Season:{season}, Year:{year}")
        return show_name, episode, season, year

    # Match group 2: [Group] Show Name S01 - 01
    elif groups[3]:
        show_name = groups[3].strip()
        season = groups[4].strip()
        episode = groups[5].strip()
        year = None
        logger.debug(f"Method 2: Parsed filename: Show:{show_name}, Episode:{episode}, Season:{season}, Year:{year}")
        return show_name, episode, season, year

    # Match group 3: Show.Name.2000.S01E01
    elif groups[6]:
        show_name = groups[6].replace(".", " ").replace("-", " ").strip()
        year = groups[7].strip() if groups[7] else None
        season = groups[8].strip() if groups[8] else None
        episode = groups[9].strip() if groups[9] else None
        logger.debug(f"Method 3: Parsed filename: Show:{show_name}, Episode:{episode}, Season:{season}, Year:{year}")
        return show_name, episode, season, year
    
    # Match group 4: Show Name - 101 [abc123]
    elif groups[10]:
        show_name = groups[10].strip()
        episode = groups[11].strip() if groups[11] else None
        season = None  # Will fall back to absolute lookup
        year = None
        logger.debug(f"Method 4: Parsed filename: Show:{show_name}, Episode:{episode}, Season:{season}, Year:{year}")
        return show_name, episode, season, None
    
    # Match group 5: underscore -_01_- separator
    elif groups[12]:
        show_name = groups[12].strip()
        episode = groups[13].strip() if groups[13] else None
        season = None
        year = None
        logger.debug(f"Method 5: Parsed filename: Show:{show_name}, Episode:{episode}, Season:{season}, Year:{year}")
        return show_name, episode, season, None
    
    # Match group 6: Name 12 [something]
    elif groups[14]:
        show_name = groups[14].strip()
        episode = groups[15].strip() if groups[15] else None
        season = None
        year = None
        logger.debug(f"Method 6: Parsed filename: Show:{show_name}, Episode:{episode}, Season:{season}, Year:{year}")   
        return show_name, episode, season, None
    
    # Match group 7: underscore + number + (
    elif groups[16]:
        show_name = groups[16].strip()
        episode = groups[17].strip() if groups[17] else None
        season = None
        year = None
        logger.debug(f"Method 7: Parsed filename: Show:{show_name}, Episode:{episode}, Season:{season}, Year:{year}")
        return show_name, episode, season, None

    else:
        logger.debug(f"Unexpected filename format: {filename}")
        return None, None, None, None


def file_routing(incoming_path: str, anime_tv_path: str, db: DBService, dry_run: bool = False) -> List[Dict[str, str]]:
    """
    Scan the incoming directory, identify files to route, and move them to their destination paths.

    Args:
        incoming_path: The directory to scan for files
        db: Instance of DBService to access show metadata
        dry_run: If True, only simulate routing without performing any filesystem operations

    Returns:
        A list of dicts containing information about routed files
    """
    logger.info(f"utils/file_routing.py::file_routing - Starting file routing")
    routed_files = []

    for root, _, files in os.walk(incoming_path):
        for filename in files:
            source_path = os.path.join(root, filename)

            show_name, episode_str, season_str, _ = parse_filename(filename)
            if not show_name:
                logger.debug(f"utils/file_routing.py::file_routing - Skipping file due to unrecognized name: {filename}")
                continue

            matched_show_row = db.get_show_by_name_or_alias(show_name)
            if not matched_show_row:
                logger.debug(f"utils/file_routing.py::file_routing - No matching show found in DB for: {show_name}")
                continue

            show = Show.from_db_record(matched_show_row)

            if season_str and episode_str:
                logger.debug(f"utils/file_routing.py::file_routing - Season and episode found in filename: {season_str}, {episode_str}")
                season_str = f"{int(season_str):02}"
                episode_str = f"{int(episode_str):02}"
            elif episode_str:
                abs_episode = int(episode_str)
                logger.debug(f"utils/file_routing.py::file_routing - Episode found in filename: {episode_str}")
                matched_episode = db.get_episode_by_absolute_number(show.tmdb_id, abs_episode)
                if matched_episode:
                    logger.debug(f"Found episode in DB for TMDB ID {show.tmdb_id} ep {abs_episode}: {matched_episode}")
                    season_str = f"{int(matched_episode['season']):02}"
                    episode_str = f"{int(matched_episode['episode']):02}"
                else:
                    logger.debug(f"utils/file_routing.py::file_routing - No episode match in DB for TMDB ID {show.tmdb_id} ep {abs_episode}")
                    continue
            else:
                logger.debug(f"utils/file_routing.py::file_routing - File has no usable episode metadata: {filename}")
                continue

            season_dir = os.path.join(show.sys_path, f"Season {season_str}")
            target_path = os.path.join(season_dir, filename)

            if dry_run:
                logger.info(f"[DRY RUN] Would move {source_path} to {target_path}")
            else:
                os.makedirs(season_dir, exist_ok=True)
                shutil.move(source_path, target_path)
                logger.info(f"Moved {source_path} to {target_path}")

            routed_files.append({
                "original_path": source_path,
                "routed_path": target_path,
                "show_name": show.sys_name,
                "season": season_str,
                "episode": episode_str
            })

    return routed_files