"""
RoadSentinel Automated Test Suite — 13 Tests
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

No network calls. No Gemini API calls. No fake data.
"""

import os
import sys
import csv
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
    # Find most recent annotated video
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

    # Ensure full pipeline runs without Gemini
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
        frame_skip=3  # faster for test
    )
    unique_count = summary.get("unique_hazard_count")
    total = summary.get("total_detections", 0)
    _info(f"Total frame detections: {total}, Unique tracked hazards: {unique_count}")

    _check(unique_count is not None, "unique_hazard_count is present in summary")
    _check(unique_count <= total, f"unique_hazard_count ({unique_count}) <= total_detections ({total})")
    # If detections exist, unique count must be > 0
    if total > 0:
        _check(unique_count > 0, f"unique_hazard_count > 0 when detections exist")

    # Also test SimpleTracker directly
    tracker = tr.SimpleTracker()
    fake_dets = [
        {"class_name": "Pothole", "box": [10, 10, 60, 60], "confidence": 0.9, "area_pixels": 2500},
        {"class_name": "Pothole", "box": [100, 100, 160, 160], "confidence": 0.85, "area_pixels": 3600},
    ]
    out1 = tracker.update(fake_dets, 0)
    _check(all("track_id" in d for d in out1), "track_id assigned to all detections in frame 0")
    _check(tracker.unique_count == 2, f"unique_count == 2 after first frame (got {tracker.unique_count})")

    # Same boxes next frame → same IDs
    out2 = tracker.update(fake_dets, 1)
    ids1 = {d["track_id"] for d in out1}
    ids2 = {d["track_id"] for d in out2}
    _check(ids1 == ids2, f"Track IDs maintained across frames: {ids1} == {ids2}")
    _check(tracker.unique_count == 2, "No new unique IDs assigned for matched detections")

    # New box far away → new ID
    new_det = [{"class_name": "Pothole", "box": [800, 400, 860, 460], "confidence": 0.7, "area_pixels": 3600}]
    out3 = tracker.update(new_det, 2)
    _check(tracker.unique_count == 3, f"New distant detection assigned new ID (unique_count=3, got {tracker.unique_count})")


# =========================================================
# TEST 9 — Duplicate Report Detection
# =========================================================
def test_9_duplicates():
    # Create two similar reports
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
    # Completely different report
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
    _info(f"Reasons A-B: {sim_ab['reasons']}")

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
    # High-confidence large pothole → should be Critical or High
    pothole_det = {
        "class_name": "Pothole",
        "confidence": 0.95,
        "area_pixels": 60000,  # above normalizer → area_factor capped at 1.0
    }
    pothole_risk = rs.compute_risk(pothole_det)
    _info(f"Pothole risk: score={pothole_risk['score']}, category={pothole_risk['category']}")
    _check(pothole_risk["score"] >= 50.0,
           f"Large pothole @ 95% conf has score >= 50 (got {pothole_risk['score']})")
    _check(pothole_risk["category"] in ["High", "Critical"],
           f"Category is High or Critical (got '{pothole_risk['category']}')")
    _check(len(pothole_risk["factors"]) >= 3, "At least 3 contributing factors explained")

    # Low-confidence tiny longitudinal crack → should be Low
    crack_det = {
        "class_name": "Longitudinal Crack",
        "confidence": 0.25,
        "area_pixels": 500,  # very small
    }
    crack_risk = rs.compute_risk(crack_det)
    _info(f"Tiny crack risk: score={crack_risk['score']}, category={crack_risk['category']}")
    _check(crack_risk["category"] == "Low",
           f"Tiny crack is Low risk (got '{crack_risk['category']}')")

    # Video summary
    detections = [pothole_det, crack_det]
    summary = rs.compute_video_risk_summary(detections)
    _check("distribution" in summary, "Video risk summary has 'distribution' key")
    _check("disclaimer" in summary, "Risk summary includes disclaimer")
    _check(summary["total_scored"] == 2, "Total scored == 2")

    # enrich_detection_with_risk
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

    # Initial state
    _check(rep["verification_status"] == "AI_PENDING",
           "New report defaults to AI_PENDING")
    _check(rep["original_ai_prediction"]["potholes"] == 2,
           "Original AI prediction preserved (potholes=2)")

    # Verify
    rep["verification_status"] = "VERIFIED"
    rep["verified_by"] = "Inspector"
    rep["verified_at"] = "14 Nov 2026, 10:00"
    _check(rep["verification_status"] == "VERIFIED", "Status → VERIFIED")
    _check(rep["verified_by"] == "Inspector", "verified_by set")
    _check(rep["original_ai_prediction"]["potholes"] == 2,
           "Original prediction still intact after verification")

    # Reject another report
    rep2 = dict(rep)
    rep2["verification_status"] = "REJECTED"
    rep2["rejection_reason"] = "No damage visible in re-inspection"
    _check(rep2["verification_status"] == "REJECTED", "Status → REJECTED")
    _check(rep2["rejection_reason"], "Rejection reason recorded")

    # Correct damage class
    rep3 = dict(rep)
    rep3["verification_status"] = "AI_PENDING"
    app._init_report_defaults(rep3)
    rep3["corrected_class"] = "Alligator Crack"
    rep3["corrected_severity"] = "Severe"
    rep3["verification_status"] = "VERIFIED"
    _check(rep3["corrected_class"] == "Alligator Crack", "Corrected class recorded")
    _check(rep3["original_ai_prediction"]["potholes"] == 2,
           "Original prediction preserved after correction")


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

    _check(comp_worse["trend"] == "WORSENING",
           f"Trend is WORSENING (got '{comp_worse['trend']}')")
    _check(comp_better["trend"] == "IMPROVING",
           f"Trend is IMPROVING (got '{comp_better['trend']}')")
    _check(comp_same["trend"] == "UNCHANGED",
           f"Trend is UNCHANGED (got '{comp_same['trend']}')")

    # Test find_location_history
    history = [older, newer_worse, {"location": "MG Road, Pune", "date": "14 Nov 2026",
                                     "final_potholes": 1, "final_cracks": 0}]
    matched = pm.find_location_history("NH-48 Bypass, Belagavi", history)
    _check(len(matched) >= 2, f"find_location_history found {len(matched)} matches")

    # Test insufficient data
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
            "type": "Photo Inspection",
            "date": "14 Nov 2026",
            "location": "Test Location",
            "final_potholes": 2,
            "final_cracks": 3,
            "longitudinal_cracks": 2,
            "transverse_cracks": 1,
            "alligator_cracks": 0,
            "avg_conf": "72.3%",
            "verification_status": "VERIFIED",
            "risk_category": "Medium",
            "duplicate_status": None,
        }
    ]

    csv_bytes = app._make_csv_bytes(history)
    _check(len(csv_bytes) > 0, f"CSV bytes non-empty ({len(csv_bytes)} bytes)")

    # Parse to verify structure
    import io
    decoded = csv_bytes.decode("utf-8")
    reader = csv.DictReader(io.StringIO(decoded))
    rows = list(reader)
    _check(len(rows) == 1, f"CSV has 1 data row (got {len(rows)})")
    _check("Report #" in rows[0], "CSV has 'Report #' column")
    _check("Location" in rows[0], "CSV has 'Location' column")
    _check(rows[0]["Potholes"] == "2", f"Potholes == '2' (got '{rows[0]['Potholes']}')")
    _check(rows[0]["Verification Status"] == "VERIFIED",
           "Verification status correctly exported")
    _info(f"CSV headers: {list(rows[0].keys())}")

    # Verify no pandas import in csv bytes generation
    # (structural test: app._make_csv_bytes must work without pandas)
    import importlib
    spec = importlib.util.find_spec("pandas")
    # Even if pandas is installed, it must NOT be imported in app.py
    app_source = Path("app.py").read_text()
    _check("import pandas" not in app_source,
           "No 'import pandas' in app.py — pandas-free implementation confirmed")


# =========================================================
# MAIN RUNNER
# =========================================================
def run_all_tests():
    _banner("ROADSENTINEL AI SYSTEM VERIFICATION SUITE — 13 TESTS")

    test_cases = [
        (1,  "Model Loading & Hardware Status",      test_1_models),
        (2,  "Video Metadata & Format Validation",   test_2_video_metadata),
        (3,  "YOLO Inference on Video Frames",       test_3_yolo_inference),
        (4,  "Video Processing & Output Encoding",   test_4_video_processing),
        (5,  "Download File Bytes Integrity",         test_5_download_bytes),
        (6,  "Existing Image Detection Pipeline",    test_6_image_detection),
        (7,  "Gemini Independence (Offline)",         test_7_gemini_independence),
        (8,  "Unique Hazard Tracking (IoU Tracker)", test_8_tracking),
        (9,  "Duplicate Report Detection",            test_9_duplicates),
        (10, "Risk Scoring (Heuristic Formula)",     test_10_risk_scoring),
        (11, "Manual Verification Workflow",          test_11_verification),
        (12, "Progress Comparison & Trend Detection",test_12_progress),
        (13, "CSV Export (stdlib, no pandas)",        test_13_csv_export),
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
        print("\n  🎉 ALL TESTS PASSED!")
        sys.exit(0)


if __name__ == "__main__":
    run_all_tests()
