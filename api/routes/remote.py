# API routes for remote SFTP operations (download, list, status)
# Handles HTTP endpoints for remote file management in Sync2NAS

from fastapi import APIRouter, Depends, HTTPException

from api.models.requests import DownloadFromRemoteRequest, ListRemoteRequest
from api.models.responses import DownloadResponse, ListRemoteResponse, ConnectionStatusResponse
from api.services.remote_service import RemoteService
from api.dependencies import get_remote_service

router = APIRouter()


@router.post("/download", response_model=DownloadResponse)
async def download_from_remote(request: DownloadFromRemoteRequest,
                              remote_service: RemoteService = Depends(get_remote_service)):
    """
    Download files from remote SFTP server to the incoming directory.
    Supports dry-run mode for simulation.
    """
    try:
        result = await remote_service.download_from_remote(dry_run=request.dry_run)
        return result
    except ValueError as e:
        # Return 400 for validation errors
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Return 500 for other errors
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/list", response_model=ListRemoteResponse)
async def list_remote_files(request: ListRemoteRequest,
                           remote_service: RemoteService = Depends(get_remote_service)):
    """
    List files on the remote SFTP server.
    Supports recursive listing and populating the sftp_temp table.
    """
    try:
        result = await remote_service.list_remote_files(
            path=request.path,
            recursive=request.recursive,
            populate_sftp_temp=request.populate_sftp_temp,
            dry_run=request.dry_run
        )
        return result
    except Exception as e:
        # Return 500 for errors
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=ConnectionStatusResponse)
async def get_connection_status(remote_service: RemoteService = Depends(get_remote_service)):
    """
    Get SFTP connection status (connected/disconnected, host, port, error info).
    """
    try:
        result = await remote_service.get_connection_status()
        return result
    except Exception as e:
        # Return 500 for errors
        raise HTTPException(status_code=500, detail=str(e)) 