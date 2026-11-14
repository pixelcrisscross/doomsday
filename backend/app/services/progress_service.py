import sys
from typing import Dict, List, Any, Optional

from backend.app.core.config import PROJECT_ROOT
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import inspection_store as istore
import progress_monitor as pm

class ProgressService:
    @staticmethod
    def get_locations_with_history() -> List[Dict[str, Any]]:
        """Returns unique locations that have 1 or more inspection reports."""
        records = istore.load_all_inspections()
        loc_map = {}

        for r in records:
            loc = r.get("location")
            if loc and loc != "Location unavailable":
                if loc not in loc_map:
                    loc_map[loc] = []
                loc_map[loc].append(r)

        results = []
        for loc, reps in loc_map.items():
            results.append({
                "location": loc,
                "inspection_count": len(reps),
                "inspections": reps
            })
        return results

    @staticmethod
    def compare_location(location_name: str) -> Dict[str, Any]:
        """Compares chronological progress for a given location."""
        records = istore.load_all_inspections()
        history = pm.find_location_history(location_name, records)
        
        if len(history) < 2:
            return {
                "location": location_name,
                "status": "INSUFFICIENT_DATA",
                "message": f"Found {len(history)} inspection(s) for '{location_name}'. At least 2 are required to evaluate progress.",
                "history": [h[1] for h in history]
            }

        comparison = pm.compare_progress(history)
        return {
            "location": location_name,
            "status": "SUCCESS",
            "comparison": comparison,
            "history": [h[1] for h in history]
        }

    @staticmethod
    def get_status_check(inspection_id: str) -> Dict[str, Any]:
        """
        Builds a comprehensive audit trail and step-by-step progress timeline
        for citizen tracking and municipal oversight.
        """
        record = istore.get_inspection(inspection_id)
        if not record:
            raise KeyError(f"Inspection #{inspection_id} not found")

        v_status = record.get("verification", {}).get("status", "AI_PENDING")
        rep_status = record.get("repair_status", "REPORTED")
        if v_status == "VERIFIED" and rep_status == "REPORTED":
            rep_status = "VERIFIED"

        p_cnt = record.get("final_potholes", 0)
        c_cnt = record.get("final_cracks", 0)
        worker_email = record.get("assigned_worker")
        worker_name = record.get("assigned_worker_name", worker_email or "Assigned Contractor")

        # Step 1: Reported
        steps = [
            {
                "step_key": "REPORTED",
                "title": "1. Citizen Report Submitted",
                "description": "Incident captured and registered into RoadSentinel AI.",
                "timestamp": record.get("date", record.get("timestamp")),
                "completed": True,
                "current": rep_status == "REPORTED" and v_status == "AI_PENDING",
                "actor": record.get("created_by", "Citizen Reporter"),
                "badge": "Captured"
            },
            {
                "step_key": "AI_ANALYZED",
                "title": "2. AI Neural Damage Assessment",
                "description": f"YOLOv8 detected {p_cnt} pothole(s), {c_cnt} crack(s). Severity: {record.get('overall_severity', 'MODERATE')}.",
                "timestamp": record.get("timestamp"),
                "completed": True,
                "current": False,
                "actor": "YOLOv8 Engine",
                "badge": f"Risk: {record.get('risk_category', 'Low')}"
            },
            {
                "step_key": "VERIFIED",
                "title": "3. Authority Validation",
                "description": "Municipal engineering department verified defect authenticity and prioritized dispatch.",
                "timestamp": record.get("verification", {}).get("verified_at"),
                "completed": v_status in ["VERIFIED"] or rep_status in ["ASSIGNED", "IN_PROGRESS", "REPAIRED", "CLOSED"],
                "current": v_status == "VERIFIED" and rep_status in ["REPORTED", "VERIFIED"],
                "actor": record.get("verification", {}).get("verified_by", "Municipal Officer"),
                "badge": v_status
            },
            {
                "step_key": "ASSIGNED",
                "title": "4. Dispatched to Contractor",
                "description": f"Assigned to {worker_name} with target completion schedule.",
                "timestamp": record.get("work_assigned_at"),
                "completed": rep_status in ["ASSIGNED", "IN_PROGRESS", "REPAIRED", "CLOSED"],
                "current": rep_status == "ASSIGNED",
                "actor": "Public Works Dispatch",
                "badge": "Dispatched" if rep_status in ["ASSIGNED", "IN_PROGRESS", "REPAIRED", "CLOSED"] else "Pending Dispatch"
            },
            {
                "step_key": "IN_PROGRESS",
                "title": "5. Active Field Remediation",
                "description": "Road maintenance crew on site performing asphalt cold/hot mix compaction.",
                "timestamp": None,
                "completed": rep_status in ["IN_PROGRESS", "REPAIRED", "CLOSED"],
                "current": rep_status == "IN_PROGRESS",
                "actor": worker_name,
                "badge": "In Progress" if rep_status in ["IN_PROGRESS", "REPAIRED", "CLOSED"] else "Awaiting Crew"
            },
            {
                "step_key": "REPAIRED",
                "title": "6. Repair Proof Submitted",
                "description": "Contractor completed remediation and submitted photo proof of restored road surface.",
                "timestamp": record.get("repair_completed_at"),
                "completed": rep_status in ["REPAIRED", "CLOSED"],
                "current": rep_status == "REPAIRED",
                "actor": worker_name,
                "badge": "Work Completed" if rep_status in ["REPAIRED", "CLOSED"] else "Uncompleted"
            },
            {
                "step_key": "CLOSED",
                "title": "7. Final Municipal Sign-off",
                "description": "Authority inspected repair quality and officially closed the hazard report.",
                "timestamp": record.get("authority_reviewed_at"),
                "completed": rep_status == "CLOSED",
                "current": rep_status == "CLOSED",
                "actor": "Municipal Inspector",
                "badge": "Resolved & Closed" if rep_status == "CLOSED" else "Open"
            }
        ]

        ann_url = f"/outputs/{record.get('annotated_filename')}" if record.get("annotated_filename") else None
        proof_url = record.get("repair_proof_url")

        return {
            "inspection_id": inspection_id,
            "media_filename": record.get("media_filename", "photo.jpg"),
            "current_status": rep_status,
            "location_name": record.get("location", "Location unavailable"),
            "latitude": record.get("latitude"),
            "longitude": record.get("longitude"),
            "severity": record.get("overall_severity", "MINOR"),
            "risk_category": record.get("risk_category", "Low"),
            "potholes_count": p_cnt,
            "cracks_count": c_cnt,
            "assigned_worker": worker_name if worker_email else None,
            "annotated_image_url": ann_url,
            "proof_image_url": proof_url,
            "timeline": steps
        }

progress_service = ProgressService()
