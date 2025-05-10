from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple, Union
import datetime
import logging
from models.episode import Episode
from contextlib import contextmanager
import os

logger = logging.getLogger(__name__)

class DatabaseInterface(ABC):
    """Abstract base class defining the interface for database operations."""
    
    @abstractmethod
    def initialize(self) -> None:
        """Initialize the database schema."""
        pass
    
    @abstractmethod
    def add_show(self, show: Any) -> None:
        """Add a show to the database."""
        pass
    
    @abstractmethod
    def add_episode(self, episode: Any) -> None:
        """Add an episode to the database."""
        pass
    
    @abstractmethod
    def add_episodes(self, episodes: List[Any]) -> None:
        """Add multiple episodes to the database."""
        pass
    
    @abstractmethod
    def show_exists(self, name: str) -> bool:
        """Check if a show exists based on name or aliases."""
        pass
    
    @abstractmethod
    def get_show_by_sys_name(self, sys_name: str) -> Optional[Dict[str, Any]]:
        """Get a show by its system name."""
        pass
    
    @abstractmethod
    def get_show_by_name_or_alias(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a show by name or alias."""
        pass
    
    @abstractmethod
    def get_show_by_tmdb_id(self, tmdb_id: int) -> Optional[dict]:
        """Fetch a show record by TMDB ID."""
        pass    
    
    @abstractmethod
    def get_all_shows(self) -> List[Dict[str, Any]]:
        """Get all shows from the database."""
        pass
    
    @abstractmethod
    def episodes_exist(self, tmdb_id: int) -> bool:
        """Check if episodes exist for the given show ID."""
        pass
    
    @abstractmethod
    def get_episodes_by_tmdb_id(self, tmdb_id: int) -> List[Dict[str, Any]]:
        """Get all episodes for a show by its TMDB ID."""
        pass
    
    @abstractmethod
    def get_inventory_files(self) -> List[Dict[str, Any]]:
        """Get all inventory files."""
        pass
    
    @abstractmethod
    def get_downloaded_files(self) -> List[Dict[str, Any]]:
        """Get all downloaded files."""
        pass
    
    @abstractmethod
    def add_downloaded_files(self, files: List[Dict[str, Any]]) -> None:
        """Add multiple downloaded files to the database."""
        pass
    
    @abstractmethod
    def get_sftp_diffs(self) -> List[Dict[str, Any]]:
        """Get differences between SFTP and downloaded files."""
        pass