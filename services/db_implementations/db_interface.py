from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple, Union
import datetime
import logging
from models.episode import Episode
from contextlib import contextmanager
import os
from models.downloaded_file import DownloadedFile, FileStatus

logger = logging.getLogger(__name__)

class DatabaseInterface(ABC):
    """
    Abstract base class defining the interface for database operations in Sync2NAS.

    All subclasses must implement methods for initializing the database, adding and retrieving shows/episodes, and managing file metadata.

    Methods:
        initialize(): Initialize the database schema.
        add_show(show): Add a show to the database.
        add_episode(episode): Add an episode to the database.
        add_episodes(episodes): Add multiple episodes to the database.
        show_exists(name): Check if a show exists.
        get_show_by_sys_name(sys_name): Get a show by its system name.
        get_show_by_name_or_alias(name): Get a show by name or alias.
        get_show_by_tmdb_id(tmdb_id): Fetch a show record by TMDB ID.
        get_all_shows(): Get all shows from the database.
        episodes_exist(tmdb_id): Check if episodes exist for the given show ID.
        get_episodes_by_tmdb_id(tmdb_id): Get all episodes for a show by its TMDB ID.
        get_inventory_files(): Get all inventory files.
        get_downloaded_files(): Get all downloaded files.
        add_downloaded_files(files): Add multiple downloaded files to the database.
        get_sftp_diffs(): Get differences between SFTP and downloaded files.
        backup_database(): Backup the database.
        get_show_by_id(show_id): Get a show by its database ID.
        is_read_only(): Check if database is in read-only mode.
    """
    
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

    @abstractmethod
    def backup_database(self) -> str:
        """
        Backs up the database.
        Returns the path or identifier of the backup.
        """
        pass

    @abstractmethod
    def get_show_by_id(self, show_id: int) -> Optional[Dict[str, Any]]:
        """Get a show by its database ID."""
        pass

    @abstractmethod
    def is_read_only(self) -> bool:
        """Check if database is in read-only mode."""
        pass

    @abstractmethod
    def upsert_downloaded_file(self, file: DownloadedFile) -> DownloadedFile:
        """Insert/update a DownloadedFile keyed by remote_path (bridged from original_path)."""
        pass

    @abstractmethod
    def set_downloaded_file_hash(self, file_id: int, algo: str, value: str, calculated_at: Optional[datetime.datetime] = None) -> None:
        pass

    @abstractmethod
    def update_downloaded_file_location(self, file_id: int, new_path: str, new_status: FileStatus = FileStatus.ROUTED, routed_at: Optional[datetime.datetime] = None) -> None:
        pass

    @abstractmethod
    def update_downloaded_file_location_by_current_path(self, current_path: str, new_path: str, new_status: FileStatus = FileStatus.ROUTED, routed_at: Optional[datetime.datetime] = None) -> None:
        pass

    @abstractmethod
    def mark_downloaded_file_error(self, file_id: int, message: str) -> None:
        pass

    @abstractmethod
    def get_downloaded_files_by_status(self, status: FileStatus) -> List[DownloadedFile]:
        pass

    @abstractmethod
    def get_downloaded_file_by_remote_path(self, remote_path: str) -> Optional[DownloadedFile]:
        pass

    @abstractmethod
    def search_downloaded_files(self,
        *,
        status: Optional[FileStatus] = None,
        file_type: Optional[str] = None,
        q: Optional[str] = None,
        tmdb_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = "modified_time",
        sort_order: str = "desc",
    ) -> Tuple[List[DownloadedFile], int]:
        """Search downloaded files with filters and pagination."""
        pass

    @abstractmethod
    def get_downloaded_file_by_id(self, file_id: int) -> Optional[DownloadedFile]:
        """Fetch a single DownloadedFile by its primary key id."""
        pass

    @abstractmethod
    def update_downloaded_file_status(self, file_id: int, new_status: FileStatus, error_message: Optional[str] = None) -> None:
        """Update only the status (and optionally error_message) of a downloaded file by id."""
        pass