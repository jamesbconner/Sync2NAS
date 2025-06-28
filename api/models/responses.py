from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class ShowResponse(BaseModel):
    id: int
    tmdb_id: int
    tmdb_name: str
    sys_name: str
    sys_path: str
    aliases: Optional[str] = None
    
    class Config:
        from_attributes = True


class EpisodeResponse(BaseModel):
    id: int
    show_id: int
    season: int
    episode: int
    title: str
    air_date: Optional[str] = None
    overview: Optional[str] = None
    
    class Config:
        from_attributes = True


class AddShowResponse(BaseModel):
    success: bool
    tmdb_name: str
    sys_path: str
    episode_count: int
    message: str


class UpdateEpisodesResponse(BaseModel):
    success: bool
    episodes_updated: int
    show_name: str
    message: str


class RouteFileResponse(BaseModel):
    original_path: str
    routed_path: str
    show_name: str
    season: str
    episode: str


class RouteFilesResponse(BaseModel):
    success: bool
    files_routed: int
    files: List[RouteFileResponse]
    message: str


class ListIncomingResponse(BaseModel):
    success: bool
    files: List[Dict[str, Any]]
    count: int
    incoming_path: str


class RemoteFileResponse(BaseModel):
    name: str
    size: Optional[int] = None
    modified_time: Optional[str] = None
    fetched_at: Optional[str] = None


class ListRemoteResponse(BaseModel):
    success: bool
    files: List[RemoteFileResponse]
    count: int
    path: str


class DownloadResponse(BaseModel):
    success: bool
    files_downloaded: int
    message: str


class ConnectionStatusResponse(BaseModel):
    success: bool
    status: str
    host: str
    port: int
    error: Optional[str] = None


class BootstrapResponse(BaseModel):
    success: bool
    added: int
    skipped: int
    failed: int
    duration: float
    message: str


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    status_code: int


class HealthResponse(BaseModel):
    status: str
    services: List[str] 