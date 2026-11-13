"""
RoadSentinel - Local File-Based Inspection Store
Module: inspection_store.py

Provides structured local JSON persistence for road damage inspection records:
  - File path: data/inspections.json
  - Atomic write via temporary file replacement (prevents corruption)
  - Full CRUD operations: save, get, list, update, delete
  - Preserves original AI predictions alongside human verification corrections
  - Operates 100% offline without database engines or MongoDB

Schema per record:
  - inspection_id: str (e.g. RS-20261114-A1B2)
  - date: str (e.g. 14 Nov 2026)
  - timestamp: str (ISO-8601)
  - media_type: 'photo' | 'video'
  - media_filename: str
  - location: dict (latitude, longitude, altitude, address, location_source, gpx_sync_quality)
  - summary: dict (pothole_count, crack_count, severity_breakdown, overall_severity, risk_category, etc.)
  - detections: list of dicts (box, class, conf, severity_category, severity_score, risk)
  - verification: dict (status, verified_by, verified_at, corrected_class, corrected_severity, rejection_reason, original_ai_prediction)
"""

import os
import json
import uuid
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional


DATA_DIR = Path("data")
DEFAULT_STORE_FILE = DATA_DIR / "inspections.json"

_lock = threading.Lock()


def _ensure_dir(filepath: Path) -> None:
    """Ensures parent directory exists."""
    filepath.parent.mkdir(parents=True, exist_ok=True)


def generate_inspection_id() -> str:
    """Generates human-readable unique inspection ID, e.g. RS-20261114-8F3A2B."""
    now_str = datetime.now().strftime("%Y%m%d")
    short_uuid = uuid.uuid4().hex[:6].upper()
    return f"RS-{now_str}-{short_uuid}"


def load_all_inspections(store_path: Path = DEFAULT_STORE_FILE) -> List[Dict[str, Any]]:
    """
    Reads and returns all inspection records from storage file.
    Returns empty list if file does not exist or is empty.
    """
    with _lock:
        if not store_path.exists():
            return []
        try:
            with open(store_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return []
                data = json.loads(content)
                if isinstance(data, list):
                    return data
                return []
        except Exception:
            return []


def _atomic_write(records: List[Dict[str, Any]], store_path: Path = DEFAULT_STORE_FILE) -> bool:
    """
    Safely writes records to a temporary file in the same directory and replaces target.
    Prevents corrupting the main inspections file if interrupted.
    """
    _ensure_dir(store_path)
    parent = store_path.parent
    try:
        # Create temp file in same directory for atomic replace on POSIX & Windows
        with tempfile.NamedTemporaryFile("w", dir=parent, delete=False, encoding="utf-8") as tf:
            json.dump(records, tf, indent=2, ensure_ascii=False)
            temp_name = tf.name

        # Atomically replace
        if os.path.exists(store_path):
            os.replace(temp_name, store_path)
        else:
            os.rename(temp_name, store_path)
        return True
    except Exception as e:
        if "temp_name" in locals() and os.path.exists(temp_name):
            try:
                os.remove(temp_name)
            except Exception:
                pass
        return False


def save_inspection(
    record: Dict[str, Any],
    store_path: Path = DEFAULT_STORE_FILE
) -> str:
    """
    Inserts a new inspection record into storage.
    Generates an inspection_id if not present.
    Returns the inspection_id.
    """
    with _lock:
        records = []
        if store_path.exists():
            try:
                with open(store_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        records = json.loads(content)
            except Exception:
                records = []

        # Ensure ID and timestamps
        if "inspection_id" not in record or not record["inspection_id"]:
            record["inspection_id"] = generate_inspection_id()

        if "timestamp" not in record or not record["timestamp"]:
            record["timestamp"] = datetime.now().isoformat()

        if "date" not in record or not record["date"]:
            record["date"] = datetime.now().strftime("%d %b %Y, %H:%M")

        # Standardize verification block if missing
        if "verification" not in record:
            record["verification"] = {
                "status": "AI_PENDING",
                "verified_by": None,
                "verified_at": None,
                "corrected_class": None,
                "corrected_severity": None,
                "rejection_reason": None,
                "original_ai_prediction": {
                    "potholes": record.get("summary", {}).get("pothole_count", 0),
                    "cracks": record.get("summary", {}).get("crack_count", 0),
                    "overall_severity": record.get("summary", {}).get("overall_severity", "MINOR")
                }
            }

        records.insert(0, record)  # Newest first
        _atomic_write(records, store_path)
        return record["inspection_id"]


def get_inspection(
    inspection_id: str,
    store_path: Path = DEFAULT_STORE_FILE
) -> Optional[Dict[str, Any]]:
    """Retrieves an inspection record by its unique inspection_id."""
    records = load_all_inspections(store_path)
    for r in records:
        if r.get("inspection_id") == inspection_id:
            return r
    return None


def list_inspections(
    media_type: Optional[str] = None,
    verification_status: Optional[str] = None,
    severity_category: Optional[str] = None,
    store_path: Path = DEFAULT_STORE_FILE
) -> List[Dict[str, Any]]:
    """
    Filters inspection records by media_type, verification_status, or severity.
    """
    records = load_all_inspections(store_path)
    filtered = []
    for r in records:
        if media_type and r.get("media_type") != media_type:
            continue
        v_status = r.get("verification", {}).get("status", "AI_PENDING")
        if verification_status and v_status != verification_status:
            continue
        sev = r.get("summary", {}).get("overall_severity")
        if severity_category and sev != severity_category:
            continue
        filtered.append(r)
    return filtered


def update_inspection(
    inspection_id: str,
    updates: Dict[str, Any],
    store_path: Path = DEFAULT_STORE_FILE
) -> bool:
    """
    Updates fields on an existing inspection record.
    Returns True if record was found and updated, False otherwise.
    """
    with _lock:
        if not store_path.exists():
            return False

        try:
            with open(store_path, "r", encoding="utf-8") as f:
                records = json.loads(f.read())
        except Exception:
            return False

        updated = False
        for i, r in enumerate(records):
            if r.get("inspection_id") == inspection_id:
                # Merge top-level or nested keys
                for k, v in updates.items():
                    if isinstance(v, dict) and isinstance(r.get(k), dict):
                        r[k].update(v)
                    else:
                        r[k] = v
                records[i] = r
                updated = True
                break

        if updated:
            return _atomic_write(records, store_path)
        return False


def delete_inspection(
    inspection_id: str,
    store_path: Path = DEFAULT_STORE_FILE
) -> bool:
    """Deletes an inspection record by ID."""
    with _lock:
        if not store_path.exists():
            return False

        try:
            with open(store_path, "r", encoding="utf-8") as f:
                records = json.loads(f.read())
        except Exception:
            return False

        initial_len = len(records)
        records = [r for r in records if r.get("inspection_id") != inspection_id]

        if len(records) < initial_len:
            return _atomic_write(records, store_path)
        return False


def count_inspections(store_path: Path = DEFAULT_STORE_FILE) -> int:
    """Returns total count of stored inspection records."""
    return len(load_all_inspections(store_path))
