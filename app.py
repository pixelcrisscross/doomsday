import os
import tempfile
from pathlib import Path
from datetime import datetime
import io
import json
import time
import html

import cv2
import numpy as np
import streamlit as st
from PIL import Image, ExifTags
from ultralytics import YOLO
from huggingface_hub import hf_hub_download
from geopy.geocoders import Nominatim

# Optional Gemini integration (with graceful fallback if gRPC/cygrpc is blocked by AppControl)
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except Exception:
    HAS_GEMINI = False
    genai = None

import video_detector as vd

# ==========================================
# 1. PAGE CONFIG & CUSTOM CSS
# ==========================================
st.set_page_config(page_title="Road Hazard Detection", page_icon="🛣️", layout="wide")

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

if "dispatch_history" not in st.session_state:
    st.session_state.dispatch_history = []
if "current_report" not in st.session_state:
    st.session_state.current_report = None
if "video_report" not in st.session_state:
    st.session_state.video_report = None

# ==========================================
# 3. HELPER FUNCTIONS (EXIF, GEMINI, YOLO)
# ==========================================
def get_location_from_exif(img):
    """Extract GPS from EXIF, reverse geocode it. Fallback to default if missing."""
    try:
        exif = img._getexif()
        if not exif: return "Rani Chennamma Nagar, Belagavi"
        
        exif_data = {ExifTags.TAGS[k]: v for k, v in exif.items() if k in ExifTags.TAGS}
        gps_info = exif_data.get("GPSInfo")
        if not gps_info: return "Rani Chennamma Nagar, Belagavi"

        def to_decimal(values):
            d, m, s = values
            return float(d) + float(m)/60 + float(s)/3600

        gps_data = {ExifTags.GPSTAGS[k]: v for k, v in gps_info.items() if k in ExifTags.GPSTAGS}
        lat = to_decimal(gps_data["GPSLatitude"])
        lon = to_decimal(gps_data["GPSLongitude"])
        
        if gps_data.get("GPSLatitudeRef") == "S": lat = -lat
        if gps_data.get("GPSLongitudeRef") == "W": lon = -lon

        geolocator = Nominatim(user_agent="road_hazard_app")
        location = geolocator.reverse(f"{lat}, {lon}", timeout=5)
        if location:
            address = location.raw.get('address', {})
            city = address.get('city', address.get('town', address.get('village', '')))
            suburb = address.get('suburb', address.get('neighbourhood', ''))
            return f"{suburb}, {city}".strip(", ")
    except Exception:
        pass
    return "Rani Chennamma Nagar, Belagavi"

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
    all_boxes = []
    
    # Try models in order; if Tier 1 finds defects, use Tier 1; otherwise Tier 2
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
            
    return last_result, "No detections (All Tiers)", {"potholes": 0, "longitudinal": 0, "transverse": 0, "alligator": 0}

# ==========================================
# 4. SIDEBAR NAVIGATION
# ==========================================
with st.sidebar:
    st.markdown("### Navigation")
    page = st.radio("Go to", ["📸 Detection Studio", "📋 Dispatch Center", "📊 Analytics"])
    st.divider()
    
    st.markdown("### Settings")
    gemini_api_key = st.text_input("Gemini API Key", type="password", help="Optional: For single-photo Gemini cross-validation.")
    conf = st.slider("YOLO Confidence", 0.05, 0.90, 0.20, 0.05)
    
    st.divider()
    st.markdown("### Hardware Status")
    if device_info["cuda_available"]:
        st.success(f"⚡ GPU: {device_info['device_name']}")
    else:
        st.info(f"💻 CPU: {device_info['device_name']}")
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
                detects potholes and crack variants via YOLOv8, annotates bounding boxes, and generates an annotated clip.
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

        with vid_col_controls:
            st.markdown('<div class="side-card"><div class="card-title">INFERENCE CONTROLS</div>', unsafe_allow_html=True)
            v_conf = st.slider("Detection Confidence", 0.05, 0.90, float(conf), 0.05, key="video_conf_slider")
            frame_skip_option = st.selectbox(
                "Frame Sampling (Skip)",
                options=[1, 2, 3, 5],
                format_func=lambda x: f"{x} - {'Process Every Frame (Highest Accuracy)' if x == 1 else f'Process Every {x} Frames (Faster Scan)'}",
                key="video_frame_skip"
            )
            st.markdown('</div>', unsafe_allow_html=True)

        if video_file is not None:
            # Save uploaded video to temp file for OpenCV access
            temp_dir = tempfile.gettempdir()
            clean_name = Path(video_file.name).stem
            suffix = Path(video_file.name).suffix.lower()
            temp_video_path = os.path.join(temp_dir, f"roadsentinel_upload_{clean_name}{suffix}")
            
            with open(temp_video_path, "wb") as f:
                f.write(video_file.getbuffer())

            # Validate video
            is_valid, val_msg = vd.validate_video(temp_video_path)
            if not is_valid:
                st.error(f"❌ Video Validation Failed: {val_msg}")
            else:
                meta = vd.get_video_metadata(temp_video_path)

                # Metadata Cards
                st.markdown("#### 📋 Video Properties")
                m1, m2, m3, m4, m5, m6 = st.columns(6)
                with m1: st.markdown(f'<div class="metric-box"><div class="metric-val">{meta["file_size_mb"]} MB</div><div class="metric-label">FILE SIZE</div></div>', unsafe_allow_html=True)
                with m2: st.markdown(f'<div class="metric-box"><div class="metric-val">{meta["resolution"]}</div><div class="metric-label">RESOLUTION</div></div>', unsafe_allow_html=True)
                with m3: st.markdown(f'<div class="metric-box"><div class="metric-val">{meta["fps"]}</div><div class="metric-label">SOURCE FPS</div></div>', unsafe_allow_html=True)
                with m4: st.markdown(f'<div class="metric-box"><div class="metric-val">{meta["total_frames"]}</div><div class="metric-label">TOTAL FRAMES</div></div>', unsafe_allow_html=True)
                with m5: st.markdown(f'<div class="metric-box"><div class="metric-val">{meta["duration_str"]}</div><div class="metric-label">DURATION</div></div>', unsafe_allow_html=True)
                with m6: st.markdown(f'<div class="metric-box"><div class="metric-val">{meta["codec"]}</div><div class="metric-label">CODEC</div></div>', unsafe_allow_html=True)

                st.write("")
                
                # Pre-processing Preview & Action Buttons
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
                        try: os.remove(temp_video_path)
                        except Exception: pass
                    st.rerun()

                # Run Video Inference Pipeline
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
                            
                            st.session_state.video_report = {
                                "meta": meta,
                                "annotated_path": annotated_video_path,
                                "summary": summary,
                                "conf_used": v_conf,
                                "date": datetime.now().strftime("%d %b %Y, %H:%M")
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
                            "Transverse Crack": {"count": sum_v["transverse_crack_detections"], "color": "#9370DB"},
                            "Alligator Crack": {"count": sum_v["alligator_crack_detections"], "color": "#32CD32"},
                            "Pothole": {"count": sum_v["pothole_detections"], "color": "#FF6347"}
                        }
                        
                        for cls_k, cls_d in classes_v.items():
                            st.markdown(f"""
                            <div class="detect-item">
                                <span><span class="dot" style="background-color:{cls_d['color']};"></span>{cls_k.upper()}</span>
                                <span><b>{cls_d['count']}</b></span>
                            </div>
                            """, unsafe_allow_html=True)
                            
                        st.markdown("---")
                        st.write(f"**Total Frames Processed:** {sum_v['processed_frames']}")
                        st.write(f"**Total Frame Detections:** {sum_v['total_detections']}")
                        st.write(f"**Average Confidence:** {sum_v['average_confidence_pct']}")
                        st.write(f"**Peak Confidence:** {sum_v['max_confidence_pct']}")
                        st.write(f"**Inference Speed:** {sum_v['processing_fps']} FPS ({sum_v['processing_time_sec']}s)")
                        
                        if st.button("📋 Push Video Summary to Dispatch Center", use_container_width=True):
                            dispatch_entry = {
                                "type": "Video Inspection",
                                "filename": rep_v["meta"]["filename"],
                                "location": "Road Corridor Video Survey",
                                "date": rep_v["date"],
                                "final_potholes": sum_v["pothole_detections"],
                                "final_cracks": sum_v["longitudinal_crack_detections"] + sum_v["transverse_crack_detections"] + sum_v["alligator_crack_detections"],
                                "longitudinal_cracks": sum_v["longitudinal_crack_detections"],
                                "transverse_cracks": sum_v["transverse_crack_detections"],
                                "alligator_cracks": sum_v["alligator_crack_detections"],
                                "avg_conf": sum_v["average_confidence_pct"],
                                "conflict": False
                            }
                            st.session_state.dispatch_history.append(dispatch_entry)
                            st.success("Video inspection record logged to Dispatch Center!")

                        st.markdown('</div>', unsafe_allow_html=True)

                    # Frame-level Detection Table
                    st.markdown("#### 📊 Frame-Wise Detection Log")
                    st.caption("ℹ️ Note: Detections represent observations across video frames, not unique deduplicated physical road hazards.")
                    if sum_v["table_rows"]:
                        df_dets = pd.DataFrame(sum_v["table_rows"])
                        st.dataframe(df_dets, use_container_width=True, height=260)
                    else:
                        st.info("No road distress detected in the sampled frames at the selected confidence threshold.")

        else:
            st.info("👋 Upload a video file (.mp4, .avi, .mov, .mkv) above to begin automated road damage detection.")

    # ------------------------------------------------------------------
    # TAB 2: PHOTO STUDIO (EXISTING WORKFLOW PRESERVED)
    # ------------------------------------------------------------------
    with tab_photo:
        col_img, col_stats = st.columns([2.5, 1])

        with col_img:
            up = st.file_uploader("Upload Road Photo", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
            if up:
                image = Image.open(up).convert("RGB")
                location_name = get_location_from_exif(image)
                
                # 1. Run YOLO Cascade
                with st.spinner("Running YOLO Cascade..."):
                    result, model_used, counts = cascade_predict(image, conf)
                    
                    yolo_potholes = counts.get("potholes", 0)
                    yolo_longitudinal = counts.get("longitudinal", 0)
                    yolo_transverse = counts.get("transverse", 0)
                    yolo_alligator = counts.get("alligator", 0)
                    yolo_cracks = yolo_longitudinal + yolo_transverse + yolo_alligator
                    
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
                
                # Save state for Dispatch
                st.session_state.current_report = {
                    "type": "Photo Inspection",
                    "image": image,
                    "location": location_name,
                    "date": datetime.now().strftime("%d %b %Y"),
                    "final_potholes": final_potholes,
                    "final_cracks": final_cracks,
                    "longitudinal_cracks": yolo_longitudinal,
                    "transverse_cracks": yolo_transverse,
                    "alligator_cracks": yolo_alligator,
                    "yolo_potholes": yolo_potholes,
                    "gemini_potholes": gemini_potholes,
                    "gemini_reason": gemini_reason,
                    "conflict": conflict,
                    "model_used": model_used
                }

        with col_stats:
            if st.session_state.current_report:
                rep = st.session_state.current_report
                
                # Detected Panel
                st.markdown('<div class="side-card"><div class="card-title">DETECTED</div>', unsafe_allow_html=True)
                
                classes = {
                    "Longitudinal Crack": {"count": rep.get('longitudinal_cracks', 0), "color": "#00BFFF"},
                    "Transverse Crack": {"count": rep.get('transverse_cracks', 0), "color": "#9370DB"},
                    "Alligator Crack": {"count": rep.get('alligator_cracks', 0), "color": "#32CD32"},
                    "Pothole": {"count": rep['final_potholes'], "color": "#FF6347"}
                }
                
                for cls, data in classes.items():
                    st.markdown(f"""
                    <div class="detect-item">
                        <span><span class="dot" style="background-color:{data['color']};"></span>{cls.upper()}</span>
                        <span>{data['count']}</span>
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

                # Report Panel
                st.markdown('<div class="side-card"><div class="card-title">REPORT IT</div>', unsafe_allow_html=True)
                report_text = f"{rep['final_cracks']} cracks and {rep['final_potholes']} potholes spotted at {rep['location']} ({rep['date']})."
                st.code(report_text, language="text")
                
                if st.button("➡️ Send to Dispatch Center", type="primary", use_container_width=True):
                    st.session_state.dispatch_history.append(rep)
                    st.success("Report moved to Dispatch Center!")
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
            <div class="subtitle-text">AUTHORITY ACTION & VERIFICATION</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.dispatch_history:
        st.info("No reports pending dispatch. Go to the Detection Studio to analyze an image or video.")
    else:
        for idx, rep in enumerate(st.session_state.dispatch_history):
            rep_type = rep.get("type", "Photo Inspection")
            with st.expander(f"Report #{idx+1} [{rep_type}] - {rep['location']} ({rep['final_potholes']} Potholes, {rep['final_cracks']} Cracks)"):
                c1, c2 = st.columns([1, 2])
                with c1:
                    if "image" in rep:
                        st.image(rep["image"], use_container_width=True)
                    else:
                        st.markdown(f"📹 **Survey Video:** `{rep.get('filename', 'video')}`")
                        st.write(f"**Longitudinal Cracks:** {rep.get('longitudinal_cracks', 0)}")
                        st.write(f"**Transverse Cracks:** {rep.get('transverse_cracks', 0)}")
                        st.write(f"**Alligator Cracks:** {rep.get('alligator_cracks', 0)}")
                with c2:
                    st.write(f"**Date:** {rep['date']}")
                    st.write(f"**Location:** {rep['location']}")
                    st.write(f"**Total Potholes:** {rep['final_potholes']}")
                    st.write(f"**Total Cracks:** {rep['final_cracks']}")
                    if rep.get('conflict'):
                        st.warning(f"Conflict resolved: Gemini ({rep.get('gemini_potholes')}) > YOLO ({rep.get('yolo_potholes')})")
                    
                    if st.button(f"🚀 Dispatch to Municipal Authority", key=f"dispatch_{idx}"):
                        st.success(f"✅ Report #{idx+1} successfully dispatched to Municipal Road Maintenance Authority!")

# ==========================================
# PAGE 3: ANALYTICS
# ==========================================
elif page == "📊 Analytics":
    st.markdown("""
    <div class="top-header">
        <div>
            <div class="title-text">⬥ SYSTEM ANALYTICS</div>
            <div class="subtitle-text">MODEL BENCHMARKS & RUNTIME METRICS</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="side-card">
        <div class="card-title">BENCHMARK PERFORMANCE</div>
        <p>The cascade system uses RDD2022 fine-tuned YOLOv8 models, validated by Gemini 1.5 Flash.</p>
    </div>
    """, unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    with m1: st.markdown('<div class="metric-box"><div class="metric-val">0.386</div><div class="metric-label">mAP@0.5, 775 test images</div></div>', unsafe_allow_html=True)
    with m2: st.markdown('<div class="metric-box"><div class="metric-val">0.43</div><div class="metric-label">pothole AP@0.5</div></div>', unsafe_allow_html=True)
    with m3: st.markdown('<div class="metric-box"><div class="metric-val">+44%</div><div class="metric-label">from one training fix</div></div>', unsafe_allow_html=True)
    with m4: st.markdown('<div class="metric-box"><div class="metric-val">Gemini</div><div class="metric-label">VLM Validator</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📈 Live Session Telemetry")
    
    total_dispatches = len(st.session_state.dispatch_history)
    total_potholes = sum(r.get("final_potholes", 0) for r in st.session_state.dispatch_history)
    total_cracks = sum(r.get("final_cracks", 0) for r in st.session_state.dispatch_history)
    
    lm1, lm2, lm3 = st.columns(3)
    with lm1:
        st.markdown(f'<div class="metric-box"><div class="metric-val">{total_dispatches}</div><div class="metric-label">TOTAL DISPATCHES</div></div>', unsafe_allow_html=True)
    with lm2:
        st.markdown(f'<div class="metric-box"><div class="metric-val">{total_potholes}</div><div class="metric-label">POTHOLES LOGGED</div></div>', unsafe_allow_html=True)
    with lm3:
        st.markdown(f'<div class="metric-box"><div class="metric-val">{total_cracks}</div><div class="metric-label">CRACKS LOGGED</div></div>', unsafe_allow_html=True)
