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
    """Initialize and return all services"""
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
    """Dependency for show service"""
    services = request.app.state.services
    return ShowService(
        services["db"],
        services["tmdb"],
        services["anime_tv_path"]
    )


def get_file_service(request: Request) -> FileService:
    """Dependency for file service"""
    services = request.app.state.services
    return FileService(
        services["db"],
        services["tmdb"],
        services["anime_tv_path"],
        services["incoming_path"]
    )


def get_remote_service(request: Request) -> RemoteService:
    """Dependency for remote service"""
    services = request.app.state.services
    return RemoteService(
        services["sftp"],
        services["db"],
        services["config"]
    )


def get_admin_service(request: Request) -> AdminService:
    """Dependency for admin service"""
    services = request.app.state.services
    return AdminService(
        services["db"],
        services["tmdb"],
        services["anime_tv_path"],
        services["config"]
    )


def get_llm_service(request: Request):
    """Dependency for LLM service"""
    services = request.app.state.services
    return services["llm_service"] 