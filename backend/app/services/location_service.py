import sys
from typing import Dict, List, Any, Optional

from backend.app.core.config import PROJECT_ROOT
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import inspection_store as istore
import location_metadata as lm
import duplicate_detector as dd

class LocationService:
    @staticmethod
    def get_damage_points() -> List[Dict[str, Any]]:
        """Returns all inspections that possess authentic GPS coordinates for map plotting."""
        records = istore.load_all_inspections()
        points = []

        for r in records:
            lat = r.get("latitude")
            lon = r.get("longitude")
            if lat is not None and lon is not None:
                try:
                    lat_f = float(lat)
                    lon_f = float(lon)
                    points.append({
                        "inspection_id": r.get("inspection_id", ""),
                        "latitude": lat_f,
                        "longitude": lon_f,
                        "location_name": r.get("location", "Unknown Location"),
                        "location_source": r.get("location_source", "UNAVAILABLE"),
                        "overall_severity": r.get("overall_severity", "MINOR"),
                        "severity_score": r.get("average_severity_score", 0.0),
                        "risk_category": r.get("risk_category", "Low"),
                        "potholes": r.get("final_potholes", 0),
                        "cracks": r.get("final_cracks", 0),
                        "media_type": r.get("media_type", "photo"),
                        "date": r.get("date", ""),
                        "verification_status": r.get("verification", {}).get("status", "AI_PENDING"),
                        "duplicate_status": r.get("duplicate_status", "NEW_REPORT"),
                        "duplicate_of": r.get("duplicate_of"),
                        "repair_status": r.get("repair_status", "REPORTED")
                    })
                except (ValueError, TypeError):
                    continue

        return points

    @staticmethod
    def get_heatmap_points() -> List[Dict[str, Any]]:
        """
        Returns weighted heatmap intensity points for city damage density visualization.
        Intensity is scaled from 0.1 to 1.0 based on pothole volume, severity, and repair status.
        """
        points = LocationService.get_damage_points()
        heatmap = []
        severity_weights = {
            "CRITICAL": 1.0,
            "SEVERE": 0.85,
            "MODERATE": 0.60,
            "MINOR": 0.35,
            "NONE": 0.10
        }

        for p in points:
            sev = p.get("overall_severity", "MINOR")
            base_intensity = severity_weights.get(sev, 0.5)
            pothole_count = p.get("potholes", 1)
            # Volume multiplier
            count_boost = min(0.3, (pothole_count - 1) * 0.1)
            intensity = min(1.0, base_intensity + count_boost)

            # Dampen intensity if already repaired
            rep_status = p.get("repair_status", "REPORTED")
            if rep_status in ["REPAIRED", "CLOSED"]:
                intensity = max(0.15, intensity * 0.3)

            heatmap.append({
                "lat": p["latitude"],
                "lng": p["longitude"],
                "intensity": round(intensity, 2),
                "count": max(1, pothole_count),
                "severity": sev,
                "inspection_id": p["inspection_id"],
                "repair_status": rep_status
            })

        return heatmap

    @staticmethod
    def get_city_summary(city_name: str = "Bengaluru Urban") -> Dict[str, Any]:
        """Calculates total potholes, active hazards, repair status, and completion rate for the city."""
        records = istore.load_all_inspections()
        total_potholes = 0
        active_hazards = 0
        under_repair = 0
        repaired_count = 0
        verified_count = 0
        pending_count = 0

        for r in records:
            p_cnt = r.get("final_potholes", 0)
            total_potholes += p_cnt

            v_status = r.get("verification", {}).get("status", "AI_PENDING")
            if v_status == "VERIFIED":
                verified_count += p_cnt
            elif v_status == "AI_PENDING":
                pending_count += p_cnt

            rep_status = r.get("repair_status", "REPORTED")
            if rep_status in ["ASSIGNED", "IN_PROGRESS"]:
                under_repair += p_cnt
            elif rep_status in ["REPAIRED", "CLOSED"]:
                repaired_count += p_cnt
            else:
                active_hazards += p_cnt

        completion_rate = (repaired_count / total_potholes * 100.0) if total_potholes > 0 else 0.0

        return {
            "city_name": city_name,
            "total_potholes": total_potholes,
            "active_hazards": active_hazards,
            "under_repair": under_repair,
            "repaired_count": repaired_count,
            "verified_count": verified_count,
            "pending_count": pending_count,
            "repair_completion_rate": round(completion_rate, 1)
        }

    @staticmethod
    def reverse_geocode(latitude: float, longitude: float) -> str:
        """Reverse geocodes latitude/longitude coordinates to a road/address name."""
        addr = lm.reverse_geocode(latitude, longitude)
        return addr or f"GPS: {latitude:.6f}, {longitude:.6f}"

    @staticmethod
    def get_geofences() -> List[Dict[str, Any]]:
        """Returns 25m duplicate proximity geofence circles for duplicate candidates."""
        records = istore.load_all_inspections()
        geofences = []

        for r in records:
            lat = r.get("latitude")
            lon = r.get("longitude")
            dup_s = r.get("duplicate_status", "")
            if lat is not None and lon is not None and dup_s in ("POSSIBLE_DUPLICATE", "CONFIRMED_DUPLICATE"):
                geofences.append({
                    "inspection_id": r.get("inspection_id"),
                    "latitude": float(lat),
                    "longitude": float(lon),
                    "radius_m": 25.0,
                    "duplicate_status": dup_s,
                    "duplicate_of": r.get("duplicate_of")
                })

        return geofences

location_service = LocationService()
