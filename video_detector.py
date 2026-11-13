"""
RoadSentinel - AI Video Detection Engine
Module: video_detector.py
Provides end-to-end video processing, multi-tier YOLO inference, bounding box rendering,
video encoding, output verification, and detection analytics.
"""

import os
import time
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Callable, Any

import cv2
import numpy as np
import torch
from ultralytics import YOLO

try:
    import imageio_ffmpeg
    HAS_IMAGEIO_FFMPEG = True
except ImportError:
    HAS_IMAGEIO_FFMPEG = False

# Supported video extensions
SUPPORTED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}

# Canonical color scheme (BGR for OpenCV, Hex for Streamlit/CSS)
CLASS_METADATA = {
    "Longitudinal Crack": {
        "bgr": (255, 191, 0),      # Deep Sky Blue
        "hex": "#00BFFF",
        "category": "crack"
    },
    "Transverse Crack": {
        "bgr": (219, 112, 147),    # Medium Purple
        "hex": "#9370DB",
        "category": "crack"
    },
    "Alligator Crack": {
        "bgr": (50, 205, 50),      # Lime Green
        "hex": "#32CD32",
        "category": "crack"
    },
    "Pothole": {
        "bgr": (71, 99, 255),      # Coral / Tomato
        "hex": "#FF6347",
        "category": "pothole"
    }
}
DEFAULT_BGR = (0, 215, 255)  # Gold/Yellow fallback


def get_device_info() -> Dict[str, Any]:
    """Detect whether CUDA hardware acceleration is available or fall back to CPU."""
    cuda_available = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if cuda_available else "CPU (Multi-threaded)"
    return {
        "cuda_available": cuda_available,
        "device_name": device_name,
        "device_type": "cuda" if cuda_available else "cpu"
    }


def normalize_class_name(raw_name: str) -> str:
    """
    Maps arbitrary model class names (from RDD2022, Pothole-specific, or custom)
    to standardized canonical labels.
    """
    clean = str(raw_name).strip().lower().replace("_", " ")
    
    # Pothole checks
    if "pothole" in clean or "d40" in clean:
        return "Pothole"
    
    # Crack checks
    if "longitudinal" in clean or "d00" in clean:
        return "Longitudinal Crack"
    elif "transverse" in clean or "d10" in clean:
        return "Transverse Crack"
    elif "alligator" in clean or "d20" in clean:
        return "Alligator Crack"
    elif "crack" in clean:
        return "Longitudinal Crack"  # Default general crack
    
    return raw_name.title()


def get_video_metadata(video_path: str) -> Dict[str, Any]:
    """
    Inspects video file and returns duration, resolution, FPS, total frames, and file size.
    Raises ValueError if video cannot be opened.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    file_size_bytes = os.path.getsize(video_path)
    file_size_mb = file_size_bytes / (1024 * 1024)
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"OpenCV could not open video: {video_path}")
    
    try:
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Handle zero or invalid FPS
        if fps <= 0 or np.isnan(fps):
            fps = 30.0
            
        duration_sec = total_frames / fps if total_frames > 0 else 0.0
        
        # Extract fourcc codec name
        fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))
        codec_name = "".join([chr((fourcc_int >> 8 * i) & 0xFF) for i in range(4)])
        if not codec_name.isprintable() or not codec_name.strip():
            codec_name = "Unknown"
            
        return {
            "filename": os.path.basename(video_path),
            "file_size_bytes": file_size_bytes,
            "file_size_mb": round(file_size_mb, 2),
            "width": width,
            "height": height,
            "resolution": f"{width}x{height}",
            "fps": round(fps, 2),
            "total_frames": total_frames,
            "duration_sec": round(duration_sec, 2),
            "duration_str": f"{int(duration_sec // 60):02d}:{int(duration_sec % 60):02d}",
            "codec": codec_name
        }
    finally:
        cap.release()


def validate_video(video_path: str, max_size_mb: float = 500.0) -> Tuple[bool, str]:
    """
    Validates file existence, extension, size limit, and frame readability.
    Returns (is_valid, error_message).
    """
    if not video_path or not os.path.exists(video_path):
        return False, "Video file does not exist."
    
    ext = Path(video_path).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return False, f"Unsupported format '{ext}'. Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
    
    size_mb = os.path.getsize(video_path) / (1024 * 1024)
    if size_mb > max_size_mb:
        return False, f"File size ({size_mb:.1f} MB) exceeds maximum allowed limit of {max_size_mb} MB."
    
    if size_mb == 0:
        return False, "Video file is empty (0 bytes)."
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return False, "Failed to initialize video decoder. File may be corrupted or use an unsupported codec."
    
    try:
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            return False, "Video reports 0 frames or invalid stream length."
        
        # Attempt reading the first frame to guarantee decode success
        ret, frame = cap.read()
        if not ret or frame is None or frame.size == 0:
            return False, "Could not decode initial video frame. Video stream appears corrupted."
            
        return True, "Valid video file."
    finally:
        cap.release()


def compute_iou(box1: List[float], box2: List[float]) -> float:
    """Calculates Intersection over Union (IoU) of two boxes [x1, y1, x2, y2]."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    
    union = area1 + area2 - intersection
    if union <= 0:
        return 0.0
    return float(intersection / union)


def process_frame(
    frame: np.ndarray,
    models: Dict[str, YOLO],
    conf_threshold: float = 0.25,
    frame_idx: int = 0,
    timestamp_sec: float = 0.0
) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    """
    Runs multi-model YOLO inference on a single BGR frame.
    Deduplicates overlapping predictions via Non-Maximum Suppression (IoU >= 0.45),
    extracts bounding box telemetry, and renders annotations.
    """
    raw_detections: List[Dict[str, Any]] = []
    h, w = frame.shape[:2]
    
    # Run all loaded models in inference mode
    with torch.no_grad():
        for model_name, model in models.items():
            if model is None:
                continue
            try:
                # Ultralytics accepts BGR numpy arrays directly
                results = model.predict(source=frame, conf=conf_threshold, verbose=False)
                if not results or len(results) == 0:
                    continue
                r = results[0]
                if r.boxes is None or len(r.boxes) == 0:
                    continue
                
                boxes = r.boxes.xyxy.cpu().numpy()
                confs = r.boxes.conf.cpu().numpy()
                classes = r.boxes.cls.cpu().numpy().astype(int)
                
                for box, conf, cls_id in zip(boxes, confs, classes):
                    raw_cls_name = r.names.get(cls_id, str(cls_id))
                    canonical_name = normalize_class_name(raw_cls_name)
                    
                    x1, y1, x2, y2 = [int(v) for v in box]
                    # Clamp coordinates to frame boundaries
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(w, x2), min(h, y2)
                    
                    area = (x2 - x1) * (y2 - y1)
                    if area <= 0:
                        continue
                        
                    raw_detections.append({
                        "class_id": int(cls_id),
                        "raw_class_name": raw_cls_name,
                        "class_name": canonical_name,
                        "confidence": float(conf),
                        "box": [x1, y1, x2, y2],
                        "area_pixels": int(area),
                        "frame_idx": frame_idx,
                        "timestamp_sec": round(timestamp_sec, 2),
                        "timestamp_str": f"{int(timestamp_sec // 60):02d}:{timestamp_sec % 60:05.2f}",
                        "model_source": model_name
                    })
            except Exception:
                # Continue if one model errors out on corrupt input
                continue
    
    # Sort detections descending by confidence for NMS
    raw_detections.sort(key=lambda d: d["confidence"], reverse=True)
    
    # Multi-class Non-Maximum Suppression across tiers
    final_detections: List[Dict[str, Any]] = []
    for det in raw_detections:
        suppressed = False
        for kept in final_detections:
            # If same class or both are potholes, suppress if IoU > 0.45
            is_same_category = (det["class_name"] == kept["class_name"]) or (
                "pothole" in det["class_name"].lower() and "pothole" in kept["class_name"].lower()
            )
            if is_same_category:
                if compute_iou(det["box"], kept["box"]) >= 0.45:
                    suppressed = True
                    break
        if not suppressed:
            final_detections.append(det)
            
    # Render annotations onto frame
    annotated_frame = draw_detections(frame, final_detections, frame_idx, timestamp_sec)
    return annotated_frame, final_detections


def draw_detections(
    frame: np.ndarray,
    detections: List[Dict[str, Any]],
    frame_idx: int = 0,
    timestamp_sec: float = 0.0
) -> np.ndarray:
    """
    Draws stylized bounding boxes, labels with confidence percentages, and a HUD header.
    """
    out = frame.copy()
    h, w = out.shape[:2]
    
    pothole_count = sum(1 for d in detections if d["class_name"] == "Pothole")
    crack_count = len(detections) - pothole_count
    
    # Draw bounding boxes
    for det in detections:
        x1, y1, x2, y2 = det["box"]
        cls_name = det["class_name"]
        conf = det["confidence"]
        
        meta = CLASS_METADATA.get(cls_name, {})
        color = meta.get("bgr", DEFAULT_BGR)
        
        # Bounding box rectangle
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)
        
        # Corner brackets for high-tech HUD look
        corner_len = min(15, (x2 - x1) // 4, (y2 - y1) // 4)
        if corner_len > 4:
            cv2.line(out, (x1, y1), (x1 + corner_len, y1), color, 3)
            cv2.line(out, (x1, y1), (x1, y1 + corner_len), color, 3)
            cv2.line(out, (x2, y1), (x2 - corner_len, y1), color, 3)
            cv2.line(out, (x2, y1), (x2, y1 + corner_len), color, 3)
            cv2.line(out, (x1, y2), (x1 + corner_len, y2), color, 3)
            cv2.line(out, (x1, y2), (x1, y2 - corner_len), color, 3)
            cv2.line(out, (x2, y2), (x2 - corner_len, y2), color, 3)
            cv2.line(out, (x2, y2), (x2, y2 - corner_len), color, 3)
            
        # Label text pill
        label = f"{cls_name} {int(conf * 100)}%"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        font_thickness = 1
        (label_w, label_h), baseline = cv2.getTextSize(label, font, font_scale, font_thickness)
        
        # Put label above box if possible, else below
        label_y1 = y1 - label_h - baseline - 4
        if label_y1 < 0:
            label_y1 = y1 + 4
            label_y2 = label_y1 + label_h + baseline + 4
        else:
            label_y2 = y1
            
        label_x2 = min(w, x1 + label_w + 8)
        
        # Solid colored background pill
        cv2.rectangle(out, (x1, label_y1), (label_x2, label_y2), color, -1)
        # Black text for maximum readability on bright tags
        text_y = label_y2 - baseline - 2
        cv2.putText(out, label, (x1 + 4, text_y), font, font_scale, (0, 0, 0), font_thickness, cv2.LINE_AA)

    # Top HUD Banner
    hud_bg_height = 32
    overlay = out.copy()
    cv2.rectangle(overlay, (0, 0), (w, hud_bg_height), (18, 18, 18), -1)
    cv2.addWeighted(overlay, 0.75, out, 0.25, 0, out)
    
    # Left HUD: RoadSentinel Branding
    hud_font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(out, "ROADSENTINEL AI", (12, 21), hud_font, 0.55, (0, 215, 255), 2, cv2.LINE_AA)
    
    # Center/Right HUD: Timestamp & Defects Count
    time_str = f"TIME: {int(timestamp_sec // 60):02d}:{timestamp_sec % 60:05.2f} (F#{frame_idx})"
    cv2.putText(out, time_str, (w // 2 - 120, 21), hud_font, 0.45, (200, 200, 200), 1, cv2.LINE_AA)
    
    stats_str = f"POTHOLES: {pothole_count}  |  CRACKS: {crack_count}"
    cv2.putText(out, stats_str, (w - 280, 21), hud_font, 0.45, (0, 255, 200) if (pothole_count + crack_count) > 0 else (160, 160, 160), 1, cv2.LINE_AA)
    
    return out


def verify_output_video(output_path: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Verifies that the generated output video exists, has non-zero size,
    and can be reopened and decoded by OpenCV.
    """
    if not os.path.exists(output_path):
        return False, {"error": "Output video file does not exist on disk."}
    
    size_bytes = os.path.getsize(output_path)
    if size_bytes == 0:
        return False, {"error": "Output video file has 0 bytes (empty file)."}
    
    cap = cv2.VideoCapture(output_path)
    if not cap.isOpened():
        return False, {"error": "OpenCV cannot open output video for playback."}
    
    try:
        frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        
        ret, frame = cap.read()
        if not ret or frame is None:
            return False, {"error": "OpenCV failed to read initial frame from output video."}
            
        return True, {
            "valid": True,
            "size_bytes": size_bytes,
            "size_mb": round(size_bytes / (1024 * 1024), 2),
            "frames": frames,
            "width": width,
            "height": height,
            "fps": round(fps, 2)
        }
    finally:
        cap.release()


def reencode_for_web(input_path: str, output_path: str) -> bool:
    """
    Transcodes OpenCV video to H.264 MP4 using imageio-ffmpeg for universal HTML5 playback.
    Returns True on success, False on failure.
    """
    if not HAS_IMAGEIO_FFMPEG:
        return False
    
    try:
        ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
        cmd = [
            ffmpeg_bin,
            "-y",                     # overwrite output
            "-i", input_path,         # input
            "-vcodec", "libx264",     # standard H.264
            "-pix_fmt", "yuv420p",    # required for wide browser compatibility
            "-movflags", "+faststart", # enables streaming before full download
            "-crf", "23",             # high perceptual quality
            "-preset", "fast",
            output_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=120)
        if res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True
        return False
    except Exception:
        return False


def process_video(
    video_path: str,
    output_dir: str,
    models: Dict[str, YOLO],
    conf_threshold: float = 0.25,
    frame_skip: int = 1,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None
) -> Tuple[Optional[str], Dict[str, Any]]:
    """
    Main sequential video processing engine.
    
    Reads video frame-by-frame (never loading entire video into RAM),
    runs multi-tier YOLO inference, annotates frames, writes video output,
    handles fallbacks, verifies output, and generates comprehensive statistics.
    """
    is_valid, err = validate_video(video_path)
    if not is_valid:
        raise ValueError(f"Invalid video: {err}")
    
    os.makedirs(output_dir, exist_ok=True)
    meta = get_video_metadata(video_path)
    
    width = meta["width"]
    height = meta["height"]
    fps = meta["fps"]
    total_frames = meta["total_frames"]
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video source: {video_path}")
    
    # Target output paths
    base_name = Path(video_path).stem
    timestamp_tag = int(time.time())
    raw_output_path = os.path.join(output_dir, f"{base_name}_annotated_{timestamp_tag}.mp4")
    avi_fallback_path = os.path.join(output_dir, f"{base_name}_annotated_{timestamp_tag}.avi")
    
    # Try mp4v codec first
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(raw_output_path, fourcc, fps, (width, height))
    active_output_path = raw_output_path
    
    # If mp4v fails to open, fallback to XVID AVI
    if not out.isOpened():
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        out = cv2.VideoWriter(avi_fallback_path, fourcc, fps, (width, height))
        active_output_path = avi_fallback_path
        if not out.isOpened():
            cap.release()
            raise RuntimeError("Failed to initialize OpenCV VideoWriter with both mp4v and XVID codecs.")
    
    all_detections: List[Dict[str, Any]] = []
    processed_count = 0
    start_time = time.time()
    last_known_detections: List[Dict[str, Any]] = []
    cancelled = False
    
    try:
        frame_idx = 0
        while True:
            # Check for cancellation signal
            if cancel_check and cancel_check():
                cancelled = True
                break
                
            ret, frame = cap.read()
            if not ret or frame is None:
                break
                
            timestamp_sec = frame_idx / fps if fps > 0 else 0.0
            
            # Determine if this frame should be inferred or skipped
            should_infer = (frame_idx % frame_skip == 0)
            
            if should_infer:
                annotated, frame_dets = process_frame(
                    frame=frame,
                    models=models,
                    conf_threshold=conf_threshold,
                    frame_idx=frame_idx,
                    timestamp_sec=timestamp_sec
                )
                last_known_detections = frame_dets
                all_detections.extend(frame_dets)
            else:
                # Reuse persistent detections on skipped frames to maintain visual continuity
                annotated = draw_detections(
                    frame=frame,
                    detections=last_known_detections,
                    frame_idx=frame_idx,
                    timestamp_sec=timestamp_sec
                )
            
            # Write annotated frame to output video
            out.write(annotated)
            processed_count += 1
            frame_idx += 1
            
            # Progress callback for UI updates
            if progress_callback and (frame_idx % 2 == 0 or frame_idx == total_frames):
                elapsed = time.time() - start_time
                current_fps = processed_count / elapsed if elapsed > 0 else 0.0
                progress_callback({
                    "current_frame": frame_idx,
                    "total_frames": total_frames,
                    "progress_ratio": min(1.0, frame_idx / total_frames) if total_frames > 0 else 0.0,
                    "elapsed_sec": round(elapsed, 1),
                    "processing_fps": round(current_fps, 1),
                    "total_detections_so_far": len(all_detections)
                })
                
    finally:
        cap.release()
        out.release()
        
    total_processing_time = max(0.001, time.time() - start_time)
    avg_processing_fps = processed_count / total_processing_time
    
    # Verify raw output video
    verified, v_info = verify_output_video(active_output_path)
    if not verified:
        raise RuntimeError(f"Output video verification failed: {v_info.get('error')}")
    
    # Transcode with imageio-ffmpeg for native browser playback if available
    web_playable_path = os.path.join(output_dir, f"{base_name}_web_{timestamp_tag}.mp4")
    final_video_path = active_output_path
    if HAS_IMAGEIO_FFMPEG:
        if reencode_for_web(active_output_path, web_playable_path):
            final_video_path = web_playable_path
            
    # Generate structured summary statistics
    summary = generate_detection_summary(
        detections=all_detections,
        processed_frames=processed_count,
        total_time_sec=total_processing_time,
        processing_fps=avg_processing_fps,
        cancelled=cancelled
    )
    
    return final_video_path, summary


def generate_detection_summary(
    detections: List[Dict[str, Any]],
    processed_frames: int,
    total_time_sec: float,
    processing_fps: float,
    cancelled: bool = False
) -> Dict[str, Any]:
    """
    Computes class breakdowns, confidence aggregates, and frame-wise detection records.
    """
    potholes = [d for d in detections if d["class_name"] == "Pothole"]
    longitudinal = [d for d in detections if d["class_name"] == "Longitudinal Crack"]
    transverse = [d for d in detections if d["class_name"] == "Transverse Crack"]
    alligator = [d for d in detections if d["class_name"] == "Alligator Crack"]
    
    confs = [d["confidence"] for d in detections]
    avg_conf = float(np.mean(confs)) if confs else 0.0
    max_conf = float(np.max(confs)) if confs else 0.0
    
    # Format tabular rows for UI display
    table_rows = []
    for d in detections:
        box_str = f"[{d['box'][0]}, {d['box'][1]}, {d['box'][2]}, {d['box'][3]}]"
        table_rows.append({
            "Frame": d["frame_idx"],
            "Timestamp": d["timestamp_str"],
            "Defect": d["class_name"],
            "Confidence": f"{d['confidence']:.1%}",
            "Bounding Box": box_str,
            "Area (px)": d["area_pixels"],
            "Source": d["model_source"]
        })
        
    return {
        "status": "cancelled" if cancelled else "completed",
        "processed_frames": processed_frames,
        "total_detections": len(detections),
        "pothole_detections": len(potholes),
        "longitudinal_crack_detections": len(longitudinal),
        "transverse_crack_detections": len(transverse),
        "alligator_crack_detections": len(alligator),
        "average_confidence": round(avg_conf, 3),
        "average_confidence_pct": f"{avg_conf:.1%}",
        "max_confidence": round(max_conf, 3),
        "max_confidence_pct": f"{max_conf:.1%}",
        "processing_time_sec": round(total_time_sec, 2),
        "processing_fps": round(processing_fps, 2),
        "table_rows": table_rows
    }
