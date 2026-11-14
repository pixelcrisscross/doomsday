from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from fastapi.responses import FileResponse

from backend.app.services.image_service import image_service
from backend.app.schemas.schemas import ImageDetectionResponse
from backend.app.core.config import OUTPUTS_DIR

router = APIRouter(prefix="/image", tags=["Image Detection"])

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

@router.post("/detect", response_model=ImageDetectionResponse)
async def detect_road_damage_image(
    file: UploadFile = File(..., description="Road image file (.jpg, .jpeg, .png, .webp)"),
    confidence: float = Form(0.20, ge=0.01, le=0.99, description="YOLO confidence threshold"),
    latitude: Optional[float] = Form(None, description="Optional GPS latitude"),
    longitude: Optional[float] = Form(None, description="Optional GPS longitude"),
    location_source: Optional[str] = Form(None, description="Source of coordinates")
):
    """
    Accepts road photo, runs YOLO cascade detection, assesses damage severity,
    calculates heuristic risk, evaluates duplicate reports, and persists inspection record.
    """
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file uploaded")
    
    ext = ("." + file.filename.split(".")[-1].lower()) if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    try:
        image_bytes = await file.read()
        result = image_service.process_image(
            image_bytes=image_bytes,
            filename=file.filename,
            confidence=confidence,
            latitude=latitude,
            longitude=longitude,
            location_source=location_source
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Image inference failed: {e}")

@router.get("/annotated/{filename}")
async def get_annotated_image(filename: str):
    """Serves annotated detection JPEG image."""
    path = OUTPUTS_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Annotated image not found")
    return FileResponse(path, media_type="image/jpeg")
