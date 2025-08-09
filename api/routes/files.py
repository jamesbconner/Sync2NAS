# API routes for file operations (routing, listing, and filename parsing)
# Handles HTTP endpoints for file management in Sync2NAS

from fastapi import APIRouter, Depends, HTTPException, Request

from api.models.requests import RouteFilesRequest, LLMParseFilenameRequest, UpdateDownloadedFileStatusRequest
from api.models.responses import RouteFilesResponse, ListIncomingResponse, LLMParseFilenameResponse, ListDownloadedFilesResponse, DownloadedFileDTO
from api.dependencies import get_db_service
from api.services.file_service import FileService
from api.dependencies import get_file_service
from services.llm_implementations.llm_interface import LLMInterface as LLMService
from api.dependencies import get_llm_service
from fastapi import Query
from models.downloaded_file import FileStatus
import os
import datetime
from services.hashing_service import HashingService

router = APIRouter()


@router.post("/route", response_model=RouteFilesResponse)
async def route_files(request: Request,
                     body: RouteFilesRequest,
                     file_service: FileService = Depends(get_file_service)):
    """
    Route files from incoming directory to show directories.
    Optionally supports dry-run and auto-add of missing shows.
    """
    try:
        result = await file_service.route_files(
            dry_run=body.dry_run,
            auto_add=body.auto_add,
            request=request
        )
        return result
    except Exception as e:
        # Return 500 error if routing fails
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/incoming", response_model=ListIncomingResponse)
async def list_incoming_files(file_service: FileService = Depends(get_file_service)):
    """
    List all files in the incoming directory (excluding excluded filenames).
    """
    try:
        result = await file_service.list_incoming_files()
        return result
    except Exception as e:
        # Return 500 error if listing fails
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/downloaded", response_model=ListDownloadedFilesResponse)
async def list_downloaded_files(
    request: Request,
    status: str | None = Query(None, description="Filter by status (downloaded, processing, routed, error, deleted)"),
    file_type: str | None = Query(None, description="Filter by file type (video, audio, subtitle, nfo, image, archive, unknown)"),
    q: str | None = Query(None, description="Free text search in name/paths"),
    tmdb_id: int | None = Query(None, description="Filter by TMDB show id"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    sort_by: str = Query("modified_time"),
    sort_order: str = Query("desc"),
):
    try:
        services = getattr(request.app.state, "services", {}) if hasattr(request.app, "state") else {}
        db = services.get("db") if services else None
        if db is None:
            raise HTTPException(status_code=500, detail="Database service not available")

        # Choose repo implementation based on backend
        # Use DB service directly (schema initialized on startup)

        items = []
        # Default filter: only 'downloaded' if status not provided
        fstatus = None
        if status:
            try:
                fstatus = FileStatus(status)
            except Exception:
                raise HTTPException(status_code=422, detail=f"Invalid status: {status}")
        else:
            fstatus = FileStatus.DOWNLOADED

        items, total = db.search_downloaded_files(
            status=fstatus,
            file_type=file_type,
            q=q,
            tmdb_id=tmdb_id,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        def to_dto(df) -> DownloadedFileDTO:
            return DownloadedFileDTO(
                id=df.id,
                name=df.name,
                remote_path=df.remote_path,
                previous_path=getattr(df, "previous_path", None),
                current_path=df.current_path,
                size=df.size,
                modified_time=df.modified_time.isoformat() if df.modified_time else None,
                fetched_at=df.fetched_at.isoformat() if df.fetched_at else None,
                is_dir=df.is_dir,
                status=df.status.value,
                file_type=df.file_type.value,
                file_hash_value=df.file_hash,
            )

        dtos = [to_dto(df) for df in items]
        return ListDownloadedFilesResponse(success=True, files=dtos, count=total)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/downloaded/{file_id}", response_model=DownloadedFileDTO)
def get_downloaded_file(file_id: int, db = Depends(get_db_service)):
    item = db.get_downloaded_file_by_id(file_id)
    if not item:
        raise HTTPException(status_code=404, detail="Downloaded file not found")
    return DownloadedFileDTO(
        id=item.id,
        name=item.name,
        remote_path=item.remote_path,
        current_path=item.current_path,
        previous_path=getattr(item, "previous_path", None),
        size=item.size,
        modified_time=item.modified_time.isoformat() if item.modified_time else None,
        fetched_at=item.fetched_at.isoformat() if item.fetched_at else None,
        is_dir=item.is_dir,
        status=item.status.value,
        file_type=item.file_type.value,
        file_hash_value=item.file_hash,
    )

@router.patch("/downloaded/{file_id}")
def patch_downloaded_file_status(file_id: int, body: UpdateDownloadedFileStatusRequest, db = Depends(get_db_service)):
    try:
        from models.downloaded_file import FileStatus
        new_status = FileStatus(body.status)
    except Exception:
        raise HTTPException(status_code=422, detail=f"Invalid status: {body.status}")
    db.update_downloaded_file_status(file_id, new_status, body.error_message)
    item = db.get_downloaded_file_by_id(file_id)
    if not item:
        raise HTTPException(status_code=404, detail="Downloaded file not found after update")
    return {
        "success": True,
        "id": item.id,
        "status": item.status.value,
        "error_message": item.error_message,
    }


@router.post("/parse-filename", response_model=LLMParseFilenameResponse)
async def parse_filename_llm(
    request: Request,
    body: LLMParseFilenameRequest,
    llm_service: LLMService = Depends(get_llm_service)
):
    """
    Parse a filename using LLM for show/season/episode extraction.
    Returns parsed metadata if LLM confidence meets the threshold.
    """
    try:
        # Use the LLM service to parse the filename
        result = llm_service.parse_filename(
            body.filename,
            max_tokens=150
        )
        # Only return if confidence meets threshold
        if result.get("confidence", 0.0) < body.llm_confidence_threshold:
            raise HTTPException(status_code=422, detail=f"LLM confidence too low: {result.get('confidence')}")
        return LLMParseFilenameResponse(**result)
    except Exception as e:
        # Return 500 error if LLM parsing fails
        raise HTTPException(status_code=500, detail=str(e)) 


@router.post("/downloaded/{file_id}/rehash")
def rehash_downloaded_file(file_id: int, db = Depends(get_db_service)):
    item = db.get_downloaded_file_by_id(file_id)
    if not item:
        raise HTTPException(status_code=404, detail="Downloaded file not found")
    if item.is_dir:
        raise HTTPException(status_code=422, detail="Cannot hash a directory")
    hasher = HashingService()
    file_path = item.current_path or item.remote_path
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk for hashing")
    try:
        crc = hasher.calculate_crc32(file_path)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Hashing failed: {e}")
    if not crc:
        raise HTTPException(status_code=422, detail="Unable to compute CRC32")
    db.set_downloaded_file_hash(item.id, "CRC32", crc, datetime.datetime.now())
    item = db.get_downloaded_file_by_id(file_id)
    return {
        "success": True,
        "id": item.id,
        "file_hash_value": item.file_hash,
        "file_hash_algo": "CRC32" if item.file_hash and len(item.file_hash) == 8 else None,
    }