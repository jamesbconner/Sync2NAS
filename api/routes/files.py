from fastapi import APIRouter, Depends, HTTPException, Request

from api.models.requests import RouteFilesRequest, LLMParseFilenameRequest
from api.models.responses import RouteFilesResponse, ListIncomingResponse, LLMParseFilenameResponse
from api.services.file_service import FileService
from api.dependencies import get_file_service

router = APIRouter()


@router.post("/route", response_model=RouteFilesResponse)
async def route_files(request: Request,
                     body: RouteFilesRequest,
                     file_service: FileService = Depends(get_file_service)):
    """Route files from incoming directory to show directories"""
    try:
        result = await file_service.route_files(
            dry_run=body.dry_run,
            auto_add=body.auto_add,
            request=request
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


@router.post("/parse-filename", response_model=LLMParseFilenameResponse)
async def parse_filename_llm(request: LLMParseFilenameRequest):
    """Parse a filename using LLM for show/season/episode extraction"""
    try:
        from fastapi import Request as FastAPIRequest
        import inspect
        # Get the FastAPI request object from the stack
        fastapi_request = None
        for frame_info in inspect.stack():
            if "request" in frame_info.frame.f_locals:
                maybe_request = frame_info.frame.f_locals["request"]
                if isinstance(maybe_request, FastAPIRequest):
                    fastapi_request = maybe_request
                    break
        if fastapi_request is None:
            raise RuntimeError("Could not access FastAPI request context for LLM service.")
        llm_service = fastapi_request.app.state.services["llm_service"]
        result = llm_service.parse_filename(
            request.filename,
            max_tokens=150
        )
        # Only return if confidence meets threshold
        if result.get("confidence", 0.0) < request.llm_confidence_threshold:
            raise HTTPException(status_code=422, detail=f"LLM confidence too low: {result.get('confidence')}")
        return LLMParseFilenameResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 