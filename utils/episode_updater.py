"""
Episode updater utility for refreshing episodes from TMDB and updating the local database.
"""
import logging
from models.episode import Episode
from models.show import Show

logger = logging.getLogger(__name__)

def refresh_episodes_for_show(db, tmdb, show, dry_run: bool) -> int:
    """
    Refresh episodes for a show from TMDB and update the local database.

    Args:
        db: Database interface for episode operations.
        tmdb: TMDBService instance for external API calls.
        show: Show object (must have tmdb_id).
        dry_run (bool): If True, do not write to the database.

    Returns:
        int: Number of episodes fetched (0 if failed).
    """
    logger.info(f"Starting update for show {show.sys_name} (tmdb_id={show.tmdb_id})")
    try:
        details = tmdb.get_show_details(show.tmdb_id)
        if not details or "info" not in details:
            logger.error(f"Failed to get TMDB details for {show.tmdb_id}")
            return 0

        episode_groups = details.get("episode_groups", {}).get("results", [])
        season_count = details["info"].get("number_of_seasons", 0)
        logger.debug(f"TMDB returned season_count={season_count}")

        episodes = Episode.parse_from_tmdb(show.tmdb_id, tmdb, episode_groups, season_count)
        logger.info(f"Parsed {len(episodes)} episodes from TMDB")

        if dry_run:
            logger.info("Dry run: skipping db.add_episodes()")
        else:
            logger.debug(f"Writing {len(episodes)} episodes to database")
            db.add_episodes(episodes)
            logger.info(f"Completed update for {show.sys_name}")
        return len(episodes)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise 