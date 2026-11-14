import sys
from datetime import datetime
from typing import Dict, List, Any, Optional

from backend.app.core.config import PROJECT_ROOT
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import inspection_store as istore

class VerificationService:
    @staticmethod
    def get_pending() -> List[Dict[str, Any]]:
        """Returns all inspections pending human verification."""
        records = istore.load_all_inspections()
        pending = []
        for r in records:
            v_status = r.get("verification", {}).get("status", "AI_PENDING")
            if v_status == "AI_PENDING":
                pending.append(r)
        return pending

    @staticmethod
    def verify(inspection_id: str, verified_by: str = "QA Inspector", notes: Optional[str] = None) -> Dict[str, Any]:
        """Marks an inspection record as VERIFIED."""
        record = istore.get_inspection(inspection_id)
        if not record:
            raise KeyError(f"Inspection #{inspection_id} not found")

        v_block = record.get("verification", {})
        v_block["status"] = "VERIFIED"
        v_block["verified_by"] = verified_by
        v_block["verified_at"] = datetime.now().isoformat()
        if notes:
            v_block["notes"] = notes

        istore.update_inspection(inspection_id, {"verification": v_block})
        return istore.get_inspection(inspection_id)

    @staticmethod
    def reject(inspection_id: str, rejection_reason: str, rejected_by: str = "QA Inspector") -> Dict[str, Any]:
        """Marks an inspection record as REJECTED with a required reason."""
        if not rejection_reason or len(rejection_reason.strip()) < 3:
            raise ValueError("A clear rejection reason is mandatory.")

        record = istore.get_inspection(inspection_id)
        if not record:
            raise KeyError(f"Inspection #{inspection_id} not found")

        v_block = record.get("verification", {})
        v_block["status"] = "REJECTED"
        v_block["verified_by"] = rejected_by
        v_block["verified_at"] = datetime.now().isoformat()
        v_block["rejection_reason"] = rejection_reason.strip()

        istore.update_inspection(inspection_id, {"verification": v_block})
        return istore.get_inspection(inspection_id)

    @staticmethod
    def correct(
        inspection_id: str,
        corrected_class: Optional[str] = None,
        corrected_severity: Optional[str] = None,
        notes: Optional[str] = None,
        corrected_by: str = "QA Inspector"
    ) -> Dict[str, Any]:
        """
        Applies human corrections to class or severity while preserving original AI predictions.
        """
        record = istore.get_inspection(inspection_id)
        if not record:
            raise KeyError(f"Inspection #{inspection_id} not found")

        v_block = record.get("verification", {})
        if "original_ai_prediction" not in v_block:
            v_block["original_ai_prediction"] = {
                "potholes": record.get("final_potholes", 0),
                "cracks": record.get("final_cracks", 0),
                "overall_severity": record.get("overall_severity", "MINOR")
            }

        v_block["status"] = "VERIFIED"
        v_block["verified_by"] = corrected_by
        v_block["verified_at"] = datetime.now().isoformat()
        if corrected_class:
            v_block["corrected_class"] = corrected_class
        if corrected_severity:
            v_block["corrected_severity"] = corrected_severity
        if notes:
            v_block["notes"] = notes

        updates = {"verification": v_block}
        if corrected_severity:
            updates["overall_severity"] = corrected_severity
            if "summary" in record and isinstance(record["summary"], dict):
                record["summary"]["overall_severity"] = corrected_severity
                updates["summary"] = record["summary"]

        istore.update_inspection(inspection_id, updates)
        return istore.get_inspection(inspection_id)

    @staticmethod
    def update_duplicate_status(
        inspection_id: str,
        status: str,
        duplicate_of: Optional[str] = None
    ) -> Dict[str, Any]:
        """Updates duplicate status (e.g. CONFIRMED_DUPLICATE, MARKED_AS_UNIQUE)."""
        record = istore.get_inspection(inspection_id)
        if not record:
            raise KeyError(f"Inspection #{inspection_id} not found")

        updates = {
            "duplicate_status": status,
            "duplicate_of": duplicate_of if status == "CONFIRMED_DUPLICATE" else None
        }
        istore.update_inspection(inspection_id, updates)
        return istore.get_inspection(inspection_id)

verification_service = VerificationService()
