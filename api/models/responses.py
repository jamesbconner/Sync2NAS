from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class ShowResponse(BaseModel):
    """
    Response model for a TV show.

    Fields:
        id (int): Database ID of the show.
        tmdb_id (int): TMDB ID of the show.
        tmdb_name (str): Official TMDB name.
        sys_name (str): System name used for directory.
        sys_path (str): Full system path to show directory.
        aliases (Optional[str]): Alternative names for the show.
    """
    id: int
    tmdb_id: int
    tmdb_name: str
    sys_name: str
    sys_path: str
    aliases: Optional[str] = None
    
    class Config:
        from_attributes = True


class EpisodeResponse(BaseModel):
    """
    Response model for an episode of a TV show.

    Fields:
        id (int): Database ID of the episode.
        show_id (int): Database ID of the show.
        season (int): Season number.
        episode (int): Episode number.
        title (str): Title of the episode.
        air_date (Optional[str]): Air date of the episode.
        overview (Optional[str]): Overview of the episode.
    """
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
    """
    Response model for the result of adding a show.

    Fields:
        success (bool): Whether the operation was successful.
        tmdb_name (str): Official TMDB name of the show.
        sys_path (str): System path where show was created.
        episode_count (int): Number of episodes added.
        message (str): Human-readable success message.
    """
    success: bool
    tmdb_name: str
    sys_path: str
    episode_count: int
    message: str


class UpdateEpisodesResponse(BaseModel):
    """
    Response model for the result of updating episodes for a show.

    Fields:
        success (bool): Whether the operation was successful.
        episodes_updated (int): Number of episodes updated.
        show_name (str): Name of the show updated.
        message (str): Human-readable success message.
    """
    success: bool
    episodes_updated: int
    show_name: str
    message: str


class RouteFileResponse(BaseModel):
    """
    Response model for a single routed file.

    Fields:
        original_path (str): Original file path.
        routed_path (str): Routed file path.
        show_name (str): Name of the show.
        season (Optional[int]): Season number.
        episode (Optional[int]): Episode number.
    """
    original_path: str
    routed_path: str
    show_name: str
    season: Optional[int] = None
    episode: Optional[int] = None


class RouteFilesResponse(BaseModel):
    """
    Response model for the result of routing files.

    Fields:
        success (bool): Whether the operation was successful.
        files_routed (int): Number of files routed.
        files (List[RouteFileResponse]): List of routed files.
        message (str): Human-readable success message.
    """
    success: bool
    files_routed: int
    files: List[RouteFileResponse]
    message: str


class ListIncomingResponse(BaseModel):
    """
    Response model for listing files in the incoming directory.

    Fields:
        success (bool): Whether the operation was successful.
        files (List[Dict[str, Any]]): List of files.
        count (int): Number of files.
        incoming_path (str): Path to the incoming directory.
    """
    success: bool
    files: List[Dict[str, Any]]
    count: int
    incoming_path: str


class RemoteFileResponse(BaseModel):
    """
    Response model for a file on the remote SFTP server.

    Fields:
        name (str): Name of the file.
        size (Optional[int]): Size of the file.
        modified_time (Optional[str]): Last modified time.
        fetched_at (Optional[str]): Time the file was fetched.
    """
    name: str
    size: Optional[int] = None
    modified_time: Optional[str] = None
    fetched_at: Optional[str] = None


class ListRemoteResponse(BaseModel):
    """
    Response model for listing files on the remote SFTP server.

    Fields:
        success (bool): Whether the operation was successful.
        files (List[RemoteFileResponse]): List of remote files.
        count (int): Number of files.
        path (str): Path that was listed.
    """
    success: bool
    files: List[RemoteFileResponse]
    count: int
    path: str


class DownloadResponse(BaseModel):
    """
    Response model for the result of downloading files from remote SFTP server.

    Fields:
        success (bool): Whether the operation was successful.
        files_downloaded (int): Number of files downloaded.
        message (str): Human-readable success message.
    """
    success: bool
    files_downloaded: int
    message: str


class ConnectionStatusResponse(BaseModel):
    """
    Response model for SFTP connection status.

    Fields:
        success (bool): Whether the connection is successful.
        status (str): Connection status (connected/disconnected).
        host (str): SFTP host.
        port (int): SFTP port.
        error (Optional[str]): Error message if connection failed.
    """
    success: bool
    status: str
    host: str
    port: int
    error: Optional[str] = None


class BootstrapResponse(BaseModel):
    """
    Response model for the result of a bootstrap operation.

    Fields:
        success (bool): Whether the operation was successful.
        added (int): Number of items added.
        skipped (int): Number of items skipped.
        failed (int): Number of items failed.
        duration (float): Duration of the operation.
        message (str): Human-readable success message.
    """
    success: bool
    added: int
    skipped: int
    failed: int
    duration: float
    message: str


class ErrorResponse(BaseModel):
    """
    Response model for API errors.

    Fields:
        error (str): Error message.
        detail (Optional[str]): Additional error details.
        status_code (int): HTTP status code.
    """
    error: str
    detail: Optional[str] = None
    status_code: int


class HealthResponse(BaseModel):
    """
    Response model for API health check.

    Fields:
        status (str): Overall API status.
        services (List[str]): List of service statuses.
    """
    status: str
    services: List[str]


class DeleteShowResponse(BaseModel):
    """
    Response model for the result of deleting a show.

    Fields:
        success (bool): Whether the deletion was successful.
        show_name (str): Name of the show that was deleted.
        episodes_deleted (int): Number of episodes that were deleted.
        message (str): Human-readable success message.
    """
    success: bool = Field(..., description="Whether the deletion was successful")
    show_name: str = Field(..., description="Name of the show that was deleted")
    episodes_deleted: int = Field(..., description="Number of episodes that were deleted")
    message: str = Field(..., description="Human-readable success message")


class LLMParseFilenameResponse(BaseModel):
    """
    Response model for the result of parsing a filename using LLM.

    Fields:
        show_name (str): Name of the show.
        season (int | None): Season number.
        episode (int | None): Episode number.
        confidence (float): Confidence score.
        reasoning (str): Reasoning for the result.
    """
    show_name: str
    season: int | None
    episode: int | None
    confidence: float
    reasoning: str 