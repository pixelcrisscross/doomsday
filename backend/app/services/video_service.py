import os
import sys
import shutil
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from backend.app.core.config import settings, PROJECT_ROOT, OUTPUTS_DIR, UPLOADS_DIR
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import video_detector as vd
import location_metadata as lm
import inspection_store as istore
from backend.app.services.model_service import model_service

class VideoService:
    @staticmethod
    def get_metadata(video_path: str) -> Dict[str, Any]:
        """Validates video and retrieves technical metadata."""
        is_valid, msg = vd.validate_video(video_path)
        if not is_valid:
            raise ValueError(f"Invalid video file: {msg}")
        return vd.get_video_metadata(video_path)

    @staticmethod
    def process_video_upload(
        video_bytes: bytes,
        filename: str,
        confidence: float = 0.20,
        frame_skip: int = 2,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        location_source: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Saves video to uploads directory, executes YOLO inference with hazard tracking,
        generates annotated MP4 video, saves inspection to JSON store.
        """
        # 1. Save uploaded bytes to disk
        stem = Path(filename).stem
        ext = Path(filename).suffix or ".mp4"
        temp_input = UPLOADS_DIR / f"upload_{stem}_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
        with open(temp_input, "wb") as f:
            f.write(video_bytes)

        # 2. Validate
        is_valid, msg = vd.validate_video(str(temp_input))
        if not is_valid:
            if temp_input.exists():
                os.remove(temp_input)
            raise ValueError(f"Video validation failed: {msg}")

        meta = vd.get_video_metadata(str(temp_input))

        # 3. Resolve location
        loc_meta = {
            "latitude": latitude,
            "longitude": longitude,
            "address": "Location unavailable",
            "location_source": location_source or "UNAVAILABLE",
            "has_gps": False
        }
        if latitude is not None and longitude is not None:
            paddr = lm.reverse_geocode(latitude, longitude) or f"GPS: {latitude:.6f}, {longitude:.6f}"
            loc_meta["address"] = paddr
            loc_meta["has_gps"] = True
            if not location_source or location_source == "UNAVAILABLE":
                loc_meta["location_source"] = "DEVICE_GEOLOCATION"

        location_display = loc_meta["address"]

        # 4. Run Video Detection with Tracking
        models = model_service.get_models()
        annotated_path, summary = vd.process_video(
            video_path=str(temp_input),
            output_dir=str(OUTPUTS_DIR),
            models=models,
            conf_threshold=confidence,
            frame_skip=frame_skip
        )

        now = datetime.now()
        date_str = now.strftime("%d %b %Y, %H:%M")
        iso_timestamp = now.isoformat()
        rep_id = istore.generate_inspection_id()

        ann_basename = Path(annotated_path).name if annotated_path else ""

        # 5. Build and save inspection record
        dispatch_entry = {
            "inspection_id": rep_id,
            "type": "Video Inspection",
            "media_type": "video",
            "media_filename": filename,
            "annotated_filename": ann_basename,
            "video_path": annotated_path,
            "location": location_display,
            "latitude": loc_meta["latitude"],
            "longitude": loc_meta["longitude"],
            "altitude_m": None,
            "location_source": loc_meta["location_source"],
            "location_metadata": loc_meta,
            "date": date_str,
            "timestamp": iso_timestamp,
            "final_potholes": summary.get("potholes_count", 0),
            "final_cracks": summary.get("cracks_count", 0),
            "longitudinal_cracks": summary.get("longitudinal_cracks", 0),
            "transverse_cracks": summary.get("transverse_cracks", 0),
            "alligator_cracks": summary.get("alligator_cracks", 0),
            "yolo_potholes": summary.get("potholes_count", 0),
            "gemini_potholes": 0,
            "conflict": False,
            "model_used": "YOLOv8 Multi-Tier",
            "overall_severity": summary.get("overall_severity", "MINOR"),
            "severity_breakdown": summary.get("severity_breakdown", {}),
            "average_severity_score": summary.get("average_severity_score", 0.0),
            "risk_category": summary.get("risk_category", "Low"),
            "risk_distribution": summary.get("risk_distribution", {}),
            "unique_hazard_count": summary.get("unique_hazard_count", 0),
            "total_detections": summary.get("total_detections", 0),
            "table_rows": summary.get("table_rows", []),
            "duplicate_status": "NEW_REPORT",
            "duplicate_of": None,
            "summary": {
                "pothole_count": summary.get("potholes_count", 0),
                "crack_count": summary.get("cracks_count", 0),
                "overall_severity": summary.get("overall_severity", "MINOR"),
                "average_severity_score": summary.get("average_severity_score", 0.0),
                "risk_category": summary.get("risk_category", "Low")
            }
        }

        istore.save_inspection(dispatch_entry)

        return {
            "inspection_id": rep_id,
            "status": "COMPLETED",
            "video_url": f"/outputs/{ann_basename}",
            "download_url": f"/outputs/{ann_basename}",
            "source_metadata": meta,
            "total_detections": summary.get("total_detections", 0),
            "unique_hazard_count": summary.get("unique_hazard_count", 0),
            "potholes_count": summary.get("potholes_count", 0),
            "cracks_count": summary.get("cracks_count", 0),
            "breakdown": {
                "potholes": summary.get("potholes_count", 0),
                "longitudinal": summary.get("longitudinal_cracks", 0),
                "transverse": summary.get("transverse_cracks", 0),
                "alligator": summary.get("alligator_cracks", 0)
            },
            "overall_severity": summary.get("overall_severity", "MINOR"),
            "average_severity_score": summary.get("average_severity_score", 0.0),
            "risk_category": summary.get("risk_category", "Low"),
            "risk_distribution": summary.get("risk_distribution", {}),
            "table_rows": summary.get("table_rows", []),
            "date": date_str,
            "timestamp": iso_timestamp
        }

video_service = VideoService()
