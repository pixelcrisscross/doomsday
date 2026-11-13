"""
RoadSentinel - Road Damage Progress Monitor
Module: progress_monitor.py

Compares inspection reports for the same geographical location over time
to identify whether damage conditions are WORSENING, IMPROVING, or UNCHANGED.

LIMITATIONS (disclosed explicitly):
  - Location matching uses fuzzy string similarity, not GPS coordinates.
    Reports may be mismatched if location text varies between inspections.
  - "Improvement" may reflect detection threshold differences, not real repair.
  - Only considers pothole and total crack counts. Fine-grained crack type
    changes are reported but not weighted in the trend decision.
  - At least 2 comparable reports are required for any trend determination.

Trend labels:
    WORSENING          → damage counts increased significantly
    IMPROVING          → damage counts decreased significantly  
    UNCHANGED          → within ±1 count or ≤ CHANGE_THRESHOLD_PCT change
    INSUFFICIENT_DATA  → fewer than 2 matched reports found
"""

from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import difflib


LOCATION_MATCH_THRESHOLD: float = 0.60   # Min similarity to group as same location
CHANGE_THRESHOLD_PCT: float = 0.20        # ≥20% change → worsening or improving
DATE_FORMATS = [
    "%d %b %Y, %H:%M",
    "%d %b %Y",
    "%Y-%m-%d",
    "%d/%m/%Y",
]


def _parse_date(date_str: str) -> Optional[datetime]:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


def _loc_sim(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _total_damage(report: Dict[str, Any]) -> int:
    return int(report.get("final_potholes", 0)) + int(report.get("final_cracks", 0))


def find_location_history(
    target_location: str,
    dispatch_history: List[Dict[str, Any]],
) -> List[Tuple[int, Dict[str, Any], float]]:
    """
    Finds all dispatch reports whose location string is sufficiently similar
    to target_location.

    Returns
    -------
    List of (original_index, report, similarity_score) sorted oldest-first by date.
    Reports with unparseable dates appear at the end.
    """
    matched: List[Tuple[int, Dict[str, Any], float]] = []
    for idx, rep in enumerate(dispatch_history):
        sim = _loc_sim(target_location, rep.get("location", ""))
        if sim >= LOCATION_MATCH_THRESHOLD:
            matched.append((idx, rep, round(sim, 3)))

    # Sort by date ascending; unparseable dates go last
    def sort_key(item: Tuple[int, Dict[str, Any], float]):
        dt = _parse_date(item[1].get("date", ""))
        return dt if dt is not None else datetime.max

    matched.sort(key=sort_key)
    return matched


def compare_inspections(
    older_report: Dict[str, Any],
    newer_report: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compares two inspection reports (older and newer) for the same location.

    Returns
    -------
    dict with:
        trend           : str   WORSENING | IMPROVING | UNCHANGED | INSUFFICIENT_DATA
        delta_potholes  : int   newer − older (positive = more potholes)
        delta_cracks    : int   newer − older
        delta_total     : int
        older_date      : str
        newer_date      : str
        location_match_warning : bool  (True if locations are similar but not identical)
        notes           : list[str]    — explanations and caveats
    """
    older_potholes = int(older_report.get("final_potholes", 0))
    newer_potholes = int(newer_report.get("final_potholes", 0))
    older_cracks   = int(older_report.get("final_cracks", 0))
    newer_cracks   = int(newer_report.get("final_cracks", 0))

    older_total = older_potholes + older_cracks
    newer_total = newer_potholes + newer_cracks

    delta_potholes = newer_potholes - older_potholes
    delta_cracks   = newer_cracks   - older_cracks
    delta_total    = newer_total    - older_total

    # Determine trend
    if older_total == 0 and newer_total == 0:
        trend = "UNCHANGED"
    elif older_total == 0:
        # Cannot compute percentage from zero baseline
        trend = "WORSENING" if newer_total > 0 else "UNCHANGED"
    else:
        pct_change = delta_total / older_total
        if abs(pct_change) <= CHANGE_THRESHOLD_PCT:
            trend = "UNCHANGED"
        elif pct_change > 0:
            trend = "WORSENING"
        else:
            trend = "IMPROVING"

    # Compose notes
    notes: List[str] = []

    loc_a = older_report.get("location", "")
    loc_b = newer_report.get("location", "")
    loc_sim = _loc_sim(loc_a, loc_b)
    location_match_warning = loc_sim < 1.0

    if location_match_warning:
        notes.append(
            f"⚠️ Location strings differ (similarity {loc_sim:.0%}). "
            "Trend may reflect different road sections, not same-site change."
        )

    if trend == "WORSENING":
        notes.append(
            f"Damage increased: {older_total} → {newer_total} total defects "
            f"(+{delta_total}, {abs(delta_total / older_total):.0%} increase)."
        )
    elif trend == "IMPROVING":
        notes.append(
            f"Damage decreased: {older_total} → {newer_total} total defects "
            f"({abs(delta_total / older_total):.0%} reduction). "
            "Verify that the reduction reflects actual repair, not detection threshold variation."
        )
    elif trend == "UNCHANGED":
        notes.append(
            f"Damage count within ±{int(CHANGE_THRESHOLD_PCT * 100)}% threshold "
            f"({older_total} → {newer_total} defects). No significant change detected."
        )

    if delta_potholes != 0:
        direction = "more" if delta_potholes > 0 else "fewer"
        notes.append(f"Potholes: {older_potholes} → {newer_potholes} ({abs(delta_potholes)} {direction}).")
    if delta_cracks != 0:
        direction = "more" if delta_cracks > 0 else "fewer"
        notes.append(f"Cracks: {older_cracks} → {newer_cracks} ({abs(delta_cracks)} {direction}).")

    notes.append(
        "DISCLAIMER: Comparison is heuristic. Location matching uses text similarity, "
        "not GPS. Detection counts depend on confidence threshold and viewing angle."
    )

    return {
        "trend": trend,
        "delta_potholes": delta_potholes,
        "delta_cracks": delta_cracks,
        "delta_total": delta_total,
        "older_potholes": older_potholes,
        "newer_potholes": newer_potholes,
        "older_cracks": older_cracks,
        "newer_cracks": newer_cracks,
        "older_total": older_total,
        "newer_total": newer_total,
        "older_date": older_report.get("date", "Unknown"),
        "newer_date": newer_report.get("date", "Unknown"),
        "older_location": loc_a,
        "newer_location": loc_b,
        "location_match_warning": location_match_warning,
        "location_similarity": round(loc_sim, 3),
        "notes": notes,
    }


def get_progress_report(
    dispatch_history: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Groups all dispatch history by location clusters and produces a progress
    comparison for each cluster that has ≥ 2 reports.

    Returns list of dicts, each representing one location cluster:
        location_key    : str   (representative location label)
        report_count    : int
        reports         : list of (index, report, sim_score)
        comparison      : compare_inspections result between oldest and newest
        trend_emoji     : str
    """
    TREND_EMOJI = {
        "WORSENING": "📈🔴",
        "IMPROVING": "📉🟢",
        "UNCHANGED": "➡️🟡",
        "INSUFFICIENT_DATA": "❓",
    }

    if not dispatch_history:
        return []

    # Cluster reports into location groups using greedy nearest-neighbor
    clusters: List[List[Tuple[int, Dict[str, Any], float]]] = []
    used_indices = set()

    for idx, rep in enumerate(dispatch_history):
        if idx in used_indices:
            continue
        # Try to find an existing cluster whose representative matches
        placed = False
        for cluster in clusters:
            representative_loc = cluster[0][1].get("location", "")
            sim = _loc_sim(rep.get("location", ""), representative_loc)
            if sim >= LOCATION_MATCH_THRESHOLD:
                cluster.append((idx, rep, round(sim, 3)))
                used_indices.add(idx)
                placed = True
                break
        if not placed:
            clusters.append([(idx, rep, 1.0)])
            used_indices.add(idx)

    results = []
    for cluster in clusters:
        # Sort cluster by date
        def sort_key(item):
            dt = _parse_date(item[1].get("date", ""))
            return dt if dt is not None else datetime.max

        cluster.sort(key=sort_key)
        rep_location = cluster[0][1].get("location", "Unknown")

        if len(cluster) < 2:
            comparison = {
                "trend": "INSUFFICIENT_DATA",
                "notes": ["Only one inspection on record. Need ≥2 reports for trend analysis."],
            }
        else:
            oldest = cluster[0][1]
            newest = cluster[-1][1]
            comparison = compare_inspections(oldest, newest)

        trend = comparison.get("trend", "INSUFFICIENT_DATA")
        results.append({
            "location_key": rep_location,
            "report_count": len(cluster),
            "reports": cluster,
            "comparison": comparison,
            "trend_emoji": TREND_EMOJI.get(trend, "❓"),
        })

    return results
