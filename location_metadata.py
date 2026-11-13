"""
RoadSentinel - GPS, EXIF & Video Location Metadata Engine
Module: location_metadata.py

Provides robust geospatial metadata extraction for inspection photos and videos:
  1. Photo EXIF GPS Extraction (Latitude, Longitude, Altitude, Capture Timestamp, Camera Make/Model)
  2. Reverse geocoding via geopy (with timeout and error handling)
  3. Video GPX Sidecar Parser & Timestamp Synchronizer
  4. Manual Location Entry validation

STRICT COMPLIANCE RULES:
  - NEVER use hardcoded fallback locations.
  - If GPS coordinates cannot be determined, explicitly return "Location unavailable".
  - NEVER use client IP-based geolocation or computer local GPS.
  - Preserve full floating-point coordinate precision without rounding truncation.
"""

import os
import math
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple

from PIL import Image, ExifTags
from geopy.geocoders import Nominatim


def _to_decimal(values: Tuple[float, float, float]) -> float:
    """Converts EXIF (degrees, minutes, seconds) tuple to decimal degrees."""
    d, m, s = values
    return float(d) + float(m) / 60.0 + float(s) / 3600.0


def reverse_geocode(lat: float, lon: float, timeout_sec: int = 5) -> Optional[str]:
    """
    Attempts reverse-geocoding of coordinates via Nominatim.
    Returns human-readable address string or None on failure/timeout.
    """
    try:
        geolocator = Nominatim(user_agent="roadsentinel_ai_engine")
        location = geolocator.reverse(f"{lat}, {lon}", timeout=timeout_sec)
        if location and location.raw:
            address = location.raw.get("address", {})
            parts = []
            for k in ["road", "neighbourhood", "suburb", "city", "county", "state", "country"]:
                val = address.get(k)
                if val and val not in parts:
                    parts.append(val)
            if parts:
                return ", ".join(parts[:4])
            return location.address
    except Exception:
        pass
    return None


def extract_image_location_metadata(img: Image.Image) -> Dict[str, Any]:
    """
    Extracts authentic GPS coordinates, altitude, timestamp, and device metadata from EXIF.

    Returns dict with keys:
        latitude: float or None
        longitude: float or None
        altitude_m: float or None
        capture_timestamp: str or None
        camera_make: str or None
        camera_model: str or None
        address: str ("Location unavailable" if GPS absent)
        location_source: "EXIF" | "UNAVAILABLE"
        has_gps: bool
    """
    result = {
        "latitude": None,
        "longitude": None,
        "altitude_m": None,
        "capture_timestamp": None,
        "camera_make": None,
        "camera_model": None,
        "address": "Location unavailable",
        "location_source": "UNAVAILABLE",
        "has_gps": False
    }

    try:
        exif = img._getexif()
        if not exif:
            return result

        exif_tags = {ExifTags.TAGS.get(k, k): v for k, v in exif.items()}

        # Device info
        result["camera_make"] = exif_tags.get("Make")
        result["camera_model"] = exif_tags.get("Model")

        # Capture timestamp
        capture_time = exif_tags.get("DateTimeOriginal") or exif_tags.get("DateTime")
        if capture_time:
            result["capture_timestamp"] = str(capture_time).strip()

        gps_info = exif_tags.get("GPSInfo")
        if not gps_info:
            return result

        gps_tags = {ExifTags.GPSTAGS.get(k, k): v for k, v in gps_info.items()}

        # Check required tags
        if "GPSLatitude" in gps_tags and "GPSLongitude" in gps_tags:
            lat = _to_decimal(gps_tags["GPSLatitude"])
            lon = _to_decimal(gps_tags["GPSLongitude"])

            if gps_tags.get("GPSLatitudeRef") == "S":
                lat = -lat
            if gps_tags.get("GPSLongitudeRef") == "W":
                lon = -lon

            # Preserve exact full precision floats
            result["latitude"] = lat
            result["longitude"] = lon
            result["has_gps"] = True
            result["location_source"] = "EXIF"

            # Altitude if available
            if "GPSAltitude" in gps_tags:
                try:
                    alt_val = float(gps_tags["GPSAltitude"])
                    if gps_tags.get("GPSAltitudeRef") == b"\x01" or gps_tags.get("GPSAltitudeRef") == 1:
                        alt_val = -alt_val
                    result["altitude_m"] = round(alt_val, 2)
                except Exception:
                    pass

            # Reverse geocode if online, or format coordinate string
            addr = reverse_geocode(lat, lon)
            if addr:
                result["address"] = addr
            else:
                result["address"] = f"GPS: {lat:.6f}, {lon:.6f}"

    except Exception:
        # Gracefully handle unexpected EXIF corruptions
        pass

    return result


def parse_gpx_file(gpx_content_or_path: Any) -> List[Dict[str, Any]]:
    """
    Parses a GPX XML file or string into a chronological list of track points.

    Returns:
        List of dicts:
            latitude: float
            longitude: float
            elevation_m: float or None
            time_dt: datetime or None
            time_epoch: float or None (seconds since epoch)
    """
    track_points: List[Dict[str, Any]] = []

    try:
        if isinstance(gpx_content_or_path, (str, os.PathLike)) and os.path.exists(str(gpx_content_or_path)):
            tree = ET.parse(str(gpx_content_or_path))
            root = tree.getroot()
        elif isinstance(gpx_content_or_path, (str, bytes)):
            root = ET.fromstring(gpx_content_or_path)
        else:
            return []

        # Handle GPX default namespace if present
        ns = ""
        if root.tag.startswith("{"):
            ns = root.tag.split("}")[0] + "}"

        for trkpt in root.iter(f"{ns}trkpt"):
            try:
                lat = float(trkpt.attrib["lat"])
                lon = float(trkpt.attrib["lon"])
                ele_node = trkpt.find(f"{ns}ele")
                time_node = trkpt.find(f"{ns}time")

                ele = float(ele_node.text) if ele_node is not None and ele_node.text else None
                time_dt = None
                time_epoch = None

                if time_node is not None and time_node.text:
                    time_str = time_node.text.strip()
                    # Parse standard ISO formats (e.g. 2026-11-14T08:30:00Z)
                    clean_str = time_str.replace("Z", "+00:00")
                    try:
                        time_dt = datetime.fromisoformat(clean_str)
                        time_epoch = time_dt.timestamp()
                    except Exception:
                        pass

                track_points.append({
                    "latitude": lat,
                    "longitude": lon,
                    "elevation_m": ele,
                    "time_dt": time_dt,
                    "time_epoch": time_epoch
                })
            except Exception:
                continue

    except Exception:
        pass

    return track_points


def match_video_timestamp_to_gpx(
    video_timestamp_sec: float,
    gpx_points: List[Dict[str, Any]],
    sync_offset_sec: float = 0.0
) -> Dict[str, Any]:
    """
    Matches an elapsed video timestamp (in seconds) to a GPX track point.

    Parameters
    ----------
    video_timestamp_sec : float
        Elapsed seconds into the video.
    gpx_points : list of dicts
        Parsed GPX track points chronologically.
    sync_offset_sec : float
        Offset in seconds between video start and GPX track start.
        (e.g., if video started 5 seconds after GPX start, offset is +5.0)

    Returns
    -------
    dict:
        latitude: float or None
        longitude: float or None
        elevation_m: float or None
        sync_quality: 'MATCHED' | 'INTERPOLATED' | 'OUT_OF_RANGE' | 'NO_GPX'
        sync_offset_applied: float
    """
    if not gpx_points:
        return {
            "latitude": None,
            "longitude": None,
            "elevation_m": None,
            "sync_quality": "NO_GPX",
            "sync_offset_applied": sync_offset_sec
        }

    # If GPX points have relative indexing or epoch timestamps
    first_epoch = gpx_points[0].get("time_epoch")
    target_time_relative = video_timestamp_sec + sync_offset_sec

    # Case 1: GPX has valid timestamps
    if first_epoch is not None:
        target_epoch = first_epoch + target_time_relative

        # Check bounds
        last_epoch = gpx_points[-1].get("time_epoch", first_epoch)
        if target_epoch < first_epoch or target_epoch > last_epoch:
            # Nearest clamp with warning
            nearest = gpx_points[0] if target_epoch < first_epoch else gpx_points[-1]
            return {
                "latitude": nearest["latitude"],
                "longitude": nearest["longitude"],
                "elevation_m": nearest.get("elevation_m"),
                "sync_quality": "OUT_OF_RANGE",
                "sync_offset_applied": sync_offset_sec
            }

        # Find bounding points for linear interpolation
        for i in range(len(gpx_points) - 1):
            p1 = gpx_points[i]
            p2 = gpx_points[i + 1]
            t1 = p1.get("time_epoch", first_epoch)
            t2 = p2.get("time_epoch", last_epoch)

            if t1 <= target_epoch <= t2:
                duration = t2 - t1
                if duration <= 0:
                    return {
                        "latitude": p1["latitude"],
                        "longitude": p1["longitude"],
                        "elevation_m": p1.get("elevation_m"),
                        "sync_quality": "MATCHED",
                        "sync_offset_applied": sync_offset_sec
                    }
                alpha = (target_epoch - t1) / duration
                lat_interp = p1["latitude"] + alpha * (p2["latitude"] - p1["latitude"])
                lon_interp = p1["longitude"] + alpha * (p2["longitude"] - p1["longitude"])
                ele_interp = None
                if p1.get("elevation_m") is not None and p2.get("elevation_m") is not None:
                    ele_interp = p1["elevation_m"] + alpha * (p2["elevation_m"] - p1["elevation_m"])

                return {
                    "latitude": lat_interp,
                    "longitude": lon_interp,
                    "elevation_m": ele_interp,
                    "sync_quality": "INTERPOLATED" if 0.05 < alpha < 0.95 else "MATCHED",
                    "sync_offset_applied": sync_offset_sec
                }

    # Case 2: No timestamps in GPX (index based assuming 1 Hz / 1 point per second)
    idx = int(round(target_time_relative))
    if 0 <= idx < len(gpx_points):
        pt = gpx_points[idx]
        return {
            "latitude": pt["latitude"],
            "longitude": pt["longitude"],
            "elevation_m": pt.get("elevation_m"),
            "sync_quality": "MATCHED",
            "sync_offset_applied": sync_offset_sec
        }
    elif idx < 0:
        return {
            "latitude": gpx_points[0]["latitude"],
            "longitude": gpx_points[0]["longitude"],
            "elevation_m": gpx_points[0].get("elevation_m"),
            "sync_quality": "OUT_OF_RANGE",
            "sync_offset_applied": sync_offset_sec
        }
    else:
        return {
            "latitude": gpx_points[-1]["latitude"],
            "longitude": gpx_points[-1]["longitude"],
            "elevation_m": gpx_points[-1].get("elevation_m"),
            "sync_quality": "OUT_OF_RANGE",
            "sync_offset_applied": sync_offset_sec
        }


def format_location_display(
    latitude: Optional[float],
    longitude: Optional[float],
    address: Optional[str] = None
) -> str:
    """
    Standardizes human-readable display of inspection location.
    If coordinates are absent, returns 'Location unavailable'.
    """
    if latitude is None or longitude is None:
        if address and address != "Location unavailable":
            return address
        return "Location unavailable"

    if address and address != "Location unavailable" and not address.startswith("GPS:"):
        return f"{address} ({latitude:.5f}, {longitude:.5f})"

    return f"Lat: {latitude:.6f}, Lon: {longitude:.6f}"
