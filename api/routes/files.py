# API routes for file operations (routing, listing, and filename parsing)
# Handles HTTP endpoints for file management in Sync2NAS

from fastapi import APIRouter, Depends, HTTPException, Request

from api.models.requests import RouteFilesRequest, LLMParseFilenameRequest, UpdateDownloadedFileStatusRequest
from api.models.responses import RouteFilesResponse, ListIncomingResponse, LLMParseFilenameResponse, ListDownloadedFilesResponse, DownloadedFileDTO
from api.dependencies import get_db_service, get_llm_chains_service
from api.services.file_service import FileService
from api.dependencies import get_file_service
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
    # Validate state transition rules explicitly
    item = db.get_downloaded_file_by_id(file_id)
    if not item:
        raise HTTPException(status_code=404, detail="Downloaded file not found")

    current = item.status
    target = body.status

    # Allowed transitions
    allowed = {
        "downloaded": {"processing", "routed", "error", "deleted"},
        "processing": {"routed", "error"},
        "routed": {"error", "deleted"},
        "error": {"processing", "deleted"},
        "deleted": set(),
    }

    if target.value not in allowed[current.value]:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid state transition: {current.value} -> {target.value}",
        )

    db.update_downloaded_file_status(file_id, target, body.error_message)
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
    llm_chains=Depends(get_llm_chains_service)
):
    """
    Parse a filename using LLM for show/season/episode extraction.
    Returns parsed metadata if LLM confidence meets the threshold.
    
    Provides detailed error handling for different failure scenarios:
    - 503: LLM service unavailable
    - 422: Low confidence result (includes partial result)
    - 500: LLM parsing failure
    """
    try:
        # Validate that LLM chains service is available
        if not llm_chains:
            raise HTTPException(
                status_code=503, 
                detail={
                    "error": "LLM service unavailable",
                    "message": "LLM chains service is not initialized or accessible",
                    "fallback_available": True  # Indicate fallback parsing might be available
                }
            )
        
        # Use the LLM chains service to parse the filename
        result = llm_chains.parse_filename(body.filename)
        
        # Convert Pydantic model to dict for response
        result_dict = result.model_dump()
        
        # Check confidence threshold
        confidence = result_dict.get("confidence", 0.0)
        if confidence < body.llm_confidence_threshold:
            raise HTTPException(
                status_code=422, 
                detail={
                    "error": "Low confidence result",
                    "confidence": confidence,
                    "threshold": body.llm_confidence_threshold,
                    "message": f"LLM confidence {confidence:.2f} below threshold {body.llm_confidence_threshold:.2f}",
                    "partial_result": result_dict,  # Include partial result for client decision
                    "suggestion": "Consider lowering confidence threshold or using fallback parsing"
                }
            )
        
        return LLMParseFilenameResponse(**result_dict)
        
    except HTTPException:
        # Re-raise HTTP exceptions (already properly formatted)
        raise
    except Exception as e:
        # Log the error for debugging
        logger.error(f"LLM parsing failed for filename '{body.filename}': {e}")
        
        # Provide detailed error information
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "LLM parsing failed",
                "filename": body.filename,
                "message": str(e),
                "suggestion": "Check LLM service status or try again later"
            }
        )


@router.post("/parse-filename-fallback", response_model=LLMParseFilenameResponse)
async def parse_filename_fallback(
    request: Request,
    body: LLMParseFilenameRequest
):
    """
    Parse a filename using regex-based fallback parsing only.
    
    This endpoint provides a reliable fallback when LLM service is unavailable
    or when LLM parsing fails. Uses the same regex patterns as the main
    filename parser but without LLM enhancement.
    
    Always returns a result (even if confidence is low) to ensure
    system functionality when LLM services are down.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        from utils.filename_parser import _regex_parse_filename
        
        # Use regex-only parsing
        result = _regex_parse_filename(body.filename)
        
        # Always return result regardless of confidence for fallback reliability
        logger.info(f"Fallback parsing for '{body.filename}': confidence {result.get('confidence', 0.0):.2f}")
        
        return LLMParseFilenameResponse(
            show_name=result["show_name"],
            season=result["season"],
            episode=result["episode"],
            confidence=result["confidence"],
            reasoning=f"Regex fallback: {result['reasoning']}"
        )
        
    except Exception as e:
        logger.error(f"Fallback parsing failed for filename '{body.filename}': {e}")
        
        # Even fallback parsing failed - return minimal result
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Fallback parsing failed",
                "filename": body.filename,
                "message": str(e),
                "suggestion": "Filename may be in an unsupported format"
            }
        ) 


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