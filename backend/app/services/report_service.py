import io
import csv
import sys
from typing import Dict, List, Any, Optional

from backend.app.core.config import PROJECT_ROOT
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import inspection_store as istore

class ReportService:
    @staticmethod
    def get_reports(
        media_type: Optional[str] = None,
        verification_status: Optional[str] = None,
        severity: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        records = istore.load_all_inspections()
        filtered = []

        for r in records:
            if media_type and r.get("media_type") != media_type:
                continue
            if verification_status:
                v_stat = r.get("verification", {}).get("status", "AI_PENDING")
                if v_stat != verification_status:
                    continue
            if severity and r.get("overall_severity") != severity:
                continue
            if search:
                s = search.lower()
                id_match = s in str(r.get("inspection_id", "")).lower()
                loc_match = s in str(r.get("location", "")).lower()
                if not (id_match or loc_match):
                    continue
            filtered.append(r)

        total = len(filtered)
        paginated = filtered[offset: offset + limit]

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "records": paginated
        }

    @staticmethod
    def get_report_by_id(inspection_id: str) -> Optional[Dict[str, Any]]:
        return istore.get_inspection(inspection_id)

    @staticmethod
    def delete_report(inspection_id: str) -> bool:
        return istore.delete_inspection(inspection_id)

    @staticmethod
    def generate_csv() -> bytes:
        """
        Generates CSV export bytes for all stored inspections using Python stdlib csv.
        No pandas or pyarrow used!
        """
        records = istore.load_all_inspections()
        fieldnames = [
            "Inspection ID", "Type", "Media Filename", "Date", "Location", "Latitude", "Longitude",
            "Location Source", "Potholes", "Cracks", "Longitudinal", "Transverse", "Alligator",
            "Overall Severity", "Avg Severity Score", "Risk", "Verification Status",
            "Verified By", "Rejection Reason", "Corrected Class", "Corrected Severity",
            "Duplicate Status", "Duplicate Of"
        ]

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames)
        writer.writeheader()

        for r in records:
            v = r.get("verification", {})
            writer.writerow({
                "Inspection ID": r.get("inspection_id", ""),
                "Type": r.get("type", "Photo Inspection"),
                "Media Filename": r.get("media_filename", ""),
                "Date": r.get("date", ""),
                "Location": r.get("location", "Location unavailable"),
                "Latitude": r.get("latitude", ""),
                "Longitude": r.get("longitude", ""),
                "Location Source": r.get("location_source", "UNAVAILABLE"),
                "Potholes": r.get("final_potholes", 0),
                "Cracks": r.get("final_cracks", 0),
                "Longitudinal": r.get("longitudinal_cracks", 0),
                "Transverse": r.get("transverse_cracks", 0),
                "Alligator": r.get("alligator_cracks", 0),
                "Overall Severity": r.get("overall_severity", "MINOR"),
                "Avg Severity Score": r.get("average_severity_score", 0.0),
                "Risk": r.get("risk_category", "Low"),
                "Verification Status": v.get("status", "AI_PENDING"),
                "Verified By": v.get("verified_by", ""),
                "Rejection Reason": v.get("rejection_reason", ""),
                "Corrected Class": v.get("corrected_class", ""),
                "Corrected Severity": v.get("corrected_severity", ""),
                "Duplicate Status": r.get("duplicate_status", "NEW_REPORT"),
                "Duplicate Of": r.get("duplicate_of", "")
            })

        return buf.getvalue().encode("utf-8")

report_service = ReportService()
