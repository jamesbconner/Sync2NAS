from fastapi import APIRouter, Depends, HTTPException

from api.models.requests import DownloadFromRemoteRequest, ListRemoteRequest
from api.models.responses import DownloadResponse, ListRemoteResponse, ConnectionStatusResponse
from api.services.remote_service import RemoteService
from api.dependencies import get_remote_service

router = APIRouter()


@router.post("/download", response_model=DownloadResponse)
async def download_from_remote(request: DownloadFromRemoteRequest,
                              remote_service: RemoteService = Depends(get_remote_service)):
    """Download files from remote SFTP server"""
    try:
        result = await remote_service.download_from_remote(dry_run=request.dry_run)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/list", response_model=ListRemoteResponse)
async def list_remote_files(request: ListRemoteRequest,
                           remote_service: RemoteService = Depends(get_remote_service)):
    """List files on remote SFTP server"""
    try:
        result = await remote_service.list_remote_files(
            path=request.path,
            recursive=request.recursive,
            populate_sftp_temp=request.populate_sftp_temp,
            dry_run=request.dry_run
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=ConnectionStatusResponse)
async def get_connection_status(remote_service: RemoteService = Depends(get_remote_service)):
    """Get SFTP connection status"""
    try:
        result = await remote_service.get_connection_status()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 