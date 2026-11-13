"""
RoadSentinel - Dedicated Damage Severity Classification Engine
Module: severity_classifier.py

Classifies visual damage severity into four standardized categories:
  - MINOR
  - MODERATE
  - SEVERE
  - CRITICAL

IMPORTANT DISCLAIMER:
  - All severity assessments are purely 2D visual estimates derived from bounding-box
    geometry, relative image area coverage, and defect aspect ratio.
  - This module does NOT measure physical pothole depth, volume, or structural road integrity.
  - Severity classification is mathematically and conceptually separate from the
    Road Hazard Index / Risk Score (which incorporates traffic hazard weights and risk).
  - Do not invent depth or volumetric measurements.
"""

from typing import Dict, List, Any, Tuple, Optional


# ---- Severity Categories & Display Metadata ---------------------------------
SEVERITY_CATEGORIES = ["MINOR", "MODERATE", "SEVERE", "CRITICAL"]

SEVERITY_METADATA = {
    "MINOR": {
        "color_hex": "#28a745",   # Green
        "bgr": (69, 167, 40),
        "emoji": "🟢",
        "description": "Superficial visual distress. Minimal surface degradation."
    },
    "MODERATE": {
        "color_hex": "#ffc107",   # Amber / Yellow
        "bgr": (7, 193, 255),
        "emoji": "🟡",
        "description": "Noticeable visual defect. Surface wear requiring scheduled monitoring."
    },
    "SEVERE": {
        "color_hex": "#fd7e14",   # Orange
        "bgr": (20, 126, 253),
        "emoji": "🟠",
        "description": "Substantial visual road distress. Structural surface compromise."
    },
    "CRITICAL": {
        "color_hex": "#dc3545",   # Red
        "bgr": (69, 53, 220),
        "emoji": "🔴",
        "description": "Extensive visual hazard. High-priority maintenance requirement."
    }
}

# ---- Threshold Configurations (Documented & Configurable) -------------------
#
# Potholes: Visual severity primarily depends on relative area coverage in frame
# and bounding dimension span.
POTHOLE_THRESHOLDS = {
    # (min_relative_area_pct, min_span_pct) -> category
    # relative_area_pct = (box_area / frame_area) * 100
    "critical": {"min_relative_area": 3.0, "min_span": 20.0},
    "severe":   {"min_relative_area": 1.2, "min_span": 12.0},
    "moderate": {"min_relative_area": 0.4, "min_span": 6.0},
    # Below moderate is MINOR
}

# Cracks: Cracks have smaller area but significant length / span across road
# Longitudinal Cracks (parallel to traffic):
LONGITUDINAL_THRESHOLDS = {
    "critical": {"min_span_pct": 35.0, "min_relative_area": 1.5},
    "severe":   {"min_span_pct": 22.0, "min_relative_area": 0.8},
    "moderate": {"min_span_pct": 10.0, "min_relative_area": 0.25},
}

# Transverse Cracks (perpendicular to traffic):
TRANSVERSE_THRESHOLDS = {
    "critical": {"min_span_pct": 30.0, "min_relative_area": 1.2},
    "severe":   {"min_span_pct": 18.0, "min_relative_area": 0.6},
    "moderate": {"min_span_pct": 8.0,  "min_relative_area": 0.2},
}

# Alligator Cracks (fatigue network cracking):
ALLIGATOR_THRESHOLDS = {
    "critical": {"min_relative_area": 4.0, "min_span": 25.0},
    "severe":   {"min_relative_area": 1.8, "min_span": 15.0},
    "moderate": {"min_relative_area": 0.6, "min_span": 8.0},
}


def classify_defect_severity(
    class_name: str,
    box: List[int],
    frame_width: int,
    frame_height: int,
    confidence: Optional[float] = None
) -> Dict[str, Any]:
    """
    Computes visual damage severity classification for a single defect bounding box.

    Parameters
    ----------
    class_name : str
        Canonical defect name ('Pothole', 'Longitudinal Crack', 'Transverse Crack', 'Alligator Crack').
    box : list of int
        [x1, y1, x2, y2] bounding box coordinates.
    frame_width : int
        Width of image/video frame in pixels.
    frame_height : int
        Height of image/video frame in pixels.
    confidence : float, optional
        YOLO detection confidence score (preserved, not modified).

    Returns
    -------
    dict:
        severity_category : str ('MINOR', 'MODERATE', 'SEVERE', 'CRITICAL')
        severity_score    : float (0.0 to 100.0)
        box_width         : int (px)
        box_height        : int (px)
        box_area          : int (px²)
        relative_area_pct : float (area as % of frame area)
        max_span_pct      : float (max(w,h) as % of max frame dimension)
        aspect_ratio      : float (width / height)
        explanation       : str (detailed human-readable explanation)
        confidence        : float or None (original model confidence preserved)
        disclaimer        : str (visual estimate notice)
    """
    x1, y1, x2, y2 = box
    bw = max(1, int(x2 - x1))
    bh = max(1, int(y2 - y1))
    box_area = bw * bh

    fw = max(1, int(frame_width))
    fh = max(1, int(frame_height))
    frame_area = fw * fh

    relative_area_pct = (box_area / frame_area) * 100.0
    relative_area_pct = round(relative_area_pct, 3)

    max_frame_dim = max(fw, fh)
    max_box_dim = max(bw, bh)
    max_span_pct = round((max_box_dim / max_frame_dim) * 100.0, 2)
    aspect_ratio = round(bw / bh, 2)

    c_norm = class_name.strip().title()

    # Rule-based classification based on defect class
    category = "MINOR"
    reasons = []

    if "Pothole" in c_norm:
        t = POTHOLE_THRESHOLDS
        if relative_area_pct >= t["critical"]["min_relative_area"] or max_span_pct >= t["critical"]["min_span"]:
            category = "CRITICAL"
            reasons.append(f"Large surface footprint ({relative_area_pct:.2f}% of frame, span {max_span_pct:.1f}%)")
        elif relative_area_pct >= t["severe"]["min_relative_area"] or max_span_pct >= t["severe"]["min_span"]:
            category = "SEVERE"
            reasons.append(f"Substantial surface cavity ({relative_area_pct:.2f}% of frame, span {max_span_pct:.1f}%)")
        elif relative_area_pct >= t["moderate"]["min_relative_area"] or max_span_pct >= t["moderate"]["min_span"]:
            category = "MODERATE"
            reasons.append(f"Noticeable road pothole ({relative_area_pct:.2f}% of frame, span {max_span_pct:.1f}%)")
        else:
            category = "MINOR"
            reasons.append(f"Minor visual depression ({relative_area_pct:.2f}% of frame, span {max_span_pct:.1f}%)")

    elif "Alligator" in c_norm:
        t = ALLIGATOR_THRESHOLDS
        if relative_area_pct >= t["critical"]["min_relative_area"] or max_span_pct >= t["critical"]["min_span"]:
            category = "CRITICAL"
            reasons.append(f"Extensive fatigue cracking network ({relative_area_pct:.2f}% of frame, span {max_span_pct:.1f}%)")
        elif relative_area_pct >= t["severe"]["min_relative_area"] or max_span_pct >= t["severe"]["min_span"]:
            category = "SEVERE"
            reasons.append(f"Developed alligator pattern ({relative_area_pct:.2f}% of frame, span {max_span_pct:.1f}%)")
        elif relative_area_pct >= t["moderate"]["min_relative_area"] or max_span_pct >= t["moderate"]["min_span"]:
            category = "MODERATE"
            reasons.append(f"Emerging interconnected crack pattern ({relative_area_pct:.2f}% of frame)")
        else:
            category = "MINOR"
            reasons.append(f"Localized fine alligator fissure ({relative_area_pct:.2f}% of frame)")

    elif "Transverse" in c_norm:
        t = TRANSVERSE_THRESHOLDS
        if max_span_pct >= t["critical"]["min_span_pct"] or relative_area_pct >= t["critical"]["min_relative_area"]:
            category = "CRITICAL"
            reasons.append(f"Major transverse fracture spanning {max_span_pct:.1f}% across road corridor")
        elif max_span_pct >= t["severe"]["min_span_pct"] or relative_area_pct >= t["severe"]["min_relative_area"]:
            category = "SEVERE"
            reasons.append(f"Prominent cross-traffic crack (span {max_span_pct:.1f}%, area {relative_area_pct:.2f}%)")
        elif max_span_pct >= t["moderate"]["min_span_pct"] or relative_area_pct >= t["moderate"]["min_relative_area"]:
            category = "MODERATE"
            reasons.append(f"Noticeable transverse fissure (span {max_span_pct:.1f}%)")
        else:
            category = "MINOR"
            reasons.append(f"Hairline or short transverse crack (span {max_span_pct:.1f}%)")

    elif "Longitudinal" in c_norm or "Crack" in c_norm:
        t = LONGITUDINAL_THRESHOLDS
        if max_span_pct >= t["critical"]["min_span_pct"] or relative_area_pct >= t["critical"]["min_relative_area"]:
            category = "CRITICAL"
            reasons.append(f"Extensive longitudinal fracture along wheel path (span {max_span_pct:.1f}%)")
        elif max_span_pct >= t["severe"]["min_span_pct"] or relative_area_pct >= t["severe"]["min_relative_area"]:
            category = "SEVERE"
            reasons.append(f"Significant linear joint separation (span {max_span_pct:.1f}%)")
        elif max_span_pct >= t["moderate"]["min_span_pct"] or relative_area_pct >= t["moderate"]["min_relative_area"]:
            category = "MODERATE"
            reasons.append(f"Moderate longitudinal crack (span {max_span_pct:.1f}%)")
        else:
            category = "MINOR"
            reasons.append(f"Minor longitudinal surface crack (span {max_span_pct:.1f}%)")

    # Map category to a continuous 0-100 severity score
    base_scores = {
        "MINOR": 20.0,
        "MODERATE": 48.0,
        "SEVERE": 75.0,
        "CRITICAL": 92.0
    }
    # Continuous refinement within category based on relative area and span
    factor = min(1.0, (relative_area_pct / 5.0 + max_span_pct / 50.0) / 2.0)
    score_bump = factor * 8.0
    severity_score = round(min(100.0, base_scores[category] + score_bump), 1)

    explanation = "; ".join(reasons)
    disclaimer = (
        "Visual 2D estimate only. Does not measure physical depth, volume, "
        "or structural road sub-base integrity."
    )

    return {
        "severity_category": category,
        "severity_score": severity_score,
        "box_width": bw,
        "box_height": bh,
        "box_area": box_area,
        "relative_area_pct": relative_area_pct,
        "max_span_pct": max_span_pct,
        "aspect_ratio": aspect_ratio,
        "explanation": explanation,
        "confidence": confidence,
        "disclaimer": disclaimer,
    }


def compute_severity_summary(classified_detections: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregates visual damage severity for a list of classified detections.
    """
    breakdown = {"MINOR": 0, "MODERATE": 0, "SEVERE": 0, "CRITICAL": 0}
    scores = []

    for d in classified_detections:
        cat = d.get("severity_category")
        if cat in breakdown:
            breakdown[cat] += 1
        if "severity_score" in d:
            scores.append(d["severity_score"])

    total = len(classified_detections)
    avg_score = round(sum(scores) / total, 1) if scores else 0.0

    # Overall inspection severity rating (highest prevalent category or max)
    if breakdown["CRITICAL"] > 0:
        overall_cat = "CRITICAL"
    elif breakdown["SEVERE"] > 0:
        overall_cat = "SEVERE"
    elif breakdown["MODERATE"] > 0:
        overall_cat = "MODERATE"
    elif total > 0:
        overall_cat = "MINOR"
    else:
        overall_cat = "NONE"

    return {
        "breakdown": breakdown,
        "overall_severity": overall_cat,
        "average_severity_score": avg_score,
        "total_classified": total,
        "disclaimer": (
            "Visual image-based assessment only. Bounding-box area is an optical proxy, "
            "not a structural or volumetric measurement."
        )
    }
