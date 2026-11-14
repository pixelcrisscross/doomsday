from typing import List, Optional
import os
import uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form, status
from PIL import Image

from backend.app.schemas.schemas import (
    AssignWorkOrderRequest,
    UpdateWorkOrderStatusRequest,
    ReviewWorkOrderRequest,
    WorkOrderResponse
)
from backend.app.services.work_order_service import work_order_service
from backend.app.core.config import OUTPUTS_DIR

router = APIRouter(prefix="/work-orders", tags=["Work Orders & Repairs"])

@router.get("", response_model=List[WorkOrderResponse])
async def list_work_orders(
    worker_email: Optional[str] = Query(None, description="Filter orders assigned to specific worker"),
    status: Optional[str] = Query(None, description="Filter by status: ASSIGNED, IN_PROGRESS, REPAIRED, CLOSED")
):
    """Lists all road repair work orders with worker and status filters."""
    return work_order_service.list_work_orders(worker_email=worker_email, status=status)

@router.post("/assign", response_model=WorkOrderResponse)
async def assign_pothole_to_worker(payload: AssignWorkOrderRequest):
    """Authority validates pothole and dispatches repair work order to a contractor."""
    try:
        return work_order_service.assign_work_order(payload)
    except KeyError as ke:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ke))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to assign work: {e}")

@router.post("/{order_id}/status", response_model=WorkOrderResponse)
async def update_work_order_status(order_id: str, payload: UpdateWorkOrderStatusRequest):
    """Worker updates progress ('IN_PROGRESS' or 'REPAIRED' with completion proof)."""
    try:
        return work_order_service.update_status(order_id, payload)
    except KeyError as ke:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ke))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Status update failed: {e}")

@router.post("/{order_id}/review", response_model=WorkOrderResponse)
async def review_completed_repair(order_id: str, payload: ReviewWorkOrderRequest):
    """Authority reviews contractor repair proof and approves or requests rework."""
    try:
        return work_order_service.review_work_order(order_id, payload)
    except KeyError as ke:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ke))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Review failed: {e}")

@router.post("/upload-proof")
async def upload_repair_proof(file: UploadFile = File(...)):
    """Accepts field repair proof photo uploaded by contractor."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    proof_name = f"proof_{uuid.uuid4().hex[:8]}_{file.filename}"
    save_path = OUTPUTS_DIR / proof_name
    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)
        
    return {
        "proof_image_url": f"/outputs/{proof_name}",
        "filename": proof_name
    }
