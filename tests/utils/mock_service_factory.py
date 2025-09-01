"""
Mock Service Factory for Sync2NAS Tests

This module provides a centralized factory for creating mock service instances
that provide predictable test behavior without external dependencies.

The factory creates mock services that implement all required abstract methods
and provide consistent, testable responses for various scenarios.
"""

import datetime
import configparser
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
from unittest.mock import Mock, MagicMock

from services.db_implementations.db_interface import DatabaseInterface
from services.llm_implementations.llm_interface import LLMInterface
from services.sftp_service import SFTPService
from services.tmdb_service import TMDBService
from models.show import Show
from models.episode import Episode
from models.downloaded_file import DownloadedFile, FileStatus
from utils.sync2nas_config import get_config_value


class MockDatabaseService(DatabaseInterface):
    """Mock database service that implements all abstract methods with predictable behavior."""
    
    def __init__(self, read_only: bool = False):
        self.read_only = read_only
        self._shows: Dict[int, Dict[str, Any]] = {}
        self._episodes: Dict[int, List[Dict[str, Any]]] = {}
        self._inventory_files: List[Dict[str, Any]] = []
        self._downloaded_files: List[Dict[str, Any]] = []
        self._downloaded_file_objects: List[DownloadedFile] = []
        self._next_id = 1
    
    def initialize(self) -> None:
        """Initialize mock database - no-op for mock."""
        pass
    
    def add_show(self, show: Any) -> None:
        """Add a show to the mock database."""
        if hasattr(show, 'to_db_tuple'):
            # Handle Show object
            show_data = show.to_db_tuple()
            show_dict = {
                "id": self._next_id,
                "sys_name": show_data[0],
                "sys_path": show_data[1],
                "tmdb_name": show_data[2],
                "tmdb_aliases": show_data[3],
                "tmdb_id": show_data[4],
                "tmdb_first_aired": show_data[5],
                "tmdb_last_aired": show_data[6],
                "tmdb_year": show_data[7],
                "tmdb_overview": show_data[8],
                "tmdb_season_count": show_data[9],
                "tmdb_episode_count": show_data[10],
                "tmdb_episode_groups": show_data[11],
                "tmdb_episodes_fetched_at": show_data[12],
                "tmdb_status": show_data[13],
                "tmdb_external_ids": show_data[14],
                "fetched_at": show_data[15] if len(show_data) > 15 else datetime.datetime.now()
            }
            self._shows[show_dict["tmdb_id"]] = show_dict
            self._next_id += 1
        else:
            # Handle dict-like object
            show_dict = {
                "id": self._next_id,
                "sys_name": getattr(show, 'sys_name', 'MockShow'),
                "sys_path": getattr(show, 'sys_path', '/mock/path'),
                "tmdb_name": getattr(show, 'tmdb_name', 'Mock Show'),
                "tmdb_aliases": getattr(show, 'tmdb_aliases', ''),
                "tmdb_id": getattr(show, 'tmdb_id', self._next_id),
                "tmdb_first_aired": getattr(show, 'tmdb_first_aired', None),
                "tmdb_last_aired": getattr(show, 'tmdb_last_aired', None),
                "tmdb_year": getattr(show, 'tmdb_year', 2020),
                "tmdb_overview": getattr(show, 'tmdb_overview', 'Mock overview'),
                "tmdb_season_count": getattr(show, 'tmdb_season_count', 1),
                "tmdb_episode_count": getattr(show, 'tmdb_episode_count', 10),
                "tmdb_episode_groups": getattr(show, 'tmdb_episode_groups', '[]'),
                "tmdb_episodes_fetched_at": getattr(show, 'tmdb_episodes_fetched_at', None),
                "tmdb_status": getattr(show, 'tmdb_status', 'Ended'),
                "tmdb_external_ids": getattr(show, 'tmdb_external_ids', '{}'),
                "fetched_at": getattr(show, 'fetched_at', datetime.datetime.now())
            }
            self._shows[show_dict["tmdb_id"]] = show_dict
            self._next_id += 1
    
    def add_episode(self, episode: Any) -> None:
        """Add an episode to the mock database."""
        if hasattr(episode, 'to_db_tuple'):
            episode_data = episode.to_db_tuple()
            episode_dict = {
                "tmdb_id": episode_data[0],
                "season": episode_data[1],
                "episode": episode_data[2],
                "abs_episode": episode_data[3],
                "episode_type": episode_data[4],
                "episode_id": episode_data[5],
                "air_date": episode_data[6],
                "fetched_at": episode_data[7],
                "name": episode_data[8],
                "overview": episode_data[9]
            }
        else:
            episode_dict = {
                "tmdb_id": getattr(episode, 'tmdb_id', 1),
                "season": getattr(episode, 'season', 1),
                "episode": getattr(episode, 'episode', 1),
                "abs_episode": getattr(episode, 'abs_episode', 1),
                "episode_type": getattr(episode, 'episode_type', 'standard'),
                "episode_id": getattr(episode, 'episode_id', 1001),
                "air_date": getattr(episode, 'air_date', datetime.datetime.now()),
                "fetched_at": getattr(episode, 'fetched_at', datetime.datetime.now()),
                "name": getattr(episode, 'name', 'Mock Episode'),
                "overview": getattr(episode, 'overview', 'Mock episode overview')
            }
        
        tmdb_id = episode_dict["tmdb_id"]
        if tmdb_id not in self._episodes:
            self._episodes[tmdb_id] = []
        self._episodes[tmdb_id].append(episode_dict)
    
    def add_episodes(self, episodes: List[Any]) -> None:
        """Add multiple episodes to the mock database."""
        for episode in episodes:
            self.add_episode(episode)
    
    def show_exists(self, name: str) -> bool:
        """Check if a show exists based on name or aliases."""
        for show in self._shows.values():
            if (show["sys_name"].lower() == name.lower() or 
                show["tmdb_name"].lower() == name.lower()):
                return True
            # Check aliases
            aliases = show.get("tmdb_aliases", "")
            if aliases:
                alias_list = [alias.strip().lower() for alias in aliases.split(",")]
                if name.lower() in alias_list:
                    return True
        return False
    
    def get_show_by_sys_name(self, sys_name: str) -> Optional[Dict[str, Any]]:
        """Get a show by its system name."""
        for show in self._shows.values():
            if show["sys_name"] == sys_name:
                return show
        return None
    
    def get_show_by_name_or_alias(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a show by name or alias."""
        for show in self._shows.values():
            if (show["sys_name"].lower() == name.lower() or 
                show["tmdb_name"].lower() == name.lower()):
                return show
            # Check aliases
            aliases = show.get("tmdb_aliases", "")
            if aliases:
                alias_list = [alias.strip().lower() for alias in aliases.split(",")]
                if name.lower() in alias_list:
                    return show
        return None
    
    def get_show_by_tmdb_id(self, tmdb_id: int) -> Optional[dict]:
        """Fetch a show record by TMDB ID."""
        return self._shows.get(tmdb_id)
    
    def get_all_shows(self) -> List[Dict[str, Any]]:
        """Get all shows from the database."""
        return list(self._shows.values())
    
    def episodes_exist(self, tmdb_id: int) -> bool:
        """Check if episodes exist for the given show ID."""
        return tmdb_id in self._episodes and len(self._episodes[tmdb_id]) > 0
    
    def get_episodes_by_tmdb_id(self, tmdb_id: int) -> List[Dict[str, Any]]:
        """Get all episodes for a show by its TMDB ID."""
        return self._episodes.get(tmdb_id, [])
    
    def get_inventory_files(self) -> List[Dict[str, Any]]:
        """Get all inventory files."""
        return self._inventory_files.copy()
    
    def get_downloaded_files(self) -> List[Dict[str, Any]]:
        """Get all downloaded files."""
        return self._downloaded_files.copy()
    
    def add_downloaded_files(self, files: List[Dict[str, Any]]) -> None:
        """Add multiple downloaded files to the database."""
        for file_data in files:
            # Convert to expected format
            downloaded_file = {
                "name": file_data.get("name", "unknown"),
                "remote_path": file_data.get("path", file_data.get("remote_path", "/unknown")),
                "size": file_data.get("size", 0),
                "modified_time": file_data.get("modified_time", datetime.datetime.now()),
                "is_dir": file_data.get("is_dir", False),
                "fetched_at": file_data.get("fetched_at", datetime.datetime.now()),
                "local_path": file_data.get("local_path", None)
            }
            self._downloaded_files.append(downloaded_file)
    
    def get_sftp_diffs(self) -> List[Dict[str, Any]]:
        """Get differences between SFTP and downloaded files."""
        # Mock implementation returns empty list by default
        return []
    
    def backup_database(self) -> str:
        """Backup the database."""
        return "/mock/backup/path.db"
    
    def get_show_by_id(self, show_id: int) -> Optional[Dict[str, Any]]:
        """Get a show by its database ID."""
        for show in self._shows.values():
            if show["id"] == show_id:
                return show
        return None
    
    def update_show_aliases(self, show_id: int, new_aliases: str) -> None:
        """Update the aliases for a show by its database ID."""
        for show in self._shows.values():
            if show["id"] == show_id:
                show["tmdb_aliases"] = new_aliases
                break
    
    def is_read_only(self) -> bool:
        """Check if database is in read-only mode."""
        return self.read_only
    
    def upsert_downloaded_file(self, file: DownloadedFile) -> DownloadedFile:
        """Insert/update a DownloadedFile keyed by remote_path."""
        # Find existing file by remote_path
        for i, existing_file in enumerate(self._downloaded_file_objects):
            if existing_file.original_path == file.original_path:
                # Update existing
                self._downloaded_file_objects[i] = file
                return file
        
        # Insert new
        if not file.id:
            file.id = self._next_id
            self._next_id += 1
        self._downloaded_file_objects.append(file)
        return file
    
    def set_downloaded_file_hash(self, file_id: int, algo: str, value: str, calculated_at: Optional[datetime.datetime] = None) -> None:
        """Set hash for a downloaded file (supports CRC32 and other hash algorithms)."""
        for file_obj in self._downloaded_file_objects:
            if file_obj.id == file_id:
                if not file_obj.hashes:
                    file_obj.hashes = {}
                file_obj.hashes[algo] = value
                break
    
    def update_downloaded_file_location(self, file_id: int, new_path: str, new_status: FileStatus = FileStatus.ROUTED, routed_at: Optional[datetime.datetime] = None) -> None:
        """Update downloaded file location."""
        for file_obj in self._downloaded_file_objects:
            if file_obj.id == file_id:
                file_obj.current_path = new_path
                file_obj.status = new_status
                if routed_at:
                    file_obj.routed_at = routed_at
                break
    
    def update_downloaded_file_location_by_current_path(self, current_path: str, new_path: str, new_status: FileStatus = FileStatus.ROUTED, routed_at: Optional[datetime.datetime] = None) -> None:
        """Update downloaded file location by current path."""
        for file_obj in self._downloaded_file_objects:
            if file_obj.current_path == current_path:
                file_obj.current_path = new_path
                file_obj.status = new_status
                if routed_at:
                    file_obj.routed_at = routed_at
                break
    
    def mark_downloaded_file_error(self, file_id: int, message: str) -> None:
        """Mark downloaded file as error."""
        for file_obj in self._downloaded_file_objects:
            if file_obj.id == file_id:
                file_obj.status = FileStatus.ERROR
                file_obj.error_message = message
                break
    
    def get_downloaded_files_by_status(self, status: FileStatus) -> List[DownloadedFile]:
        """Get downloaded files by status."""
        return [f for f in self._downloaded_file_objects if f.status == status]
    
    def get_downloaded_file_by_remote_path(self, remote_path: str) -> Optional[DownloadedFile]:
        """Get downloaded file by remote path."""
        for file_obj in self._downloaded_file_objects:
            if file_obj.original_path == remote_path:
                return file_obj
        return None
    
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
        results = self._downloaded_file_objects.copy()
        
        # Apply filters
        if status:
            results = [f for f in results if f.status == status]
        if file_type:
            results = [f for f in results if f.file_type == file_type]
        if q:
            results = [f for f in results if q.lower() in f.name.lower()]
        if tmdb_id:
            results = [f for f in results if f.tmdb_id == tmdb_id]
        
        # Apply pagination
        total = len(results)
        start = (page - 1) * page_size
        end = start + page_size
        results = results[start:end]
        
        return results, total
    
    def get_downloaded_file_by_id(self, file_id: int) -> Optional[DownloadedFile]:
        """Fetch a single DownloadedFile by its primary key id."""
        for file_obj in self._downloaded_file_objects:
            if file_obj.id == file_id:
                return file_obj
        return None
    
    def update_downloaded_file_status(self, file_id: int, new_status: FileStatus, error_message: Optional[str] = None) -> None:
        """Update only the status (and optionally error_message) of a downloaded file by id."""
        for file_obj in self._downloaded_file_objects:
            if file_obj.id == file_id:
                file_obj.status = new_status
                if error_message:
                    file_obj.error_message = error_message
                break
    
    # Additional mock-specific methods for test setup
    def clear_sftp_temp_files(self) -> None:
        """Clear SFTP temp files (mock-specific)."""
        pass
    
    def insert_sftp_temp_files(self, files: List[Dict[str, Any]]) -> None:
        """Insert SFTP temp files (mock-specific)."""
        pass
    
    def delete_show_and_episodes(self, tmdb_id: int) -> None:
        """Delete show and episodes (mock-specific)."""
        if tmdb_id in self._shows:
            del self._shows[tmdb_id]
        if tmdb_id in self._episodes:
            del self._episodes[tmdb_id]
    
    def add_inventory_files(self, files: List[Dict[str, Any]]) -> None:
        """Add inventory files (mock-specific)."""
        self._inventory_files.extend(files)
    
    def get_episodes_by_show_name(self, show_name: str) -> List[Dict[str, Any]]:
        """Get episodes by show name (mock-specific)."""
        show = self.get_show_by_name_or_alias(show_name)
        if show:
            return self.get_episodes_by_tmdb_id(show["tmdb_id"])
        return []
    
    def get_episode_by_absolute_number(self, tmdb_id: int, abs_episode: int) -> Optional[Dict[str, Any]]:
        """Get episode by absolute number (mock-specific)."""
        episodes = self.get_episodes_by_tmdb_id(tmdb_id)
        for episode in episodes:
            if episode.get("abs_episode") == abs_episode:
                return episode
        return None


class MockLLMService(LLMInterface):
    """Mock LLM service that implements all abstract methods with predictable behavior."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, service_type: str = "ollama"):
        self.config = config or {}
        self.service_type = service_type
        self.parse_results = {}  # For customizing parse results in tests
        
        # Set model based on service type and config
        if service_type == "ollama":
            self.model = self.config.get("ollama", {}).get("model", "qwen3:14b")
        elif service_type == "openai":
            self.model = self.config.get("openai", {}).get("model", "qwen3:14b")
        elif service_type == "anthropic":
            self.model = self.config.get("anthropic", {}).get("model", "qwen3:14b")
        else:
            self.model = "qwen3:14b"
    
    def parse_filename(self, filename: str, max_tokens: int = 150) -> Dict[str, Any]:
        """Parse a filename using mock LLM logic."""
        # Check if custom result is set for this filename
        if filename in self.parse_results:
            return self.parse_results[filename]
        
        # Default mock parsing logic
        result = {
            "show_name": "Mock Show",
            "season": 1,
            "episode": 1,
            "crc32": None,
            "confidence": 0.9,
            "reasoning": "Mock LLM parsing",
            "filename": filename
        }
        
        # Try to extract some basic info from filename for more realistic behavior
        if "S" in filename and "E" in filename:
            try:
                # Look for SxxExx pattern
                import re
                match = re.search(r'S(\d+)E(\d+)', filename, re.IGNORECASE)
                if match:
                    result["season"] = int(match.group(1))
                    result["episode"] = int(match.group(2))
                    result["confidence"] = 0.95
            except:
                pass
        
        # Try to extract CRC32 from filename (8 hex chars in brackets at end)
        try:
            import re
            # Look for [8 hex chars] pattern at the end of filename for CRC32 hash
            crc32_match = re.search(r'\[([A-Fa-f0-9]{8})\]', filename)
            if crc32_match:
                result["crc32"] = crc32_match.group(1).upper()
                result["confidence"] = 0.95
        except:
            pass
        
        # Extract show name from filename
        show_part = filename.split('.')[0] if '.' in filename else filename
        show_part = show_part.replace('_', ' ').replace('-', ' ')
        if show_part:
            result["show_name"] = show_part
        
        return result
    
    def batch_parse_filenames(self, filenames: List[str], max_tokens: int = 150) -> List[Dict[str, Any]]:
        """Parse multiple filenames in batch."""
        return [self.parse_filename(filename, max_tokens) for filename in filenames]
    
    def suggest_short_dirname(self, long_name: str, max_length: int = 20) -> str:
        """Suggest a short directory name."""
        if len(long_name) <= max_length:
            return long_name
        
        # Simple truncation with ellipsis
        return long_name[:max_length-3] + "..."
    
    def suggest_short_filename(self, long_name: str, max_length: int = 20) -> str:
        """Suggest a short filename."""
        if len(long_name) <= max_length:
            return long_name
        
        # Preserve extension if present
        if '.' in long_name:
            name, ext = long_name.rsplit('.', 1)
            available_length = max_length - len(ext) - 1  # -1 for the dot
            if available_length > 3:
                return name[:available_length-3] + "..." + "." + ext
        
        return long_name[:max_length-3] + "..."
    
    def suggest_show_name(self, show_name: str, detailed_results: list) -> dict:
        """Suggest the best show match from TMDB results."""
        if not detailed_results:
            return {
                "tmdb_id": None,
                "show_name": show_name,
                "confidence": 0.1,
                "reasoning": "No TMDB results available"
            }
        
        # Return the first result as the best match
        best_match = detailed_results[0]
        return {
            "tmdb_id": best_match.get("id"),
            "show_name": best_match.get("name", show_name),
            "confidence": 0.9,
            "reasoning": "Mock LLM selected first result"
        }
    
    def set_parse_result(self, filename: str, result: Dict[str, Any]) -> None:
        """Set a custom parse result for a specific filename (test helper)."""
        self.parse_results[filename] = result


class MockSFTPService:
    """Mock SFTP service that provides predictable behavior without network dependencies."""
    
    def __init__(self, host: str, port: int, username: str, ssh_key_path: str, llm_service=None):
        self.host = host
        self.port = port
        self.username = username
        self.ssh_key_path = ssh_key_path
        self.llm_service = llm_service
        self.client = None
        self.transport = None
        
        # Mock file system
        self._remote_files = {}
        self._setup_default_files()
    
    def _setup_default_files(self):
        """Set up default mock files for testing."""
        now = datetime.datetime.now()
        self._remote_files = {
            "/remote/show1/S01E01.mkv": {
                "name": "S01E01.mkv",
                "remote_path": "/remote/show1/S01E01.mkv",
                "size": 1000000,
                "modified_time": now,
                "is_dir": False,
                "fetched_at": now
            },
            "/remote/show1/S01E02.mkv": {
                "name": "S01E02.mkv",
                "remote_path": "/remote/show1/S01E02.mkv",
                "size": 1100000,
                "modified_time": now,
                "is_dir": False,
                "fetched_at": now
            },
            "/remote/show2": {
                "name": "show2",
                "remote_path": "/remote/show2",
                "size": 0,
                "modified_time": now,
                "is_dir": True,
                "fetched_at": now
            }
        }
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
    
    def connect(self):
        """Mock connection - always succeeds."""
        return self
    
    def disconnect(self):
        """Mock disconnection."""
        pass
    
    def reconnect(self):
        """Mock reconnection."""
        return self.connect()
    
    def list_remote_dir(self, remote_path: str) -> List[Dict[str, Any]]:
        """List contents of a remote directory."""
        remote_path = remote_path.rstrip('/')
        results = []
        
        for path, file_info in self._remote_files.items():
            if path.startswith(remote_path + '/') and path != remote_path:
                # Check if this is a direct child
                relative_path = path[len(remote_path) + 1:]
                if '/' not in relative_path or file_info["is_dir"]:
                    results.append(file_info.copy())
        
        return results
    
    def list_remote_files(self, remote_path: str) -> List[Dict[str, Any]]:
        """List files in a remote directory (non-recursive)."""
        return [f for f in self.list_remote_dir(remote_path) if not f["is_dir"]]
    
    def list_remote_files_recursive(self, remote_path: str) -> List[Dict[str, Any]]:
        """List all files recursively."""
        remote_path = remote_path.rstrip('/')
        results = []
        
        for path, file_info in self._remote_files.items():
            if path.startswith(remote_path + '/') and not file_info["is_dir"]:
                results.append(file_info.copy())
        
        return results
    
    def download_file(self, remote_path: str, local_path: str, max_path_length: int = 250) -> None:
        """Mock file download."""
        # Simulate successful download
        pass
    
    def download_dir(self, remote_path: str, local_path: str, filename_map=None, max_workers: int = 4) -> List[Dict[str, Any]]:
        """Mock directory download."""
        files = self.list_remote_files_recursive(remote_path)
        # Simulate successful download by returning the file list
        for file_info in files:
            file_info["local_path"] = local_path + "/" + file_info["name"]
        return files
    
    def add_mock_file(self, remote_path: str, name: str, size: int = 1000000, is_dir: bool = False) -> None:
        """Add a mock file to the remote file system (test helper)."""
        now = datetime.datetime.now()
        self._remote_files[remote_path] = {
            "name": name,
            "remote_path": remote_path,
            "size": size,
            "modified_time": now,
            "is_dir": is_dir,
            "fetched_at": now
        }


class MockTMDBService:
    """Mock TMDB service that provides predictable behavior without API dependencies."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._shows = {}
        self._setup_default_shows()
    
    def _setup_default_shows(self):
        """Set up default mock shows for testing."""
        self._shows = {
            "mock show": {
                "results": [
                    {
                        "id": 12345,
                        "name": "Mock Show",
                        "first_air_date": "2020-01-01",
                        "overview": "A mock show for testing"
                    }
                ]
            }
        }
    
    def search_show(self, query: str) -> Dict[str, Any]:
        """Search for shows."""
        query_lower = query.lower()
        if query_lower in self._shows:
            return self._shows[query_lower]
        
        # Default response
        return {
            "results": [
                {
                    "id": 99999,
                    "name": query,
                    "first_air_date": "2020-01-01",
                    "overview": f"Mock show for query: {query}"
                }
            ]
        }
    
    def get_show_details(self, tmdb_id: int) -> Dict[str, Any]:
        """Get detailed show information."""
        return {
            "info": {
                "id": tmdb_id,
                "name": f"Mock Show {tmdb_id}",
                "first_air_date": "2020-01-01",
                "number_of_seasons": 2,
                "number_of_episodes": 20,
                "overview": f"Mock show details for ID {tmdb_id}"
            },
            "episode_groups": {"results": []},
            "alternative_titles": {"results": []},
            "external_ids": {}
        }
    
    def get_show_season_details(self, tmdb_id: int, season_number: int) -> Dict[str, Any]:
        """Get season details."""
        episodes = []
        for ep_num in range(1, 11):  # 10 episodes per season
            episodes.append({
                "episode_number": ep_num,
                "id": tmdb_id * 1000 + season_number * 100 + ep_num,
                "air_date": f"2020-{season_number:02d}-{ep_num:02d}",
                "name": f"Episode {ep_num}",
                "overview": f"Mock episode {ep_num} overview"
            })
        
        return {
            "id": tmdb_id * 100 + season_number,
            "air_date": f"2020-{season_number:02d}-01",
            "season_number": season_number,
            "episodes": episodes
        }
    
    def get_show_episode_details(self, tmdb_id: int, season: int, episode: int) -> Dict[str, Any]:
        """Get episode details."""
        return {
            "episode_number": episode,
            "id": tmdb_id * 1000 + season * 100 + episode,
            "air_date": f"2020-{season:02d}-{episode:02d}",
            "name": f"Episode {episode}",
            "overview": f"Mock episode {episode} overview",
            "season_number": season,
            "show_id": tmdb_id
        }
    
    def add_mock_show(self, query: str, show_data: Dict[str, Any]) -> None:
        """Add a mock show for testing (test helper)."""
        self._shows[query.lower()] = {"results": [show_data]}


class MockServiceFactory:
    """
    Factory class for creating mock service instances with standardized behavior.
    
    This factory provides a centralized way to create mock services that implement
    all required abstract methods and provide predictable test behavior without
    external dependencies.
    
    CRITICAL: All mock services use the SAME model as the main config (qwen3:14b)
    to prevent GPU RAM exhaustion and CPU fallback during testing.
    """
    
    # CRITICAL: Use the EXACT same model as main config to prevent GPU issues
    STANDARD_TEST_MODEL = "qwen3:14b"
    
    @staticmethod
    def create_mock_db_service(config: Dict[str, Any], read_only: bool = False) -> MockDatabaseService:
        """
        Create a mock database service.
        
        Args:
            config: Configuration dictionary (not used in mock, but kept for interface compatibility)
            read_only: Whether the database should be in read-only mode
            
        Returns:
            MockDatabaseService: Mock database service instance
        """
        return MockDatabaseService(read_only=read_only)
    
    @staticmethod
    def create_mock_llm_service(config: Dict[str, Any], service_type: str = None) -> MockLLMService:
        """
        Create a mock LLM service with all abstract methods implemented.
        
        Args:
            config: Configuration dictionary
            service_type: Optional service type override (ollama, openai, anthropic)
            
        Returns:
            MockLLMService: Mock LLM service instance
        """
        # Determine service type from config if not provided
        if service_type is None:
            service_type = config.get("llm", {}).get("service", "ollama")
        
        return MockLLMService(config, service_type)
    
    @staticmethod
    def create_mock_sftp_service(config: Dict[str, Any]) -> MockSFTPService:
        """
        Create a mock SFTP service.
        
        Args:
            config: Configuration dictionary containing SFTP settings
            
        Returns:
            MockSFTPService: Mock SFTP service instance
        """
        sftp_config = config.get("sftp", config.get("SFTP", {}))
        return MockSFTPService(
            host=sftp_config.get("host", "localhost"),
            port=int(sftp_config.get("port", 22)),
            username=sftp_config.get("username", "testuser"),
            ssh_key_path=sftp_config.get("ssh_key_path", "/tmp/test_key")
        )
    
    @staticmethod
    def create_mock_tmdb_service(config: Dict[str, Any]) -> MockTMDBService:
        """
        Create a mock TMDB service.
        
        Args:
            config: Configuration dictionary containing TMDB settings
            
        Returns:
            MockTMDBService: Mock TMDB service instance
        """
        tmdb_config = config.get("tmdb", config.get("TMDB", {}))
        return MockTMDBService(api_key=tmdb_config.get("api_key", "test_api_key"))
    
    @staticmethod
    def create_all_mock_services(config: Dict[str, Any], read_only: bool = False) -> Dict[str, Any]:
        """
        Create all mock services at once.
        
        Args:
            config: Configuration dictionary
            read_only: Whether database should be in read-only mode
            
        Returns:
            Dict containing all mock service instances
        """
        return {
            "db": MockServiceFactory.create_mock_db_service(config, read_only),
            "llm_service": MockServiceFactory.create_mock_llm_service(config),
            "sftp": MockServiceFactory.create_mock_sftp_service(config),
            "tmdb": MockServiceFactory.create_mock_tmdb_service(config)
        }
    
    @staticmethod
    def get_standard_test_config() -> Dict[str, Any]:
        """
        Get standardized test configuration that uses the SAME model as main config.
        
        CRITICAL: This ensures all tests use qwen3:14b to prevent GPU RAM issues.
        
        Returns:
            Dict containing standardized test configuration
        """
        import tempfile
        from pathlib import Path
        
        temp_dir = Path(tempfile.gettempdir()) / "test_sync2nas"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        return {
            "database": {"type": "sqlite"},
            "sqlite": {"db_file": ":memory:"},  # Use in-memory for speed
            "llm": {"service": "ollama"},
            "ollama": {
                "model": MockServiceFactory.STANDARD_TEST_MODEL,  # CRITICAL: Same as main config
                "host": "http://localhost:11434",
                "timeout": "30"
            },
            "sftp": {
                "host": "localhost",
                "port": "22",
                "username": "testuser",
                "ssh_key_path": str(temp_dir / "test_key"),
                "paths": "/remote/test"
            },
            "tmdb": {"api_key": "test_tmdb_api_key"},
            "transfers": {"incoming": str(temp_dir / "incoming")},
            "routing": {"anime_tv_path": str(temp_dir / "anime_tv")}
        }
    
    @staticmethod
    def create_mock_context_object(config: Dict[str, Any], **overrides) -> Dict[str, Any]:
        """
        Create a complete mock context object for CLI testing.
        
        Args:
            config: Configuration dictionary
            **overrides: Override specific services or config values
            
        Returns:
            Dict containing complete context object for CLI tests
        """
        services = MockServiceFactory.create_all_mock_services(config, overrides.get("dry_run", False))
        
        context = {
            "config": config,
            "db": services["db"],
            "llm_service": services["llm_service"],
            "sftp": services["sftp"],
            "tmdb": services["tmdb"],
            "anime_tv_path": config.get("routing", config.get("Routing", {})).get("anime_tv_path", "/tmp/anime"),
            "incoming_path": config.get("transfers", config.get("Transfers", {})).get("incoming", "/tmp/incoming"),
            "dry_run": False
        }
        
        # Apply any overrides
        context.update(overrides)
        
        return context
    
    @staticmethod
    def patch_llm_service_creation():
        """
        Patch LLM service creation to always use mocks in tests.
        
        CRITICAL: This prevents tests from loading real LLM models which causes
        GPU RAM exhaustion and CPU fallback.
        
        Returns:
            Context manager that patches LLM service creation
        """
        from unittest.mock import patch
        
        def mock_create_llm_service(config, validate_health=True, startup_mode=False):
            """Mock LLM service creation that always returns a mock."""
            return MockServiceFactory.create_mock_llm_service(config)
        
        return patch('services.llm_factory.create_llm_service', side_effect=mock_create_llm_service)
    
    @staticmethod
    def ensure_test_model_consistency(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure configuration uses the standard test model to prevent GPU issues.
        
        CRITICAL: This function forces all test configs to use qwen3:14b
        regardless of what model they originally specified.
        
        Args:
            config: Original configuration
            
        Returns:
            Configuration with corrected model
        """
        # Make a copy to avoid modifying original
        corrected_config = config.copy()
        
        # Force the correct model for all LLM services
        if "ollama" in corrected_config:
            if isinstance(corrected_config["ollama"], dict):
                corrected_config["ollama"] = corrected_config["ollama"].copy()
                corrected_config["ollama"]["model"] = MockServiceFactory.STANDARD_TEST_MODEL
            else:
                corrected_config["ollama"] = {"model": MockServiceFactory.STANDARD_TEST_MODEL}
        
        # Also handle uppercase versions (legacy configs)
        if "Ollama" in corrected_config:
            if isinstance(corrected_config["Ollama"], dict):
                corrected_config["Ollama"] = corrected_config["Ollama"].copy()
                corrected_config["Ollama"]["model"] = MockServiceFactory.STANDARD_TEST_MODEL
            else:
                corrected_config["Ollama"] = {"model": MockServiceFactory.STANDARD_TEST_MODEL}
        
        return corrected_config


def fix_test_model_usage():
    """
    CRITICAL FUNCTION: Fix model usage across all test files.
    
    This function can be called to automatically update test files that use
    incorrect models to use the standard test model (qwen3:14b).
    
    This prevents GPU RAM exhaustion and CPU fallback during testing.
    """
    import os
    import re
    from pathlib import Path
    
    # Models that should be replaced with the standard test model
    INCORRECT_MODELS = [
        "ollama3.2",  # Invalid model name
        "llama3.2",   # Different model
        "llama3",     # Different model
        "gpt-4",      # Different service entirely
        "claude-3-haiku",  # Different service entirely
    ]
    
    # Pattern to match model assignments in test files
    MODEL_PATTERNS = [
        (r'"model":\s*"([^"]*)"', r'"model": "qwen3:14b"'),
        (r"'model':\s*'([^']*)'", r"'model': 'qwen3:14b'"),
        (r'parser\["ollama"\]\s*=\s*\{"model":\s*"([^"]*)"', r'parser["ollama"] = {"model": "qwen3:14b"'),
        (r"parser\['ollama'\]\s*=\s*\{'model':\s*'([^']*)'", r"parser['ollama'] = {'model': 'qwen3:14b'"),
    ]
    
    test_dir = Path(__file__).parent.parent  # tests/ directory
    
    print("🔧 Scanning for incorrect model usage in test files...")
    
    files_fixed = 0
    total_replacements = 0
    
    for test_file in test_dir.rglob("*.py"):
        if test_file.name == "mock_service_factory.py":
            continue  # Skip this file
        
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            file_replacements = 0
            
            # Apply all patterns
            for pattern, replacement in MODEL_PATTERNS:
                matches = re.findall(pattern, content)
                for match in matches:
                    if match in INCORRECT_MODELS:
                        content = re.sub(pattern, replacement, content)
                        file_replacements += 1
            
            # If we made changes, write the file back
            if content != original_content:
                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                files_fixed += 1
                total_replacements += file_replacements
                print(f"✅ Fixed {file_replacements} model references in {test_file.relative_to(test_dir)}")
        
        except Exception as e:
            print(f"❌ Error processing {test_file}: {e}")
    
    print(f"\n🎉 Model fix complete!")
    print(f"📁 Files fixed: {files_fixed}")
    print(f"🔄 Total replacements: {total_replacements}")
    print(f"🎯 All tests now use: {MockServiceFactory.STANDARD_TEST_MODEL}")
    
    if files_fixed > 0:
        print("\n⚠️  IMPORTANT: Run tests to verify all changes work correctly!")
        print("⚠️  IMPORTANT: Commit these changes to prevent GPU RAM issues!")


if __name__ == "__main__":
    # Allow running this module directly to fix model usage
    fix_test_model_usage()


class TestConfigurationHelper:
    """
    Helper class for managing test configurations and fixing common issues.
    
    This class provides utilities to handle the transition from ConfigParser
    to normalized configuration dictionaries in tests.
    """
    
    @staticmethod
    def update_config_file_with_normalized_data(config_path: str, normalized_config: Dict[str, Any]) -> None:
        """
        Update a configuration file with normalized configuration data.
        
        Args:
            config_path: Path to the configuration file to update
            normalized_config: Normalized configuration dictionary
        """
        parser = configparser.ConfigParser()
        
        # Convert normalized config back to ConfigParser format
        for section_name, section_data in normalized_config.items():
            parser_section_name = section_name.title()
            parser[parser_section_name] = {}
            for key, value in section_data.items():
                parser[parser_section_name][key] = str(value)
        
        with open(config_path, 'w') as f:
            parser.write(f)
    
    @staticmethod
    def create_test_directories_from_config(config: Dict[str, Any]) -> Dict[str, Path]:
        """
        Create test directories referenced in configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Dict[str, Path]: Created directory paths keyed by purpose
        """
        created_dirs = {}
        
        # Create directories from configuration paths
        path_mappings = [
            ("transfers", "incoming", "incoming_dir"),
            ("routing", "anime_tv_path", "anime_tv_dir"),
        ]
        
        for section, key, dir_key in path_mappings:
            path_value = get_config_value(config, section, key)
            if path_value:
                dir_path = Path(path_value)
                dir_path.mkdir(parents=True, exist_ok=True)
                created_dirs[dir_key] = dir_path
        
        # Create SSH key directory if specified
        ssh_key_path = get_config_value(config, "sftp", "ssh_key_path")
        if ssh_key_path:
            ssh_key_dir = Path(ssh_key_path).parent
            ssh_key_dir.mkdir(parents=True, exist_ok=True)
            created_dirs["ssh_key_dir"] = ssh_key_dir
        
        return created_dirs
    
    @staticmethod
    def get_db_path_from_config(config: Dict[str, Any], fallback_path: Optional[str] = None) -> str:
        """
        Get database path from configuration with fallback.
        
        Args:
            config: Configuration dictionary
            fallback_path: Fallback path if not found in config
            
        Returns:
            str: Database path
        """
        return get_config_value(config, "sqlite", "db_file", fallback_path or ":memory:")
    
    @staticmethod
    def get_anime_tv_path_from_config(config: Dict[str, Any], fallback_path: Optional[str] = None) -> str:
        """
        Get anime TV path from configuration with fallback.
        
        Args:
            config: Configuration dictionary
            fallback_path: Fallback path if not found in config
            
        Returns:
            str: Anime TV path
        """
        return get_config_value(config, "routing", "anime_tv_path", fallback_path or "/tmp/anime_tv")
    
    @staticmethod
    def get_incoming_path_from_config(config: Dict[str, Any], fallback_path: Optional[str] = None) -> str:
        """
        Get incoming path from configuration with fallback.
        
        Args:
            config: Configuration dictionary
            fallback_path: Fallback path if not found in config
            
        Returns:
            str: Incoming path
        """
        return get_config_value(config, "transfers", "incoming", fallback_path or "/tmp/incoming")
    
    @staticmethod
    def get_sftp_path_from_config(config: Dict[str, Any], fallback_path: Optional[str] = None) -> str:
        """
        Get SFTP path from configuration with fallback.
        
        Args:
            config: Configuration dictionary
            fallback_path: Fallback path if not found in config
            
        Returns:
            str: SFTP path
        """
        return get_config_value(config, "sftp", "paths", fallback_path or "/remote")
    
    @staticmethod
    def create_cli_context_from_config(
        config: Dict[str, Any], 
        tmp_path: Optional[Path] = None,
        dry_run: bool = False,
        **service_overrides
    ) -> Dict[str, Any]:
        """
        Create a complete CLI context object from configuration.
        
        Args:
            config: Configuration dictionary
            tmp_path: Temporary path for test files
            dry_run: Whether this is a dry run context
            **service_overrides: Override specific services
            
        Returns:
            Dict[str, Any]: Complete CLI context object
        """
        if tmp_path is None:
            tmp_path = Path(tempfile.gettempdir()) / "test_sync2nas_cli"
            tmp_path.mkdir(parents=True, exist_ok=True)
        
        # Create test directories
        TestConfigurationHelper.create_test_directories_from_config(config)
        
        # Create services
        services = MockServiceFactory.create_all_mock_services(config, dry_run)
        
        # Override services if provided
        services.update(service_overrides)
        
        # Build context object
        context = {
            "config": config,
            "db": services["db"],
            "llm_service": services["llm_service"],
            "sftp": services["sftp"],
            "tmdb": services["tmdb"],
            "anime_tv_path": TestConfigurationHelper.get_anime_tv_path_from_config(config, str(tmp_path / "anime_tv")),
            "incoming_path": TestConfigurationHelper.get_incoming_path_from_config(config, str(tmp_path / "incoming")),
            "dry_run": dry_run
        }
        
        return context
