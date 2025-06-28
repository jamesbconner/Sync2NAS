"""
Show Service Module

This module provides the business logic for TV show management operations
in the Sync2NAS API. It handles show creation, retrieval, updates, and deletion
by coordinating between the database, TMDB service, and file system operations.

Dependencies:
    - DatabaseInterface: Database operations
    - TMDBService: External TMDB API operations
    - Show/Episode models: Data models
    - Utility functions: show_adder, episode_updater
"""

import logging
from typing import List, Optional, Dict, Any
from services.db_implementations.db_interface import DatabaseInterface
from services.tmdb_service import TMDBService
from utils.show_adder import add_show_interactively
from models.show import Show
from models.episode import Episode
from utils.episode_updater import refresh_episodes_for_show

logger = logging.getLogger(__name__)


class ShowService:
    """
    Service class for managing TV show operations.
    
    Provides methods for adding, retrieving, updating, and deleting shows
    and their associated episodes. Coordinates between database operations,
    TMDB API calls, and file system management.
    
    Attributes:
        db: Database interface for show and episode operations
        tmdb: TMDB service for external API calls
        anime_tv_path: Base path for TV show directories
    """
    
    def __init__(self, db: DatabaseInterface, tmdb: TMDBService, anime_tv_path: str):
        """
        Initialize the ShowService with required dependencies.
        
        Args:
            db: Database interface for show and episode operations
            tmdb: TMDB service for external API calls
            anime_tv_path: Base path for TV show directories
        """
        self.db = db
        self.tmdb = tmdb
        self.anime_tv_path = anime_tv_path
        logger.debug(f"api/services/show_service.py::__init__ - ShowService initialized with anime_tv_path: {anime_tv_path}")

    async def add_show(self, show_name: Optional[str] = None, 
                      tmdb_id: Optional[int] = None,
                      override_dir: bool = False) -> Dict[str, Any]:
        """
        Add a new TV show to the database and file system.
        
        This method coordinates the process of adding a show by:
        1. Validating input parameters
        2. Searching TMDB for show information (if needed)
        3. Creating the show directory structure
        4. Adding show and episode data to the database
        5. Returning detailed operation results
        
        Args:
            show_name: Name of the show to search for (optional if tmdb_id provided)
            tmdb_id: TMDB ID of the show (optional if show_name provided)
            override_dir: Whether to use show_name directly for directory name
            
        Returns:
            dict: Operation result containing:
                - success: Boolean indicating operation success
                - tmdb_name: Official TMDB name of the show
                - sys_path: System path where show was created
                - episode_count: Number of episodes added
                - message: Human-readable success message
                
        Raises:
            ValueError: If neither show_name nor tmdb_id is provided
            FileExistsError: If show already exists and override_dir is False
            Exception: For other operational errors
        """
        logger.info(f"api/services/show_service.py::add_show - Starting show addition: show_name={show_name}, tmdb_id={tmdb_id}, override_dir={override_dir}")
        
        # Input validation
        if not show_name and not tmdb_id:
            logger.error("api/services/show_service.py::add_show - Missing required parameters: neither show_name nor tmdb_id provided")
            raise ValueError("Either show_name or tmdb_id must be provided")

        try:
            # Delegate to existing utility function for show addition logic
            logger.debug("api/services/show_service.py::add_show - Calling add_show_interactively utility")
            result = add_show_interactively(
                show_name=show_name,
                tmdb_id=tmdb_id,
                db=self.db,
                tmdb=self.tmdb,
                anime_tv_path=self.anime_tv_path,
                dry_run=False,
                override_dir=override_dir,
            )
            
            # Format response for API consumption
            api_result = {
                "success": True,
                "tmdb_name": result["tmdb_name"],
                "sys_path": result["sys_path"],
                "episode_count": result["episode_count"],
                "message": f"Show added successfully: {result['tmdb_name']}"
            }
            
            logger.info(f"api/services/show_service.py::add_show - Successfully added show: {result['tmdb_name']} with {result['episode_count']} episodes")
            return api_result
            
        except ValueError as e:
            logger.error(f"api/services/show_service.py::add_show - Validation error: {e}")
            raise
        except FileExistsError as e:
            logger.error(f"api/services/show_service.py::add_show - Show already exists: {e}")
            raise
        except Exception as e:
            logger.exception(f"api/services/show_service.py::add_show - Unexpected error during show addition: {e}")
            raise

    async def get_shows(self) -> List[Dict[str, Any]]:
        """
        Retrieve all shows from the database.
        
        Returns:
            list: List of show dictionaries containing:
                - id: Database ID of the show
                - tmdb_id: TMDB ID of the show
                - tmdb_name: Official TMDB name
                - sys_name: System name used for directory
                - sys_path: Full system path to show directory
                - aliases: Alternative names for the show
                
        Raises:
            Exception: If database operation fails
        """
        logger.info("api/services/show_service.py::get_shows - Retrieving all shows from database")
        
        try:
            shows = self.db.get_all_shows()
            
            # Transform database records to API response format
            api_shows = [
                {
                    "id": show["id"],
                    "tmdb_id": show["tmdb_id"],
                    "tmdb_name": show["tmdb_name"],
                    "sys_name": show["sys_name"],
                    "sys_path": show["sys_path"],
                    "aliases": show.get("aliases")
                }
                for show in shows
            ]
            
            logger.info(f"api/services/show_service.py::get_shows - Successfully retrieved {len(api_shows)} shows")
            return api_shows
            
        except Exception as e:
            logger.exception(f"api/services/show_service.py::get_shows - Failed to retrieve shows: {e}")
            raise

    async def get_show(self, show_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific show by its database ID.
        
        Args:
            show_id: Database ID of the show to retrieve
            
        Returns:
            dict: Show information if found, None otherwise
            
        Raises:
            Exception: If database operation fails
        """
        logger.info(f"api/services/show_service.py::get_show - Retrieving show with ID: {show_id}")
        
        try:
            show = self.db.get_show_by_id(show_id)
            
            if not show:
                logger.warning(f"api/services/show_service.py::get_show - Show with ID {show_id} not found")
                return None
            
            # Transform database record to API response format
            api_show = {
                "id": show["id"],
                "tmdb_id": show["tmdb_id"],
                "tmdb_name": show["tmdb_name"],
                "sys_name": show["sys_name"],
                "sys_path": show["sys_path"],
                "aliases": show.get("aliases")
            }
            
            logger.info(f"api/services/show_service.py::get_show - Successfully retrieved show: {show['tmdb_name']}")
            return api_show
            
        except Exception as e:
            logger.exception(f"api/services/show_service.py::get_show - Failed to retrieve show {show_id}: {e}")
            raise

    async def update_episodes(self, show_name: Optional[str] = None,
                            tmdb_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Update episodes for a show by refreshing data from TMDB.
        
        This method refreshes episode information for a show by:
        1. Locating the show in the database
        2. Fetching fresh episode data from TMDB
        3. Updating the database with new episode information
        
        Args:
            show_name: Name of the show to update (optional if tmdb_id provided)
            tmdb_id: TMDB ID of the show to update (optional if show_name provided)
            
        Returns:
            dict: Operation result containing:
                - success: Boolean indicating operation success
                - episodes_updated: Number of episodes updated
                - show_name: Name of the show updated
                - message: Human-readable success message
                
        Raises:
            ValueError: If neither show_name nor tmdb_id is provided, or if show not found
            Exception: For other operational errors
        """
        logger.info(f"api/services/show_service.py::update_episodes - Starting episode update: show_name={show_name}, tmdb_id={tmdb_id}")
        
        # Input validation
        if not show_name and not tmdb_id:
            logger.error("api/services/show_service.py::update_episodes - Missing required parameters: neither show_name nor tmdb_id provided")
            raise ValueError("Either show_name or tmdb_id must be provided")

        try:
            # Resolve show record from database
            if tmdb_id:
                logger.debug(f"api/services/show_service.py::update_episodes - Looking up show by TMDB ID: {tmdb_id}")
                show_row = self.db.get_show_by_tmdb_id(tmdb_id)
                if not show_row:
                    logger.error(f"api/services/show_service.py::update_episodes - No show found in DB for TMDB ID {tmdb_id}")
                    raise ValueError(f"No show found in DB for TMDB ID {tmdb_id}")
            else:
                logger.debug(f"api/services/show_service.py::update_episodes - Looking up show by name: {show_name}")
                show_row = self.db.get_show_by_name_or_alias(show_name)
                if not show_row:
                    logger.error(f"api/services/show_service.py::update_episodes - No show found in DB for show name '{show_name}'")
                    raise ValueError(f"No show found in DB for show name '{show_name}'")

            # Create Show object and refresh episodes
            show = Show.from_db_record(show_row)
            logger.info(f"api/services/show_service.py::update_episodes - Found show: {show.sys_name} (TMDB ID {show.tmdb_id})")
            
            logger.debug("api/services/show_service.py::update_episodes - Calling refresh_episodes_for_show utility")
            num_episodes = refresh_episodes_for_show(self.db, self.tmdb, show, dry_run=False)
            
            if num_episodes == 0:
                logger.error(f"api/services/show_service.py::update_episodes - Failed to fetch or update episodes for {show.sys_name}")
                raise ValueError(f"Failed to fetch or update episodes for {show.sys_name}")

            # Format response for API consumption
            api_result = {
                "success": True,
                "episodes_updated": num_episodes,
                "show_name": show.sys_name,
                "message": f"{num_episodes} episodes added/updated for {show.sys_name}"
            }
            
            logger.info(f"api/services/show_service.py::update_episodes - Successfully updated {num_episodes} episodes for {show.sys_name}")
            return api_result
            
        except ValueError as e:
            logger.error(f"api/services/show_service.py::update_episodes - Validation error: {e}")
            raise
        except Exception as e:
            logger.exception(f"api/services/show_service.py::update_episodes - Unexpected error during episode update: {e}")
            raise

    async def delete_show(self, show_id: int) -> Dict[str, Any]:
        """
        Delete a show and all its associated episodes from the database.
        
        This method is primarily used for fixing mis-identified shows by:
        1. Removing the show and all episodes from the database
        2. Allowing the show to be re-added with correct identification
        
        Args:
            show_id: Database ID of the show to delete
            
        Returns:
            dict: Operation result containing:
                - success: Boolean indicating operation success
                - show_name: Name of the show that was deleted
                - episodes_deleted: Number of episodes deleted
                - message: Human-readable success message
                
        Raises:
            ValueError: If show not found
            Exception: For other operational errors
        """
        logger.info(f"api/services/show_service.py::delete_show - Starting show deletion: show_id={show_id}")
        
        try:
            # First verify the show exists and get its details
            show = self.db.get_show_by_id(show_id)
            if not show:
                logger.error(f"api/services/show_service.py::delete_show - Show with ID {show_id} not found")
                raise ValueError(f"Show with ID {show_id} not found")
            
            show_name = show["tmdb_name"]
            tmdb_id = show["tmdb_id"]
            
            logger.info(f"api/services/show_service.py::delete_show - Found show to delete: {show_name} (TMDB ID {tmdb_id})")
            
            # Get episode count before deletion for reporting
            episodes = self.db.get_episodes_by_tmdb_id(tmdb_id)
            episode_count = len(episodes)
            
            # Delete the show and all episodes using existing database method
            logger.debug(f"api/services/show_service.py::delete_show - Calling database delete_show_and_episodes method")
            self.db.delete_show_and_episodes(tmdb_id)
            
            # Format response for API consumption
            api_result = {
                "success": True,
                "show_name": show_name,
                "episodes_deleted": episode_count,
                "message": f"Successfully deleted show '{show_name}' and {episode_count} episodes"
            }
            
            logger.info(f"api/services/show_service.py::delete_show - Successfully deleted show: {show_name} with {episode_count} episodes")
            return api_result
            
        except ValueError as e:
            logger.error(f"api/services/show_service.py::delete_show - Validation error: {e}")
            raise
        except Exception as e:
            logger.exception(f"api/services/show_service.py::delete_show - Unexpected error during show deletion: {e}")
            raise 