# Main entry point for the Sync2NAS FastAPI application
# Sets up the API, middleware, service initialization, and health check endpoint

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os

from api.dependencies import get_services
from api.routes import shows, files, remote, admin
from utils.sync2nas_config import load_configuration
from utils.logging_config import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup logic ---
    setup_logging(verbosity=1)  # Set up logging at INFO level by default
    logging.info("Starting Sync2NAS API server")
    
    # Load configuration from environment or default path
    config_path = os.getenv('SYNC2NAS_CONFIG', './config/sync2nas_config.ini')
    app.state.config = load_configuration(config_path)
    
    # Initialize all core services and attach to app state
    app.state.services = get_services(app.state.config)
    
    yield  # Application runs here
    
    # --- Shutdown logic ---
    logging.info("Shutting down Sync2NAS API server")


# Create FastAPI app instance with metadata and lifespan handler
app = FastAPI(
    title="Sync2NAS API",
    description="API for managing TV show synchronization and file routing",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware to allow cross-origin requests (adjust for production!)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all API routers for different domains
app.include_router(shows.router, prefix="/api/shows", tags=["shows"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(remote.router, prefix="/api/remote", tags=["remote"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])


@app.get("/")
async def root():
    """Root endpoint: returns API info and version."""
    return {"message": "Sync2NAS API", "version": "1.0.0"}


@app.get("/health")
async def health_check(request: Request):
    """
    Health check endpoint.
    Verifies connectivity to database, SFTP, and TMDB services.
    Returns a status summary for each service and overall health.
    """
    services = request.app.state.services
    status = {"api": "ok"}
    healthy = True

    # 1. Database connectivity check
    try:
        db = services["db"]
        if hasattr(db, "get_all_shows"):
            db.get_all_shows()
        status["database"] = "ok"
    except Exception as e:
        status["database"] = f"error: {e}"
        healthy = False

    # 2. SFTP server connectivity check
    try:
        sftp = services["sftp"]
        with sftp as s:
            s.list_remote_dir("/")
        status["sftp"] = "ok"
    except Exception as e:
        status["sftp"] = f"error: {e}"
        healthy = False

    # 3. TMDB API connectivity check
    try:
        tmdb = services["tmdb"]
        result = tmdb.search_show("Attack on Titan")
        if result is not None:
            status["tmdb"] = "ok"
        else:
            status["tmdb"] = "error: no response"
            healthy = False
    except Exception as e:
        status["tmdb"] = f"error: {e}"
        healthy = False

    status["status"] = "healthy" if healthy else "unhealthy"
    return status


if __name__ == "__main__":
    # Run the API server using uvicorn if executed directly
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)