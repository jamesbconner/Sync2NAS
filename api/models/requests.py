from pydantic import BaseModel, Field
from typing import Optional


class AddShowRequest(BaseModel):
    """
    Request model for adding a new show.

    Fields:
        show_name (Optional[str]): Name of the show to add.
        tmdb_id (Optional[int]): TMDB ID of the show.
        override_dir (bool): Use show_name directly for folder name.
    """
    show_name: Optional[str] = Field(None, description="Name of the show to add")
    tmdb_id: Optional[int] = Field(None, description="TMDB ID of the show")
    override_dir: bool = Field(False, description="Use show_name directly for folder name")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "show_name": "Breaking Bad",
                "tmdb_id": 1396,
                "override_dir": False
            }
        }
    }


class UpdateEpisodesRequest(BaseModel):
    """
    Request model for updating episodes for a show.

    Fields:
        show_name (Optional[str]): Name of the show.
        tmdb_id (Optional[int]): TMDB ID of the show.
    """
    show_name: Optional[str] = Field(None, description="Name of the show")
    tmdb_id: Optional[int] = Field(None, description="TMDB ID of the show")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "show_name": "Breaking Bad"
            }
        }
    }


class RouteFilesRequest(BaseModel):
    """
    Request model for routing files from incoming directory.

    Fields:
        dry_run (bool): Simulate without moving files.
        auto_add (bool): Auto-add missing shows.
    """
    dry_run: bool = Field(False, description="Simulate without moving files")
    auto_add: bool = Field(False, description="Auto-add missing shows")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "dry_run": True,
                "auto_add": True
            }
        }
    }


class DownloadFromRemoteRequest(BaseModel):
    """
    Request model for downloading files from remote SFTP server.

    Fields:
        dry_run (bool): Simulate without downloading.
    """
    dry_run: bool = Field(False, description="Simulate without downloading")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "dry_run": True
            }
        }
    }


class ListRemoteRequest(BaseModel):
    """
    Request model for listing files on remote SFTP server.

    Fields:
        path (Optional[str]): Path to list.
        recursive (bool): List recursively.
        populate_sftp_temp (bool): Populate sftp_temp table.
        dry_run (bool): Simulate without listing.
    """
    path: Optional[str] = Field(None, description="Path to list")
    recursive: bool = Field(False, description="List recursively")
    populate_sftp_temp: bool = Field(False, description="Populate sftp_temp table")
    dry_run: bool = Field(False, description="Simulate without listing")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "path": "/tv",
                "recursive": True,
                "populate_sftp_temp": False,
                "dry_run": False
            }
        }
    }


class BootstrapShowsRequest(BaseModel):
    """
    Request model for bootstrapping TV shows from the anime_tv_path directory.

    Fields:
        dry_run (bool): Simulate without writing to DB.
    """
    dry_run: bool = Field(False, description="Simulate without writing to DB")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "dry_run": True
            }
        }
    }


class BootstrapEpisodesRequest(BaseModel):
    """
    Request model for bootstrapping episodes for all shows in the database.

    Fields:
        dry_run (bool): Simulate without writing to DB.
    """
    dry_run: bool = Field(False, description="Simulate without writing to DB")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "dry_run": True
            }
        }
    }


class LLMParseFilenameRequest(BaseModel):
    """
    Request model for parsing a filename using LLM.

    Fields:
        filename (str): Filename to parse using LLM.
        llm_confidence_threshold (float): Minimum confidence to accept LLM result.
    """
    filename: str = Field(..., description="Filename to parse using LLM")
    llm_confidence_threshold: float = Field(0.7, description="Minimum confidence to accept LLM result")

    model_config = {
        "json_schema_extra": {
            "example": {
                "filename": "Breaking.Bad.S01E01.1080p.mkv",
                "llm_confidence_threshold": 0.7
            }
        }
    }


class UpdateDownloadedFileStatusRequest(BaseModel):
    """Request model to update downloaded file status and optional error message."""
    status: str = Field(..., description="New status (downloaded, processing, routed, error, deleted)")
    error_message: Optional[str] = Field(None, description="Optional error message")