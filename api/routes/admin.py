from fastapi import APIRouter, Depends, HTTPException

from api.models.requests import BootstrapShowsRequest, BootstrapEpisodesRequest
from api.models.responses import BootstrapResponse
from api.services.admin_service import AdminService
from api.dependencies import get_admin_service

router = APIRouter()


@router.post("/bootstrap/shows", response_model=BootstrapResponse)
async def bootstrap_tv_shows(request: BootstrapShowsRequest,
                            admin_service: AdminService = Depends(get_admin_service)):
    """Bootstrap TV shows from directory"""
    try:
        result = await admin_service.bootstrap_tv_shows(dry_run=request.dry_run)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bootstrap/episodes", response_model=BootstrapResponse)
async def bootstrap_episodes(request: BootstrapEpisodesRequest,
                            admin_service: AdminService = Depends(get_admin_service)):
    """Bootstrap episodes for all shows"""
    try:
        result = await admin_service.bootstrap_episodes(dry_run=request.dry_run)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backup")
async def backup_database(admin_service: AdminService = Depends(get_admin_service)):
    """Create database backup"""
    try:
        result = await admin_service.backup_database()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/init-db")
async def init_database(admin_service: AdminService = Depends(get_admin_service)):
    """Initialize database"""
    try:
        result = await admin_service.init_database()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 