"""
Show adder utility for interactively adding shows to the database, with optional LLM support for TMDB selection.
"""
import os
import click
import logging
from models.show import Show
from models.episode import Episode
from services.db_implementations.db_interface import DatabaseInterface
from services.tmdb_service import TMDBService
from utils.file_filters import sanitize_filename

logger = logging.getLogger(__name__)

def add_show_interactively(
    show_name: str,
    tmdb_id: int,
    db: DatabaseInterface,
    tmdb: TMDBService,
    anime_tv_path: str,
    dry_run: bool = False,
    override_dir: bool = False,
    llm_service=None,
    use_llm: bool = False,
    max_tmdb_results: int = 20,
    llm_confidence: float = 0.7
) -> dict:
    """
    Add a show interactively, optionally using LLM to select the best TMDB match.

    Args:
        show_name (str): Name of the show to add.
        tmdb_id (int): TMDB ID of the show (if known).
        db (DatabaseInterface): Database interface for show/episode operations.
        tmdb (TMDBService): TMDB service for external API calls.
        anime_tv_path (str): Base path for TV show directories.
        dry_run (bool): If True, simulate actions without writing to DB or filesystem.
        override_dir (bool): Use show_name directly for folder name.
        llm_service: Optional LLM service for show selection.
        use_llm (bool): Whether to use LLM for show selection.
        max_tmdb_results (int): Max TMDB search results to consider for LLM selection.
        llm_confidence (float): Minimum confidence for LLM selection.

    Returns:
        dict: Information about the added show (sys_path, tmdb_name, episode_count).

    Raises:
        ValueError: If show cannot be found or added.
    """
    logger.debug(f"Called with show_name={show_name}, tmdb_id={tmdb_id}, override_dir={override_dir}, dry_run={dry_run}, use_llm={use_llm}, max_tmdb_results={max_tmdb_results}")
    try:
        if tmdb_id:
            logger.info("Using tmdb_id branch")
            details = tmdb.get_show_details(tmdb_id)
            if not details or "info" not in details:
                logger.exception("tmdb_id Branch - Could not retrieve show details for TMDB ID")
                raise ValueError("tmdb_id Branch - Could not retrieve show details for TMDB ID")
            #sys_name = details["info"]["name"] # original code
            sys_name = details["info"].get("name")
            
        elif use_llm and llm_service:
            logger.info("Using LLM branch")
            # Use LLM to search for the show name
            # Pull all results from TMDB for the show name
            results = tmdb.search_show(show_name)
            if not results or not results.get("results"):
                logger.exception(f"LLM Branch - No results found for show name: {show_name}")
                raise ValueError(f"No results found for show name: {show_name}")
            # Limit number of candidates
            candidates = results["results"][:max_tmdb_results]
            detailed_results = []
            
            # Get detailed results for each candidate
            for result in candidates:
                det = tmdb.get_show_details(result["id"])
                if det and "info" in det:
                    detailed_results.append(det)
            
            # If no detailed results, raise an error
            if not detailed_results:
                logger.exception(f"LLM Branch - No detailed TMDB results for show name: {show_name}")
                raise ValueError(f"LLM Branch - No detailed TMDB results for show name: {show_name}")
            logger.debug("Calling llm_service.suggest_show_name")

            # Use LLM to select best match and English name
            llm_response = llm_service.suggest_show_name(show_name, detailed_results)
            logger.debug(f"LLM Branch - LLM response: {llm_response}")

            # If LLM could not determine the best show match, raise an error
            if not llm_response or not llm_response.get("tmdb_id") or not llm_response.get("show_name"):
                logger.exception(f"LLM Branch - LLM could not determine the best show match. Response: {llm_response}")
                raise ValueError("LLM Branch - Could not determine the best show match.")
            
            # If LLM confidence is below the threshold, raise an error
            if llm_response.get("confidence") < llm_confidence:
                logger.exception(f"LLM Branch - LLM confidence is below the threshold: {llm_confidence}")
                raise ValueError(f"LLM Branch - LLM confidence is below the threshold: {llm_confidence}")

            # Use LLM to set the tmdb_id and sys_name vars
            tmdb_id = llm_response["tmdb_id"]
            sys_name = sanitize_filename(llm_response["show_name"])
            details = tmdb.get_show_details(tmdb_id)
            
            if not details or "info" not in details:
                logger.exception(f"LLM Branch - Failed to retrieve full details for TMDB ID {tmdb_id}")
                raise ValueError(f"LLM Branch - Failed to retrieve full details for TMDB ID {tmdb_id}")
            
        elif show_name:
            logger.info("Using show_name branch")
            results = tmdb.search_show(show_name)
            if not results or not results.get("results"):
                logger.exception(f"show_name Branch - No results found for show name: {show_name}")
                raise ValueError(f"show_name Branch - No results found for show name: {show_name}")
            first_result = results["results"][0]
            tmdb_id = first_result["id"]
            details = tmdb.get_show_details(tmdb_id)
            if not details or "info" not in details:
                logger.exception(f"show_name Branch - Failed to retrieve full details for TMDB ID {tmdb_id}")
                raise ValueError(f"show_name Branch - Failed to retrieve full details for TMDB ID {tmdb_id}")
            sys_name = show_name
        else:
            logger.exception("Neither show_name nor tmdb_id provided")
            raise ValueError("Neither show_name nor tmdb_id provided")

        if override_dir:
            sys_path = os.path.join(anime_tv_path, sanitize_filename(show_name))
            logger.debug(f"override_dir Branch - Using provided show_name directly for the folder name: {sys_path}")
            sys_name = show_name
            logger.debug(f"override_dir Branch - Using provided show_name directly for the sys_name: {sys_name}")
        else:
            sys_path = os.path.join(anime_tv_path, sanitize_filename(sys_name))
            logger.debug(f"Using sanitized derived sys_name for the folder name: {sys_path}")

        # If the show already exists and we're not overriding the directory, raise an error
        #   If we're overriding the directory, assume we know what we're doing and continue
        #   Why does this scenario exist:  Remakes like Rurouni Kenshin and Ranma 1/2
        # TODO:  This is a hack and needs to be refactored with better logic
        if db.show_exists(sys_name):
            if not override_dir:
                logger.exception(f"Show already exists in DB: {sys_name}")
                #raise FileExistsError(f"Show already exists in DB: {sys_name}")
                return(f"Show already exists in DB: {sys_name}")
            else:
                logger.info(f"Show already exists in DB: {sys_name}, but overriding directory. Likely a remake.")

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
    except Exception as e:
        logger.exception(f"Exception: {e}")
        raise
