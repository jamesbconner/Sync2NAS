from pydantic import BaseModel, Field
from typing import Optional


class AddShowRequest(BaseModel):
    show_name: Optional[str] = Field(None, description="Name of the show to add")
    tmdb_id: Optional[int] = Field(None, description="TMDB ID of the show")
    override_dir: bool = Field(False, description="Use show_name directly for folder name")
    
    class Config:
        json_schema_extra = {
            "example": {
                "show_name": "Breaking Bad",
                "tmdb_id": 1396,
                "override_dir": False
            }
        }


class UpdateEpisodesRequest(BaseModel):
    show_name: Optional[str] = Field(None, description="Name of the show")
    tmdb_id: Optional[int] = Field(None, description="TMDB ID of the show")
    
    class Config:
        json_schema_extra = {
            "example": {
                "show_name": "Breaking Bad"
            }
        }


class RouteFilesRequest(BaseModel):
    dry_run: bool = Field(False, description="Simulate without moving files")
    auto_add: bool = Field(False, description="Auto-add missing shows")
    
    class Config:
        json_schema_extra = {
            "example": {
                "dry_run": True,
                "auto_add": True
            }
        }


class DownloadFromRemoteRequest(BaseModel):
    dry_run: bool = Field(False, description="Simulate without downloading")
    
    class Config:
        json_schema_extra = {
            "example": {
                "dry_run": True
            }
        }


class ListRemoteRequest(BaseModel):
    path: Optional[str] = Field(None, description="Path to list")
    recursive: bool = Field(False, description="List recursively")
    populate_sftp_temp: bool = Field(False, description="Populate sftp_temp table")
    dry_run: bool = Field(False, description="Simulate without listing")
    
    class Config:
        json_schema_extra = {
            "example": {
                "path": "/tv",
                "recursive": True,
                "populate_sftp_temp": False,
                "dry_run": False
            }
        }


class BootstrapShowsRequest(BaseModel):
    dry_run: bool = Field(False, description="Simulate without writing to DB")
    
    class Config:
        json_schema_extra = {
            "example": {
                "dry_run": True
            }
        }


class BootstrapEpisodesRequest(BaseModel):
    dry_run: bool = Field(False, description="Simulate without writing to DB")
    
    class Config:
        json_schema_extra = {
            "example": {
                "dry_run": True
            }
        }


class LLMParseFilenameRequest(BaseModel):
    filename: str = Field(..., description="Filename to parse using LLM")
    llm_confidence_threshold: float = Field(0.7, description="Minimum confidence to accept LLM result")

    class Config:
        json_schema_extra = {
            "example": {
                "filename": "Breaking.Bad.S01E01.1080p.mkv",
                "llm_confidence_threshold": 0.7
            }
        } 