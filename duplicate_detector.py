"""
RoadSentinel - Duplicate Report Detector
Module: duplicate_detector.py

Compares a new dispatch report against existing history entries to flag
possible duplicate reports of the same physical road hazard.

Matching uses three lightweight heuristics — no GPS coordinates required:
  1. Location string similarity  (difflib SequenceMatcher, weight 0.5)
  2. Damage type overlap         (Jaccard similarity on defect sets, weight 0.3)
  3. Date proximity              (within-7-days window, weight 0.2)

Composite threshold ≥ 0.60 → flagged as "Possible Duplicate".

IMPORTANT: Duplicates are flagged, NOT auto-deleted. Human review is required.
False positives can occur when two distinct defects are genuinely in the same
location and detected on the same day.
"""

import difflib
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional


DUPLICATE_THRESHOLD: float = 0.60    # Composite similarity to flag as duplicate
LOCATION_WEIGHT: float = 0.50
DAMAGE_WEIGHT: float = 0.30
DATE_WEIGHT: float = 0.20
DATE_WINDOW_DAYS: int = 7            # Reports within this window score full date similarity
DATE_FORMATS: List[str] = [
    "%d %b %Y, %H:%M",
    "%d %b %Y",
    "%Y-%m-%d",
    "%d/%m/%Y",
]


def _parse_date(date_str: str) -> Optional[datetime]:
    """Attempts to parse a date string using known formats."""
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


def _location_similarity(loc_a: str, loc_b: str) -> float:
    """
    Fuzzy string similarity between two location strings (0.0–1.0).
    Case-insensitive, strips whitespace.
    """
    a = str(loc_a).lower().strip()
    b = str(loc_b).lower().strip()
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def _damage_type_similarity(rep_a: Dict[str, Any], rep_b: Dict[str, Any]) -> float:
    """
    Jaccard similarity between damage type sets present in two reports.
    A damage type is considered "present" if its count > 0.
    """
    damage_keys = [
        ("final_potholes", "pothole"),
        ("longitudinal_cracks", "longitudinal"),
        ("transverse_cracks", "transverse"),
        ("alligator_cracks", "alligator"),
    ]
    set_a = {label for key, label in damage_keys if rep_a.get(key, 0) > 0}
    set_b = {label for key, label in damage_keys if rep_b.get(key, 0) > 0}

    if not set_a and not set_b:
        return 0.5  # Both empty → neither confirms nor denies similarity
    union = set_a | set_b
    intersection = set_a & set_b
    return len(intersection) / len(union)


def _date_similarity(date_a_str: str, date_b_str: str) -> float:
    """
    Returns 1.0 if dates are within DATE_WINDOW_DAYS, decays linearly to 0.0 at 2× window.
    Returns 0.0 if either date cannot be parsed.
    """
    dt_a = _parse_date(date_a_str)
    dt_b = _parse_date(date_b_str)
    if dt_a is None or dt_b is None:
        return 0.0

    delta_days = abs((dt_a - dt_b).days)
    if delta_days <= DATE_WINDOW_DAYS:
        return 1.0
    if delta_days <= DATE_WINDOW_DAYS * 2:
        return 1.0 - (delta_days - DATE_WINDOW_DAYS) / DATE_WINDOW_DAYS
    return 0.0


def compute_report_similarity(
    report_a: Dict[str, Any],
    report_b: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Computes weighted composite similarity score between two dispatch reports.

    Parameters
    ----------
    report_a, report_b : dicts with keys:
        location (str), date (str), final_potholes (int),
        longitudinal_cracks, transverse_cracks, alligator_cracks (int)

    Returns
    -------
    dict:
        score       : float  0.0–1.0
        is_duplicate: bool   (score >= DUPLICATE_THRESHOLD)
        reasons     : list[str]  — explanation per factor
        breakdown   : dict   { location, damage, date } sub-scores
    """
    loc_score = _location_similarity(
        report_a.get("location", ""), report_b.get("location", "")
    )
    dmg_score = _damage_type_similarity(report_a, report_b)
    date_score = _date_similarity(
        report_a.get("date", ""), report_b.get("date", "")
    )

    composite = (
        LOCATION_WEIGHT * loc_score
        + DAMAGE_WEIGHT * dmg_score
        + DATE_WEIGHT * date_score
    )
    composite = round(composite, 3)
    is_dup = composite >= DUPLICATE_THRESHOLD

    reasons: List[str] = []
    if loc_score >= 0.7:
        reasons.append(f"Location strings are very similar ({loc_score:.0%} match)")
    elif loc_score >= 0.4:
        reasons.append(f"Partial location overlap ({loc_score:.0%} match)")

    if dmg_score >= 0.7:
        reasons.append("Identical damage types reported")
    elif dmg_score >= 0.4:
        reasons.append("Overlapping damage categories")

    if date_score >= 1.0:
        reasons.append(f"Reports within {DATE_WINDOW_DAYS}-day window")
    elif date_score > 0:
        reasons.append("Reports within extended time window")

    if not reasons:
        reasons.append("Low similarity across all factors")

    return {
        "score": composite,
        "is_duplicate": is_dup,
        "reasons": reasons,
        "breakdown": {
            "location": round(loc_score, 3),
            "damage": round(dmg_score, 3),
            "date": round(date_score, 3),
        },
    }


def find_duplicates(
    new_report: Dict[str, Any],
    history: List[Dict[str, Any]],
    skip_index: Optional[int] = None,
) -> List[Tuple[int, Dict[str, Any]]]:
    """
    Compares new_report against each entry in history.
    Returns list of (history_index, similarity_result) for flagged duplicates.

    Parameters
    ----------
    new_report   : report dict to check
    history      : list of existing dispatch report dicts
    skip_index   : optional index in history to exclude (e.g. the report itself)

    Returns
    -------
    List of (index, similarity_dict) tuples where similarity['is_duplicate'] is True,
    sorted descending by score.
    """
    matches: List[Tuple[int, Dict[str, Any]]] = []
    for idx, existing in enumerate(history):
        if skip_index is not None and idx == skip_index:
            continue
        sim = compute_report_similarity(new_report, existing)
        if sim["is_duplicate"]:
            matches.append((idx, sim))

    matches.sort(key=lambda x: x[1]["score"], reverse=True)
    return matches
