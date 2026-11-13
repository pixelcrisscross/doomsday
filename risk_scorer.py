"""
RoadSentinel - Heuristic Road Damage Risk Scorer
Module: risk_scorer.py

Computes a transparent, rule-based risk score for each detected road defect
and produces aggregate risk distributions for a set of detections.

DISCLAIMER: This is a heuristic estimate derived from class type, detection
confidence, and bounding-box area. It is NOT a statistically validated
accident probability model. Do not use this score for safety-critical
infrastructure decisions without expert civil engineering validation.

Risk Formula:
    score = CLASS_WEIGHT[class_name] × confidence × area_factor × 100
    area_factor = min(area_pixels / AREA_NORMALIZER, 1.0)

Category thresholds (score 0–100):
    0–24   → Low
    25–49  → Medium
    50–74  → High
    75–100 → Critical
"""

from typing import Dict, List, Any, Tuple


# ---- Configuration -------------------------------------------------------

# Class weights reflect structural severity of each damage type
CLASS_WEIGHTS: Dict[str, float] = {
    "Pothole": 1.0,           # Highest risk — sudden vehicle damage, falls
    "Alligator Crack": 0.85,  # Structural failure indicator
    "Transverse Crack": 0.65, # Moderate — perpendicular to traffic
    "Longitudinal Crack": 0.5 # Lower — parallel to traffic, slower hazard
}
DEFAULT_CLASS_WEIGHT: float = 0.5

# Area normalizer: pixels² considered a "large" defect at standard resolution
# 50 000 px² ≈ 224×224 bbox on a 886×594 frame (≈ medium pothole)
AREA_NORMALIZER: float = 50_000.0

# Score thresholds for category labels
THRESHOLDS: List[Tuple[float, str, str]] = [
    (75.0, "Critical", "🔴"),
    (50.0, "High",     "🟠"),
    (25.0, "Medium",   "🟡"),
    (0.0,  "Low",      "🟢"),
]

# -------------------------------------------------------------------------


def _category(score: float) -> Tuple[str, str]:
    """Maps numeric score to (category_label, emoji)."""
    for threshold, label, emoji in THRESHOLDS:
        if score >= threshold:
            return label, emoji
    return "Low", "🟢"


def compute_risk(detection: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes heuristic risk score for a single detection dict.

    Parameters
    ----------
    detection : dict
        Must contain 'class_name' (str), 'confidence' (float 0-1),
        and 'area_pixels' (int).

    Returns
    -------
    dict with keys:
        score        : float  (0–100)
        category     : str    (Low / Medium / High / Critical)
        emoji        : str
        factors      : list[str]  — human-readable explanation
    """
    class_name = detection.get("class_name", "")
    confidence = float(detection.get("confidence", 0.0))
    area_pixels = int(detection.get("area_pixels", 0))

    class_weight = CLASS_WEIGHTS.get(class_name, DEFAULT_CLASS_WEIGHT)
    area_factor = min(area_pixels / AREA_NORMALIZER, 1.0) if AREA_NORMALIZER > 0 else 0.0

    score = class_weight * confidence * area_factor * 100.0
    score = round(min(score, 100.0), 1)

    category, emoji = _category(score)

    factors = [
        f"Damage type: {class_name} (weight {class_weight:.2f})",
        f"Detection confidence: {confidence:.0%}",
        f"Bounding-box area: {area_pixels:,} px² "
        f"(area factor {area_factor:.2f} of max {int(AREA_NORMALIZER):,} px²)",
        f"Composite heuristic score: {score:.1f}/100 → {category}",
    ]

    return {
        "score": score,
        "category": category,
        "emoji": emoji,
        "factors": factors,
    }


def compute_video_risk_summary(detections: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Scores all detections and returns aggregate risk distribution.

    Parameters
    ----------
    detections : list of detection dicts (must each have risk fields already
                 computed, OR raw detections — this function will score them).

    Returns
    -------
    dict with keys:
        distribution   : dict  { 'Low': n, 'Medium': n, 'High': n, 'Critical': n }
        highest_risk   : dict  { score, category, emoji, detection }
        avg_score      : float
        total_scored   : int
        disclaimer     : str
    """
    distribution: Dict[str, int] = {
        "Low": 0, "Medium": 0, "High": 0, "Critical": 0
    }
    scores: List[float] = []
    highest: Dict[str, Any] = {"score": -1.0}

    for det in detections:
        # Use pre-computed risk if available, else compute now
        if "risk_score" in det:
            risk = {
                "score": det["risk_score"],
                "category": det.get("risk_category", "Low"),
                "emoji": det.get("risk_emoji", "🟢"),
                "factors": det.get("risk_factors", [])
            }
        else:
            risk = compute_risk(det)

        cat = risk["category"]
        if cat in distribution:
            distribution[cat] += 1
        scores.append(risk["score"])

        if risk["score"] > highest["score"]:
            highest = {
                "score": risk["score"],
                "category": risk["category"],
                "emoji": risk["emoji"],
                "detection": det
            }

    avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

    return {
        "distribution": distribution,
        "highest_risk": highest if highest["score"] >= 0 else None,
        "avg_score": avg_score,
        "total_scored": len(detections),
        "disclaimer": (
            "⚠️ Heuristic estimate only. Not a validated accident probability. "
            "Consult qualified engineers before infrastructure decisions."
        ),
    }


def enrich_detection_with_risk(detection: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adds risk fields (risk_score, risk_category, risk_emoji, risk_factors)
    directly to a detection dict. Returns the same dict (mutates in place).
    """
    risk = compute_risk(detection)
    detection["risk_score"] = risk["score"]
    detection["risk_category"] = risk["category"]
    detection["risk_emoji"] = risk["emoji"]
    detection["risk_factors"] = risk["factors"]
    return detection
