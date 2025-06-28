"""
Show Routes Module

This module defines the REST API endpoints for TV show management operations.
It handles HTTP requests for show CRUD operations and delegates business logic
to the ShowService.

Endpoints:
    - GET /: Retrieve all shows
    - GET /{show_id}: Retrieve specific show
    - POST /: Add new show
    - POST /{show_id}/episodes/refresh: Update episodes for show
    - DELETE /{show_id}: Delete a specific show and all its episodes
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import List

from api.models.requests import AddShowRequest, UpdateEpisodesRequest
from api.models.responses import (
    ShowResponse, AddShowResponse, UpdateEpisodesResponse, DeleteShowResponse
)
from api.services.show_service import ShowService
from api.dependencies import get_show_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[ShowResponse])
async def get_shows(show_service: ShowService = Depends(get_show_service)):
    """
    Retrieve all TV shows from the database.
    
    Returns:
        List[ShowResponse]: List of all shows with their details
        
    Raises:
        HTTPException: If database operation fails
    """
    logger.info("api/routes/shows.py::get_shows - GET /api/shows/ endpoint accessed")
    
    try:
        shows = await show_service.get_shows()
        logger.info(f"api/routes/shows.py::get_shows - Successfully retrieved {len(shows)} shows")
        return shows
    except Exception as e:
        logger.exception(f"api/routes/shows.py::get_shows - Failed to retrieve shows: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve shows: {str(e)}")


@router.get("/{show_id}", response_model=ShowResponse)
async def get_show(show_id: int, show_service: ShowService = Depends(get_show_service)):
    """
    Retrieve a specific TV show by its database ID.
    
    Args:
        show_id: Database ID of the show to retrieve
        
    Returns:
        ShowResponse: Show details if found
        
    Raises:
        HTTPException: If show not found or database operation fails
    """
    logger.info(f"api/routes/shows.py::get_show - GET /api/shows/{show_id} endpoint accessed")
    
    try:
        show = await show_service.get_show(show_id)
        
        if not show:
            logger.warning(f"api/routes/shows.py::get_show - Show with ID {show_id} not found")
            raise HTTPException(status_code=404, detail=f"Show with ID {show_id} not found")
        
        logger.info(f"api/routes/shows.py::get_show - Successfully retrieved show: {show['tmdb_name']}")
        return show
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.exception(f"api/routes/shows.py::get_show - Failed to retrieve show {show_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve show: {str(e)}")


@router.post("/", response_model=AddShowResponse)
async def add_show(request: AddShowRequest, 
                  show_service: ShowService = Depends(get_show_service)):
    """
    Add a new TV show to the database and file system.
    
    Args:
        request: AddShowRequest containing show details
        
    Returns:
        AddShowResponse: Operation result with show details
        
    Raises:
        HTTPException: If validation fails or operation errors occur
    """
    logger.info(f"api/routes/shows.py::add_show - POST /api/shows/ endpoint accessed with request: {request}")
    
    try:
        result = await show_service.add_show(
            show_name=request.show_name,
            tmdb_id=request.tmdb_id,
            override_dir=request.override_dir
        )
        
        logger.info(f"api/routes/shows.py::add_show - Successfully added show: {result['tmdb_name']}")
        return result
        
    except ValueError as e:
        logger.error(f"api/routes/shows.py::add_show - Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except FileExistsError as e:
        logger.error(f"api/routes/shows.py::add_show - Show already exists: {e}")
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.exception(f"api/routes/shows.py::add_show - Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add show: {str(e)}")


@router.post("/{show_id}/episodes/refresh", response_model=UpdateEpisodesResponse)
async def update_episodes(show_id: int, request: UpdateEpisodesRequest,
                         show_service: ShowService = Depends(get_show_service)):
    """
    Update episodes for a specific show by refreshing data from TMDB.
    
    Args:
        show_id: Database ID of the show to update
        request: UpdateEpisodesRequest containing optional override parameters
        
    Returns:
        UpdateEpisodesResponse: Operation result with episode count
        
    Raises:
        HTTPException: If show not found, validation fails, or operation errors occur
    """
    logger.info(f"api/routes/shows.py::update_episodes - POST /api/shows/{show_id}/episodes/refresh endpoint accessed")
    
    try:
        # First verify the show exists
        show = await show_service.get_show(show_id)
        if not show:
            logger.warning(f"api/routes/shows.py::update_episodes - Show with ID {show_id} not found")
            raise HTTPException(status_code=404, detail=f"Show with ID {show_id} not found")

        # Update episodes using show data or request overrides
        result = await show_service.update_episodes(
            show_name=request.show_name or show["sys_name"],
            tmdb_id=request.tmdb_id or show["tmdb_id"]
        )
        
        logger.info(f"api/routes/shows.py::update_episodes - Successfully updated {result['episodes_updated']} episodes for {result['show_name']}")
        return result
        
    except ValueError as e:
        logger.error(f"api/routes/shows.py::update_episodes - Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.exception(f"api/routes/shows.py::update_episodes - Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update episodes: {str(e)}")


@router.delete("/{show_id}", response_model=DeleteShowResponse)
async def delete_show(show_id: int, show_service: ShowService = Depends(get_show_service)):
    """
    Delete a specific TV show and all its episodes from the database.
    
    This endpoint is primarily used for fixing mis-identified shows by removing
    them from the database so they can be re-added with correct identification.
    
    Args:
        show_id: Database ID of the show to delete
        
    Returns:
        DeleteShowResponse: Operation result with deletion details
        
    Raises:
        HTTPException: If show not found or operation errors occur
    """
    logger.info(f"api/routes/shows.py::delete_show - DELETE /api/shows/{show_id} endpoint accessed")
    
    try:
        result = await show_service.delete_show(show_id)
        
        logger.info(f"api/routes/shows.py::delete_show - Successfully deleted show: {result['show_name']}")
        return result
        
    except ValueError as e:
        logger.error(f"api/routes/shows.py::delete_show - Validation error: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"api/routes/shows.py::delete_show - Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete show: {str(e)}") 