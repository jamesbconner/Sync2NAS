# Dependency injection setup for Sync2NAS FastAPI application
# Provides functions to initialize and retrieve core services for API endpoints

from fastapi import Depends, Request
from services.db_factory import create_db_service
from services.sftp_service import SFTPService
from services.tmdb_service import TMDBService
from api.services.show_service import ShowService
from api.services.file_service import FileService
from api.services.remote_service import RemoteService
from api.services.admin_service import AdminService
from services.llm_factory import create_llm_service


def get_services(config):
    """
    Initialize and return all core services as a dictionary.
    This is called once at API startup and attached to app.state.services.
    """
    db = create_db_service(config)
    sftp = SFTPService(
        config["SFTP"]["host"], 
        int(config["SFTP"]["port"]), 
        config["SFTP"]["username"], 
        config["SFTP"]["ssh_key_path"]
    )
    tmdb = TMDBService(config["TMDB"]["api_key"])
    
    anime_tv_path = config["Routing"]["anime_tv_path"]
    incoming_path = config["Transfers"]["incoming"]
    llm_service = create_llm_service(config)
    
    return {
        "db": db,
        "sftp": sftp,
        "tmdb": tmdb,
        "anime_tv_path": anime_tv_path,
        "incoming_path": incoming_path,
        "config": config,
        "llm_service": llm_service
    }


def get_show_service(request: Request) -> ShowService:
    """
    Dependency for show service.
    Returns a ShowService instance for use in show-related endpoints.
    """
    services = request.app.state.services
    return ShowService(
        services["db"],
        services["tmdb"],
        services["anime_tv_path"]
    )


def get_file_service(request: Request) -> FileService:
    """
    Dependency for file service.
    Returns a FileService instance for use in file-related endpoints.
    """
    services = request.app.state.services
    return FileService(
        services["db"],
        services["tmdb"],
        services["anime_tv_path"],
        services["incoming_path"]
    )


def get_remote_service(request: Request) -> RemoteService:
    """
    Dependency for remote service.
    Returns a RemoteService instance for use in remote/SFTP-related endpoints.
    """
    services = request.app.state.services
    return RemoteService(
        services["sftp"],
        services["db"],
        services["config"]
    )


def get_admin_service(request: Request) -> AdminService:
    """
    Dependency for admin service.
    Returns an AdminService instance for use in admin-related endpoints.
    """
    services = request.app.state.services
    return AdminService(
        services["db"],
        services["tmdb"],
        services["anime_tv_path"],
        services["config"]
    )


def get_llm_service(request: Request):
    """
    Dependency for LLM service.
    Returns the LLM service instance for use in endpoints that require LLM parsing.
    """
    services = request.app.state.services
    return services["llm_service"] 