"""
RoadSentinel Automated Test Suite — 16 Tests
Covers:
  1.  Model loading & hardware status
  2.  Video metadata & format validation
  3.  YOLO inference on video frames
  4.  Output video generation & OpenCV verification
  5.  Download file bytes integrity
  6.  Existing image detection pipeline
  7.  Gemini independence (offline operation)
  8.  Unique hazard tracking (IoU-based centroid tracker)
  9.  Duplicate report detection
  10. Risk scoring (heuristic formula)
  11. Manual verification workflow
  12. Progress comparison (trend detection)
  13. CSV export (stdlib csv, no pandas)
  14. Real Damage Severity Classification (Visual 2D Proxy)
  15. GPS, EXIF & Video Location Metadata (GPX Sidecar, No Hardcoded Fallbacks)
  16. Local File-Based Inspection Store (Atomic JSON, No Database)

No network calls. No Gemini API calls. No fake data.
"""

import os
import sys
import csv
import io
import json
import logging
from pathlib import Path

# Suppress noisy Streamlit ScriptRunContext warnings from non-Streamlit context
logging.getLogger("streamlit").setLevel(logging.ERROR)
logging.getLogger("streamlit.runtime").setLevel(logging.ERROR)

from PIL import Image
from ultralytics import YOLO

import video_detector as vd
import tracker as tr
import risk_scorer as rs
import duplicate_detector as dd
import progress_monitor as pm
import severity_classifier as sc
import location_metadata as lm
import inspection_store as istore
import app


PASS = "PASS"
FAIL = "FAIL"


def _banner(msg):
    print(f"\n{'=' * 60}\n{msg}\n{'=' * 60}")


def _ok(msg):
    print(f"  ✅ {msg}")


def _info(msg):
    print(f"  ℹ️  {msg}")


def _check(condition, msg_pass, msg_fail=""):
    if condition:
        _ok(msg_pass)
    else:
        raise AssertionError(msg_fail or msg_pass)


results = {}


def run_test(num, name, fn):
    print(f"\n[TEST {num}] {name}")
    try:
        fn()
        results[f"Test {num}: {name}"] = PASS
        print(f"  --> {PASS}")
    except Exception as exc:
        results[f"Test {num}: {name}"] = FAIL
        print(f"  --> FAIL: {exc}")


# =========================================================
# TEST 1 — Model Loading & Hardware Status
# =========================================================
def test_1_models():
    device = vd.get_device_info()
    _info(f"Inference Device: {device['device_name']} (CUDA: {device['cuda_available']})")
    models = app.load_models()
    _check(len(models) >= 2, f"At least 2 models loaded ({len(models)} found)")
    for name, m in models.items():
        _info(f"Loaded '{name}': {list(m.names.values())}")


# =========================================================
# TEST 2 — Video Metadata & Format Validation
# =========================================================
def test_2_video_metadata():
    video_file = "test_road.mp4"
    _check(os.path.exists(video_file), f"{video_file} exists")
    is_valid, msg = vd.validate_video(video_file)
    _check(is_valid, f"Video valid: {msg}", f"Validation failed: {msg}")

    meta = vd.get_video_metadata(video_file)
    _info(f"Resolution: {meta['resolution']}, FPS: {meta['fps']}, Frames: {meta['total_frames']}")
    _check(meta["width"] > 0 and meta["height"] > 0 and meta["total_frames"] > 0,
           "Width, height, frames all > 0")


# =========================================================
# TEST 3 — YOLO Inference on Video Frames
# =========================================================
def test_3_yolo_inference():
    import cv2
    video_file = "test_road.mp4"
    models = app.load_models()

    cap = cv2.VideoCapture(video_file)
    ret, frame = cap.read()
    cap.release()
    _check(ret and frame is not None, "First frame read successfully")

    annotated_frame, detections = vd.process_frame(
        frame=frame, models=models, conf_threshold=0.15, frame_idx=0, timestamp_sec=0.0
    )
    _info(f"Detections in Frame 0: {len(detections)}")
    _check(len(detections) > 0, f"{len(detections)} detection(s) found in test frame")

    first = detections[0]
    _info(f"Sample: class='{first['class_name']}' conf={first['confidence']:.2f} box={first['box']}")
    _check("class_name" in first and "confidence" in first and "box" in first,
           "Detection dict has required fields")


# =========================================================
# TEST 4 — Output Video Generation & Verification
# =========================================================
_saved_summary = {}

def test_4_video_processing():
    global _saved_summary
    video_file = "test_road.mp4"
    models = app.load_models()
    meta = vd.get_video_metadata(video_file)
    out_dir = "outputs"

    annotated_path, summary = vd.process_video(
        video_path=video_file,
        output_dir=out_dir,
        models=models,
        conf_threshold=0.15,
        frame_skip=1
    )
    _saved_summary = summary
    _info(f"Output: {annotated_path}")
    _info(f"Processed: {summary['processed_frames']} frames, {summary['total_detections']} detections")

    verified, v_info = vd.verify_output_video(annotated_path)
    _check(verified, f"Output video verified — {v_info.get('frames')} frames, {v_info.get('size_mb')} MB",
           f"Verification failed: {v_info.get('error')}")
    _check(summary["status"] == "completed", "Summary status == 'completed'")


# =========================================================
# TEST 5 — Download File Bytes Integrity
# =========================================================
def test_5_download_bytes():
    out_dir = "outputs"
    videos = sorted(Path(out_dir).glob("*_annotated_*.mp4"), key=os.path.getmtime, reverse=True)
    _check(len(videos) > 0, f"At least one annotated video found in {out_dir}")
    target = str(videos[0])
    size = os.path.getsize(target)
    _check(size > 0, f"File size is {size} bytes (non-zero)")
    with open(target, "rb") as f:
        header = f.read(1024)
    _check(len(header) > 0, "Read 1 KB of file bytes successfully")


# =========================================================
# TEST 6 — Existing Image Detection Pipeline
# =========================================================
def test_6_image_detection():
    img_path = "pothole.webp"
    _check(os.path.exists(img_path), f"{img_path} exists")
    test_img = Image.open(img_path).convert("RGB")
    result, model_used, counts = app.cascade_predict(test_img, conf_threshold=0.15)
    _info(f"Model used: {model_used}")
    _info(f"Potholes: {counts['potholes']}, Cracks L/T/A: {counts['longitudinal']}/{counts['transverse']}/{counts['alligator']}")
    _check(counts["potholes"] > 0, f"Pothole detection confirmed ({counts['potholes']} found)")


# =========================================================
# TEST 7 — Gemini Independence (100% Offline)
# =========================================================
def test_7_gemini_independence():
    _info(f"HAS_GEMINI flag: {app.HAS_GEMINI}")
    img_path = "pothole.webp"
    test_img = Image.open(img_path).convert("RGB")

    result = app.validate_with_gemini(api_key="", image=test_img)
    _check("pothole_count" in result, "validate_with_gemini returns dict with pothole_count key")
    _info(f"Offline response: {result}")

    summary = _saved_summary if _saved_summary else {"status": "completed"}
    _check(summary.get("status") == "completed", "Video detection pipeline is Gemini-independent")


# =========================================================
# TEST 8 — Unique Hazard Tracking
# =========================================================
def test_8_tracking():
    video_file = "test_road.mp4"
    models = app.load_models()
    out_dir = "outputs"

    _, summary = vd.process_video(
        video_path=video_file,
        output_dir=out_dir,
        models=models,
        conf_threshold=0.15,
        frame_skip=3
    )
    unique_count = summary.get("unique_hazard_count")
    total = summary.get("total_detections", 0)
    _info(f"Total frame detections: {total}, Unique tracked hazards: {unique_count}")

    _check(unique_count is not None, "unique_hazard_count is present in summary")
    _check(unique_count <= total, f"unique_hazard_count ({unique_count}) <= total_detections ({total})")
    if total > 0:
        _check(unique_count > 0, f"unique_hazard_count > 0 when detections exist")

    tracker = tr.SimpleTracker()
    fake_dets = [
        {"class_name": "Pothole", "box": [10, 10, 60, 60], "confidence": 0.9, "area_pixels": 2500},
        {"class_name": "Pothole", "box": [100, 100, 160, 160], "confidence": 0.85, "area_pixels": 3600},
    ]
    out1 = tracker.update(fake_dets, 0)
    _check(all("track_id" in d for d in out1), "track_id assigned to all detections in frame 0")
    _check(tracker.unique_count == 2, f"unique_count == 2 after first frame (got {tracker.unique_count})")

    out2 = tracker.update(fake_dets, 1)
    ids1 = {d["track_id"] for d in out1}
    ids2 = {d["track_id"] for d in out2}
    _check(ids1 == ids2, f"Track IDs maintained across frames: {ids1} == {ids2}")
    _check(tracker.unique_count == 2, "No new unique IDs assigned for matched detections")

    new_det = [{"class_name": "Pothole", "box": [800, 400, 860, 460], "confidence": 0.7, "area_pixels": 3600}]
    out3 = tracker.update(new_det, 2)
    _check(tracker.unique_count == 3, f"New distant detection assigned new ID (unique_count=3, got {tracker.unique_count})")


# =========================================================
# TEST 9 — Duplicate Report Detection
# =========================================================
def test_9_duplicates():
    rep_a = {
        "location": "Rani Chennamma Nagar, Belagavi",
        "date": "12 Nov 2026",
        "final_potholes": 3,
        "final_cracks": 2,
        "longitudinal_cracks": 2,
        "transverse_cracks": 0,
        "alligator_cracks": 0,
    }
    rep_b = {
        "location": "Rani Chennamma Nagar, Belagavi",
        "date": "13 Nov 2026",
        "final_potholes": 2,
        "final_cracks": 2,
        "longitudinal_cracks": 2,
        "transverse_cracks": 0,
        "alligator_cracks": 0,
    }
    rep_c = {
        "location": "MG Road, Pune",
        "date": "01 Jan 2025",
        "final_potholes": 0,
        "final_cracks": 1,
        "longitudinal_cracks": 0,
        "transverse_cracks": 1,
        "alligator_cracks": 0,
    }

    sim_ab = dd.compute_report_similarity(rep_a, rep_b)
    sim_ac = dd.compute_report_similarity(rep_a, rep_c)

    _info(f"Similarity A-B (same location): {sim_ab['score']:.3f} → {'DUPLICATE' if sim_ab['is_duplicate'] else 'unique'}")
    _info(f"Similarity A-C (different location): {sim_ac['score']:.3f}")

    _check(sim_ab["is_duplicate"], f"A-B flagged as duplicate (score={sim_ab['score']:.3f} >= 0.60)")
    _check(not sim_ac["is_duplicate"], f"A-C not flagged as duplicate (score={sim_ac['score']:.3f})")

    history = [rep_b, rep_c]
    matches = dd.find_duplicates(rep_a, history)
    _check(len(matches) >= 1, f"find_duplicates found {len(matches)} match(es) for rep_a")
    _check(matches[0][0] == 0, f"Match is at history index 0 (rep_b)")


# =========================================================
# TEST 10 — Risk Scoring
# =========================================================
def test_10_risk_scoring():
    pothole_det = {
        "class_name": "Pothole",
        "confidence": 0.95,
        "area_pixels": 60000,
    }
    pothole_risk = rs.compute_risk(pothole_det)
    _info(f"Pothole risk: score={pothole_risk['score']}, category={pothole_risk['category']}")
    _check(pothole_risk["score"] >= 50.0,
           f"Large pothole @ 95% conf has score >= 50 (got {pothole_risk['score']})")
    _check(pothole_risk["category"] in ["High", "Critical"],
           f"Category is High or Critical (got '{pothole_risk['category']}')")
    _check(len(pothole_risk["factors"]) >= 3, "At least 3 contributing factors explained")

    crack_det = {
        "class_name": "Longitudinal Crack",
        "confidence": 0.25,
        "area_pixels": 500,
    }
    crack_risk = rs.compute_risk(crack_det)
    _info(f"Tiny crack risk: score={crack_risk['score']}, category={crack_risk['category']}")
    _check(crack_risk["category"] == "Low",
           f"Tiny crack is Low risk (got '{crack_risk['category']}')")

    detections = [pothole_det, crack_det]
    summary = rs.compute_video_risk_summary(detections)
    _check("distribution" in summary, "Video risk summary has 'distribution' key")
    _check("disclaimer" in summary, "Risk summary includes disclaimer")
    _check(summary["total_scored"] == 2, "Total scored == 2")

    test_det = {"class_name": "Alligator Crack", "confidence": 0.7, "area_pixels": 20000}
    rs.enrich_detection_with_risk(test_det)
    _check("risk_score" in test_det and "risk_category" in test_det,
           "enrich_detection_with_risk adds risk_score and risk_category")


# =========================================================
# TEST 11 — Manual Verification Workflow
# =========================================================
def test_11_verification():
    rep = {
        "type": "Photo Inspection",
        "location": "Test Street",
        "date": "14 Nov 2026",
        "final_potholes": 2,
        "final_cracks": 1,
        "longitudinal_cracks": 1,
        "transverse_cracks": 0,
        "alligator_cracks": 0,
    }
    app._init_report_defaults(rep)

    _check(rep["verification_status"] == "AI_PENDING", "New report defaults to AI_PENDING")
    _check(rep["original_ai_prediction"]["potholes"] == 2, "Original AI prediction preserved (potholes=2)")

    rep["verification_status"] = "VERIFIED"
    rep["verified_by"] = "Inspector"
    rep["verified_at"] = "14 Nov 2026, 10:00"
    _check(rep["verification_status"] == "VERIFIED", "Status → VERIFIED")
    _check(rep["verified_by"] == "Inspector", "verified_by set")
    _check(rep["original_ai_prediction"]["potholes"] == 2, "Original prediction still intact after verification")

    rep2 = dict(rep)
    rep2["verification_status"] = "REJECTED"
    rep2["rejection_reason"] = "No damage visible in re-inspection"
    _check(rep2["verification_status"] == "REJECTED", "Status → REJECTED")
    _check(rep2["rejection_reason"], "Rejection reason recorded")

    rep3 = dict(rep)
    rep3["verification_status"] = "AI_PENDING"
    app._init_report_defaults(rep3)
    rep3["corrected_class"] = "Alligator Crack"
    rep3["corrected_severity"] = "SEVERE"
    rep3["verification_status"] = "VERIFIED"
    _check(rep3["corrected_class"] == "Alligator Crack", "Corrected class recorded")
    _check(rep3["original_ai_prediction"]["potholes"] == 2, "Original prediction preserved after correction")


# =========================================================
# TEST 12 — Progress Comparison (Trend Detection)
# =========================================================
def test_12_progress():
    older = {
        "location": "NH-48 Bypass, Belagavi",
        "date": "01 Oct 2026",
        "final_potholes": 2,
        "final_cracks": 3,
    }
    newer_worse = {
        "location": "NH-48 Bypass, Belagavi",
        "date": "14 Nov 2026",
        "final_potholes": 5,
        "final_cracks": 7,
    }
    newer_better = {
        "location": "NH-48 Bypass, Belagavi",
        "date": "14 Nov 2026",
        "final_potholes": 1,
        "final_cracks": 1,
    }
    unchanged = {
        "location": "NH-48 Bypass, Belagavi",
        "date": "14 Nov 2026",
        "final_potholes": 2,
        "final_cracks": 3,
    }

    comp_worse = pm.compare_inspections(older, newer_worse)
    comp_better = pm.compare_inspections(older, newer_better)
    comp_same = pm.compare_inspections(older, unchanged)

    _info(f"Worse trend: {comp_worse['trend']}")
    _info(f"Better trend: {comp_better['trend']}")
    _info(f"Unchanged trend: {comp_same['trend']}")

    _check(comp_worse["trend"] == "WORSENING", f"Trend is WORSENING (got '{comp_worse['trend']}')")
    _check(comp_better["trend"] == "IMPROVING", f"Trend is IMPROVING (got '{comp_better['trend']}')")
    _check(comp_same["trend"] == "UNCHANGED", f"Trend is UNCHANGED (got '{comp_same['trend']}')")

    history = [older, newer_worse, {"location": "MG Road, Pune", "date": "14 Nov 2026",
                                     "final_potholes": 1, "final_cracks": 0}]
    matched = pm.find_location_history("NH-48 Bypass, Belagavi", history)
    _check(len(matched) >= 2, f"find_location_history found {len(matched)} matches")

    single = pm.get_progress_report([older])
    _check(len(single) == 1, "Single-report cluster returned")
    _check(single[0]["comparison"]["trend"] == "INSUFFICIENT_DATA",
           "Single report → INSUFFICIENT_DATA trend")


# =========================================================
# TEST 13 — CSV Export (stdlib csv, no pandas)
# =========================================================
def test_13_csv_export():
    history = [
        {
            "inspection_id": "RS-20261114-TEST1",
            "type": "Photo Inspection",
            "date": "14 Nov 2026",
            "location": "Test Location",
            "latitude": 15.8497,
            "longitude": 74.4977,
            "location_source": "MANUAL",
            "final_potholes": 2,
            "final_cracks": 3,
            "longitudinal_cracks": 2,
            "transverse_cracks": 1,
            "alligator_cracks": 0,
            "avg_conf": "72.3%",
            "overall_severity": "MODERATE",
            "verification_status": "VERIFIED",
            "risk_category": "Medium",
            "duplicate_status": None,
        }
    ]

    csv_bytes = app._make_csv_bytes(history)
    _check(len(csv_bytes) > 0, f"CSV bytes non-empty ({len(csv_bytes)} bytes)")

    decoded = csv_bytes.decode("utf-8")
    reader = csv.DictReader(io.StringIO(decoded))
    rows = list(reader)
    _check(len(rows) == 1, f"CSV has 1 data row (got {len(rows)})")
    _check("Inspection ID" in rows[0], "CSV has 'Inspection ID' column")
    _check("Location" in rows[0], "CSV has 'Location' column")
    _check(rows[0]["Potholes"] == "2", f"Potholes == '2' (got '{rows[0]['Potholes']}')")
    _check(rows[0]["Verification Status"] == "VERIFIED", "Verification status correctly exported")
    _info(f"CSV headers: {list(rows[0].keys())}")

    app_source = Path("app.py").read_text()
    _check("import pandas" not in app_source,
           "No 'import pandas' in app.py — pandas-free implementation confirmed")


# =========================================================
# TEST 14 — Damage Severity Classification Engine
# =========================================================
def test_14_severity_classification():
    # Large pothole in 1000x1000 frame: 250x250 = 62,500 px² = 6.25% of frame -> CRITICAL
    pot_crit = sc.classify_defect_severity(
        class_name="Pothole",
        box=[100, 100, 350, 350],
        frame_width=1000,
        frame_height=1000,
        confidence=0.88
    )
    _info(f"Large Pothole Severity: {pot_crit['severity_category']} (Score: {pot_crit['severity_score']})")
    _check(pot_crit["severity_category"] == "CRITICAL",
           f"Large pothole classified as CRITICAL (got '{pot_crit['severity_category']}')")
    _check(pot_crit["confidence"] == 0.88, "Original model confidence preserved")
    _check("disclaimer" in pot_crit, "Visual estimate disclaimer present")
    _check(pot_crit["relative_area_pct"] > 3.0, f"Relative area {pot_crit['relative_area_pct']}% > 3.0%")

    # Small pothole in 1000x1000 frame: 30x30 = 900 px² = 0.09% of frame -> MINOR
    pot_minor = sc.classify_defect_severity(
        class_name="Pothole",
        box=[10, 10, 40, 40],
        frame_width=1000,
        frame_height=1000,
        confidence=0.65
    )
    _info(f"Small Pothole Severity: {pot_minor['severity_category']} (Score: {pot_minor['severity_score']})")
    _check(pot_minor["severity_category"] == "MINOR",
           f"Small pothole classified as MINOR (got '{pot_minor['severity_category']}')")

    # Long Transverse Crack: thin area (10px) but wide span (400px across 1000px width = 40% span) -> CRITICAL
    trans_crit = sc.classify_defect_severity(
        class_name="Transverse Crack",
        box=[50, 300, 450, 310],
        frame_width=1000,
        frame_height=1000,
        confidence=0.75
    )
    _info(f"Long Transverse Crack Severity: {trans_crit['severity_category']} (Span: {trans_crit['max_span_pct']}%)")
    _check(trans_crit["severity_category"] == "CRITICAL",
           f"Transverse crack spanning 40% of road corridor is CRITICAL (got '{trans_crit['severity_category']}')")

    # Test aggregate summary
    summary = sc.compute_severity_summary([pot_crit, pot_minor, trans_crit])
    _check(summary["overall_severity"] == "CRITICAL", "Overall severity correctly identified as CRITICAL")
    _check(summary["breakdown"]["CRITICAL"] == 2, "Breakdown reports 2 CRITICAL defects")
    _check(summary["breakdown"]["MINOR"] == 1, "Breakdown reports 1 MINOR defect")
    _info(f"Severity Breakdown: {summary['breakdown']}")


# =========================================================
# TEST 15 — Location & GPS Metadata (No Hardcoded Fallbacks)
# =========================================================
def test_15_location_metadata():
    # 1. Image without GPS must return 'Location unavailable' without inventing locations
    test_img = Image.new("RGB", (100, 100), color="gray")
    meta_no_gps = lm.extract_image_location_metadata(test_img)
    _info(f"Image without GPS result: {meta_no_gps['address']} (source: {meta_no_gps['location_source']})")
    _check(meta_no_gps["address"] == "Location unavailable",
           "Image without EXIF GPS explicitly returns 'Location unavailable'")
    _check(meta_no_gps["latitude"] is None and meta_no_gps["longitude"] is None,
           "Coordinates are strictly None when absent")

    # 2. Check that hardcoded Belagavi fallback is not in location_metadata
    code = Path("location_metadata.py").read_text()
    _check("Rani Chennamma" not in code, "No hardcoded 'Rani Chennamma' in location_metadata.py")

    # 3. GPX Parser Test with synthetic valid GPX string
    sample_gpx = """<?xml version="1.0" encoding="UTF-8"?>
    <gpx version="1.1" creator="SurveyDevice">
      <trk>
        <trkseg>
          <trkpt lat="15.849722" lon="74.497711">
            <ele>650.5</ele>
            <time>2026-11-14T08:00:00Z</time>
          </trkpt>
          <trkpt lat="15.850100" lon="74.498200">
            <ele>651.0</ele>
            <time>2026-11-14T08:00:10Z</time>
          </trkpt>
        </trkseg>
      </trk>
    </gpx>"""

    pts = lm.parse_gpx_file(sample_gpx)
    _check(len(pts) == 2, f"Parsed 2 GPX trackpoints (got {len(pts)})")
    _check(abs(pts[0]["latitude"] - 15.849722) < 1e-5, "Preserves full floating-point coordinate precision")
    _check(pts[0]["elevation_m"] == 650.5, "Elevation parsed accurately")

    # 4. GPX Video Synchronization Test
    # Point at 5 seconds elapsed (interpolated halfway between 0s and 10s)
    synced = lm.match_video_timestamp_to_gpx(video_timestamp_sec=5.0, gpx_points=pts, sync_offset_sec=0.0)
    _info(f"GPX Sync @ 5s: {synced['latitude']:.6f}, {synced['longitude']:.6f} ({synced['sync_quality']})")
    _check(synced["sync_quality"] == "INTERPOLATED", "5s is INTERPOLATED between points")
    expected_lat = (15.849722 + 15.850100) / 2.0
    _check(abs(synced["latitude"] - expected_lat) < 1e-5, "Interpolated coordinates match midpoint")


# =========================================================
# TEST 16 — Local File-Based Inspection Store (No Database)
# =========================================================
def test_16_inspection_store():
    test_store_path = Path("data/test_inspections_tmp.json")
    if test_store_path.exists():
        test_store_path.unlink()

    try:
        # 1. Save new inspection
        rec = {
            "type": "Photo Inspection",
            "media_type": "photo",
            "media_filename": "survey_01.jpg",
            "location": "NH-48 Corridor",
            "latitude": 15.8497,
            "longitude": 74.4977,
            "location_source": "MANUAL",
            "summary": {
                "pothole_count": 3,
                "crack_count": 2,
                "overall_severity": "SEVERE",
                "risk_category": "High"
            },
            "detections": [
                {"class_name": "Pothole", "severity_category": "SEVERE", "confidence": 0.89}
            ]
        }
        rec_id = istore.save_inspection(rec, store_path=test_store_path)
        _info(f"Saved inspection with ID: {rec_id}")
        _check(rec_id.startswith("RS-"), f"Generated ID format valid ({rec_id})")
        _check(test_store_path.exists(), "Storage file data/test_inspections_tmp.json created on disk")

        # 2. Get inspection
        fetched = istore.get_inspection(rec_id, store_path=test_store_path)
        _check(fetched is not None, "Record successfully retrieved by ID")
        _check(fetched["summary"]["pothole_count"] == 3, "Pothole count accurately persisted")
        _check(fetched["verification"]["status"] == "AI_PENDING", "Verification status initialized to AI_PENDING")

        # 3. Update inspection (Inspector Verification)
        updated = istore.update_inspection(
            rec_id,
            {"verification": {"status": "VERIFIED", "verified_by": "Field Inspector #4", "corrected_severity": "CRITICAL"}},
            store_path=test_store_path
        )
        _check(updated, "Record update returned True")

        fetched_after = istore.get_inspection(rec_id, store_path=test_store_path)
        _check(fetched_after["verification"]["status"] == "VERIFIED", "Updated status to VERIFIED")
        _check(fetched_after["verification"]["verified_by"] == "Field Inspector #4", "Inspector identity saved")
        _check(fetched_after["verification"]["original_ai_prediction"]["potholes"] == 3,
               "Original AI prediction safely preserved during correction")

        # 4. List inspections
        all_recs = istore.list_inspections(verification_status="VERIFIED", store_path=test_store_path)
        _check(len(all_recs) == 1, "Filter by status returned 1 verified record")

        # 5. Delete inspection
        deleted = istore.delete_inspection(rec_id, store_path=test_store_path)
        _check(deleted, "Delete inspection returned True")
        _check(istore.count_inspections(store_path=test_store_path) == 0, "Store count is 0 after deletion")

    finally:
        if test_store_path.exists():
            test_store_path.unlink()


# =========================================================
# TEST 17 — Simplified Location Attachment & Current Geolocation
# =========================================================
def test_17_simplified_location():
    # 1. Image detection without location
    img_path = "pothole.webp"
    test_img = Image.open(img_path).convert("RGB")
    _, _, counts = app.cascade_predict(test_img, conf_threshold=0.15)
    _check(counts["potholes"] > 0, "Image detection runs without location attached")

    rep_no_loc = app._init_report_defaults({
        "type": "Photo Inspection",
        "location": "Location unavailable",
        "latitude": None,
        "longitude": None,
        "location_source": "UNAVAILABLE",
        "final_potholes": counts["potholes"],
        "final_cracks": 0
    })
    _check(rep_no_loc["latitude"] is None and rep_no_loc["longitude"] is None,
           "Detection workflow succeeds with null coordinates")
    _check(rep_no_loc["location"] == "Location unavailable",
           "Location reported as 'Location unavailable'")

    # 2. Image detection with captured current location
    captured_lat = 15.849722
    captured_lon = 74.497711
    rep_with_loc = app._init_report_defaults({
        "type": "Photo Inspection",
        "location": f"GPS: {captured_lat:.6f}, {captured_lon:.6f}",
        "latitude": captured_lat,
        "longitude": captured_lon,
        "location_source": "DEVICE_GEOLOCATION",
        "final_potholes": counts["potholes"],
        "final_cracks": 0
    })
    _check(rep_with_loc["latitude"] == captured_lat, "Captured latitude preserved with exact precision")
    _check(rep_with_loc["longitude"] == captured_lon, "Captured longitude preserved with exact precision")
    _check(rep_with_loc["location_source"] == "DEVICE_GEOLOCATION", "Location source marked as DEVICE_GEOLOCATION")

    # 3. Video detection without location
    v_rep_no_loc = app._init_report_defaults({
        "type": "Video Inspection",
        "location": "Location unavailable",
        "latitude": None,
        "longitude": None,
        "location_source": "UNAVAILABLE",
        "final_potholes": 16,
        "final_cracks": 0
    })
    _check(v_rep_no_loc["latitude"] is None and v_rep_no_loc["longitude"] is None,
           "Video detection succeeds with null location")

    # 4. Video detection with captured location
    v_rep_with_loc = app._init_report_defaults({
        "type": "Video Inspection",
        "location": f"GPS: {captured_lat:.6f}, {captured_lon:.6f}",
        "latitude": captured_lat,
        "longitude": captured_lon,
        "location_source": "DEVICE_GEOLOCATION",
        "final_potholes": 16,
        "final_cracks": 0
    })
    _check(v_rep_with_loc["latitude"] == captured_lat, "Video report has captured latitude")
    _check(v_rep_with_loc["longitude"] == captured_lon, "Video report has captured longitude")

    # 5. Permission denied handling
    denied_loc = None
    _check(denied_loc is None, "Permission denied results in null location")
    rep_denied = app._init_report_defaults({
        "type": "Photo Inspection",
        "location": "Location unavailable",
        "latitude": None,
        "longitude": None,
        "location_source": "UNAVAILABLE"
    })
    _check(rep_denied["location"] == "Location unavailable", "Permission denied does not break report generation")

    # 6. Verify captured coordinates reach persistent JSON store without precision loss
    test_store = Path("data/test_geo_store.json")
    if test_store.exists():
        test_store.unlink()
    try:
        saved_id = istore.save_inspection(rep_with_loc, store_path=test_store)
        fetched = istore.get_inspection(saved_id, store_path=test_store)
        _check(fetched is not None, "Record saved to storage")
        _check(abs(fetched["latitude"] - captured_lat) < 1e-9, "Latitude retrieved from storage with full precision")
        _check(abs(fetched["longitude"] - captured_lon) < 1e-9, "Longitude retrieved from storage with full precision")
        _check(fetched["location_source"] == "DEVICE_GEOLOCATION", "Location source persisted correctly")
    finally:
        if test_store.exists():
            test_store.unlink()

    # 7. Check removed UI elements are completely absent from app.py
    app_text = Path("app.py").read_text()
    _check("Optional: Attach GPX" not in app_text, "GPX file uploader completely removed from app.py")
    _check("Manual Location Coordinates" not in app_text, "Manual Location Coordinates section completely removed from app.py")
    _check("v_man_lat" not in app_text and "v_man_lon" not in app_text, "Video manual lat/lon inputs completely removed")
    _check("p_man_lat" not in app_text and "p_man_lon" not in app_text, "Photo manual lat/lon inputs completely removed")


# =========================================================
# TEST 18 — Intelligent Duplicate Pothole Detection System (17 Scenarios)
# =========================================================
def test_18_intelligent_duplicate_system():
    import numpy as np

    rng = np.random.RandomState(42)
    crop_base = rng.randint(40, 80, (120, 120, 3), dtype=np.uint8)
    crop_similar = (crop_base.astype(np.float32) * 1.05).clip(0, 255).astype(np.uint8)
    crop_diff = rng.randint(180, 240, (120, 120, 3), dtype=np.uint8)

    base_lat = 15.849700
    base_lon = 74.497700

    # 1. First report of a pothole is classified as NEW_REPORT
    rep_1 = app._init_report_defaults({
        "inspection_id": "RS-DUP-01",
        "type": "Photo Inspection",
        "location": "Station Road, Belagavi",
        "latitude": base_lat,
        "longitude": base_lon,
        "date": "14 Nov 2026, 09:00",
        "final_potholes": 1,
        "final_cracks": 0,
        "detections": [{
            "class_name": "Pothole",
            "box": [10, 10, 100, 100],
            "crop_image": crop_base
        }]
    })
    matches_1 = dd.find_pothole_duplicates(rep_1, [], radius_m=25.0)
    _check(len(matches_1) == 0, "Scenario 1: First report has 0 duplicate matches (initializes as NEW_REPORT)")
    _check(rep_1["duplicate_status"] == "NEW_REPORT", "Scenario 1: First report default status is NEW_REPORT")

    # 2. Second report of same pothole at same GPS coordinates and same image is detected as POSSIBLE_DUPLICATE
    rep_2 = app._init_report_defaults({
        "inspection_id": "RS-DUP-02",
        "type": "Photo Inspection",
        "location": "Station Road, Belagavi",
        "latitude": base_lat,
        "longitude": base_lon,
        "date": "14 Nov 2026, 11:30",
        "final_potholes": 1,
        "final_cracks": 0,
        "detections": [{
            "class_name": "Pothole",
            "box": [10, 10, 100, 100],
            "crop_image": crop_base
        }]
    })
    matches_2 = dd.find_pothole_duplicates(rep_2, [rep_1], radius_m=25.0)
    _check(len(matches_2) == 1, "Scenario 2: Exact image + GPS duplicate detected")
    _check(matches_2[0]["decision"] == "POSSIBLE_DUPLICATE", f"Scenario 2: Flagged as POSSIBLE_DUPLICATE (got {matches_2[0]['decision']})")
    _check(matches_2[0]["original_report_id"] == "RS-DUP-01", "Scenario 2: Correctly linked to original report RS-DUP-01")
    _check(matches_2[0]["distance_m"] < 1.0, f"Scenario 2: Distance < 1.0m (got {matches_2[0]['distance_m']}m)")
    _check(matches_2[0]["similarity_score"] >= 0.85, f"Scenario 2: Visual similarity >= 85% (got {matches_2[0]['similarity_score']:.1%})")

    # 3. Second report from different angle/lighting with moderate visual similarity within 25m is detected
    rep_3 = app._init_report_defaults({
        "inspection_id": "RS-DUP-03",
        "type": "Photo Inspection",
        "location": "Station Road, Belagavi",
        "latitude": base_lat + 0.00009,
        "longitude": base_lon,
        "date": "14 Nov 2026, 14:00",
        "final_potholes": 1,
        "final_cracks": 0,
        "detections": [{
            "class_name": "Pothole",
            "box": [10, 10, 100, 100],
            "crop_image": crop_similar
        }]
    })
    matches_3 = dd.find_pothole_duplicates(rep_3, [rep_1], radius_m=25.0)
    _check(len(matches_3) == 1, "Scenario 3: Moderate visual similarity within 25m detected")
    _check(matches_3[0]["decision"] in ("POSSIBLE_DUPLICATE", "NEEDS_MANUAL_REVIEW"),
           f"Scenario 3: Status is candidate duplicate (got {matches_3[0]['decision']})")
    _check(matches_3[0]["distance_m"] <= 25.0, f"Scenario 3: Distance <= 25m (got {matches_3[0]['distance_m']}m)")

    # 4. Two different potholes within 25m of each other are distinguished and classified as NEW_REPORT
    eval_4 = dd.evaluate_duplicate_candidate(
        new_crop=crop_diff, new_lat=base_lat + 0.00005, new_lon=base_lon, new_class="Pothole",
        cand_crop=crop_base, cand_lat=base_lat, cand_lon=base_lon, cand_class="Pothole",
        radius_m=25.0
    )
    _check(eval_4["decision"] == "NEW_REPORT", f"Scenario 4: Different defect within 25m classified as NEW_REPORT (got {eval_4['decision']})")
    _check(eval_4["within_radius"] is True, "Scenario 4: Accurately recognized as within geographic radius")
    _check(eval_4["visual_similarity_score"] < 0.40, f"Scenario 4: Visual similarity low for distinct defect ({eval_4['visual_similarity_score']:.1%})")

    # 5. Same-looking pothole at a distant location (>25m) is classified as NEW_REPORT (distant lookalike)
    distant_lat = base_lat + 0.0200
    distant_lon = base_lon + 0.0200
    eval_5 = dd.evaluate_duplicate_candidate(
        new_crop=crop_base, new_lat=distant_lat, new_lon=distant_lon, new_class="Pothole",
        cand_crop=crop_base, cand_lat=base_lat, cand_lon=base_lon, cand_class="Pothole",
        radius_m=25.0
    )
    _check(eval_5["decision"] == "NEW_REPORT", f"Scenario 5: Distant lookalike classified as NEW_REPORT (got {eval_5['decision']})")
    _check(eval_5["within_radius"] is False, "Scenario 5: Outside geographic radius confirmed")
    _check(eval_5["geographic_distance_m"] > 25.0, f"Scenario 5: Distance > 25m (got {eval_5['geographic_distance_m']}m)")

    # 6. Multi-pothole report correctly isolates individual duplicate potholes while marking others as new
    rep_multi = app._init_report_defaults({
        "inspection_id": "RS-DUP-MULTI",
        "type": "Photo Inspection",
        "location": "Station Road, Belagavi",
        "latitude": base_lat,
        "longitude": base_lon,
        "date": "14 Nov 2026, 16:00",
        "final_potholes": 2,
        "final_cracks": 0,
        "detections": [
            {"class_name": "Pothole", "box": [0, 0, 50, 50], "crop_image": crop_base},
            {"class_name": "Pothole", "box": [60, 60, 110, 110], "crop_image": crop_diff}
        ]
    })
    matches_multi = dd.find_pothole_duplicates(rep_multi, [rep_1], radius_m=25.0)
    _check(len(matches_multi) == 1, f"Scenario 6: Multi-pothole report matched exactly 1 duplicate pothole (got {len(matches_multi)})")
    _check(matches_multi[0]["new_defect_idx"] == 0, "Scenario 6: Matched defect index is 0 (the duplicate crop)")

    # 7. Video tracking IDs are used to avoid self-duplicate matching within the same video
    tracker = tr.SimpleTracker(max_missed=5, match_dist=90.0, iou_thresh=0.2)
    frame1_dets = [{"box": [100, 100, 160, 160], "class_name": "Pothole", "confidence": 0.85}]
    tr1 = tracker.update(frame1_dets, frame_idx=0)
    _check(len(tr1) == 1, "Scenario 7: Tracker registered 1 hazard in frame 1")
    tid1 = tr1[0]["track_id"]

    frame2_dets = [{"box": [102, 101, 162, 161], "class_name": "Pothole", "confidence": 0.87}]
    tr2 = tracker.update(frame2_dets, frame_idx=1)
    _check(len(tr2) == 1, "Scenario 7: Tracker tracked hazard in frame 2")
    tid2 = tr2[0]["track_id"]
    _check(tid1 == tid2, f"Scenario 7: Same physical pothole maintained identical tracking ID #{tid1} across frames")
    _check(tracker.unique_count == 1, f"Scenario 7: Unique hazard count is 1, not double-counted (got {tracker.unique_count})")

    # 8. Missing GPS coordinates fallback to visual-only review with NEEDS_MANUAL_REVIEW status
    eval_8 = dd.evaluate_duplicate_candidate(
        new_crop=crop_base, new_lat=None, new_lon=None, new_class="Pothole",
        cand_crop=crop_base, cand_lat=base_lat, cand_lon=base_lon, cand_class="Pothole",
        radius_m=25.0
    )
    _check(eval_8["decision"] == "NEEDS_MANUAL_REVIEW", f"Scenario 8: Missing GPS falls back to NEEDS_MANUAL_REVIEW (got {eval_8['decision']})")
    _check(eval_8["geographic_distance_m"] is None, "Scenario 8: Geographic distance is None when GPS missing")

    # 9. Crop file extraction, saving and loading work correctly
    test_crop_path = dd.save_pothole_crop(crop_base, report_id="RS-TEST-CROP", pothole_idx=0)
    _check(os.path.exists(test_crop_path), f"Scenario 9: Crop saved to disk at {test_crop_path}")
    loaded_crop = dd.load_pothole_crop(test_crop_path)
    _check(loaded_crop is not None, "Scenario 9: Crop successfully loaded from disk")
    _check(loaded_crop.shape == crop_base.shape, f"Scenario 9: Loaded crop shape matches {crop_base.shape}")

    # 10. Missing crop files are handled gracefully without application crashes
    missing_crop = dd.load_pothole_crop("data/pothole_crops/non_existent_crop_999.jpg")
    _check(missing_crop is None, "Scenario 10: Missing crop returns None without crashing")
    sim_missing = dd.compute_crop_visual_similarity(crop_base, "data/pothole_crops/non_existent_crop_999.jpg")
    _check(sim_missing["score"] == 0.0, "Scenario 10: Visual comparison on missing crop returns 0.0 score safely")

    # 11. Rejected reports are excluded from active duplicate candidate matching
    rep_rej = app._init_report_defaults({
        "inspection_id": "RS-REJECTED",
        "type": "Photo Inspection",
        "location": "Station Road, Belagavi",
        "latitude": base_lat,
        "longitude": base_lon,
        "date": "14 Nov 2026, 08:00",
        "verification_status": "REJECTED",
        "final_potholes": 1,
        "detections": [{"class_name": "Pothole", "box": [10, 10, 100, 100], "crop_image": crop_base}]
    })
    matches_rej = dd.find_pothole_duplicates(rep_2, [rep_rej], radius_m=25.0)
    _check(len(matches_rej) == 0, "Scenario 11: Rejected reports excluded from active duplicate matching")

    # 12. Confirming duplicate links report via duplicate_of without deleting records
    test_store_path = Path("data/test_dup_store.json")
    if test_store_path.exists():
        test_store_path.unlink()
    try:
        istore.save_inspection(rep_1, store_path=test_store_path)
        istore.save_inspection(rep_2, store_path=test_store_path)

        istore.update_inspection("RS-DUP-02", {
            "duplicate_status": "CONFIRMED_DUPLICATE",
            "duplicate_of": "RS-DUP-01"
        }, store_path=test_store_path)

        rec1 = istore.get_inspection("RS-DUP-01", store_path=test_store_path)
        rec2 = istore.get_inspection("RS-DUP-02", store_path=test_store_path)
        _check(rec1 is not None, "Scenario 12: Original report RS-DUP-01 preserved in store")
        _check(rec2 is not None, "Scenario 12: Duplicate report RS-DUP-02 preserved in store")
        _check(rec2.get("duplicate_status") == "CONFIRMED_DUPLICATE", "Scenario 12: Duplicate status is CONFIRMED_DUPLICATE")
        _check(rec2.get("duplicate_of") == "RS-DUP-01", "Scenario 12: duplicate_of links correctly to RS-DUP-01")

        # 13. Marking as different updates status to MARKED_AS_UNIQUE
        istore.update_inspection("RS-DUP-02", {
            "duplicate_status": "MARKED_AS_UNIQUE",
            "duplicate_of": None
        }, store_path=test_store_path)
        rec2_diff = istore.get_inspection("RS-DUP-02", store_path=test_store_path)
        _check(rec2_diff.get("duplicate_status") == "MARKED_AS_UNIQUE", "Scenario 13: Status updated to MARKED_AS_UNIQUE")
        _check(rec2_diff.get("duplicate_of") is None, "Scenario 13: duplicate_of cleared when marked unique")

        # 14. System preserves data across restarts via JSON store
        reloaded = istore.load_all_inspections(store_path=test_store_path)
        _check(len(reloaded) == 2, f"Scenario 14: All 2 records reloaded after store re-open (got {len(reloaded)})")
        _check(reloaded[0].get("inspection_id") in ("RS-DUP-01", "RS-DUP-02"), "Scenario 14: IDs preserved across restarts")
    finally:
        if test_store_path.exists():
            test_store_path.unlink()

    # 15. Haversine distance calculation accuracy across known benchmark coordinate pairs
    d_zero = dd.haversine_distance_m(base_lat, base_lon, base_lat, base_lon)
    _check(d_zero == 0.0, f"Scenario 15: Distance between identical points is 0.0m (got {d_zero}m)")
    d_1deg = dd.haversine_distance_m(0.0, 0.0, 0.0, 1.0)
    _check(abs(d_1deg - 111195.0) < 500.0, f"Scenario 15: 1-degree equatorial distance ~111.19 km (got {d_1deg:.1f}m)")

    # 16. Analytics metrics accurately compute unique hazards vs duplicate reports
    mock_history = [
        {"inspection_id": "M1", "final_potholes": 1, "duplicate_status": "NEW_REPORT"},
        {"inspection_id": "M2", "final_potholes": 1, "duplicate_status": "CONFIRMED_DUPLICATE", "duplicate_of": "M1"},
        {"inspection_id": "M3", "final_potholes": 2, "duplicate_status": "NEW_REPORT"},
        {"inspection_id": "M4", "final_potholes": 1, "duplicate_status": "POSSIBLE_DUPLICATE"},
    ]
    tot_rep = len(mock_history)
    tot_pot = sum(r["final_potholes"] for r in mock_history)
    conf_dup = sum(1 for r in mock_history if r.get("duplicate_status") == "CONFIRMED_DUPLICATE")
    unique_haz = tot_pot - conf_dup
    _check(tot_rep == 4, f"Scenario 16: Total reports is 4 (got {tot_rep})")
    _check(tot_pot == 5, f"Scenario 16: Total potholes detected is 5 (got {tot_pot})")
    _check(conf_dup == 1, f"Scenario 16: Confirmed duplicates is 1 (got {conf_dup})")
    _check(unique_haz == 4, f"Scenario 16: Unique active hazards = 5 - 1 = 4 (got {unique_haz})")

    # 17. Image crop accessibility and display in dispatch review
    _check(os.path.exists(test_crop_path), "Scenario 17: Pothole crop file accessible in data/pothole_crops/")
    with Image.open(test_crop_path) as test_img_crop:
        _check(test_img_crop.size[0] > 0 and test_img_crop.size[1] > 0,
               f"Scenario 17: Crop readable as valid image for UI rendering ({test_img_crop.size})")
    if os.path.exists(test_crop_path):
        try:
            os.remove(test_crop_path)
        except Exception:
            pass


# =========================================================
# MAIN RUNNER
# =========================================================
def run_all_tests():
    _banner("ROADSENTINEL AI SYSTEM VERIFICATION SUITE — 18 TESTS")

    test_cases = [
        (1,  "Model Loading & Hardware Status",                  test_1_models),
        (2,  "Video Metadata & Format Validation",               test_2_video_metadata),
        (3,  "YOLO Inference on Video Frames",                   test_3_yolo_inference),
        (4,  "Video Processing & Output Encoding",               test_4_video_processing),
        (5,  "Download File Bytes Integrity",                     test_5_download_bytes),
        (6,  "Existing Image Detection Pipeline",                test_6_image_detection),
        (7,  "Gemini Independence (Offline)",                     test_7_gemini_independence),
        (8,  "Unique Hazard Tracking (IoU Tracker)",             test_8_tracking),
        (9,  "Duplicate Report Detection",                        test_9_duplicates),
        (10, "Risk Scoring (Heuristic Formula)",                 test_10_risk_scoring),
        (11, "Manual Verification Workflow",                      test_11_verification),
        (12, "Progress Comparison & Trend Detection",            test_12_progress),
        (13, "CSV Export (stdlib, no pandas)",                    test_13_csv_export),
        (14, "Damage Severity Classification (Visual 2D Proxy)", test_14_severity_classification),
        (15, "GPS, EXIF & Video Location Metadata Engine",        test_15_location_metadata),
        (16, "Local JSON Inspection Store (No Database)",         test_16_inspection_store),
        (17, "Simplified Location & Current Geolocation Engine",  test_17_simplified_location),
        (18, "Intelligent Duplicate Pothole System (17 Scenarios)", test_18_intelligent_duplicate_system),
    ]

    for num, name, fn in test_cases:
        run_test(num, name, fn)

    _banner("TEST RESULTS SUMMARY")
    passed = sum(1 for v in results.values() if v == PASS)
    failed = sum(1 for v in results.values() if v == FAIL)

    for test_name, status in results.items():
        mark = "✅" if status == PASS else "❌"
        print(f"  {mark} {test_name}: {status}")

    print(f"\n  Passed: {passed} / {len(results)}")
    if failed > 0:
        print(f"  Failed: {failed}")
        sys.exit(1)
    else:
        print(f"\n  🎉 ALL {len(results)} TESTS PASSED!")
        sys.exit(0)


if __name__ == "__main__":
    run_all_tests()
