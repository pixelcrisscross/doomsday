import sys
from typing import Dict, List, Any
from collections import defaultdict

from backend.app.core.config import PROJECT_ROOT
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import inspection_store as istore
import video_detector as vd

class AnalyticsService:
    @staticmethod
    def get_overview() -> Dict[str, Any]:
        records = istore.load_all_inspections()
        total_inspections = len(records)
        total_potholes = 0
        total_cracks = 0
        unique_hazards = 0

        severity_counts = {"MINOR": 0, "MODERATE": 0, "SEVERE": 0, "CRITICAL": 0}
        risk_counts = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
        verification_counts = {"AI_PENDING": 0, "VERIFIED": 0, "REJECTED": 0}
        duplicate_counts = {
            "NEW_REPORT": 0,
            "POSSIBLE_DUPLICATE": 0,
            "CONFIRMED_DUPLICATE": 0,
            "MARKED_AS_UNIQUE": 0,
            "NEEDS_MANUAL_REVIEW": 0
        }

        for r in records:
            p = r.get("final_potholes", 0) or r.get("yolo_potholes", 0) or 0
            c = r.get("final_cracks", 0) or 0
            total_potholes += p
            total_cracks += c
            
            # Unique hazards
            u = r.get("unique_hazard_count")
            if u is not None:
                unique_hazards += u
            else:
                unique_hazards += p

            # Severity
            sev = r.get("overall_severity", "MINOR")
            if sev in severity_counts:
                severity_counts[sev] += 1
            elif sev != "NONE":
                severity_counts["MINOR"] += 1

            # Risk
            risk = r.get("risk_category", "Low")
            if risk in risk_counts:
                risk_counts[risk] += 1
            elif risk != "None":
                risk_counts["Low"] += 1

            # Verification
            v_status = r.get("verification", {}).get("status", "AI_PENDING")
            if v_status in verification_counts:
                verification_counts[v_status] += 1
            else:
                verification_counts["AI_PENDING"] += 1

            # Duplicate status
            dup_s = r.get("duplicate_status", "NEW_REPORT")
            if dup_s in duplicate_counts:
                duplicate_counts[dup_s] += 1
            else:
                duplicate_counts["NEW_REPORT"] += 1

        device_info = vd.get_device_info()

        return {
            "total_inspections": total_inspections,
            "total_potholes": total_potholes,
            "total_cracks": total_cracks,
            "unique_hazards": unique_hazards,
            "severity_breakdown": severity_counts,
            "risk_distribution": risk_counts,
            "verification_counts": verification_counts,
            "duplicate_counts": duplicate_counts,
            "device_info": device_info
        }

    @staticmethod
    def get_trends() -> List[Dict[str, Any]]:
        records = istore.load_all_inspections()
        # Group by day or month
        grouped = defaultdict(lambda: {"inspections": 0, "potholes": 0, "cracks": 0, "critical_defects": 0})
        
        for r in records:
            # Parse date or default
            date_raw = r.get("date", "Recent")
            # Short key e.g. "14 Nov"
            period = " ".join(date_raw.split()[:2]) if len(date_raw.split()) >= 2 else date_raw
            
            p = r.get("final_potholes", 0) or 0
            c = r.get("final_cracks", 0) or 0
            is_critical = 1 if r.get("overall_severity") == "CRITICAL" else 0

            grouped[period]["inspections"] += 1
            grouped[period]["potholes"] += p
            grouped[period]["cracks"] += c
            grouped[period]["critical_defects"] += is_critical

        result = []
        for period, data in list(grouped.items())[-10:]:
            result.append({
                "period": period,
                **data
            })
        return result

analytics_service = AnalyticsService()
