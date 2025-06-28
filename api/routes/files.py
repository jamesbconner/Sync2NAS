from fastapi import APIRouter, Depends, HTTPException

from api.models.requests import RouteFilesRequest
from api.models.responses import RouteFilesResponse, ListIncomingResponse
from api.services.file_service import FileService
from api.dependencies import get_file_service

router = APIRouter()


@router.post("/route", response_model=RouteFilesResponse)
async def route_files(request: RouteFilesRequest,
                     file_service: FileService = Depends(get_file_service)):
    """Route files from incoming directory to show directories"""
    try:
        result = await file_service.route_files(
            dry_run=request.dry_run,
            auto_add=request.auto_add
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/incoming", response_model=ListIncomingResponse)
async def list_incoming_files(file_service: FileService = Depends(get_file_service)):
    """List files in the incoming directory"""
    try:
        result = await file_service.list_incoming_files()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 