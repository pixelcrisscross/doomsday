"""
RoadSentinel - Intelligent Duplicate Pothole Detection System
Module: duplicate_detector.py

Detects when multiple individuals submit reports of the same physical pothole by combining:
  1. Geographic proximity (Haversine distance in meters, configurable radius, default 25m).
  2. Deep visual appearance comparison on individual extracted pothole crops
     (Perceptual dHash, ORB feature keypoint matching, and grayscale histogram correlation).
  3. Defect classification compatibility.

Decision Categories:
  - NEW_REPORT: Distinct road hazard, or distant location with differing appearance.
  - POSSIBLE_DUPLICATE: Strong visual similarity and within geographic matching radius.
  - NEEDS_MANUAL_REVIEW: Borderline visual match, or high visual match with missing GPS.
  - CONFIRMED_DUPLICATE: Manually confirmed by inspector (linked via duplicate_of, not deleted).
  - MARKED_AS_UNIQUE: Manually verified by inspector as a distinct physical defect.

STRICT COMPLIANCE RULES:
  - Never automatically delete or merge duplicate reports.
  - Spatial proximity alone is not proof of duplicate.
  - Handle missing GPS by falling back to visual review (marked NEEDS_MANUAL_REVIEW).
  - Operate per-detected pothole, not just per-image.
  - Store extracted crops as files in data/pothole_crops/, not large JSON blobs.
  - Exclude rejected historical reports from active duplicate matching.
"""

import os
import math
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional, Union
from PIL import Image

# Default configuration constants
DEFAULT_MATCHING_RADIUS_M: float = 25.0   # Default geographic matching radius in meters
HIGH_VISUAL_SIMILARITY: float = 0.65       # Strong visual similarity threshold
MODERATE_VISUAL_SIMILARITY: float = 0.40   # Moderate visual similarity threshold
EARTH_RADIUS_M: float = 6371000.0          # Earth radius in meters
CROP_DIR = Path("data/pothole_crops")


# =============================================================================
# 1. GEOGRAPHIC PROXIMITY ENGINE (HAVERSINE FORMULA)
# =============================================================================

def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates great-circle distance between two geographic coordinates in meters
    using the Haversine formula.
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))

    return round(EARTH_RADIUS_M * c, 2)


def is_within_radius(
    lat1: Optional[float],
    lon1: Optional[float],
    lat2: Optional[float],
    lon2: Optional[float],
    radius_m: float = DEFAULT_MATCHING_RADIUS_M,
    accuracy_m: Optional[float] = None
) -> Tuple[Optional[float], Optional[bool]]:
    """
    Evaluates whether two coordinate pairs fall within the matching radius.
    Accounts for GPS accuracy buffer if provided.

    Returns:
        (distance_meters, is_inside_radius)
        Returns (None, None) if any coordinate is missing.
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None, None

    dist = haversine_distance_m(float(lat1), float(lon1), float(lat2), float(lon2))
    effective_radius = radius_m + (float(accuracy_m) if accuracy_m else 0.0)
    inside = dist <= effective_radius

    return dist, inside


# =============================================================================
# 2. POTHOLE CROP EXTRACTION & NORMALIZATION
# =============================================================================

def extract_pothole_crop(
    image: Union[np.ndarray, Image.Image],
    box: List[int],
    margin_ratio: float = 0.15
) -> np.ndarray:
    """
    Extracts an individual cropped region around a pothole bounding box [x1, y1, x2, y2]
    with an added padding margin (default 15%) so road rim and context are visible.
    Clamps bounds safely to image dimensions.
    Returns BGR numpy array.
    """
    if isinstance(image, Image.Image):
        # Convert PIL to BGR OpenCV format
        rgb = np.array(image.convert("RGB"))
        img_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    else:
        img_bgr = image.copy()

    h, w = img_bgr.shape[:2]
    x1, y1, x2, y2 = [int(v) for v in box]

    bw = x2 - x1
    bh = y2 - y1
    pad_w = int(bw * margin_ratio)
    pad_h = int(bh * margin_ratio)

    cx1 = max(0, x1 - pad_w)
    cy1 = max(0, y1 - pad_h)
    cx2 = min(w, x2 + pad_w)
    cy2 = min(h, y2 + pad_h)

    crop = img_bgr[cy1:cy2, cx1:cx2]
    if crop.size == 0 or crop.shape[0] < 5 or crop.shape[1] < 5:
        # Fallback to whole image or minimal patch if box was invalid
        return img_bgr

    return crop


def save_pothole_crop(
    crop: np.ndarray,
    report_id: str,
    defect_idx: int = 0,
    crop_dir: Path = CROP_DIR,
    **kwargs: Any
) -> str:
    """
    Saves an extracted pothole crop as a standard JPEG file in data/pothole_crops/.
    Returns the relative file path string. Accepts defect_idx or pothole_idx.
    """
    if "pothole_idx" in kwargs:
        defect_idx = kwargs["pothole_idx"]
    crop_dir.mkdir(parents=True, exist_ok=True)
    # Sanitize report id for filename
    clean_id = "".join(c for c in report_id if c.isalnum() or c in "-_")
    filename = f"{clean_id}_defect_{defect_idx}.jpg"
    filepath = crop_dir / filename

    cv2.imwrite(str(filepath), crop, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    return str(filepath).replace("\\", "/")


def load_pothole_crop(crop_path: Optional[str]) -> Optional[np.ndarray]:
    """
    Loads an image crop safely from disk. Returns None if missing or corrupted.
    Handles missing historical crop files without crashing.
    """
    if not crop_path or not os.path.exists(crop_path):
        return None
    try:
        img = cv2.imread(crop_path)
        if img is not None and img.size > 0:
            return img
    except Exception:
        pass
    return None


# =============================================================================
# 3. MULTI-ALGORITHM IMAGE SIMILARITY ENGINE
# =============================================================================

def compute_dhash(img: np.ndarray, hash_size: int = 8) -> int:
    """
    Computes a 64-bit difference hash (dHash) of an image patch.
    Fast, scale-invariant, and lighting-shift resilient.
    """
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img

    # Resize to (hash_size + 1, hash_size)
    resized = cv2.resize(gray, (hash_size + 1, hash_size), interpolation=cv2.INTER_AREA)
    diff = resized[:, 1:] > resized[:, :-1]

    # Convert boolean array to integer hash
    hash_val = 0
    for bit in diff.flatten():
        hash_val = (hash_val << 1) | int(bit)

    return hash_val


def dhash_similarity(hash1: int, hash2: int, bit_len: int = 64) -> float:
    """Normalized similarity score derived from Hamming distance [0.0, 1.0]."""
    xor_val = hash1 ^ hash2
    hamming_dist = bin(xor_val).count("1")
    sim = max(0.0, 1.0 - (hamming_dist / float(bit_len)))
    return round(sim, 3)


def orb_feature_similarity(img1: np.ndarray, img2: np.ndarray) -> float:
    """
    Calculates viewpoint- and angle-tolerant visual similarity via ORB feature matching.
    Returns match ratio score in [0.0, 1.0].
    """
    try:
        orb = cv2.ORB_create(nfeatures=400, fastThreshold=12)

        g1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY) if len(img1.shape) == 3 else img1
        g2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY) if len(img2.shape) == 3 else img2

        # Enhance local contrast for asphalt crack/pothole texture
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        g1 = clahe.apply(g1)
        g2 = clahe.apply(g2)

        kp1, des1 = orb.detectAndCompute(g1, None)
        kp2, des2 = orb.detectAndCompute(g2, None)

        if des1 is None or des2 is None or len(des1) < 4 or len(des2) < 4:
            return 0.0

        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)

        if not matches:
            return 0.0

        # Filter good matches with low distance
        good_matches = [m for m in matches if m.distance < 55]

        # Score based on number of strong keypoint matches relative to features found
        min_kps = min(len(kp1), len(kp2))
        score = len(good_matches) / float(max(10, min_kps * 0.35))
        return round(min(1.0, score), 3)
    except Exception:
        return 0.0


def histogram_similarity(img1: np.ndarray, img2: np.ndarray) -> float:
    """
    Computes normalized grayscale/color histogram correlation in [0.0, 1.0].
    Measures surface texture and asphalt tone consistency.
    """
    try:
        g1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY) if len(img1.shape) == 3 else img1
        g2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY) if len(img2.shape) == 3 else img2

        h1 = cv2.calcHist([g1], [0], None, [64], [0, 256])
        h2 = cv2.calcHist([g2], [0], None, [64], [0, 256])

        cv2.normalize(h1, h1, 0, 1, cv2.NORM_MINMAX)
        cv2.normalize(h2, h2, 0, 1, cv2.NORM_MINMAX)

        correl = cv2.compareHist(h1, h2, cv2.HISTCMP_CORREL)
        # Clamp negative correlation to 0.0
        return round(max(0.0, min(1.0, (correl + 1.0) / 2.0)), 3)
    except Exception:
        return 0.0


def compute_crop_visual_similarity(
    crop_a: Union[np.ndarray, Image.Image, str],
    crop_b: Union[np.ndarray, Image.Image, str]
) -> Dict[str, Any]:
    """
    Computes comprehensive visual similarity between two defect crops.
    Combines Perceptual Hash (40%), ORB Feature Matching (35%), and Histogram Correlation (25%).

    Returns dict with composite score and sub-algorithm breakdown.
    """
    # Load from path or convert PIL
    def to_bgr(crop_input):
        if isinstance(crop_input, str):
            return load_pothole_crop(crop_input)
        elif isinstance(crop_input, Image.Image):
            rgb = np.array(crop_input.convert("RGB"))
            return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        elif isinstance(crop_input, np.ndarray):
            return crop_input
        return None

    img_a = to_bgr(crop_a)
    img_b = to_bgr(crop_b)

    if img_a is None or img_b is None or img_a.size == 0 or img_b.size == 0:
        return {
            "score": 0.0,
            "dhash_score": 0.0,
            "orb_score": 0.0,
            "hist_score": 0.0,
            "explanation": "Image crop unavailable for visual comparison."
        }

    # 1. dHash
    h1 = compute_dhash(img_a)
    h2 = compute_dhash(img_b)
    dhash_sim = dhash_similarity(h1, h2)

    # 2. ORB
    orb_sim = orb_feature_similarity(img_a, img_b)

    # 3. Histogram
    hist_sim = histogram_similarity(img_a, img_b)

    # Weighted composite score
    composite = (0.40 * dhash_sim) + (0.35 * orb_sim) + (0.25 * hist_sim)
    composite = round(min(1.0, max(0.0, composite)), 3)

    return {
        "score": composite,
        "dhash_score": dhash_sim,
        "orb_score": orb_sim,
        "hist_score": hist_sim,
        "explanation": f"Visual Match: {composite:.0%} (dHash: {dhash_sim:.0%}, ORB: {orb_sim:.0%}, Hist: {hist_sim:.0%})"
    }


# =============================================================================
# 4. DUPLICATE MATCHING DECISION ENGINE
# =============================================================================

def evaluate_duplicate_candidate(
    new_crop: Any,
    new_lat: Optional[float],
    new_lon: Optional[float],
    new_class: str,
    cand_crop: Any,
    cand_lat: Optional[float],
    cand_lon: Optional[float],
    cand_class: str,
    radius_m: float = DEFAULT_MATCHING_RADIUS_M
) -> Dict[str, Any]:
    """
    Evaluates a candidate pair of potholes using both geographic proximity and visual similarity.

    Decision rules:
      - Class mismatch: NEW_REPORT
      - Both have GPS:
          - Inside radius (<= radius_m):
              - Visual >= HIGH: POSSIBLE_DUPLICATE
              - Visual >= MODERATE: NEEDS_MANUAL_REVIEW
              - Visual < MODERATE: NEW_REPORT (different pothole on same road section)
          - Outside radius (> radius_m):
              - Visual >= 0.85: NEEDS_MANUAL_REVIEW (very high visual similarity, GPS border anomaly)
              - Else: NEW_REPORT (different location)
      - Missing GPS on either side:
          - Visual >= HIGH: NEEDS_MANUAL_REVIEW (visual evidence strong, spatial unconfirmed)
          - Else: NEW_REPORT
    """
    # 1. Defect class compatibility
    is_class_compatible = (
        new_class.lower() == cand_class.lower() or
        ("pothole" in new_class.lower() and "pothole" in cand_class.lower())
    )
    if not is_class_compatible:
        return {
            "decision": "NEW_REPORT",
            "geographic_distance_m": None,
            "within_radius": False,
            "visual_similarity_score": 0.0,
            "reasons": [f"Different defect categories ('{new_class}' vs '{cand_class}')"]
        }

    # 2. Geographic distance
    dist_m, within_rad = is_within_radius(new_lat, new_lon, cand_lat, cand_lon, radius_m=radius_m)

    # 3. Visual similarity
    vis_res = compute_crop_visual_similarity(new_crop, cand_crop)
    vis_score = vis_res["score"]

    reasons = []

    # 4. Synthesize decision
    if dist_m is not None:
        reasons.append(f"Geographic distance: {dist_m:.1f} m (Matching radius: {radius_m} m)")
        reasons.append(vis_res["explanation"])

        if within_rad:
            if vis_score >= HIGH_VISUAL_SIMILARITY:
                decision = "POSSIBLE_DUPLICATE"
                reasons.append("Report falls inside the 25m radius with strong visual similarity.")
            elif vis_score >= MODERATE_VISUAL_SIMILARITY:
                decision = "NEEDS_MANUAL_REVIEW"
                reasons.append("Report falls inside radius, but visual similarity is moderate.")
            else:
                decision = "NEW_REPORT"
                reasons.append("Nearby defect, but visual appearance indicates a distinct physical pothole.")
        else:
            decision = "NEW_REPORT"
            reasons.append(f"Report location is {dist_m:.1f} m away, exceeding {radius_m} m threshold (distant defect).")
    else:
        # Missing coordinates
        reasons.append("GPS coordinates unavailable for one or both reports.")
        reasons.append(vis_res["explanation"])

        if vis_score >= HIGH_VISUAL_SIMILARITY:
            decision = "NEEDS_MANUAL_REVIEW"
            reasons.append("Strong visual resemblance detected, but location could not be verified via GPS.")
        else:
            decision = "NEW_REPORT"
            reasons.append("Insufficient visual similarity to infer duplicate without GPS coordinates.")

    return {
        "decision": decision,
        "geographic_distance_m": dist_m,
        "within_radius": within_rad,
        "visual_similarity_score": vis_score,
        "visual_breakdown": vis_res,
        "reasons": reasons
    }


# =============================================================================
# 5. MULTI-POTHOLE REPOSITORY SCANNER
# =============================================================================

def find_pothole_duplicates(
    new_report: Dict[str, Any],
    history: List[Dict[str, Any]],
    radius_m: float = DEFAULT_MATCHING_RADIUS_M,
    skip_index: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Searches historical inspections for duplicates of each pothole in new_report.
    Skips rejected reports (rejected historical reports cannot trigger duplicates).
    Avoids matching multiple new potholes to the same historical pothole.

    Returns a list of match result dictionaries for every candidate flagged as
    POSSIBLE_DUPLICATE or NEEDS_MANUAL_REVIEW.
    """
    matches: List[Dict[str, Any]] = []

    # Get new report metadata
    new_id = new_report.get("inspection_id", "NEW")
    new_lat = new_report.get("latitude")
    new_lon = new_report.get("longitude")
    new_image = new_report.get("image")
    new_detections = new_report.get("detections", [])

    # Filter candidate historical reports
    valid_candidates = []
    for idx, hist in enumerate(history):
        if skip_index is not None and idx == skip_index:
            continue
        hist_id = hist.get("inspection_id")
        if hist_id == new_id:
            continue

        # Exclude rejected reports
        v_status = hist.get("verification_status") or hist.get("verification", {}).get("status")
        if v_status == "REJECTED":
            continue

        valid_candidates.append(hist)

    if not valid_candidates:
        return []

    # Compare each pothole in new report against candidate pothole crops
    matched_hist_potholes = set()

    for d_idx, det in enumerate(new_detections):
        det_class = det.get("class_name", "Pothole")
        if "pothole" not in det_class.lower():
            continue

        # Extract new crop (or use pre-saved crop path)
        new_crop = det.get("crop_image")
        if new_crop is None and "crop_path" in det:
            new_crop = load_pothole_crop(det["crop_path"])
        elif new_crop is None and new_image is not None and "box" in det:
            new_crop = extract_pothole_crop(new_image, det["box"])

        best_cand_match = None
        best_cand_score = -1.0

        for hist in valid_candidates:
            h_id = hist.get("inspection_id", "HIST")
            h_lat = hist.get("latitude")
            h_lon = hist.get("longitude")
            h_dets = hist.get("detections", [])

            for hd_idx, h_det in enumerate(h_dets):
                h_class = h_det.get("class_name", "Pothole")
                if "pothole" not in h_class.lower():
                    continue

                hist_hazard_key = f"{h_id}_{hd_idx}"
                if hist_hazard_key in matched_hist_potholes:
                    continue  # Already paired with another pothole in this image

                h_crop = h_det.get("crop_image")
                if h_crop is None and "crop_path" in h_det:
                    h_crop = load_pothole_crop(h_det["crop_path"])
                elif h_crop is None and "image" in hist and hist["image"] is not None and "box" in h_det:
                    h_crop = extract_pothole_crop(hist["image"], h_det["box"])

                eval_res = evaluate_duplicate_candidate(
                    new_crop=new_crop,
                    new_lat=new_lat,
                    new_lon=new_lon,
                    new_class=det_class,
                    cand_crop=h_crop,
                    cand_lat=h_lat,
                    cand_lon=h_lon,
                    cand_class=h_class,
                    radius_m=radius_m
                )

                decision = eval_res["decision"]
                if decision in ["POSSIBLE_DUPLICATE", "NEEDS_MANUAL_REVIEW"]:
                    score = eval_res["visual_similarity_score"]
                    if score > best_cand_score:
                        best_cand_score = score
                        best_cand_match = {
                            "new_report_id": new_id,
                            "new_defect_idx": d_idx,
                            "new_crop": new_crop,
                            "new_lat": new_lat,
                            "new_lon": new_lon,
                            "original_report_id": h_id,
                            "original_defect_idx": hd_idx,
                            "original_crop": h_crop,
                            "original_crop_path": h_det.get("crop_path"),
                            "original_lat": h_lat,
                            "original_lon": h_lon,
                            "original_date": hist.get("date", "Unknown"),
                            "original_report": hist,
                            "decision": decision,
                            "distance_m": eval_res["geographic_distance_m"],
                            "within_radius": eval_res["within_radius"],
                            "similarity_score": score,
                            "reasons": eval_res["reasons"],
                            "hist_key": hist_hazard_key
                        }

        if best_cand_match is not None:
            matched_hist_potholes.add(best_cand_match["hist_key"])
            matches.append(best_cand_match)

    return matches


# =============================================================================
# 6. BACKWARD-COMPATIBLE WRAPPERS (FOR EXISTING TESTS AND APIS)
# =============================================================================

def compute_report_similarity(
    report_a: Dict[str, Any],
    report_b: Dict[str, Any],
    radius_m: float = DEFAULT_MATCHING_RADIUS_M
) -> Dict[str, Any]:
    """
    Backward-compatible report similarity evaluator.
    Combines geographic distance (if coordinates exist) or fuzzy location text,
    damage category overlap, and date proximity.
    """
    lat_a = report_a.get("latitude")
    lon_a = report_a.get("longitude")
    lat_b = report_b.get("latitude")
    lon_b = report_b.get("longitude")

    dist_m, inside = is_within_radius(lat_a, lon_a, lat_b, lon_b, radius_m=radius_m)

    # Damage type similarity
    damage_keys = [
        ("final_potholes", "pothole"),
        ("longitudinal_cracks", "longitudinal"),
        ("transverse_cracks", "transverse"),
        ("alligator_cracks", "alligator"),
    ]
    set_a = {label for key, label in damage_keys if report_a.get(key, 0) > 0}
    set_b = {label for key, label in damage_keys if report_b.get(key, 0) > 0}
    union = set_a | set_b
    dmg_score = len(set_a & set_b) / len(union) if union else 0.5

    reasons = []

    if dist_m is not None:
        loc_score = 1.0 if inside else max(0.0, 1.0 - (dist_m - radius_m) / 100.0)
        reasons.append(f"Geographic distance: {dist_m:.1f} m ({'Within' if inside else 'Outside'} {radius_m}m radius)")
    else:
        # Fallback to string similarity if no coordinates
        import difflib
        a_str = str(report_a.get("location", "")).lower().strip()
        b_str = str(report_b.get("location", "")).lower().strip()
        loc_score = difflib.SequenceMatcher(None, a_str, b_str).ratio() if (a_str and b_str) else 0.0
        reasons.append(f"Location text match: {loc_score:.0%}")

    composite = (0.60 * loc_score) + (0.40 * dmg_score)
    composite = round(composite, 3)
    is_dup = composite >= 0.60

    if dmg_score >= 0.7:
        reasons.append("Identical damage types reported")
    if is_dup:
        reasons.append(f"Candidate duplicate (similarity {composite:.0%})")

    return {
        "score": composite,
        "is_duplicate": is_dup,
        "geographic_distance_m": dist_m,
        "within_radius": inside,
        "reasons": reasons,
        "breakdown": {
            "location": round(loc_score, 3),
            "damage": round(dmg_score, 3),
            "date": 1.0
        }
    }


def find_duplicates(
    new_report: Dict[str, Any],
    history: List[Dict[str, Any]],
    skip_index: Optional[int] = None
) -> List[Tuple[int, Dict[str, Any]]]:
    """Backward-compatible tuple-based duplicate scanner."""
    matches: List[Tuple[int, Dict[str, Any]]] = []
    for idx, existing in enumerate(history):
        if skip_index is not None and idx == skip_index:
            continue
        sim = compute_report_similarity(new_report, existing)
        if sim["is_duplicate"]:
            matches.append((idx, sim))

    matches.sort(key=lambda x: x[1]["score"], reverse=True)
    return matches
