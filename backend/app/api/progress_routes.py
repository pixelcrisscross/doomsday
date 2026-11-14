from fastapi import APIRouter, Query, HTTPException

from backend.app.services.progress_service import progress_service
from backend.app.schemas.schemas import InspectionStatusCheckResponse

router = APIRouter(prefix="/progress", tags=["Progress Monitoring"])

@router.get("/locations")
async def get_locations_with_history():
    """Lists geographical locations having historical inspections."""
    return progress_service.get_locations_with_history()

@router.get("/compare")
async def compare_progress_for_location(location: str = Query(..., description="Target location address or name")):
    """Compares condition trend over time for a target road location."""
    return progress_service.compare_location(location)

@router.get("/status/{inspection_id}", response_model=InspectionStatusCheckResponse)
async def check_inspection_status(inspection_id: str):
    """
    Returns full progress report and audit lifecycle timeline for an individual pothole report.
    Allows citizens and municipal authorities to track repair progression in real-time.
    """
    try:
        return progress_service.get_status_check(inspection_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Inspection #{inspection_id} not found")
