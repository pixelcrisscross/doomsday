from fastapi import APIRouter, HTTPException, status
from typing import List, Dict, Any

from backend.app.services.verification_service import verification_service
from backend.app.schemas.schemas import VerifyActionRequest, RejectActionRequest, CorrectActionRequest

router = APIRouter(prefix="/verification", tags=["Verification Queue"])

@router.get("/pending", response_model=List[Dict[str, Any]])
async def get_pending_inspections():
    """Retrieves all detections pending human verification."""
    return verification_service.get_pending()

@router.post("/{inspection_id}/verify")
async def verify_inspection(inspection_id: str, payload: VerifyActionRequest):
    """Verifies and approves an inspection detection."""
    try:
        return verification_service.verify(
            inspection_id=inspection_id,
            verified_by=payload.verified_by or "QA Inspector",
            notes=payload.notes
        )
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Inspection #{inspection_id} not found")

@router.post("/{inspection_id}/reject")
async def reject_inspection(inspection_id: str, payload: RejectActionRequest):
    """Rejects false positives with mandatory justification."""
    try:
        return verification_service.reject(
            inspection_id=inspection_id,
            rejection_reason=payload.rejection_reason,
            rejected_by=payload.rejected_by or "QA Inspector"
        )
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Inspection #{inspection_id} not found")
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

@router.post("/{inspection_id}/correct")
async def correct_inspection(inspection_id: str, payload: CorrectActionRequest):
    """Corrects damage category or visual severity, preserving original AI prediction."""
    try:
        return verification_service.correct(
            inspection_id=inspection_id,
            corrected_class=payload.corrected_class,
            corrected_severity=payload.corrected_severity,
            notes=payload.notes,
            corrected_by=payload.corrected_by or "QA Inspector"
        )
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Inspection #{inspection_id} not found")
