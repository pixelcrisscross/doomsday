import os
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Ensure project root is in sys.path
CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parent.parent
PROJECT_ROOT = BACKEND_DIR.parent if BACKEND_DIR.name == "backend" else BACKEND_DIR
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import settings, OUTPUTS_DIR, CROPS_DIR
from backend.app.core.database import mongo_manager
from backend.app.api import (
    image_routes,
    video_routes,
    verification_routes,
    analytics_routes,
    reports_routes,
    location_routes,
    progress_routes,
    auth_routes,
    work_order_routes
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Directories for Media Streaming and Previews
app.mount("/outputs", StaticFiles(directory=str(OUTPUTS_DIR)), name="outputs")
if CROPS_DIR.exists():
    app.mount("/data/pothole_crops", StaticFiles(directory=str(CROPS_DIR)), name="pothole_crops")

# Include API Routers under /api/v1 and /api
API_PREFIX = settings.API_V1_STR
for prefix in [API_PREFIX, "/api"]:
    app.include_router(image_routes.router, prefix=prefix)
    app.include_router(video_routes.router, prefix=prefix)
    app.include_router(verification_routes.router, prefix=prefix)
    app.include_router(analytics_routes.router, prefix=prefix)
    app.include_router(reports_routes.router, prefix=prefix)
    app.include_router(location_routes.router, prefix=prefix)
    app.include_router(progress_routes.router, prefix=prefix)
    app.include_router(auth_routes.router, prefix=prefix)
    app.include_router(work_order_routes.router, prefix=prefix)

@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "online",
        "platform": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database": "MongoDB Atlas" if mongo_manager.is_connected() else "Local File Store (Fallback)",
        "mongodb_connected": mongo_manager.is_connected(),
        "docs": "/docs",
        "api_v1": settings.API_V1_STR
    }

@app.get("/api/v1/health", tags=["Health"])
@app.get("/api/health", tags=["Health"])
async def health():
    return {
        "status": "healthy",
        "models_loaded": True,
        "database": "MongoDB Atlas" if mongo_manager.is_connected() else "Local Fallback",
        "mongodb_connected": mongo_manager.is_connected(),
        "platform": settings.PROJECT_NAME
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
