"""
RoadSentinel - Lightweight IoU-Based Centroid Tracker
Module: tracker.py

Assigns persistent tracking IDs to road hazard detections across consecutive
video frames using centroid distance + IoU matching. Requires no additional
pip packages beyond numpy (already a project dependency).

Design:
  - New detection → assign next available track_id
  - Existing detection → match to nearest active track by centroid distance
  - Track expires after MAX_MISSED_FRAMES consecutive missed frames
  - unique_count = total distinct track IDs ever assigned during a video

IMPORTANT: This is a heuristic tracker, not a physically validated counter.
Moving camera angles, overlapping objects, and lighting changes can cause
ID switches. The unique count is a lower-bound estimate.
"""

from typing import Dict, List, Any, Optional
import numpy as np


# Configuration constants
MAX_MISSED_FRAMES: int = 10          # Frames before a track is considered lost
MATCH_DISTANCE_PX: float = 90.0     # Max centroid distance (pixels) to match
IOU_MATCH_THRESHOLD: float = 0.20   # Min IoU to prefer IoU over distance-only match


def _centroid(box: List[int]) -> np.ndarray:
    """Returns (cx, cy) centroid of a bounding box [x1, y1, x2, y2]."""
    return np.array([(box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0], dtype=float)


def _iou(box1: List[int], box2: List[int]) -> float:
    """Computes Intersection over Union for two boxes [x1, y1, x2, y2]."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    a1 = max(1, (box1[2] - box1[0]) * (box1[3] - box1[1]))
    a2 = max(1, (box2[2] - box2[0]) * (box2[3] - box2[1]))
    return inter / float(a1 + a2 - inter)


class SimpleTracker:
    """
    Single-class or multi-class road hazard tracker.
    
    Usage:
        tracker = SimpleTracker()
        for frame_dets in all_frame_detections:
            tracked_dets = tracker.update(frame_dets, frame_idx)
            # each detection now has a 'track_id' field
        print(f"Unique hazards tracked: {tracker.unique_count}")
    """

    def __init__(
        self,
        max_missed: int = MAX_MISSED_FRAMES,
        match_dist: float = MATCH_DISTANCE_PX,
        iou_thresh: float = IOU_MATCH_THRESHOLD,
    ) -> None:
        self._next_id: int = 1
        self._max_missed: int = max_missed
        self._match_dist: float = match_dist
        self._iou_thresh: float = iou_thresh

        # Active tracks: { track_id: { 'box', 'centroid', 'class_name', 'missed', 'frame_last_seen' } }
        self._active: Dict[int, Dict[str, Any]] = {}
        self._unique_count: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(
        self, detections: List[Dict[str, Any]], frame_idx: int
    ) -> List[Dict[str, Any]]:
        """
        Match current-frame detections to existing tracks.
        Adds 'track_id' field to each detection dict (mutates in-place copy).
        Returns the list of detections with track_id populated.
        """
        if not detections:
            # Increment missed counter for all active tracks
            self._age_tracks(frame_idx, assigned_ids=set())
            return []

        # Build output list (shallow copies to avoid mutating originals)
        result: List[Dict[str, Any]] = []
        assigned_track_ids: set = set()

        # For each detection, find best matching active track
        for det in detections:
            det_copy = dict(det)
            box = det_copy.get("box", [0, 0, 0, 0])
            c_name = det_copy.get("class_name", "")
            cen = _centroid(box)

            best_id: Optional[int] = None
            best_score: float = float("inf")  # lower = better (distance-based)

            for tid, track in self._active.items():
                if tid in assigned_track_ids:
                    continue
                # Same-class preference (can relax for pothole-only videos)
                if track["class_name"] != c_name:
                    continue

                dist = float(np.linalg.norm(cen - track["centroid"]))
                iou_score = _iou(box, track["box"])

                # Composite score: prefer low distance; boost if IoU is decent
                composite = dist * (0.6 if iou_score >= self._iou_thresh else 1.0)

                if composite < best_score and dist <= self._match_dist:
                    best_score = composite
                    best_id = tid

            if best_id is not None:
                # Update existing track
                self._active[best_id]["box"] = box
                self._active[best_id]["centroid"] = cen
                self._active[best_id]["missed"] = 0
                self._active[best_id]["frame_last_seen"] = frame_idx
                det_copy["track_id"] = best_id
                assigned_track_ids.add(best_id)
            else:
                # Register new track
                new_id = self._next_id
                self._next_id += 1
                self._unique_count += 1
                self._active[new_id] = {
                    "box": box,
                    "centroid": cen,
                    "class_name": c_name,
                    "missed": 0,
                    "frame_last_seen": frame_idx,
                }
                det_copy["track_id"] = new_id
                assigned_track_ids.add(new_id)

            result.append(det_copy)

        # Age out tracks not matched this frame
        self._age_tracks(frame_idx, assigned_ids=assigned_track_ids)
        return result

    @property
    def unique_count(self) -> int:
        """Total distinct road hazard IDs assigned since tracker was created."""
        return self._unique_count

    @property
    def active_track_count(self) -> int:
        """Number of tracks currently active (not yet expired)."""
        return len(self._active)

    def reset(self) -> None:
        """Resets tracker to initial state (call between videos)."""
        self._next_id = 1
        self._active = {}
        self._unique_count = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _age_tracks(self, frame_idx: int, assigned_ids: set) -> None:
        """Increments missed counter for unmatched tracks; prunes expired ones."""
        expired = []
        for tid in list(self._active.keys()):
            if tid not in assigned_ids:
                self._active[tid]["missed"] += 1
                if self._active[tid]["missed"] > self._max_missed:
                    expired.append(tid)
        for tid in expired:
            del self._active[tid]
