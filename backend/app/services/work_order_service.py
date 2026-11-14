import os
import uuid
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from backend.app.core.config import settings, OUTPUTS_DIR
from backend.app.core.database import mongo_manager
from backend.app.schemas.schemas import (
    AssignWorkOrderRequest,
    UpdateWorkOrderStatusRequest,
    ReviewWorkOrderRequest,
    WorkOrderResponse
)
from backend.app.services.auth_service import auth_service
import inspection_store as istore

logger = logging.getLogger("roadsentinel.work_order")

class WorkOrderService:
    def __init__(self):
        self._local_orders: Dict[str, Dict[str, Any]] = {}

    def _sync_to_mongo(self, collection_name: str, doc_filter: Dict[str, Any], doc: Dict[str, Any]):
        col = mongo_manager.get_collection(collection_name)
        if col is not None:
            try:
                col.update_one(doc_filter, {"$set": doc}, upsert=True)
            except Exception as e:
                logger.warning(f"Failed to sync {collection_name} to MongoDB: {e}")

    def assign_work_order(self, req: AssignWorkOrderRequest) -> WorkOrderResponse:
        now = datetime.now()
        order_id = f"WO-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        # 1. Fetch inspection details
        inspection = istore.get_inspection(req.inspection_id)
        if not inspection:
            raise KeyError(f"Inspection #{req.inspection_id} not found")

        # 2. Worker info
        worker = auth_service.get_user_by_email(req.assigned_worker_email)
        worker_name = worker.name if worker else req.assigned_worker_email.split("@")[0].title()

        # 3. Pothole crop or image url
        crop_url = None
        detections = inspection.get("detections", [])
        for d in detections:
            if d.get("crop_path"):
                crop_url = f"/data/pothole_crops/{Path(d['crop_path']).name}"
                break
        if not crop_url and inspection.get("annotated_filename"):
            crop_url = f"/outputs/{inspection['annotated_filename']}"

        order_data = {
            "order_id": order_id,
            "inspection_id": req.inspection_id,
            "assigned_worker_email": req.assigned_worker_email.lower().strip(),
            "assigned_worker_name": worker_name,
            "priority": req.priority,
            "status": "ASSIGNED",
            "target_date": req.target_date or (now.strftime("%Y-%m-%d")),
            "repair_notes": req.repair_notes or "Immediate pothole milling, cleaning, and asphalt patch required.",
            "worker_notes": None,
            "materials_used": None,
            "proof_image_url": None,
            "estimated_cost": req.estimated_cost or 4500.0,
            "actual_cost": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "location_name": inspection.get("location", "Location unavailable"),
            "latitude": inspection.get("latitude"),
            "longitude": inspection.get("longitude"),
            "pothole_crop_url": crop_url
        }

        # 4. Update inspection record
        istore.update_inspection(req.inspection_id, {
            "repair_status": "ASSIGNED",
            "assigned_worker": req.assigned_worker_email,
            "assigned_worker_name": worker_name,
            "work_order_id": order_id
        })

        # 5. Save order in MongoDB and local memory
        self._local_orders[order_id] = order_data
        self._sync_to_mongo("work_orders", {"order_id": order_id}, order_data)

        # 6. Audit log in MongoDB
        log_entry = {
            "log_id": str(uuid.uuid4()),
            "inspection_id": req.inspection_id,
            "order_id": order_id,
            "action": "WORK_ASSIGNED",
            "actor": req.dispatched_by or "Municipal Authority",
            "description": f"Work order dispatched to contractor {worker_name} with priority {req.priority}.",
            "timestamp": now.isoformat()
        }
        self._sync_to_mongo("repair_logs", {"log_id": log_entry["log_id"]}, log_entry)

        return WorkOrderResponse(**order_data)

    def update_status(self, order_id: str, req: UpdateWorkOrderStatusRequest) -> WorkOrderResponse:
        order = self.get_work_order(order_id)
        if not order:
            raise KeyError(f"Work order #{order_id} not found")

        now = datetime.now()
        updated_dict = order.model_dump()
        new_status = req.status.upper()
        updated_dict["status"] = new_status
        updated_dict["updated_at"] = now.isoformat()

        if req.worker_notes:
            updated_dict["worker_notes"] = req.worker_notes
        if req.materials_used:
            updated_dict["materials_used"] = req.materials_used
        if req.actual_cost is not None:
            updated_dict["actual_cost"] = req.actual_cost
        if req.proof_image_url:
            updated_dict["proof_image_url"] = req.proof_image_url

        # Update inspection record
        istore.update_inspection(updated_dict["inspection_id"], {
            "repair_status": new_status,
            "repair_proof_url": updated_dict.get("proof_image_url")
        })

        self._local_orders[order_id] = updated_dict
        self._sync_to_mongo("work_orders", {"order_id": order_id}, updated_dict)

        # Audit log
        action_name = "REPAIR_STARTED" if new_status == "IN_PROGRESS" else "REPAIR_COMPLETED"
        log_entry = {
            "log_id": str(uuid.uuid4()),
            "inspection_id": updated_dict["inspection_id"],
            "order_id": order_id,
            "action": action_name,
            "actor": updated_dict["assigned_worker_name"],
            "description": f"Field repair status transitioned to {new_status}. {req.worker_notes or ''}",
            "timestamp": now.isoformat()
        }
        self._sync_to_mongo("repair_logs", {"log_id": log_entry["log_id"]}, log_entry)

        return WorkOrderResponse(**updated_dict)

    def review_work_order(self, order_id: str, req: ReviewWorkOrderRequest) -> WorkOrderResponse:
        order = self.get_work_order(order_id)
        if not order:
            raise KeyError(f"Work order #{order_id} not found")

        now = datetime.now()
        updated_dict = order.model_dump()
        is_approved = req.decision.upper() == "APPROVED"
        final_status = "CLOSED" if is_approved else "IN_PROGRESS"

        updated_dict["status"] = final_status
        updated_dict["updated_at"] = now.isoformat()

        # Update inspection
        istore.update_inspection(updated_dict["inspection_id"], {
            "repair_status": final_status,
            "authority_review_notes": req.feedback,
            "authority_reviewed_at": now.isoformat()
        })

        self._local_orders[order_id] = updated_dict
        self._sync_to_mongo("work_orders", {"order_id": order_id}, updated_dict)

        # Audit log
        log_entry = {
            "log_id": str(uuid.uuid4()),
            "inspection_id": updated_dict["inspection_id"],
            "order_id": order_id,
            "action": "AUTHORITY_APPROVAL" if is_approved else "AUTHORITY_REJECT_REWORK",
            "actor": req.reviewed_by or "Municipal Authority",
            "description": f"Authority {req.decision.upper()} the completed field repair. Feedback: {req.feedback or 'Standard verified.'}",
            "timestamp": now.isoformat()
        }
        self._sync_to_mongo("repair_logs", {"log_id": log_entry["log_id"]}, log_entry)

        return WorkOrderResponse(**updated_dict)

    def get_work_order(self, order_id: str) -> Optional[WorkOrderResponse]:
        col = mongo_manager.get_collection("work_orders")
        if col is not None:
            try:
                doc = col.find_one({"order_id": order_id})
                if doc:
                    doc.pop("_id", None)
                    return WorkOrderResponse(**doc)
            except Exception:
                pass
        if order_id in self._local_orders:
            return WorkOrderResponse(**self._local_orders[order_id])
        return None

    def list_work_orders(
        self,
        worker_email: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[WorkOrderResponse]:
        results: List[WorkOrderResponse] = []
        col = mongo_manager.get_collection("work_orders")
        if col is not None:
            try:
                query = {}
                if worker_email:
                    query["assigned_worker_email"] = worker_email.lower().strip()
                if status:
                    query["status"] = status.upper()
                cursor = col.find(query).sort("created_at", -1)
                for doc in cursor:
                    doc.pop("_id", None)
                    results.append(WorkOrderResponse(**doc))
                if results:
                    return results
            except Exception:
                pass

        for o in self._local_orders.values():
            if worker_email and o["assigned_worker_email"] != worker_email.lower().strip():
                continue
            if status and o["status"] != status.upper():
                continue
            results.append(WorkOrderResponse(**o))
        return sorted(results, key=lambda x: x.created_at, reverse=True)

work_order_service = WorkOrderService()
