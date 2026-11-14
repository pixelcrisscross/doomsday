import os
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from fastapi.responses import FileResponse

from backend.app.services.video_service import video_service
from backend.app.schemas.schemas import VideoDetectionResponse, VideoMetadataResponse
from backend.app.core.config import OUTPUTS_DIR, UPLOADS_DIR

router = APIRouter(prefix="/video", tags=["Video Detection"])

ALLOWED_VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv"}

@router.post("/detect", response_model=VideoDetectionResponse)
async def detect_road_damage_video(
    file: UploadFile = File(..., description="Road video file (.mp4, .avi, .mov, .mkv)"),
    confidence: float = Form(0.20, ge=0.01, le=0.99, description="Confidence threshold"),
    frame_skip: int = Form(2, ge=1, le=10, description="Process every Nth frame"),
    latitude: Optional[float] = Form(None, description="Optional GPS latitude"),
    longitude: Optional[float] = Form(None, description="Optional GPS longitude"),
    location_source: Optional[str] = Form(None, description="Location source")
):
    """
    Accepts road video, processes sequential frames with YOLO, persists unique tracked hazards,
    draws bounding boxes and labels, renders annotated video, and returns full inspection metrics.
    """
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No video file provided")

    ext = ("." + file.filename.split(".")[-1].lower()) if "." in file.filename else ""
    if ext not in ALLOWED_VIDEO_EXTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported video format '{ext}'. Allowed: {', '.join(ALLOWED_VIDEO_EXTS)}"
        )

    try:
        video_bytes = await file.read()
        result = video_service.process_video_upload(
            video_bytes=video_bytes,
            filename=file.filename,
            confidence=confidence,
            frame_skip=frame_skip,
            latitude=latitude,
            longitude=longitude,
            location_source=location_source
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Video processing failed: {e}")

@router.get("/download/{filename}")
async def download_annotated_video(filename: str):
    """Provides processed/annotated video file download."""
    path = OUTPUTS_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processed video file not found")
    return FileResponse(path, media_type="video/mp4", filename=filename)
