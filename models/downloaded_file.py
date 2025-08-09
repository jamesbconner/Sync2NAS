"""
DownloadedFile model for Sync2NAS, representing downloaded file metadata and database serialization logic.
"""
import os
import datetime
import hashlib
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, field_validator
from enum import Enum

logger = logging.getLogger(__name__)

class FileStatus(str, Enum):
    """Status of a downloaded file in the system."""
    DOWNLOADED = "downloaded"
    ROUTED = "routed"
    PROCESSING = "processing"
    ERROR = "error"
    DELETED = "deleted"

class FileType(str, Enum):
    """Type of file based on extension and content."""
    VIDEO = "video"
    AUDIO = "audio"
    SUBTITLE = "subtitle"
    NFO = "nfo"
    IMAGE = "image"
    ARCHIVE = "archive"
    UNKNOWN = "unknown"

class DownloadedFile(BaseModel):
    """
    Represents a downloaded file with metadata and processing state.

    Attributes:
        id (Optional[int]): Database ID (auto-generated).
        name (str): Filename.
        remote_path (str): Remote/original path where file was downloaded.
        current_path (Optional[str]): Current path after routing (if moved).
        size (int): File size in bytes.
        modified_time (datetime.datetime): Last modification time.
        fetched_at (datetime.datetime): When file was first discovered.
        is_dir (bool): Whether this is a directory.
        status (FileStatus): Current processing status.
        file_type (FileType): Type of file based on extension.
        file_hash (Optional[str]): SHA256 hash of file content.
        show_name (Optional[str]): Extracted show name from filename.
        season (Optional[int]): Extracted season number.
        episode (Optional[int]): Extracted episode number.
        confidence (Optional[float]): Confidence score for parsing (0.0-1.0).
        reasoning (Optional[str]): Reasoning for parsing decisions.
        tmdb_id (Optional[int]): Associated TMDB show ID.
        routing_attempts (int): Number of routing attempts.
        last_routing_attempt (Optional[datetime.datetime]): Last routing attempt timestamp.
        error_message (Optional[str]): Error message if processing failed.
        metadata (Optional[Dict[str, Any]]): Additional metadata (JSON-encoded).
    """
    
    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        extra='forbid'
    )
    
    # Database fields
    id: Optional[int] = Field(None, description="Database ID (auto-generated)")
    
    # File metadata
    name: str = Field(..., description="Filename")
    remote_path: str = Field(..., description="Remote/original path where file was downloaded")
    current_path: Optional[str] = Field(None, description="Current path after routing (if moved)")
    previous_path: Optional[str] = Field(None, description="Previous path before last routing move")
    size: int = Field(..., ge=0, description="File size in bytes")
    modified_time: datetime.datetime = Field(..., description="Last modification time")
    fetched_at: datetime.datetime = Field(default_factory=datetime.datetime.now, description="When file was first discovered")
    is_dir: bool = Field(False, description="Whether this is a directory")
    
    # Processing state
    status: FileStatus = Field(FileStatus.DOWNLOADED, description="Current processing status")
    
    # Content identification
    file_hash: Optional[str] = Field(None, description="CRC32 hash of file content (default)")
    
    def __init__(self, **data):
        # Backward compatibility: accept 'original_path' as input
        if 'original_path' in data and 'remote_path' not in data:
            data['remote_path'] = data.pop('original_path')
        super().__init__(**data)
        # Initialize hash cache as a private attribute
        self._hash_cache = {}

    # Backward compatibility for code/tests still using original_path
    @property
    def original_path(self) -> str:
        return self.remote_path

    @original_path.setter
    def original_path(self, value: str) -> None:
        self.remote_path = value
    
    @property
    def file_type(self) -> FileType:
        """Get file type based on filename extension."""
        if not self.name:
            return FileType.UNKNOWN
        
        ext = Path(self.name).suffix.lower()
        
        # Video files
        if ext in {'.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.ts', '.mts', '.m2ts'}:
            return FileType.VIDEO
        
        # Audio files
        if ext in {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'}:
            return FileType.AUDIO
        
        # Subtitle files
        if ext in {'.srt', '.ass', '.ssa', '.sub', '.vtt', '.idx', '.sub'}:
            return FileType.SUBTITLE
        
        # NFO files
        if ext == '.nfo':
            return FileType.NFO
        
        # Image files
        if ext in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}:
            return FileType.IMAGE
        
        # Archive files
        if ext in {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'}:
            return FileType.ARCHIVE
        
        return FileType.UNKNOWN
    
    # Parsed metadata
    show_name: Optional[str] = Field(None, description="Extracted show name from filename")
    season: Optional[int] = Field(None, ge=0, description="Extracted season number")
    episode: Optional[int] = Field(None, ge=0, description="Extracted episode number")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score for parsing (0.0-1.0)")
    reasoning: Optional[str] = Field(None, description="Reasoning for parsing decisions")
    
    # Show association
    tmdb_id: Optional[int] = Field(None, gt=0, description="Associated TMDB show ID")
    
    # Processing tracking
    routing_attempts: int = Field(0, ge=0, description="Number of routing attempts")
    last_routing_attempt: Optional[datetime.datetime] = Field(None, description="Last routing attempt timestamp")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")
    
    # Additional metadata
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata (JSON-encoded)")



    @field_validator('current_path')
    @classmethod
    def validate_paths(cls, v, info):
        """Ensure current_path is different from remote_path if set."""
        if v and info.data and 'remote_path' in info.data and v == info.data['remote_path']:
            raise ValueError("current_path should be different from original_path when set")
        return v

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Ensure name is not empty."""
        if not v or not v.strip():
            raise ValueError("name cannot be empty")
        return v

    def to_db_tuple(self) -> tuple:
        """
        Serialize the DownloadedFile object as a tuple for database insertion.
        Only includes core database fields, not processing state fields.

        Returns:
            tuple: Values for DB insertion.
        """
        # Maintain stable tuple shape expected by tests (20 fields)
        # Insert file_type before show_name and append routing fields and metadata JSON at the end
        import json as _json
        return (
            self.name,  # 0
            self.remote_path,  # 1
            self.current_path,  # 2
            self.size,  # 3
            self.modified_time,  # 4
            self.fetched_at,  # 5
            self.is_dir,  # 6
            self.status.value,  # 7
            self.file_hash,  # 8
            self.file_type.value,  # 9 (inserted to align indices)
            self.show_name,  # 10
            self.season,  # 11
            self.episode,  # 12
            self.confidence,  # 13
            self.reasoning,  # 14
            self.tmdb_id,  # 15
            self.routing_attempts,  # 16
            self.last_routing_attempt,  # 17
            self.error_message,  # 18
            _json.dumps(self.metadata) if self.metadata is not None else None  # 19
        )

    @classmethod
    def from_db_record(cls, record: dict) -> "DownloadedFile":
        """
        Construct a DownloadedFile object from a database record.
        Only loads core database fields, processing state fields are initialized to defaults.

        Args:
            record (dict): Database record for the downloaded file.

        Returns:
            DownloadedFile: Instantiated DownloadedFile object.
        """
        import json as _json
        # Parse metadata if provided as JSON string
        raw_metadata = record.get("metadata")
        parsed_metadata = None
        if isinstance(raw_metadata, dict):
            parsed_metadata = raw_metadata
        elif isinstance(raw_metadata, str):
            try:
                parsed_metadata = _json.loads(raw_metadata)
            except Exception:
                logger.warning("Invalid metadata JSON in DB record; setting metadata=None")
                parsed_metadata = None

        return cls(
            id=record.get("id"),
            name=record["name"],
            remote_path=record.get("remote_path") or record.get("original_path"),
            current_path=record.get("current_path"),
            size=record["size"],
            modified_time=record["modified_time"],
            fetched_at=record["fetched_at"],
            is_dir=record["is_dir"],
            status=FileStatus(record.get("status", "downloaded")),
            file_hash=record.get("file_hash"),
            show_name=record.get("show_name"),
            season=record.get("season"),
            episode=record.get("episode"),
            confidence=record.get("confidence"),
            reasoning=record.get("reasoning"),
            tmdb_id=record.get("tmdb_id"),
            metadata=parsed_metadata
            # Processing state fields (routing_attempts, last_routing_attempt, error_message, metadata) 
            # are initialized to defaults and managed in memory during processing
        )

    @classmethod
    def from_sftp_entry(cls, entry: Dict[str, Any], base_path: str) -> "DownloadedFile":
        """
        Construct a DownloadedFile object from an SFTP listing entry.

        Args:
            entry (Dict[str, Any]): SFTP entry with file metadata.
            base_path (str): Base path where file was downloaded.

        Returns:
            DownloadedFile: Instantiated DownloadedFile object.
        """
        # Determine the remote path from entry (preferred key: remote_path; fallback: path)
        remote_path_value = entry.get("remote_path") or entry.get("path")
        if not remote_path_value:
            raise ValueError("from_sftp_entry requires 'remote_path' or 'path' in entry")
        # Determine local download destination if provided by caller; otherwise infer from base_path
        local_current_path = entry.get("local_path") or str(Path(base_path) / str(remote_path_value))

        return cls(
            name=entry["name"],
            remote_path=str(remote_path_value) if remote_path_value is not None else None,
            current_path=str(local_current_path) if local_current_path is not None else None,
            size=entry["size"],
            modified_time=entry["modified_time"],
            fetched_at=entry["fetched_at"],
            is_dir=entry["is_dir"],
        )

    def calculate_hash(self, hash_type: str = "crc32") -> Optional[str]:
        """
        Calculate hash of the file content using the specified hash type.
        Returns cached value if available, otherwise computes and caches the hash.
        
        Args:
            hash_type (str): Type of hash to calculate. Options: "crc32", "sha256", "sha1", "md5".
                           Defaults to "crc32".
        
        Returns:
            Optional[str]: Hash value or None if file doesn't exist or hash type is invalid.
        """
        hash_type = hash_type.lower()
        
        if hash_type == "crc32":
            return self.calculate_crc32()
        elif hash_type == "sha256":
            return self.calculate_sha256()
        elif hash_type == "sha1":
            return self.calculate_sha1()
        elif hash_type == "md5":
            return self.calculate_md5()
        else:
            logger.warning(f"Unknown hash type: {hash_type}")
            return None

    def calculate_crc32(self) -> Optional[str]:
        """
        Calculate CRC32 hash of the file content.
        Returns cached value if available, otherwise computes and caches the hash.
        
        Returns:
            Optional[str]: CRC32 hash or None if file doesn't exist.
        """
        try:
            file_path = self.current_path or self.remote_path
            if not os.path.exists(file_path):
                # Clear cache for this hash type if file doesn't exist
                if "crc32" in self._hash_cache:
                    del self._hash_cache["crc32"]
                return None
            
            # Return cached value if available
            if "crc32" in self._hash_cache:
                return self._hash_cache["crc32"]
            
            import zlib
            crc = 0
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(1048576), b""):
                    crc = zlib.crc32(chunk, crc)
            
            # Cache the computed hash
            self._hash_cache["crc32"] = f"{crc & 0xFFFFFFFF:08X}"  # Return as 8-character uppercase hex string
            return self._hash_cache["crc32"]
        except Exception as e:
            logger.warning(f"Failed to calculate CRC32 hash for {file_path}: {e}")
            return None

    def calculate_sha256(self) -> Optional[str]:
        """
        Calculate SHA256 hash of the file content.
        Returns cached value if available, otherwise computes and caches the hash.
        
        Returns:
            Optional[str]: SHA256 hash or None if file doesn't exist.
        """
        try:
            file_path = self.current_path or self.remote_path
            if not os.path.exists(file_path):
                # Clear cache for this hash type if file doesn't exist
                if "sha256" in self._hash_cache:
                    del self._hash_cache["sha256"]
                return None
            
            # Return cached value if available
            if "sha256" in self._hash_cache:
                return self._hash_cache["sha256"]
            
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(1048576), b""):
                    hash_sha256.update(chunk)
            
            # Cache the computed hash
            self._hash_cache["sha256"] = hash_sha256.hexdigest()
            return self._hash_cache["sha256"]
        except Exception as e:
            logger.warning(f"Failed to calculate SHA256 hash for {file_path}: {e}")
            return None

    def calculate_sha1(self) -> Optional[str]:
        """
        Calculate SHA1 hash of the file content.
        Returns cached value if available, otherwise computes and caches the hash.
        
        Returns:
            Optional[str]: SHA1 hash or None if file doesn't exist.
        """
        try:
            file_path = self.current_path or self.remote_path
            if not os.path.exists(file_path):
                # Clear cache for this hash type if file doesn't exist
                if "sha1" in self._hash_cache:
                    del self._hash_cache["sha1"]
                return None
            
            # Return cached value if available
            if "sha1" in self._hash_cache:
                return self._hash_cache["sha1"]
            
            hash_sha1 = hashlib.sha1()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(1048576), b""):
                    hash_sha1.update(chunk)
            
            # Cache the computed hash
            self._hash_cache["sha1"] = hash_sha1.hexdigest()
            return self._hash_cache["sha1"]
        except Exception as e:
            logger.warning(f"Failed to calculate SHA1 hash for {file_path}: {e}")
            return None

    def calculate_md5(self) -> Optional[str]:
        """
        Calculate MD5 hash of the file content.
        Returns cached value if available, otherwise computes and caches the hash.
        
        Returns:
            Optional[str]: MD5 hash or None if file doesn't exist.
        """
        try:
            file_path = self.current_path or self.remote_path
            if not os.path.exists(file_path):
                # Clear cache for this hash type if file doesn't exist
                if "md5" in self._hash_cache:
                    del self._hash_cache["md5"]
                return None
            
            # Return cached value if available
            if "md5" in self._hash_cache:
                return self._hash_cache["md5"]
            
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(1048576), b""):
                    hash_md5.update(chunk)
            
            # Cache the computed hash
            self._hash_cache["md5"] = hash_md5.hexdigest()
            return self._hash_cache["md5"]
        except Exception as e:
            logger.warning(f"Failed to calculate MD5 hash for {file_path}: {e}")
            return None

    def update_hash(self, hash_type: str = "crc32") -> bool:
        """
        Update the file hash if the file exists.
        
        Args:
            hash_type (str): Type of hash to calculate. Defaults to "crc32".
        
        Returns:
            bool: True if hash was updated successfully.
        """
        new_hash = self.calculate_hash(hash_type)
        if new_hash:
            self.file_hash = new_hash
            return True
        return False

    def clear_hash_cache(self) -> None:
        """
        Clear all cached hash values.
        Useful when the file content may have changed.
        """
        self._hash_cache.clear()

    def clear_hash_cache_for_type(self, hash_type: str) -> None:
        """
        Clear cached hash value for a specific hash type.
        
        Args:
            hash_type (str): Type of hash to clear cache for.
        """
        hash_type = hash_type.lower()
        if hash_type in self._hash_cache:
            del self._hash_cache[hash_type]
        else:
            logger.warning(f"Unknown hash type for cache clearing: {hash_type}")

    def get_file_path(self) -> str:
        """
        Get the current file path (current_path if set, otherwise remote_path).
        
        Returns:
            str: Current file path.
        """
        return self.current_path or self.remote_path

    def exists(self) -> bool:
        """
        Check if the file exists on disk.
        
        Returns:
            bool: True if file exists.
        """
        return os.path.exists(self.get_file_path())

    def get_file_size(self) -> Optional[int]:
        """
        Get the current file size on disk.
        
        Returns:
            Optional[int]: File size in bytes or None if file doesn't exist.
        """
        try:
            return os.path.getsize(self.get_file_path())
        except OSError:
            return None

    def is_media_file(self) -> bool:
        """
        Check if this is a media file (video, audio, subtitle).
        
        Returns:
            bool: True if file is media.
        """
        return self.file_type in {FileType.VIDEO, FileType.AUDIO, FileType.SUBTITLE}

    def is_video_file(self) -> bool:
        """
        Check if this is a video file.
        
        Returns:
            bool: True if file is video.
        """
        return self.file_type == FileType.VIDEO

    def can_be_routed(self) -> bool:
        """
        Check if this file can be routed (is a media file and has been downloaded).
        
        Returns:
            bool: True if file can be routed.
        """
        return (
            self.is_media_file() and 
            self.status == FileStatus.DOWNLOADED
        )

    def mark_as_processing(self) -> None:
        """Mark the file as being processed."""
        self.status = FileStatus.PROCESSING
        self.last_routing_attempt = datetime.datetime.now()
        self.routing_attempts += 1

    def mark_as_routed(self, new_path: str) -> None:
        """
        Mark the file as successfully routed.
        
        Args:
            new_path (str): New path where file was moved.
        """
        self.status = FileStatus.ROUTED
        self.current_path = new_path
        self.last_routing_attempt = datetime.datetime.now()

    def mark_as_error(self, error_message: str) -> None:
        """
        Mark the file as having an error.
        
        Args:
            error_message (str): Error message describing the issue.
        """
        self.status = FileStatus.ERROR
        self.error_message = error_message
        self.last_routing_attempt = datetime.datetime.now()

    def reset_status(self) -> None:
        """Reset the file status to downloaded."""
        self.status = FileStatus.DOWNLOADED
        self.error_message = None

    def to_processing_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary including processing state for temporary storage.
        Used for in-memory processing state management.
        
        Returns:
            Dict[str, Any]: Dictionary including processing state fields.
        """
        return {
            "id": self.id,
            "name": self.name,
            "original_path": self.remote_path,
            "current_path": self.current_path,
            "size": self.size,
            "modified_time": self.modified_time.isoformat() if self.modified_time else None,
            "fetched_at": self.fetched_at.isoformat() if self.fetched_at else None,
            "is_dir": self.is_dir,
            "status": self.status.value,
            "file_type": self.file_type.value,
            "file_hash": self.file_hash,
            "show_name": self.show_name,
            "season": self.season,
            "episode": self.episode,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "tmdb_id": self.tmdb_id,
            "routing_attempts": self.routing_attempts,
            "last_routing_attempt": self.last_routing_attempt.isoformat() if self.last_routing_attempt else None,
            "error_message": self.error_message,
            "metadata": self.metadata
        }

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the file.
        """
        return {
            "id": self.id,
            "name": self.name,
            "original_path": self.remote_path,
            "current_path": self.current_path,
            "size": self.size,
            "modified_time": self.modified_time.isoformat() if self.modified_time else None,
            "fetched_at": self.fetched_at.isoformat() if self.fetched_at else None,
            "is_dir": self.is_dir,
            "status": self.status.value,
            "file_type": self.file_type.value,
            "file_hash": self.file_hash,
            "show_name": self.show_name,
            "season": self.season,
            "episode": self.episode,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "tmdb_id": self.tmdb_id,
            "routing_attempts": self.routing_attempts,
            "last_routing_attempt": self.last_routing_attempt.isoformat() if self.last_routing_attempt else None,
            "error_message": self.error_message,
            "metadata": self.metadata
        } 