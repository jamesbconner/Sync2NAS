from fastapi import FastAPI, HTTPException
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
async def health_check():
    """Health check endpoint"""
    try:
        # Basic health check - could be extended to check DB, SFTP, etc.
        return {"status": "healthy", "services": ["api"]}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)