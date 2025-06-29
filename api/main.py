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
    # Startup
    setup_logging(verbosity=1)  # Default to INFO level
    logging.info("Starting Sync2NAS API server")
    
    # Load configuration
    config_path = os.getenv('SYNC2NAS_CONFIG', './config/sync2nas_config.ini')
    app.state.config = load_configuration(config_path)
    
    # Initialize services
    app.state.services = get_services(app.state.config)
    
    yield
    
    # Shutdown
    logging.info("Shutting down Sync2NAS API server")


app = FastAPI(
    title="Sync2NAS API",
    description="API for managing TV show synchronization and file routing",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(shows.router, prefix="/api/shows", tags=["shows"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(remote.router, prefix="/api/remote", tags=["remote"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])


@app.get("/")
async def root():
    return {"message": "Sync2NAS API", "version": "1.0.0"}


@app.get("/health")
async def health_check(request: Request):
    """Health check endpoint"""
    services = request.app.state.services
    status = {"api": "ok"}
    healthy = True

    # 1. Database connectivity
    try:
        db = services["db"]
        if hasattr(db, "get_all_shows"):
            db.get_all_shows()
        status["database"] = "ok"
    except Exception as e:
        status["database"] = f"error: {e}"
        healthy = False

    # 2. SFTP server connectivity
    try:
        sftp = services["sftp"]
        with sftp as s:
            s.list_remote_dir("/")
        status["sftp"] = "ok"
    except Exception as e:
        status["sftp"] = f"error: {e}"
        healthy = False

    # 3. TMDB API connectivity
    try:
        tmdb = services["tmdb"]
        result = tmdb.search_show("Breaking Bad")
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
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)