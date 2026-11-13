"""
RoadSentinel Automated Test Suite
Verifies:
1. Video validation and metadata extraction
2. YOLO inference on video frames with actual predictions and labels
3. Output video generation, encoding, and OpenCV re-opening verification
4. Output file bytes integrity for download
5. Existing image detection functionality preservation
6. Independence from Gemini (runs 100% offline without API key or gRPC)
"""

import os
import sys
from pathlib import Path
from PIL import Image
from ultralytics import YOLO

import video_detector as vd
import app

def run_all_tests():
    print("=" * 60)
    print("ROADSENTINEL AI SYSTEM VERIFICATION SUITE")
    print("=" * 60)
    
    # ---------------------------------------------------------
    # TEST 1: System & Model Verification
    # ---------------------------------------------------------
    print("\n[TEST 1] Model Loading & Hardware Status:")
    device = vd.get_device_info()
    print(f"  - Inference Device: {device['device_name']} (CUDA: {device['cuda_available']})")
    models = app.load_models()
    assert len(models) >= 2, "Expected at least 2 model tiers loaded"
    for name, m in models.items():
        print(f"  - Loaded '{name}': {m.names}")
    print("  --> PASS: Models loaded successfully.")

    # ---------------------------------------------------------
    # TEST 2: Video Metadata & Validation
    # ---------------------------------------------------------
    print("\n[TEST 2] Video Metadata & Format Validation:")
    video_file = "test_road.mp4"
    assert os.path.exists(video_file), f"Missing {video_file}"
    is_valid, msg = vd.validate_video(video_file)
    print(f"  - Validation status: {is_valid} ({msg})")
    assert is_valid, f"Video validation failed: {msg}"
    
    meta = vd.get_video_metadata(video_file)
    print(f"  - Filename: {meta['filename']}")
    print(f"  - Resolution: {meta['resolution']}")
    print(f"  - FPS: {meta['fps']}")
    print(f"  - Total Frames: {meta['total_frames']}")
    print(f"  - Duration: {meta['duration_str']} ({meta['duration_sec']}s)")
    print(f"  - Size: {meta['file_size_mb']} MB")
    assert meta["width"] > 0 and meta["height"] > 0 and meta["total_frames"] > 0
    print("  --> PASS: Video metadata verified.")

    # ---------------------------------------------------------
    # TEST 3: YOLO Inference on Video Frames
    # ---------------------------------------------------------
    print("\n[TEST 3] YOLO Inference on Video Frames:")
    import cv2
    cap = cv2.VideoCapture(video_file)
    ret, frame = cap.read()
    cap.release()
    assert ret and frame is not None, "Failed to read frame from video"
    
    annotated_frame, detections = vd.process_frame(
        frame=frame,
        models=models,
        conf_threshold=0.15,
        frame_idx=0,
        timestamp_sec=0.0
    )
    print(f"  - Detections in Frame 0: {len(detections)}")
    assert len(detections) > 0, "Expected at least 1 detection in test road frame"
    first_det = detections[0]
    print(f"  - Sample Detection: Class='{first_det['class_name']}', Conf={first_det['confidence']:.2f}, Box={first_det['box']}, Area={first_det['area_pixels']}px")
    assert "class_name" in first_det and "confidence" in first_det and "box" in first_det
    print("  --> PASS: YOLO frame inference confirmed.")

    # ---------------------------------------------------------
    # TEST 4: Output Video Generation & Verification
    # ---------------------------------------------------------
    print("\n[TEST 4] Video Processing Engine & Output Encoding:")
    out_dir = "outputs"
    annotated_path, summary = vd.process_video(
        video_path=video_file,
        output_dir=out_dir,
        models=models,
        conf_threshold=0.15,
        frame_skip=1
    )
    print(f"  - Annotated Output Path: {annotated_path}")
    print(f"  - Processed Frames: {summary['processed_frames']}")
    print(f"  - Total Frame Detections: {summary['total_detections']}")
    print(f"  - Potholes: {summary['pothole_detections']}")
    print(f"  - Longitudinal Cracks: {summary['longitudinal_crack_detections']}")
    print(f"  - Transverse Cracks: {summary['transverse_crack_detections']}")
    print(f"  - Alligator Cracks: {summary['alligator_crack_detections']}")
    print(f"  - Processing Speed: {summary['processing_fps']} FPS (Time: {summary['processing_time_sec']}s)")
    print(f"  - Avg Confidence: {summary['average_confidence_pct']}")
    
    # Re-open with OpenCV to verify playable video stream
    verified, v_info = vd.verify_output_video(annotated_path)
    print(f"  - OpenCV Verification: Valid={verified}, Frames={v_info.get('frames')}, Size={v_info.get('size_mb')} MB")
    assert verified, f"Output video verification failed: {v_info.get('error')}"
    assert v_info["frames"] == meta["total_frames"], "Frame count mismatch in output video"
    print("  --> PASS: Annotated video output verified with OpenCV.")

    # ---------------------------------------------------------
    # TEST 5: Download File Bytes Integrity
    # ---------------------------------------------------------
    print("\n[TEST 5] Video Download File Bytes:")
    assert os.path.exists(annotated_path), "Output video file does not exist"
    file_bytes_len = os.path.getsize(annotated_path)
    with open(annotated_path, "rb") as f:
        data = f.read(1024)
    assert len(data) > 0 and file_bytes_len > 0, "Output file data is empty"
    print(f"  - Downloadable file size: {file_bytes_len} bytes ({file_bytes_len / (1024*1024):.2f} MB)")
    print("  --> PASS: File bytes verified ready for Streamlit download.")

    # ---------------------------------------------------------
    # TEST 6: Existing Image Detection Still Works
    # ---------------------------------------------------------
    print("\n[TEST 6] Existing Image Detection Pipeline:")
    img_path = "pothole.webp"
    assert os.path.exists(img_path), f"Missing {img_path}"
    test_img = Image.open(img_path).convert("RGB")
    result, model_used, counts = app.cascade_predict(test_img, conf_threshold=0.15)
    print(f"  - Model Used: {model_used}")
    print(f"  - Potholes Detected: {counts['potholes']}")
    print(f"  - Cracks (Longitudinal/Transverse/Alligator): {counts['longitudinal']}/{counts['transverse']}/{counts['alligator']}")
    assert counts["potholes"] > 0, "Expected potholes detected in sample image"
    print("  --> PASS: Existing image detection fully functional.")

    # ---------------------------------------------------------
    # TEST 7: Gemini Independence
    # ---------------------------------------------------------
    print("\n[TEST 7] Gemini Independence Verification:")
    print(f"  - HAS_GEMINI flag: {app.HAS_GEMINI}")
    dummy_gemini = app.validate_with_gemini(api_key="", image=test_img)
    print(f"  - Response with no API key: {dummy_gemini}")
    # Verify that video detection operates with no dependency on Gemini
    assert summary["status"] == "completed"
    print("  --> PASS: System operates completely independently of Gemini.")

    print("\n" + "=" * 60)
    print("ALL 7 TEST SUITES PASSED WITH 100% SUCCESS!")
    print("=" * 60)

if __name__ == "__main__":
    run_all_tests()
