import io
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from PIL import Image
import numpy as np

from backend.app.core.config import settings, PROJECT_ROOT, OUTPUTS_DIR, CROPS_DIR
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import video_detector as vd
import duplicate_detector as dd
import severity_classifier as sc
import risk_scorer as rs
import location_metadata as lm
import inspection_store as istore
from backend.app.services.model_service import model_service

class ImageService:
    @staticmethod
    def process_image(
        image_bytes: bytes,
        filename: str,
        confidence: float = 0.20,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        location_source: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Runs complete AI image damage detection pipeline, assesses severity,
        scores risk, checks duplicate reports, and persists to local JSON store.
        """
        # 1. Load image safely
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img_w, img_h = image.size
            if img_w <= 0 or img_h <= 0:
                raise ValueError("Invalid image dimensions")
        except Exception as e:
            raise ValueError(f"Failed to decode image: {e}")

        # 2. Resolve Location
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
        else:
            exif_meta = lm.extract_image_location_metadata(image)
            if exif_meta.get("has_gps"):
                loc_meta = exif_meta

        location_display = loc_meta["address"]

        # 3. Execute YOLO Cascade Prediction
        result, model_used, counts = model_service.cascade_predict(image, conf_threshold=confidence)
        
        rep_id = istore.generate_inspection_id()
        potholes_count = counts.get("potholes", 0)
        longitudinal = counts.get("longitudinal", 0)
        transverse = counts.get("transverse", 0)
        alligator = counts.get("alligator", 0)
        cracks_count = longitudinal + transverse + alligator

        defect_classifications = []
        potholes_list = []

        if result and result.boxes is not None and len(result.boxes) > 0:
            boxes_xyxy = result.boxes.xyxy.cpu().numpy()
            confs = result.boxes.conf.cpu().numpy()
            clss = result.boxes.cls.cpu().numpy().astype(int)

            for b, cf, cid in zip(boxes_xyxy, confs, clss):
                cname = vd.normalize_class_name(result.names.get(cid, str(cid)))
                box_coords = [int(v) for v in b]
                sev = sc.classify_defect_severity(
                    class_name=cname,
                    box=box_coords,
                    frame_width=img_w,
                    frame_height=img_h,
                    confidence=float(cf)
                )
                sev["class_name"] = cname
                sev["box"] = box_coords

                area_px = max(0, (box_coords[2] - box_coords[0])) * max(0, (box_coords[3] - box_coords[1]))
                r_info = rs.compute_risk({
                    "class_name": cname,
                    "confidence": float(cf),
                    "area_pixels": area_px
                })
                sev["risk_score"] = r_info["score"]
                sev["risk_category"] = r_info["category"]

                if cname == "Pothole":
                    p_idx = len(potholes_list)
                    crop_bgr = dd.extract_pothole_crop(image, box_coords, margin_pct=0.15)
                    crop_path = dd.save_pothole_crop(crop_bgr, report_id=rep_id, pothole_idx=p_idx)
                    dhash_val = dd.compute_dhash(crop_bgr)
                    sev["crop_path"] = crop_path
                    sev["crop_image"] = crop_bgr
                    sev["dhash"] = dhash_val
                    potholes_list.append({
                        "pothole_idx": p_idx,
                        "box": box_coords,
                        "crop_path": crop_path,
                        "crop_image": crop_bgr,
                        "dhash": dhash_val,
                        "severity": sev.get("severity_category", "MODERATE"),
                        "status": "NEW_REPORT"
                    })
                defect_classifications.append(sev)

            sev_summary = sc.compute_severity_summary(defect_classifications)
            overall_sev = sev_summary["overall_severity"]
            avg_sev_score = sev_summary["average_severity_score"]
            sev_breakdown = sev_summary["breakdown"]
            annotated_bgr = result.plot()
            annotated_rgb = annotated_bgr[:, :, ::-1]
        else:
            overall_sev = "NONE"
            avg_sev_score = 0.0
            sev_breakdown = {"MINOR": 0, "MODERATE": 0, "SEVERE": 0, "CRITICAL": 0}
            if result is not None:
                annotated_rgb = result.plot()[:, :, ::-1]
            else:
                annotated_rgb = np.array(image)

        # 4. Save Annotated Image to outputs
        annotated_filename = f"annotated_{rep_id}.jpg"
        annotated_path = OUTPUTS_DIR / annotated_filename
        Image.fromarray(annotated_rgb).save(annotated_path, format="JPEG", quality=95)

        # 5. Risk Assessment for whole image
        total_defects = potholes_count + cracks_count
        if total_defects == 0:
            image_risk = "None"
        elif overall_sev == "CRITICAL":
            image_risk = "Critical"
        elif potholes_count >= 3 or overall_sev == "SEVERE":
            image_risk = "High"
        elif potholes_count >= 1 or cracks_count >= 3:
            image_risk = "Medium"
        else:
            image_risk = "Low"

        now = datetime.now()
        date_str = now.strftime("%d %b %Y, %H:%M")
        iso_timestamp = now.isoformat()

        # 6. Build Inspection Record
        inspection_record = {
            "inspection_id": rep_id,
            "type": "Photo Inspection",
            "media_type": "photo",
            "media_filename": filename,
            "annotated_filename": annotated_filename,
            "location": location_display,
            "latitude": loc_meta["latitude"],
            "longitude": loc_meta["longitude"],
            "altitude_m": loc_meta.get("altitude_m"),
            "location_source": loc_meta["location_source"],
            "location_metadata": loc_meta,
            "date": date_str,
            "timestamp": iso_timestamp,
            "final_potholes": potholes_count,
            "final_cracks": cracks_count,
            "longitudinal_cracks": longitudinal,
            "transverse_cracks": transverse,
            "alligator_cracks": alligator,
            "yolo_potholes": potholes_count,
            "gemini_potholes": 0,
            "conflict": False,
            "model_used": model_used,
            "overall_severity": overall_sev,
            "severity_breakdown": sev_breakdown,
            "average_severity_score": avg_sev_score,
            "risk_category": image_risk,
            "detections": defect_classifications,
            "potholes": potholes_list,
            "summary": {
                "pothole_count": potholes_count,
                "crack_count": cracks_count,
                "overall_severity": overall_sev,
                "average_severity_score": avg_sev_score,
                "risk_category": image_risk
            }
        }

        # 7. Duplicate Detection against stored history
        all_inspections = istore.load_all_inspections()
        dup_matches = dd.find_pothole_duplicates(
            inspection_record,
            all_inspections,
            radius_m=25.0
        )
        if dup_matches:
            primary = dup_matches[0]
            inspection_record["duplicate_status"] = primary["decision"]
            inspection_record["duplicate_of"] = primary["original_report_id"]
            inspection_record["duplicate_candidates"] = [
                {
                    "original_report_id": m["original_report_id"],
                    "distance_m": m["distance_m"],
                    "similarity_score": m["similarity_score"],
                    "decision": m["decision"],
                    "reasons": m["reasons"],
                    "original_crop_path": m.get("original_crop_path")
                }
                for m in dup_matches
            ]
        else:
            inspection_record["duplicate_status"] = "NEW_REPORT"
            inspection_record["duplicate_of"] = None
            inspection_record["duplicate_candidates"] = []

        # 8. Save Record to JSON Store
        istore.save_inspection(inspection_record)

        # 9. Format response for API
        clean_detections = []
        for d in defect_classifications:
            clean_detections.append({
                "class_name": d.get("class_name", ""),
                "box": d.get("box", []),
                "confidence": d.get("confidence", 0.0),
                "severity_category": d.get("severity_category", "MODERATE"),
                "severity_score": d.get("severity_score", 0.0),
                "risk_score": d.get("risk_score", 0.0),
                "risk_category": d.get("risk_category", "Low"),
                "crop_path": d.get("crop_path"),
                "dhash": str(d.get("dhash")) if d.get("dhash") is not None else None
            })

        return {
            "inspection_id": rep_id,
            "status": "COMPLETED" if total_defects > 0 else "NO_DEFECTS",
            "model_used": model_used,
            "total_defects": total_defects,
            "potholes": potholes_count,
            "cracks": cracks_count,
            "breakdown": {
                "potholes": potholes_count,
                "longitudinal": longitudinal,
                "transverse": transverse,
                "alligator": alligator
            },
            "overall_severity": overall_sev,
            "average_severity_score": avg_sev_score,
            "risk_category": image_risk,
            "annotated_image_url": f"/outputs/{annotated_filename}",
            "detections": clean_detections,
            "location": location_display,
            "latitude": loc_meta["latitude"],
            "longitude": loc_meta["longitude"],
            "location_source": loc_meta["location_source"],
            "duplicate_status": inspection_record["duplicate_status"],
            "duplicate_of": inspection_record["duplicate_of"],
            "duplicate_candidates": inspection_record["duplicate_candidates"],
            "date": date_str,
            "timestamp": iso_timestamp
        }

image_service = ImageService()
