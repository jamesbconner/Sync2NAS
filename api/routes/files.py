# API routes for file operations (routing, listing, and filename parsing)
# Handles HTTP endpoints for file management in Sync2NAS

from fastapi import APIRouter, Depends, HTTPException, Request

from api.models.requests import RouteFilesRequest, LLMParseFilenameRequest
from api.models.responses import RouteFilesResponse, ListIncomingResponse, LLMParseFilenameResponse
from api.services.file_service import FileService
from api.dependencies import get_file_service
from services.llm_implementations.llm_interface import LLMInterface as LLMService
from api.dependencies import get_llm_service

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