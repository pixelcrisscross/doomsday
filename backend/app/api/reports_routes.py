from typing import Optional
from fastapi import APIRouter, HTTPException, status, Query, Response
from fastapi.responses import Response

from backend.app.services.report_service import report_service

router = APIRouter(prefix="/reports", tags=["Inspection Reports"])

@router.get("/")
async def list_reports(
    media_type: Optional[str] = Query(None, description="Filter by 'photo' or 'video'"),
    verification_status: Optional[str] = Query(None, description="Filter by 'AI_PENDING', 'VERIFIED', 'REJECTED'"),
    severity: Optional[str] = Query(None, description="Filter by 'MINOR', 'MODERATE', 'SEVERE', 'CRITICAL'"),
    search: Optional[str] = Query(None, description="Search by inspection ID or location"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """Lists inspection reports with filtering and pagination."""
    return report_service.get_reports(
        media_type=media_type,
        verification_status=verification_status,
        severity=severity,
        search=search,
        limit=limit,
        offset=offset
    )

@router.get("/export/csv")
async def export_reports_csv():
    """Generates and downloads full CSV report using Python standard library (no pandas)."""
    csv_bytes = report_service.generate_csv()
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=roadsentinel_inspections.csv"}
    )

@router.get("/{inspection_id}")
async def get_report_details(inspection_id: str):
    """Retrieves single inspection report by ID."""
    record = report_service.get_report_by_id(inspection_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Inspection #{inspection_id} not found")
    return record

@router.delete("/{inspection_id}")
async def delete_report(inspection_id: str):
    """Deletes an inspection record."""
    success = report_service.delete_report(inspection_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Inspection #{inspection_id} not found or could not be deleted")
    return {"message": f"Inspection #{inspection_id} successfully deleted", "success": True}
