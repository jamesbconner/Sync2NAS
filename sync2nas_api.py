#!/usr/bin/env python3
"""
FastAPI server runner for Sync2NAS
"""
import uvicorn
import os
from api.main import app

if __name__ == "__main__":
    host = os.getenv("SYNC2NAS_HOST", "0.0.0.0")
    port = int(os.getenv("SYNC2NAS_PORT", "8000"))
    
    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=True,  # Enable auto-reload for development
        log_level="info"
    ) 