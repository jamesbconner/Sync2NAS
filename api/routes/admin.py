# API routes for admin operations (bootstrap, backup, init-db)
# Handles HTTP endpoints for administrative tasks in Sync2NAS

from fastapi import APIRouter, Depends, HTTPException

from api.models.requests import BootstrapShowsRequest, BootstrapEpisodesRequest
from api.models.responses import BootstrapResponse
from api.services.admin_service import AdminService
from api.dependencies import get_admin_service

router = APIRouter()


@router.post("/bootstrap/shows", response_model=BootstrapResponse)
async def bootstrap_tv_shows(request: BootstrapShowsRequest,
                            admin_service: AdminService = Depends(get_admin_service)):
    """
    Bootstrap TV shows from the anime_tv_path directory.
    Adds shows to the database based on folders found in the directory.
    """
    try:
        result = await admin_service.bootstrap_tv_shows(dry_run=request.dry_run)
        return result
    except Exception as e:
        # Return 500 for errors
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bootstrap/episodes", response_model=BootstrapResponse)
async def bootstrap_episodes(request: BootstrapEpisodesRequest,
                            admin_service: AdminService = Depends(get_admin_service)):
    """
    Bootstrap episodes for all shows in the database.
    Fetches episode data from TMDB and populates the database.
    """
    try:
        result = await admin_service.bootstrap_episodes(dry_run=request.dry_run)
        return result
    except Exception as e:
        # Return 500 for errors
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backup")
async def backup_database(admin_service: AdminService = Depends(get_admin_service)):
    """
    Create a backup of the database.
    """
    try:
        result = await admin_service.backup_database()
        return result
    except Exception as e:
        # Return 500 for errors
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/init-db")
async def init_database(admin_service: AdminService = Depends(get_admin_service)):
    """
    Initialize the database (create schema, tables, etc.).
    """
    try:
        result = await admin_service.init_database()
        return result
    except Exception as e:
        # Return 500 for errors
        raise HTTPException(status_code=500, detail=str(e)) 