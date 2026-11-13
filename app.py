import os
import csv
import io
import json
import time
import html
import tempfile
from pathlib import Path
from datetime import datetime

import cv2
import numpy as np
import streamlit as st
from PIL import Image, ExifTags
from ultralytics import YOLO
from huggingface_hub import hf_hub_download

# Optional Gemini integration (graceful fallback if gRPC/cygrpc is blocked by AppControl)
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except Exception:
    HAS_GEMINI = False
    genai = None

import video_detector as vd
import duplicate_detector as dd
import progress_monitor as pm
import risk_scorer as rs
import severity_classifier as sc
import location_metadata as lm
import inspection_store as istore

# ==========================================
# 1. PAGE CONFIG & CUSTOM CSS
# ==========================================
st.set_page_config(page_title="RoadSentinel AI", page_icon="🛣️", layout="wide")

st.markdown("""
<style>
    /* Dark Theme */
    .stApp { background-color: #121212; color: #ffffff; }
    header {visibility: hidden;}

    /* Header Styling */
    .top-header {
        display: flex; align-items: center; justify-content: space-between;
        border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px;
    }
    .title-text { font-size: 24px; font-weight: bold; color: #FFD700; line-height: 1.2; }
    .subtitle-text { font-size: 11px; color: #888; letter-spacing: 1px; }

    /* Side Panel Cards */
    .side-card {
        background-color: #1e1e1e; border: 1px solid #333;
        border-radius: 8px; padding: 15px; margin-bottom: 15px;
    }
    .card-title {
        color: #FFD700; font-size: 12px; font-weight: bold;
        margin-bottom: 10px; letter-spacing: 1px;
    }

    /* Detection List */
    .detect-item {
        display: flex; justify-content: space-between;
        padding: 6px 0; font-size: 13px; border-bottom: 1px solid #333;
    }
    .dot { height: 10px; width: 10px; border-radius: 50%; display: inline-block; margin-right: 8px; }

    /* Bottom Metrics */
    .metric-box {
        background-color: #1e1e1e; border: 1px solid #333;
        border-radius: 5px; padding: 10px; text-align: left;
    }
    .metric-val { font-size: 20px; font-weight: bold; color: #FFD700; }
    .metric-label { font-size: 11px; color: #888; }

    /* Badges */
    .badge {
        display: inline-block; padding: 2px 8px; font-size: 11px;
        font-weight: bold; border-radius: 4px; margin-right: 5px;
    }
    .badge-info { background-color: #17a2b8; color: #fff; }
    .badge-success { background-color: #28a745; color: #fff; }
    .badge-warn { background-color: #ffc107; color: #000; }
    .badge-orange { background-color: #fd7e14; color: #fff; }
    .badge-danger { background-color: #dc3545; color: #fff; }
    .badge-pending { background-color: #6c757d; color: #fff; }
    .badge-loc { background-color: #20c997; color: #000; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 12px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #1e1e1e;
        border-radius: 6px;
        color: #ddd;
        padding: 8px 16px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2a2a2a !important;
        color: #FFD700 !important;
        border-bottom: 2px solid #FFD700 !important;
    }

    /* Buttons */
    .stButton>button { background-color: transparent; color: #FFD700; border: 1px solid #FFD700; border-radius: 5px; }
    .stButton>button:hover { background-color: #FFD700; color: #000; }

    /* Detection table */
    .det-table { border-collapse: collapse; width: 100%; font-size: 12px; color: #ddd; }
    .det-table th { background: #2a2a2a; color: #FFD700; padding: 6px 8px; text-align: left; border-bottom: 1px solid #444; }
    .det-table td { padding: 5px 8px; border-bottom: 1px solid #2a2a2a; }
    .det-table tr:hover td { background: #1e1e1e; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. LOAD MODELS & INIT STATE
# ==========================================
@st.cache_resource
def load_models():
    """Loads YOLO models with local weight caching and remote HuggingFace fallback."""
    models = {}
    with st.spinner("Loading models (local cache with HF Hub fallback)..."):
        local_t1 = Path("weights/rdd2022_yolov8m.pt")
        local_t2 = Path("weights/pothole_yolov8.pt")

        # Tier 1: General RDD2022 multi-class model
        try:
            if local_t1.exists():
                models["Tier 1 (RDD2022)"] = YOLO(str(local_t1))
            else:
                t1_path = hf_hub_download(repo_id="dronefreak/rdd2022-yolov8m", filename="best.pt")
                models["Tier 1 (RDD2022)"] = YOLO(t1_path)
        except Exception as e:
            st.error(f"Failed to load Tier 1: {e}")

        # Tier 2: Pothole-specific model
        try:
            if local_t2.exists():
                models["Tier 2 (Pothole)"] = YOLO(str(local_t2))
            else:
                t2_path = hf_hub_download(repo_id="samdutse/pothole-yolov8", filename="best.pt")
                models["Tier 2 (Pothole)"] = YOLO(t2_path)
        except Exception as e:
            st.warning(f"Tier 2 unavailable: {e}")

        # Tier 3 is optional
        t3_repo = os.getenv("FINE_TUNED_MODEL_REPO")
        if t3_repo:
            try:
                t3_path = hf_hub_download(repo_id=t3_repo, filename="best.pt")
                models["Tier 3 (Fine-Tuned)"] = YOLO(t3_path)
            except Exception as e:
                st.warning(f"Tier 3 unavailable: {e}")

    return models


models = load_models()
device_info = vd.get_device_info()

# Initialize session state from persistent JSON store
if "dispatch_history" not in st.session_state:
    st.session_state.dispatch_history = istore.load_all_inspections()
if "current_report" not in st.session_state:
    st.session_state.current_report = None
if "video_report" not in st.session_state:
    st.session_state.video_report = None

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def validate_with_gemini(api_key, image):
    """Sends image to Gemini to count potholes (optional verification)."""
    if not HAS_GEMINI or genai is None:
        return {
            "error": "Gemini unavailable: gRPC binary restricted by Windows Application Control policy.",
            "pothole_count": 0,
            "crack_count": 0,
            "reasoning": "Gemini disabled by system security policy; YOLO autonomous detection active."
        }
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = """Analyze this road image carefully.
        Count the number of distinct potholes and distinct cracks.
        Respond ONLY with a valid JSON object:
        {"pothole_count": <int>, "crack_count": <int>, "reasoning": "<short explanation>"}"""
        response = model.generate_content([prompt, image])
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        return {"error": str(e), "pothole_count": 0, "crack_count": 0}


def cascade_predict(image_source, conf_threshold):
    """
    Ensemble inference for image input.
    Runs Tier 1 and Tier 2, returning result, model_name, and class counts.
    """
    if not models:
        return None, "No models loaded", {}

    last_result = None

    for model_name, model in models.items():
        try:
            r = model.predict(source=image_source, conf=conf_threshold, verbose=False)[0]
            last_result = r
            if len(r.boxes) > 0:
                counts = {"potholes": 0, "longitudinal": 0, "transverse": 0, "alligator": 0}
                for c in r.boxes.cls.tolist():
                    c_name = r.names[int(c)].lower()
                    canonical = vd.normalize_class_name(c_name)
                    if canonical == "Pothole":
                        counts["potholes"] += 1
                    elif canonical == "Longitudinal Crack":
                        counts["longitudinal"] += 1
                    elif canonical == "Transverse Crack":
                        counts["transverse"] += 1
                    elif canonical == "Alligator Crack":
                        counts["alligator"] += 1
                return r, model_name, counts
        except Exception:
            pass

    return last_result, "No detections (All Tiers)", {
        "potholes": 0, "longitudinal": 0, "transverse": 0, "alligator": 0
    }


def render_html_table(rows, max_height=300):
    """Renders a list of dicts as a styled HTML table (no pandas required)."""
    if not rows:
        return ""
    headers = list(rows[0].keys())
    header_html = "<tr>" + "".join(
        f'<th class="det-table">{html.escape(str(h))}</th>' for h in headers
    ) + "</tr>"
    body_html = ""
    for row in rows:
        body_html += "<tr>" + "".join(
            f'<td>{html.escape(str(row.get(h, "")))}</td>' for h in headers
        ) + "</tr>"
    return (
        f'<div style="overflow-x:auto;max-height:{max_height}px;overflow-y:auto">'
        f'<table class="det-table">{header_html}{body_html}</table></div>'
    )


def _verification_badge(status):
    """Returns HTML badge for a verification status string."""
    badges = {
        "AI_PENDING": '<span class="badge badge-pending">🤖 AI_PENDING</span>',
        "VERIFIED":   '<span class="badge badge-success">✅ VERIFIED</span>',
        "REJECTED":   '<span class="badge badge-danger">❌ REJECTED</span>',
    }
    return badges.get(status, f'<span class="badge badge-info">{html.escape(str(status))}</span>')


def _severity_badge(sev):
    """Returns HTML badge for a severity category."""
    badges = {
        "MINOR":    '<span class="badge badge-success">🟢 MINOR</span>',
        "MODERATE": '<span class="badge badge-warn">🟡 MODERATE</span>',
        "SEVERE":   '<span class="badge badge-orange">🟠 SEVERE</span>',
        "CRITICAL": '<span class="badge badge-danger">🔴 CRITICAL</span>',
    }
    return badges.get(sev, f'<span class="badge badge-info">{html.escape(str(sev))}</span>')


def _make_csv_bytes(dispatch_history):
    """Generates CSV bytes from dispatch history using stdlib csv (no pandas)."""
    fieldnames = [
        "Inspection ID", "Type", "Date", "Location", "Latitude", "Longitude",
        "Location Source", "Potholes", "Cracks", "Longitudinal", "Transverse", "Alligator",
        "Overall Severity", "Avg Severity Score", "Risk", "Avg Confidence",
        "Verification Status", "Corrected Severity", "Corrected Class"
    ]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for rep in dispatch_history:
        loc_dict = rep.get("location_metadata", {})
        summ = rep.get("summary", {})
        verif = rep.get("verification", {})
        writer.writerow({
            "Inspection ID": rep.get("inspection_id", ""),
            "Type": rep.get("media_type") or rep.get("type", ""),
            "Date": rep.get("date", ""),
            "Location": rep.get("location") or loc_dict.get("address", "Location unavailable"),
            "Latitude": rep.get("latitude") if rep.get("latitude") is not None else loc_dict.get("latitude", ""),
            "Longitude": rep.get("longitude") if rep.get("longitude") is not None else loc_dict.get("longitude", ""),
            "Location Source": rep.get("location_source") or loc_dict.get("location_source", ""),
            "Potholes": rep.get("final_potholes", summ.get("pothole_count", 0)),
            "Cracks": rep.get("final_cracks", summ.get("crack_count", 0)),
            "Longitudinal": rep.get("longitudinal_cracks", summ.get("longitudinal_cracks", 0)),
            "Transverse": rep.get("transverse_cracks", summ.get("transverse_cracks", 0)),
            "Alligator": rep.get("alligator_cracks", summ.get("alligator_cracks", 0)),
            "Overall Severity": rep.get("overall_severity") or summ.get("overall_severity", "MINOR"),
            "Avg Severity Score": rep.get("average_severity_score") or summ.get("average_severity_score", ""),
            "Risk": rep.get("risk_category") or summ.get("risk_category", ""),
            "Avg Confidence": rep.get("avg_conf", ""),
            "Verification Status": verif.get("status") or rep.get("verification_status", "AI_PENDING"),
            "Corrected Severity": verif.get("corrected_severity") or rep.get("corrected_severity", ""),
            "Corrected Class": verif.get("corrected_class") or rep.get("corrected_class", ""),
        })
    return buf.getvalue().encode("utf-8")


def _init_report_defaults(rep):
    """Ensures all required verification/tracking/severity fields exist on a report dict."""
    if "inspection_id" not in rep or not rep["inspection_id"]:
        rep["inspection_id"] = istore.generate_inspection_id()

    rep.setdefault("verification_status", "AI_PENDING")
    rep.setdefault("verified_by", None)
    rep.setdefault("verified_at", None)
    rep.setdefault("corrected_class", None)
    rep.setdefault("corrected_severity", None)
    rep.setdefault("rejection_reason", None)
    rep.setdefault("overall_severity", "MINOR")
    rep.setdefault("average_severity_score", 20.0)
    rep.setdefault("severity_breakdown", {"MINOR": 0, "MODERATE": 0, "SEVERE": 0, "CRITICAL": 0})
    rep.setdefault("original_ai_prediction", {
        "potholes": rep.get("final_potholes", 0),
        "cracks": rep.get("final_cracks", 0),
        "overall_severity": rep.get("overall_severity", "MINOR")
    })
    rep.setdefault("duplicate_status", None)
    rep.setdefault("risk_category", "Low")
    rep.setdefault("location_source", "UNAVAILABLE")
    rep.setdefault("latitude", None)
    rep.setdefault("longitude", None)
    return rep


# ==========================================
# 4. SIDEBAR NAVIGATION
# ==========================================
with st.sidebar:
    st.markdown("### Navigation")
    page = st.radio("Go to", [
        "📸 Detection Studio",
        "📋 Dispatch Center",
        "📊 Analytics"
    ])
    st.divider()

    st.markdown("### Settings")
    gemini_api_key = st.text_input(
        "Gemini API Key", type="password",
        help="Optional: For single-photo Gemini cross-validation."
    )
    conf = st.slider("YOLO Confidence", 0.05, 0.90, 0.20, 0.05)

    st.divider()
    st.markdown("### Hardware Status")
    if device_info["cuda_available"]:
        st.success(f"⚡ GPU: {device_info['device_name']}")
    else:
        st.info(f"💻 CPU: {device_info['device_name']}")

    st.divider()
    record_count = istore.count_inspections()
    st.caption(f"📁 Local Store: `data/inspections.json` ({record_count} records)")
    st.caption("RoadSentinel v2.0 AI Engine")


# ==========================================
# PAGE 1: DETECTION STUDIO
# ==========================================
if page == "📸 Detection Studio":
    st.markdown("""
    <div class="top-header">
        <div>
            <div class="title-text">⬥ DETECTION STUDIO</div>
            <div class="subtitle-text">AI ROAD DAMAGE DETECTION — VIDEO & PHOTO PIPELINE</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab_video, tab_photo = st.tabs(["🎥 Video Detection Engine", "📸 Photo Studio"])

    # ------------------------------------------------------------------
    # TAB 1: VIDEO DETECTION ENGINE
    # ------------------------------------------------------------------
    with tab_video:
        st.markdown("""
        <div class="side-card">
            <div class="card-title">VIDEO INFERENCE PIPELINE</div>
            <p style="font-size: 13px; color: #ccc; margin: 0;">
                Upload a dashcam or road survey video. The AI engine processes frames sequentially,
                detects potholes and crack variants via YOLOv8, tracks unique hazards with IoU-based
                centroid tracking, assesses damage severity, scores risk heuristically, annotates bounding boxes,
                and generates an annotated clip.
            </p>
        </div>
        """, unsafe_allow_html=True)

        vid_col_upload, vid_col_controls = st.columns([2, 1])

        with vid_col_upload:
            video_file = st.file_uploader(
                "Upload Road Video",
                type=["mp4", "avi", "mov", "mkv"],
                help="Supported formats: .mp4, .avi, .mov, .mkv. Max file size: 500 MB."
            )
            gpx_file = st.file_uploader(
                "Optional: Attach GPX GPS Track (.gpx)",
                type=["gpx"],
                help="Synchronize video frames with recorded GPS trackpoints from survey device."
            )

        with vid_col_controls:
            st.markdown('<div class="side-card"><div class="card-title">INFERENCE & GPS CONTROLS</div>', unsafe_allow_html=True)
            v_conf = st.slider("Detection Confidence", 0.05, 0.90, float(conf), 0.05, key="video_conf_slider")
            frame_skip_option = st.selectbox(
                "Frame Sampling (Skip)",
                options=[1, 2, 3, 5],
                format_func=lambda x: f"{x} - {'Process Every Frame (Highest Accuracy)' if x == 1 else f'Process Every {x} Frames (Faster Scan)'}",
                key="video_frame_skip"
            )
            gpx_offset = st.number_input(
                "GPX Sync Offset (seconds)",
                value=0.0, step=0.5,
                help="Offset between video start and GPX track start in seconds."
            )
            st.markdown('</div>', unsafe_allow_html=True)

        # Manual location coordinates override for video
        with st.expander("📍 Manual Location Coordinates (Optional override if GPS absent)"):
            m_lat_col, m_lon_col = st.columns(2)
            with m_lat_col:
                v_manual_lat = st.text_input("Manual Latitude", placeholder="e.g. 15.8497", key="v_man_lat")
            with m_lon_col:
                v_manual_lon = st.text_input("Manual Longitude", placeholder="e.g. 74.4977", key="v_man_lon")

        if video_file is not None:
            temp_dir = tempfile.gettempdir()
            clean_name = Path(video_file.name).stem
            suffix = Path(video_file.name).suffix.lower()
            temp_video_path = os.path.join(temp_dir, f"roadsentinel_upload_{clean_name}{suffix}")

            with open(temp_video_path, "wb") as f:
                f.write(video_file.getbuffer())

            is_valid, val_msg = vd.validate_video(temp_video_path)
            if not is_valid:
                st.error(f"❌ Video Validation Failed: {val_msg}")
            else:
                meta = vd.get_video_metadata(temp_video_path)

                # Parse GPX if uploaded
                gpx_trackpoints = []
                if gpx_file is not None:
                    gpx_bytes = gpx_file.getvalue()
                    gpx_trackpoints = lm.parse_gpx_file(gpx_bytes)
                    if gpx_trackpoints:
                        st.success(f"📍 GPX sidecar parsed: {len(gpx_trackpoints)} trackpoints recorded.")
                    else:
                        st.warning("⚠️ GPX file parsed but contains 0 valid trackpoints.")

                st.markdown("#### 📋 Video Properties")
                m1, m2, m3, m4, m5, m6 = st.columns(6)
                with m1: st.markdown(f'<div class="metric-box"><div class="metric-val">{meta["file_size_mb"]} MB</div><div class="metric-label">FILE SIZE</div></div>', unsafe_allow_html=True)
                with m2: st.markdown(f'<div class="metric-box"><div class="metric-val">{meta["resolution"]}</div><div class="metric-label">RESOLUTION</div></div>', unsafe_allow_html=True)
                with m3: st.markdown(f'<div class="metric-box"><div class="metric-val">{meta["fps"]}</div><div class="metric-label">SOURCE FPS</div></div>', unsafe_allow_html=True)
                with m4: st.markdown(f'<div class="metric-box"><div class="metric-val">{meta["total_frames"]}</div><div class="metric-label">TOTAL FRAMES</div></div>', unsafe_allow_html=True)
                with m5: st.markdown(f'<div class="metric-box"><div class="metric-val">{meta["duration_str"]}</div><div class="metric-label">DURATION</div></div>', unsafe_allow_html=True)
                with m6: st.markdown(f'<div class="metric-box"><div class="metric-val">{meta["codec"]}</div><div class="metric-label">CODEC</div></div>', unsafe_allow_html=True)

                st.write("")

                col_prev, col_act = st.columns([2, 1])
                with col_prev:
                    st.markdown("**Original Video Preview:**")
                    st.video(temp_video_path)

                with col_act:
                    st.markdown('<div class="side-card"><div class="card-title">EXECUTE DETECTION</div>', unsafe_allow_html=True)
                    st.write(f"⚙️ Confidence Threshold: **{int(v_conf*100)}%**")
                    st.write(f"⚙️ Frame Step: **{frame_skip_option}**")
                    st.write(f"⚙️ Target Frames: **{meta['total_frames'] // frame_skip_option}**")

                    start_processing = st.button("🚀 Run Video Detection", type="primary", use_container_width=True)
                    clear_processing = st.button("🔄 Clear Video / Reset", use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)

                if clear_processing:
                    st.session_state.video_report = None
                    if os.path.exists(temp_video_path):
                        try:
                            os.remove(temp_video_path)
                        except Exception:
                            pass
                    st.rerun()

                if start_processing:
                    progress_container = st.container()
                    with progress_container:
                        st.markdown("---")
                        st.markdown("### ⚙️ Processing Video Stream...")

                        prog_bar = st.progress(0.0)
                        status_text = st.empty()

                        s_c1, s_c2, s_c3, s_c4 = st.columns(4)
                        m_frame = s_c1.empty()
                        m_speed = s_c2.empty()
                        m_time = s_c3.empty()
                        m_det = s_c4.empty()

                        def update_progress(data):
                            ratio = data.get("progress_ratio", 0.0)
                            prog_bar.progress(ratio)
                            cur = data.get("current_frame", 0)
                            tot = data.get("total_frames", 0)
                            fps_val = data.get("processing_fps", 0.0)
                            el_sec = data.get("elapsed_sec", 0.0)
                            dets = data.get("total_detections_so_far", 0)
                            status_text.markdown(f"**Processing Frame {cur} of {tot} ({int(ratio * 100)}%)**")
                            m_frame.metric("Current Frame", f"{cur} / {tot}")
                            m_speed.metric("Processing FPS", f"{fps_val} fps")
                            m_time.metric("Elapsed Time", f"{el_sec} s")
                            m_det.metric("Detections", f"{dets}")

                        try:
                            output_dir = os.path.join(os.getcwd(), "outputs")
                            annotated_video_path, summary = vd.process_video(
                                video_path=temp_video_path,
                                output_dir=output_dir,
                                models=models,
                                conf_threshold=v_conf,
                                frame_skip=frame_skip_option,
                                progress_callback=update_progress
                            )

                            # Resolve location from GPX or manual input
                            v_lat, v_lon = None, None
                            v_address = "Location unavailable"
                            v_loc_source = "UNAVAILABLE"

                            if gpx_trackpoints:
                                sync_pt = lm.match_video_timestamp_to_gpx(0.0, gpx_trackpoints, gpx_offset)
                                if sync_pt.get("latitude") is not None:
                                    v_lat = sync_pt["latitude"]
                                    v_lon = sync_pt["longitude"]
                                    v_loc_source = "GPX"
                                    v_address = f"GPS (GPX): {v_lat:.6f}, {v_lon:.6f}"
                            elif v_manual_lat and v_manual_lon:
                                try:
                                    v_lat = float(v_manual_lat.strip())
                                    v_lon = float(v_manual_lon.strip())
                                    v_loc_source = "MANUAL"
                                    v_address = f"GPS (Manual): {v_lat:.6f}, {v_lon:.6f}"
                                except Exception:
                                    pass

                            st.session_state.video_report = {
                                "meta": meta,
                                "annotated_path": annotated_video_path,
                                "summary": summary,
                                "conf_used": v_conf,
                                "date": datetime.now().strftime("%d %b %Y, %H:%M"),
                                "location_metadata": {
                                    "latitude": v_lat,
                                    "longitude": v_lon,
                                    "address": v_address,
                                    "location_source": v_loc_source
                                }
                            }
                            st.success("✅ Video processing and annotation completed successfully!")
                        except Exception as ex:
                            st.error(f"❌ Video Processing Failed: {ex}")

                # Render Video Detection Results
                if st.session_state.video_report:
                    rep_v = st.session_state.video_report
                    sum_v = rep_v["summary"]
                    ann_path = rep_v["annotated_path"]

                    st.markdown("---")
                    st.markdown("### 🎬 Annotated Video & Results")

                    col_vid_left, col_vid_right = st.columns([1.5, 1])

                    with col_vid_left:
                        if os.path.exists(ann_path):
                            st.markdown("**Annotated Output Video:**")
                            st.video(ann_path)
                            with open(ann_path, "rb") as vf:
                                v_bytes = vf.read()
                            st.download_button(
                                label="📥 Download Annotated Video",
                                data=v_bytes,
                                file_name=f"RoadSentinel_Annotated_{rep_v['meta']['filename']}",
                                mime="video/mp4",
                                type="primary",
                                use_container_width=True
                            )
                        else:
                            st.warning("Processed video output file not found.")

                    with col_vid_right:
                        st.markdown('<div class="side-card"><div class="card-title">VIDEO DETECTION BREAKDOWN</div>', unsafe_allow_html=True)

                        classes_v = {
                            "Longitudinal Crack": {"count": sum_v["longitudinal_crack_detections"], "color": "#00BFFF"},
                            "Transverse Crack":   {"count": sum_v["transverse_crack_detections"],   "color": "#9370DB"},
                            "Alligator Crack":    {"count": sum_v["alligator_crack_detections"],    "color": "#32CD32"},
                            "Pothole":            {"count": sum_v["pothole_detections"],            "color": "#FF6347"}
                        }

                        for cls_k, cls_d in classes_v.items():
                            st.markdown(f"""
                            <div class="detect-item">
                                <span><span class="dot" style="background-color:{cls_d['color']};"></span>{cls_k.upper()}</span>
                                <span><b>{cls_d['count']}</b></span>
                            </div>
                            """, unsafe_allow_html=True)

                        st.markdown("---")
                        st.write(f"**Total Frame Detections:** {sum_v['total_detections']}")

                        unique_count = sum_v.get("unique_hazard_count")
                        if unique_count is not None:
                            st.write(f"**Unique Tracked Hazards:** {unique_count}")
                            st.caption("⚠️ Heuristic estimate — not physically validated")
                        else:
                            st.write("**Unique Tracked Hazards:** N/A")

                        # Severity breakdown
                        sev_bk = sum_v.get("severity_breakdown", {})
                        overall_sev = sum_v.get("overall_severity", "MINOR")
                        st.markdown("---")
                        st.markdown(f"**Overall Severity:** {_severity_badge(overall_sev)}", unsafe_allow_html=True)
                        st.write(f"Critical: {sev_bk.get('CRITICAL', 0)} | Severe: {sev_bk.get('SEVERE', 0)} | Moderate: {sev_bk.get('MODERATE', 0)} | Minor: {sev_bk.get('MINOR', 0)}")
                        st.caption("⚠️ Visual 2D estimate only. Does not measure physical depth or volume.")

                        # Risk distribution
                        risk_dist = sum_v.get("risk_distribution", {})
                        if any(risk_dist.values()):
                            st.markdown("---")
                            st.markdown("**🎯 Risk Distribution:**")
                            risk_colors = {"Low": "🟢", "Medium": "🟡", "High": "🟠", "Critical": "🔴"}
                            for cat, count in risk_dist.items():
                                st.write(f"{risk_colors.get(cat, '')} {cat}: **{count}**")
                            st.caption("⚠️ Heuristic risk estimate — not a validated accident probability")

                        st.markdown('</div>', unsafe_allow_html=True)

                    # Dispatch button (outside both columns)
                    if st.button("📋 Push Video Summary to Dispatch Center", use_container_width=True):
                        v_loc = rep_v.get("location_metadata", {})
                        risk_dist = sum_v.get("risk_distribution", {})
                        if risk_dist.get("Critical", 0) > 0:
                            v_risk = "Critical"
                        elif risk_dist.get("High", 0) > 0:
                            v_risk = "High"
                        elif risk_dist.get("Medium", 0) > 0:
                            v_risk = "Medium"
                        else:
                            v_risk = "Low"

                        new_id = istore.generate_inspection_id()
                        dispatch_entry = _init_report_defaults({
                            "inspection_id": new_id,
                            "type": "Video Inspection",
                            "media_type": "video",
                            "filename": rep_v["meta"]["filename"],
                            "location": v_loc.get("address", "Location unavailable"),
                            "latitude": v_loc.get("latitude"),
                            "longitude": v_loc.get("longitude"),
                            "location_source": v_loc.get("location_source", "UNAVAILABLE"),
                            "location_metadata": v_loc,
                            "date": rep_v["date"],
                            "final_potholes": sum_v["pothole_detections"],
                            "final_cracks": (
                                sum_v["longitudinal_crack_detections"]
                                + sum_v["transverse_crack_detections"]
                                + sum_v["alligator_crack_detections"]
                            ),
                            "longitudinal_cracks": sum_v["longitudinal_crack_detections"],
                            "transverse_cracks": sum_v["transverse_crack_detections"],
                            "alligator_cracks": sum_v["alligator_crack_detections"],
                            "avg_conf": sum_v["average_confidence_pct"],
                            "conflict": False,
                            "unique_hazard_count": sum_v.get("unique_hazard_count"),
                            "overall_severity": sum_v.get("overall_severity", "MINOR"),
                            "severity_breakdown": sum_v.get("severity_breakdown", {}),
                            "average_severity_score": sum_v.get("average_severity_score", 0.0),
                            "risk_category": v_risk,
                            "summary": {
                                "pothole_count": sum_v["pothole_detections"],
                                "crack_count": (
                                    sum_v["longitudinal_crack_detections"]
                                    + sum_v["transverse_crack_detections"]
                                    + sum_v["alligator_crack_detections"]
                                ),
                                "overall_severity": sum_v.get("overall_severity", "MINOR"),
                                "average_severity_score": sum_v.get("average_severity_score", 0.0),
                                "risk_category": v_risk
                            }
                        })

                        # Persist to local JSON store
                        istore.save_inspection(dispatch_entry)
                        st.session_state.dispatch_history.insert(0, dispatch_entry)
                        st.success(f"Video inspection record #{new_id} saved to Dispatch Center & JSON Store!")

                    # Frame-level Detection Table
                    st.markdown("#### 📊 Frame-Wise Detection Log")
                    st.caption("ℹ️ Detections are frame-level observations. Track ID shows hazard continuity. Severity is visual 2D proxy.")
                    if sum_v["table_rows"]:
                        table_html = render_html_table(sum_v["table_rows"], max_height=300)
                        st.markdown(table_html, unsafe_allow_html=True)
                    else:
                        st.info("No road distress detected in the sampled frames at the selected confidence threshold.")

        else:
            st.info("👋 Upload a video file (.mp4, .avi, .mov, .mkv) above to begin automated road damage detection.")

    # ------------------------------------------------------------------
    # TAB 2: PHOTO STUDIO
    # ------------------------------------------------------------------
    with tab_photo:
        col_img, col_stats = st.columns([2.5, 1])

        with col_img:
            up = st.file_uploader("Upload Road Photo", type=["jpg", "jpeg", "png"], label_visibility="collapsed")

            # Manual location override for photo if EXIF is absent
            with st.expander("📍 Manual GPS Coordinates (Optional override if image lacks EXIF)"):
                p_lat_c, p_lon_c = st.columns(2)
                with p_lat_c:
                    p_manual_lat = st.text_input("Latitude", placeholder="e.g. 15.8497", key="p_man_lat")
                with p_lon_c:
                    p_manual_lon = st.text_input("Longitude", placeholder="e.g. 74.4977", key="p_man_lon")

            if up:
                image = Image.open(up).convert("RGB")
                img_w, img_h = image.size

                # Extract authentic GPS metadata without hardcoded fallbacks
                exif_meta = lm.extract_image_location_metadata(image)
                if p_manual_lat and p_manual_lon:
                    try:
                        exif_meta["latitude"] = float(p_manual_lat.strip())
                        exif_meta["longitude"] = float(p_manual_lon.strip())
                        exif_meta["location_source"] = "MANUAL"
                        exif_meta["address"] = f"GPS (Manual): {exif_meta['latitude']:.6f}, {exif_meta['longitude']:.6f}"
                        exif_meta["has_gps"] = True
                    except Exception:
                        pass

                location_display = exif_meta["address"]

                # Display Location Metadata Pill
                if exif_meta["has_gps"]:
                    st.success(f"📍 Location: **{location_display}** (Source: {exif_meta['location_source']})")
                else:
                    st.warning("📍 **Location unavailable** (No EXIF GPS metadata found in uploaded image)")

                # 1. Run YOLO Cascade
                with st.spinner("Running YOLO Cascade..."):
                    result, model_used, counts = cascade_predict(image, conf)
                    yolo_potholes = counts.get("potholes", 0)
                    yolo_longitudinal = counts.get("longitudinal", 0)
                    yolo_transverse = counts.get("transverse", 0)
                    yolo_alligator = counts.get("alligator", 0)
                    yolo_cracks = yolo_longitudinal + yolo_transverse + yolo_alligator

                    # Compute per-defect severity and summary
                    defect_classifications = []
                    if result and result.boxes is not None and len(result.boxes) > 0:
                        boxes_xyxy = result.boxes.xyxy.cpu().numpy()
                        confs = result.boxes.conf.cpu().numpy()
                        clss = result.boxes.cls.cpu().numpy().astype(int)
                        for b, cf, cid in zip(boxes_xyxy, confs, clss):
                            cname = vd.normalize_class_name(result.names.get(cid, str(cid)))
                            sev = sc.classify_defect_severity(
                                class_name=cname,
                                box=[int(v) for v in b],
                                frame_width=img_w,
                                frame_height=img_h,
                                confidence=float(cf)
                            )
                            defect_classifications.append(sev)

                        sev_summary = sc.compute_severity_summary(defect_classifications)
                        overall_sev = sev_summary["overall_severity"]
                        avg_sev_score = sev_summary["average_severity_score"]
                        sev_breakdown = sev_summary["breakdown"]
                    else:
                        overall_sev = "MINOR"
                        avg_sev_score = 0.0
                        sev_breakdown = {"MINOR": 0, "MODERATE": 0, "SEVERE": 0, "CRITICAL": 0}

                    if result:
                        st.image(result.plot()[:, :, ::-1], use_container_width=True)

                # 2. Run Gemini Validation (Optional)
                gemini_potholes = 0
                gemini_cracks = 0
                gemini_reason = "Gemini not called (No API Key)"
                if gemini_api_key:
                    with st.spinner("Gemini validating image..."):
                        gemini_data = validate_with_gemini(gemini_api_key, image)
                        gemini_potholes = gemini_data.get("pothole_count", 0)
                        gemini_cracks = gemini_data.get("crack_count", 0)
                        gemini_reason = gemini_data.get("reasoning", "No reasoning provided")

                # 3. Conflict Resolution
                final_potholes = max(yolo_potholes, gemini_potholes)
                final_cracks = max(yolo_cracks, gemini_cracks)
                conflict = (gemini_potholes > yolo_potholes) or (gemini_cracks > yolo_cracks)

                if conflict:
                    st.warning("⚠️ **Conflict Detected!** Gemini found more defects than YOLO. Report updated to match Gemini.")

                # Risk score for image detection
                image_risk = "Low"
                if yolo_potholes > 0:
                    image_risk = "High" if yolo_potholes >= 3 else "Medium" if yolo_potholes >= 1 else "Low"
                elif yolo_cracks > 0:
                    image_risk = "Medium" if yolo_cracks >= 3 else "Low"

                # Save state for Dispatch
                rep_id = istore.generate_inspection_id()
                st.session_state.current_report = _init_report_defaults({
                    "inspection_id": rep_id,
                    "type": "Photo Inspection",
                    "media_type": "photo",
                    "image": image,
                    "location": location_display,
                    "latitude": exif_meta["latitude"],
                    "longitude": exif_meta["longitude"],
                    "altitude_m": exif_meta.get("altitude_m"),
                    "location_source": exif_meta["location_source"],
                    "location_metadata": exif_meta,
                    "date": datetime.now().strftime("%d %b %Y, %H:%M"),
                    "final_potholes": final_potholes,
                    "final_cracks": final_cracks,
                    "longitudinal_cracks": yolo_longitudinal,
                    "transverse_cracks": yolo_transverse,
                    "alligator_cracks": yolo_alligator,
                    "yolo_potholes": yolo_potholes,
                    "gemini_potholes": gemini_potholes,
                    "gemini_reason": gemini_reason,
                    "conflict": conflict,
                    "model_used": model_used,
                    "overall_severity": overall_sev,
                    "severity_breakdown": sev_breakdown,
                    "average_severity_score": avg_sev_score,
                    "risk_category": image_risk,
                    "detections": defect_classifications,
                    "summary": {
                        "pothole_count": final_potholes,
                        "crack_count": final_cracks,
                        "overall_severity": overall_sev,
                        "average_severity_score": avg_sev_score,
                        "risk_category": image_risk
                    }
                })

        with col_stats:
            if st.session_state.current_report:
                rep = st.session_state.current_report

                st.markdown('<div class="side-card"><div class="card-title">DETECTED DEFECTS</div>', unsafe_allow_html=True)
                classes = {
                    "Longitudinal Crack": {"count": rep.get('longitudinal_cracks', 0), "color": "#00BFFF"},
                    "Transverse Crack":   {"count": rep.get('transverse_cracks', 0),   "color": "#9370DB"},
                    "Alligator Crack":    {"count": rep.get('alligator_cracks', 0),    "color": "#32CD32"},
                    "Pothole":            {"count": rep['final_potholes'],              "color": "#FF6347"}
                }

                for cls, data in classes.items():
                    st.markdown(f"""
                    <div class="detect-item">
                        <span><span class="dot" style="background-color:{data['color']};"></span>{cls.upper()}</span>
                        <span>{data['count']}</span>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("---")
                st.markdown(f"**Visual Severity:** {_severity_badge(rep.get('overall_severity', 'MINOR'))}", unsafe_allow_html=True)
                st.caption("⚠️ 2D visual estimate only. Does not measure physical depth or volume.")

                risk_cat = rep.get("risk_category", "")
                if risk_cat:
                    st.markdown(f"**Risk Estimate:** `{risk_cat}` *(heuristic only)*")

                st.markdown('</div>', unsafe_allow_html=True)

                st.markdown('<div class="side-card"><div class="card-title">REPORT SUMMARY</div>', unsafe_allow_html=True)
                report_text = f"ID: {rep.get('inspection_id')}\n{rep['final_cracks']} cracks, {rep['final_potholes']} potholes.\nLocation: {rep['location']}\nDate: {rep['date']}"
                st.code(report_text, language="text")

                if st.button("➡️ Save & Send to Dispatch Center", type="primary", use_container_width=True):
                    # Persist to local JSON store
                    istore.save_inspection(rep)
                    st.session_state.dispatch_history.insert(0, rep)
                    st.success(f"Report #{rep.get('inspection_id')} saved to Dispatch Center & JSON Store!")
                st.markdown('</div>', unsafe_allow_html=True)

                if rep['conflict']:
                    st.info(f"**Gemini Note:** {rep['gemini_reason']}")
                st.caption(f"⚡ Model Used: {rep['model_used']}")


# ==========================================
# PAGE 2: DISPATCH CENTER
# ==========================================
elif page == "📋 Dispatch Center":
    st.markdown("""
    <div class="top-header">
        <div>
            <div class="title-text">⬥ DISPATCH CENTER</div>
            <div class="subtitle-text">AUTHORITY ACTION, SEVERITY VERIFICATION & PROGRESS MONITORING</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    dispatch_tabs = st.tabs([
        "📄 Reports & Verification",
        "🔁 Duplicate Review",
        "📈 Progress Monitor"
    ])

    # ------------------------------------------------------------------
    # SUB-TAB: Reports & Verification
    # ------------------------------------------------------------------
    with dispatch_tabs[0]:
        if not st.session_state.dispatch_history:
            st.info("No reports pending dispatch. Go to the Detection Studio to analyze an image or video.")
        else:
            st.markdown(f"**{len(st.session_state.dispatch_history)} report(s) in local inspection registry (`data/inspections.json`).**")

            for idx, rep in enumerate(st.session_state.dispatch_history):
                _init_report_defaults(rep)
                rep_id = rep.get("inspection_id", f"RS-REP-{idx+1}")
                rep_type = rep.get("type") or rep.get("media_type", "Photo Inspection")
                v_status = rep.get("verification_status", "AI_PENDING")
                v_badge = _verification_badge(v_status)
                sev_cat = rep.get("overall_severity", "MINOR")
                s_badge = _severity_badge(sev_cat)

                # Duplicate flag
                dup_flag = ""
                if rep.get("duplicate_status") == "flagged":
                    dup_flag = ' <span class="badge badge-warn">⚠️ POSSIBLE DUPLICATE</span>'

                loc_str = rep.get("location") or "Location unavailable"
                label = f"[{rep_id}] {rep_type} — {loc_str} | {rep.get('final_potholes', 0)} Potholes, {rep.get('final_cracks', 0)} Cracks"

                with st.expander(label):
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        if "image" in rep and rep["image"] is not None:
                            st.image(rep["image"], use_container_width=True)
                        else:
                            st.markdown(f"📹 **Survey Video:** `{rep.get('filename', 'video')}`")
                            st.write(f"Longitudinal: {rep.get('longitudinal_cracks', 0)}")
                            st.write(f"Transverse: {rep.get('transverse_cracks', 0)}")
                            st.write(f"Alligator: {rep.get('alligator_cracks', 0)}")
                            if rep.get("unique_hazard_count") is not None:
                                st.write(f"**Unique Tracked Hazards:** {rep['unique_hazard_count']}")
                                st.caption("*(heuristic — not physically validated)*")

                    with c2:
                        st.markdown(f"**Inspection ID:** `{rep_id}`")
                        st.write(f"**Date:** {rep.get('date', 'Unknown')}")

                        # Authentic GPS coordinate representation
                        lat = rep.get("latitude")
                        lon = rep.get("longitude")
                        source = rep.get("location_source", "UNAVAILABLE")
                        if lat is not None and lon is not None:
                            st.markdown(f"**GPS Coordinates:** `{lat:.6f}, {lon:.6f}` <span class='badge badge-loc'>{source}</span>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"**Location:** `{loc_str}` <span class='badge badge-pending'>NO GPS</span>", unsafe_allow_html=True)

                        st.write(f"**Potholes:** {rep.get('final_potholes', 0)}  |  **Cracks:** {rep.get('final_cracks', 0)}")
                        st.markdown(f"**Verification:** {v_badge}{dup_flag}", unsafe_allow_html=True)
                        st.markdown(f"**Visual Severity:** {s_badge}", unsafe_allow_html=True)
                        st.caption("⚠️ Visual estimate only. Does not measure physical depth or volume.")

                        risk_cat = rep.get("risk_category", "")
                        if risk_cat:
                            risk_map = {"Low": "🟢", "Medium": "🟡", "High": "🟠", "Critical": "🔴"}
                            st.write(f"**Risk Estimate:** {risk_map.get(risk_cat, '')} {risk_cat} *(heuristic)*")

                        # Original AI prediction preservation
                        orig = rep.get("original_ai_prediction", {})
                        if rep.get("corrected_class") or rep.get("corrected_severity"):
                            st.info(
                                f"🤖 **Original AI Prediction:** {orig.get('potholes', 0)} potholes, "
                                f"{orig.get('cracks', 0)} cracks | Severity: {orig.get('overall_severity', 'MINOR')}"
                            )
                            if rep.get("corrected_class"):
                                st.write(f"✏️ **Corrected Class:** `{rep['corrected_class']}`")
                            if rep.get("corrected_severity"):
                                st.write(f"✏️ **Corrected Severity:** `{rep['corrected_severity']}`")

                        if rep.get("rejection_reason"):
                            st.error(f"Rejection reason: {rep['rejection_reason']}")

                    # Verification actions
                    st.markdown("---")
                    st.markdown("**🔎 Inspector Verification & Correction**")
                    vcol1, vcol2, vcol3, vcol4 = st.columns(4)

                    with vcol1:
                        if st.button("✅ Verify", key=f"verify_{rep_id}", use_container_width=True):
                            rep["verification_status"] = "VERIFIED"
                            rep["verified_by"] = "Authorized Inspector"
                            rep["verified_at"] = datetime.now().strftime("%d %b %Y, %H:%M")
                            istore.update_inspection(rep_id, {
                                "verification": {
                                    "status": "VERIFIED",
                                    "verified_by": rep["verified_by"],
                                    "verified_at": rep["verified_at"],
                                    "original_ai_prediction": rep.get("original_ai_prediction")
                                }
                            })
                            st.success(f"Report #{rep_id} verified.")
                            st.rerun()

                    with vcol2:
                        if st.button("❌ Reject", key=f"reject_{rep_id}", use_container_width=True):
                            rep["verification_status"] = "REJECTED"
                            rep["rejection_reason"] = "Marked as false detection during field review."
                            rep["verified_at"] = datetime.now().strftime("%d %b %Y, %H:%M")
                            istore.update_inspection(rep_id, {
                                "verification": {
                                    "status": "REJECTED",
                                    "rejection_reason": rep["rejection_reason"],
                                    "verified_at": rep["verified_at"]
                                }
                            })
                            st.error(f"Report #{rep_id} rejected.")
                            st.rerun()

                    with vcol3:
                        with st.popover("✏️ Correct"):
                            corr_class = st.selectbox(
                                "Correct Damage Class",
                                ["— No change —", "Pothole", "Longitudinal Crack", "Transverse Crack", "Alligator Crack"],
                                key=f"corr_cls_{rep_id}"
                            )
                            corr_sev = st.selectbox(
                                "Correct Damage Severity",
                                ["— No change —", "MINOR", "MODERATE", "SEVERE", "CRITICAL"],
                                key=f"corr_sev_{rep_id}"
                            )
                            if st.button("Apply Correction", key=f"apply_{rep_id}"):
                                if corr_class != "— No change —":
                                    rep["corrected_class"] = corr_class
                                if corr_sev != "— No change —":
                                    rep["corrected_severity"] = corr_sev
                                    rep["overall_severity"] = corr_sev
                                rep["verification_status"] = "VERIFIED"
                                rep["verified_at"] = datetime.now().strftime("%d %b %Y, %H:%M")
                                istore.update_inspection(rep_id, {
                                    "overall_severity": rep["overall_severity"],
                                    "verification": {
                                        "status": "VERIFIED",
                                        "corrected_class": rep.get("corrected_class"),
                                        "corrected_severity": rep.get("corrected_severity"),
                                        "verified_at": rep["verified_at"],
                                        "original_ai_prediction": rep.get("original_ai_prediction")
                                    }
                                })
                                st.rerun()

                    with vcol4:
                        if st.button("🚀 Dispatch", key=f"disp_{rep_id}", use_container_width=True):
                            st.success(f"✅ Report #{rep_id} dispatched to Municipal Road Maintenance Authority!")

    # ------------------------------------------------------------------
    # SUB-TAB: Duplicate Review
    # ------------------------------------------------------------------
    with dispatch_tabs[1]:
        st.markdown("### 🔁 Duplicate Report Detection")
        st.caption(
            "Compares reports by location similarity, damage types, and date proximity. "
            "Flagged reports require manual review — no automatic deletion."
        )

        history = st.session_state.dispatch_history
        if len(history) < 2:
            st.info("Need at least 2 reports in Dispatch Center to run duplicate analysis.")
        else:
            flagged_pairs = []
            for i in range(len(history)):
                matches = dd.find_duplicates(history[i], history, skip_index=i)
                for j, sim in matches:
                    if j > i:
                        flagged_pairs.append((i, j, sim))

            if not flagged_pairs:
                st.success("✅ No duplicate reports detected among current dispatch records.")
            else:
                st.warning(f"⚠️ {len(flagged_pairs)} possible duplicate pair(s) detected.")

                for i, j, sim in flagged_pairs:
                    rep_a = history[i]
                    rep_b = history[j]
                    score = sim["score"]
                    reasons = sim["reasons"]
                    breakdown = sim["breakdown"]

                    with st.expander(f"⚠️ [{rep_a.get('inspection_id', i+1)}] & [{rep_b.get('inspection_id', j+1)}] — Match: {score:.0%}"):
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.markdown(f"**Report #{rep_a.get('inspection_id', i+1)}**")
                            st.write(f"Location: {rep_a.get('location', '')}")
                            st.write(f"Date: {rep_a.get('date', '')}")
                            st.write(f"Potholes: {rep_a.get('final_potholes', 0)} | Cracks: {rep_a.get('final_cracks', 0)}")
                        with col_b:
                            st.markdown(f"**Report #{rep_b.get('inspection_id', j+1)}**")
                            st.write(f"Location: {rep_b.get('location', '')}")
                            st.write(f"Date: {rep_b.get('date', '')}")
                            st.write(f"Potholes: {rep_b.get('final_potholes', 0)} | Cracks: {rep_b.get('final_cracks', 0)}")

                        st.markdown("**Similarity Factors:**")
                        for r in reasons:
                            st.write(f"• {r}")
                        st.write(
                            f"Breakdown — Location: {breakdown['location']:.0%} | "
                            f"Damage: {breakdown['damage']:.0%} | Date: {breakdown['date']:.0%}"
                        )

                        dc1, dc2, dc3 = st.columns(3)
                        with dc1:
                            if st.button(f"🚩 Flag #{rep_a.get('inspection_id', i+1)}", key=f"fl_a_{i}_{j}"):
                                history[i]["duplicate_status"] = "flagged"
                                istore.update_inspection(rep_a.get("inspection_id"), {"duplicate_status": "flagged"})
                                st.warning("Flagged as possible duplicate.")
                        with dc2:
                            if st.button(f"🚩 Flag #{rep_b.get('inspection_id', j+1)}", key=f"fl_b_{i}_{j}"):
                                history[j]["duplicate_status"] = "flagged"
                                istore.update_inspection(rep_b.get("inspection_id"), {"duplicate_status": "flagged"})
                                st.warning("Flagged as possible duplicate.")
                        with dc3:
                            if st.button("✅ Mark Both Unique", key=f"unq_{i}_{j}"):
                                history[i]["duplicate_status"] = "confirmed_unique"
                                history[j]["duplicate_status"] = "confirmed_unique"
                                istore.update_inspection(rep_a.get("inspection_id"), {"duplicate_status": "confirmed_unique"})
                                istore.update_inspection(rep_b.get("inspection_id"), {"duplicate_status": "confirmed_unique"})
                                st.success("Both marked unique.")

    # ------------------------------------------------------------------
    # SUB-TAB: Progress Monitor
    # ------------------------------------------------------------------
    with dispatch_tabs[2]:
        st.markdown("### 📈 Road Damage Progress Monitoring")
        st.caption(
            "Groups reports by location and compares oldest vs newest inspection. "
            "Location matching is text-based — treat trends with caution."
        )

        history = st.session_state.dispatch_history
        if len(history) < 2:
            st.info("Need at least 2 reports in Dispatch Center to monitor progress.")
        else:
            progress_data = pm.get_progress_report(history)

            if not progress_data:
                st.info("No progress clusters found.")
            else:
                for cluster in progress_data:
                    loc_key = cluster["location_key"]
                    report_count = cluster["report_count"]
                    comp = cluster["comparison"]
                    trend = comp.get("trend", "INSUFFICIENT_DATA")
                    trend_emoji = cluster["trend_emoji"]

                    with st.expander(f"{trend_emoji} {loc_key} — {report_count} inspection(s) | Trend: {trend}"):
                        if trend == "INSUFFICIENT_DATA":
                            st.info("Only one inspection on record. Need ≥2 reports for trend analysis.")
                        else:
                            pc1, pc2, pc3 = st.columns(3)
                            with pc1:
                                st.metric("Trend", trend)
                            with pc2:
                                st.metric(
                                    "Potholes",
                                    comp.get("newer_potholes", 0),
                                    delta=comp.get("delta_potholes", 0)
                                )
                            with pc3:
                                st.metric(
                                    "Cracks",
                                    comp.get("newer_cracks", 0),
                                    delta=comp.get("delta_cracks", 0)
                                )

                            st.write(f"**Older inspection:** {comp.get('older_date', '')} — {comp.get('older_total', 0)} defects")
                            st.write(f"**Newer inspection:** {comp.get('newer_date', '')} — {comp.get('newer_total', 0)} defects")

                            for note in comp.get("notes", []):
                                if note.startswith("⚠️") or note.startswith("DISCLAIMER"):
                                    st.caption(note)
                                else:
                                    st.write(f"• {note}")

                        st.markdown("**All Reports in This Location Cluster:**")
                        for orig_idx, r, sim in cluster["reports"]:
                            rid = r.get("inspection_id", orig_idx+1)
                            status = r.get("verification_status", "AI_PENDING")
                            st.write(
                                f"• [{rid}] {r.get('date', '')} | "
                                f"{r.get('final_potholes', 0)} potholes, {r.get('final_cracks', 0)} cracks | "
                                f"Severity: {r.get('overall_severity', 'MINOR')} | Status: {status}"
                            )


# ==========================================
# PAGE 3: ANALYTICS
# ==========================================
elif page == "📊 Analytics":
    st.markdown("""
    <div class="top-header">
        <div>
            <div class="title-text">⬥ SYSTEM ANALYTICS</div>
            <div class="subtitle-text">MODEL BENCHMARKS, DAMAGE SEVERITY & STORAGE METRICS</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    history = st.session_state.dispatch_history

    # --- Benchmark panel (static) ---
    st.markdown("""
    <div class="side-card">
        <div class="card-title">BENCHMARK PERFORMANCE</div>
        <p>The cascade system uses RDD2022 fine-tuned YOLOv8 models, optionally cross-validated by Gemini 1.5 Flash.</p>
    </div>
    """, unsafe_allow_html=True)

    bm1, bm2, bm3, bm4 = st.columns(4)
    with bm1: st.markdown('<div class="metric-box"><div class="metric-val">0.386</div><div class="metric-label">mAP@0.5, 775 test images</div></div>', unsafe_allow_html=True)
    with bm2: st.markdown('<div class="metric-box"><div class="metric-val">0.43</div><div class="metric-label">pothole AP@0.5</div></div>', unsafe_allow_html=True)
    with bm3: st.markdown('<div class="metric-box"><div class="metric-val">+44%</div><div class="metric-label">from one training fix</div></div>', unsafe_allow_html=True)
    with bm4: st.markdown('<div class="metric-box"><div class="metric-val">Gemini</div><div class="metric-label">VLM Validator (optional)</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📈 Live Session Telemetry")

    total_dispatches = len(history)
    total_potholes = sum(r.get("final_potholes", 0) for r in history)
    total_cracks = sum(r.get("final_cracks", 0) for r in history)
    verified_count = sum(1 for r in history if r.get("verification_status") == "VERIFIED" or r.get("verification", {}).get("status") == "VERIFIED")
    rejected_count = sum(1 for r in history if r.get("verification_status") == "REJECTED" or r.get("verification", {}).get("status") == "REJECTED")
    pending_count = total_dispatches - (verified_count + rejected_count)

    tel1, tel2, tel3, tel4, tel5, tel6 = st.columns(6)
    with tel1: st.markdown(f'<div class="metric-box"><div class="metric-val">{total_dispatches}</div><div class="metric-label">TOTAL REPORTS</div></div>', unsafe_allow_html=True)
    with tel2: st.markdown(f'<div class="metric-box"><div class="metric-val">{total_potholes}</div><div class="metric-label">POTHOLES LOGGED</div></div>', unsafe_allow_html=True)
    with tel3: st.markdown(f'<div class="metric-box"><div class="metric-val">{total_cracks}</div><div class="metric-label">CRACKS LOGGED</div></div>', unsafe_allow_html=True)
    with tel4: st.markdown(f'<div class="metric-box"><div class="metric-val">{verified_count}</div><div class="metric-label">VERIFIED</div></div>', unsafe_allow_html=True)
    with tel5: st.markdown(f'<div class="metric-box"><div class="metric-val">{rejected_count}</div><div class="metric-label">REJECTED</div></div>', unsafe_allow_html=True)
    with tel6: st.markdown(f'<div class="metric-box"><div class="metric-val">{pending_count}</div><div class="metric-label">AI PENDING</div></div>', unsafe_allow_html=True)

    if history:
        st.markdown("---")
        st.markdown("### 📊 Damage, Severity & Risk Distribution")

        dist_col1, dist_col2, dist_col3, dist_col4 = st.columns(4)

        with dist_col1:
            st.markdown("**Damage Category Distribution**")
            long_total = sum(r.get("longitudinal_cracks", 0) for r in history)
            tran_total = sum(r.get("transverse_cracks", 0) for r in history)
            alli_total = sum(r.get("alligator_cracks", 0) for r in history)
            dmg_rows = [
                {"Category": "Pothole",           "Count": total_potholes},
                {"Category": "Longitudinal Crack", "Count": long_total},
                {"Category": "Transverse Crack",   "Count": tran_total},
                {"Category": "Alligator Crack",    "Count": alli_total},
            ]
            st.markdown(render_html_table(dmg_rows, max_height=180), unsafe_allow_html=True)

        with dist_col2:
            st.markdown("**Severity Distribution (Visual)**")
            sev_counts = {"CRITICAL": 0, "SEVERE": 0, "MODERATE": 0, "MINOR": 0}
            for r in history:
                s_val = r.get("overall_severity", "MINOR")
                if s_val in sev_counts:
                    sev_counts[s_val] += 1
                else:
                    sev_counts["MINOR"] += 1
            sev_rows = [{"Severity": k, "Reports": v} for k, v in sev_counts.items()]
            st.markdown(render_html_table(sev_rows, max_height=180), unsafe_allow_html=True)
            st.caption("⚠️ 2D visual estimate only.")

        with dist_col3:
            st.markdown("**Risk Distribution (Heuristic)**")
            risk_counts = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
            for r in history:
                cat = r.get("risk_category", "")
                if cat in risk_counts:
                    risk_counts[cat] += 1
                else:
                    risk_counts["Low"] += 1
            risk_rows = [{"Risk": k, "Reports": v} for k, v in risk_counts.items()]
            st.markdown(render_html_table(risk_rows, max_height=180), unsafe_allow_html=True)
            st.caption("⚠️ Heuristic estimate only.")

        with dist_col4:
            st.markdown("**Verification Status**")
            vs_rows = [
                {"Status": "✅ VERIFIED",   "Count": verified_count},
                {"Status": "❌ REJECTED",   "Count": rejected_count},
                {"Status": "🤖 AI_PENDING", "Count": pending_count},
            ]
            st.markdown(render_html_table(vs_rows, max_height=180), unsafe_allow_html=True)

        # --- Local Storage Status ---
        st.markdown("---")
        st.markdown("### 🗄️ Local Inspection Storage Status")
        st.write(f"• Persistent Store: `data/inspections.json`")
        st.write(f"• Total Saved Records: **{istore.count_inspections()}**")
        st.caption("Storage operates 100% locally via atomic JSON writes without external database dependencies.")

        # --- Downloadable CSV ---
        st.markdown("---")
        st.markdown("### 📥 Export Inspection Report")
        csv_bytes = _make_csv_bytes(history)
        st.download_button(
            label="⬇️ Download Full Inspection Report (CSV)",
            data=csv_bytes,
            file_name=f"RoadSentinel_Inspections_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        st.caption("CSV generated with Inspection ID, GPS metadata, defect breakdown, visual severity and verification state.")

    else:
        st.info("No dispatch records yet. Analyze images or videos in Detection Studio and push to Dispatch Center.")
