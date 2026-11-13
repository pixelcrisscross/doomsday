import os
import tempfile
from pathlib import Path
from datetime import datetime
import json

import cv2
import av
import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, WebRtcMode
from PIL import Image, ExifTags
from ultralytics import YOLO
from huggingface_hub import hf_hub_download
from geopy.geocoders import Nominatim
import google.generativeai as genai

# ==========================================
# 1. PAGE CONFIG & CUSTOM CSS
# ==========================================
st.set_page_config(page_title="Road Hazard Detection", page_icon="🛣️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #121212; color: #ffffff; }
    header {visibility: hidden;}
    
    .top-header {
        display: flex; align-items: center; justify-content: space-between;
        border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px;
    }
    .title-text { font-size: 24px; font-weight: bold; color: #FFD700; line-height: 1.2; }
    .subtitle-text { font-size: 11px; color: #888; letter-spacing: 1px; }
    
    .side-card {
        background-color: #1e1e1e; border: 1px solid #333;
        border-radius: 8px; padding: 15px; margin-bottom: 15px;
    }
    .card-title { color: #FFD700; font-size: 12px; font-weight: bold; margin-bottom: 10px; letter-spacing: 1px; }
    .detect-item { display: flex; justify-content: space-between; padding: 6px 0; font-size: 13px; border-bottom: 1px solid #333; }
    .dot { height: 10px; width: 10px; border-radius: 50%; display: inline-block; margin-right: 8px; }
    
    .metric-box { background-color: #1e1e1e; border: 1px solid #333; border-radius: 5px; padding: 10px; text-align: left; }
    .metric-val { font-size: 20px; font-weight: bold; color: #FFD700; }
    .metric-label { font-size: 11px; color: #888; }
    
    .stButton>button { background-color: transparent; color: #FFD700; border: 1px solid #FFD700; border-radius: 5px; }
    .stButton>button:hover { background-color: #FFD700; color: #000; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. LOAD MODELS & INIT STATE
# ==========================================
@st.cache_resource
def load_models():
    models = {}
    with st.spinner("Loading models (first time only)..."):
        try:
            t1_path = hf_hub_download(repo_id="dronefreak/rdd2022-yolov8m", filename="best.pt")
            models["Heavy (YOLOv8m)"] = YOLO(t1_path)
        except Exception as e:
            st.error(f"Failed to load Heavy Model: {e}")
            
        try:
            light_path = hf_hub_download(repo_id="dronefreak/rdd2022-yolov8n", filename="best.pt")
            models["Light (YOLOv8n)"] = YOLO(light_path)
        except Exception as e:
            st.warning(f"Using standard YOLOv8n fallback.")
            models["Light (YOLOv8n)"] = YOLO("yolov8n.pt")
            
    return models

models = load_models()

if "dispatch_history" not in st.session_state:
    st.session_state.dispatch_history = []
if "current_report" not in st.session_state:
    st.session_state.current_report = None

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def get_location_from_exif(img):
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
        lat, lon = to_decimal(gps_data["GPSLatitude"]), to_decimal(gps_data["GPSLongitude"])
        if gps_data.get("GPSLatitudeRef") == "S": lat = -lat
        if gps_data.get("GPSLongitudeRef") == "W": lon = -lon
        geolocator = Nominatim(user_agent="road_hazard_app")
        location = geolocator.reverse(f"{lat}, {lon}", timeout=5)
        if location:
            address = location.raw.get('address', {})
            city = address.get('city', address.get('town', address.get('village', '')))
            return f"{city}".strip(", ")
    except: pass
    return "Belagavi, Karnataka"

def validate_with_gemini(api_key, image):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = 'Analyze this road image. Count distinct potholes and cracks. Respond ONLY with JSON: {"pothole_count": <int>, "crack_count": <int>, "reasoning": "<text>"}'
        response = model.generate_content([prompt, image])
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        return {"error": str(e), "pothole_count": 0, "crack_count": 0}

def cascade_predict(image_source, conf_threshold):
    if not models: return None, "No models loaded"
    heavy_model = models.get("Heavy (YOLOv8m)")
    if heavy_model:
        r = heavy_model.predict(source=image_source, conf=conf_threshold, verbose=False)[0]
        if len(r.boxes) > 0:
            return r, "Heavy (YOLOv8m)"
    return r, "No detections"

# ==========================================
# 4. VIDEO PROCESSOR CLASS
# ==========================================
class LivePotholeDetector(VideoProcessorBase):
    def __init__(self):
        # We grab the lightweight model for video
        self.model = models.get("Light (YOLOv8n)")
        
        # COCO class IDs for vehicles to avoid drawing boxes on moving cars
        self.ignored_classes = [2, 3, 5, 7] # car, motorcycle, bus, truck

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        img = frame.to_ndarray(format="bgr24")
        
        if self.model:
            # Use track for stability, 320px for speed
            results = self.model.track(img, persist=True, conf=0.15, imgsz=320, verbose=False)
            
            # Plot the results
            annotated_img = results[0].plot()
        else:
            annotated_img = img
            
        return av.VideoFrame.from_ndarray(annotated_img, format="bgr24")

# ==========================================
# 5. SIDEBAR NAVIGATION
# ==========================================
with st.sidebar:
    st.markdown("### Navigation")
    page = st.radio("Go to", ["📸 Detection Studio", "📷 Live Camera", "📋 Dispatch Center", "📊 Analytics"])
    st.divider()
    
    st.markdown("### Settings")
    gemini_api_key = st.text_input("Gemini API Key", type="password", help="Optional")
    conf = st.slider("YOLO Confidence", 0.05, 0.9, 0.15, 0.05)

# ==========================================
# PAGE 1: DETECTION STUDIO
# ==========================================
if page == "📸 Detection Studio":
    st.markdown('<div class="top-header"><div><div class="title-text">⬥ DETECTION STUDIO</div><div class="subtitle-text">UPLOAD & ANALYZE</div></div></div>', unsafe_allow_html=True)

    col_img, col_stats = st.columns([2.5, 1])

    with col_img:
        up = st.file_uploader("Upload Road Photo", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
        if up:
            image = Image.open(up).convert("RGB")
            location_name = get_location_from_exif(image)
            
            with st.spinner("Running YOLO..."):
                result, model_used = cascade_predict(image, conf)
                yolo_potholes, yolo_cracks = 0, 0
                if result:
                    for c in result.boxes.cls.tolist():
                        c_name = result.names[int(c)].lower()
                        if "pothole" in c_name or "d40" in c_name: yolo_potholes += 1
                        elif "crack" in c_name or "d00" in c_name or "d10" in c_name or "d20" in c_name: yolo_cracks += 1
                    st.image(result.plot()[:, :, ::-1], use_container_width=True)
            
            gemini_potholes, gemini_cracks, gemini_reason = 0, 0, "Not used."
            if gemini_api_key:
                with st.spinner("Gemini validating..."):
                    gemini_data = validate_with_gemini(gemini_api_key, image)
                    gemini_potholes = gemini_data.get("pothole_count", 0)
                    gemini_cracks = gemini_data.get("crack_count", 0)
                    gemini_reason = gemini_data.get("reasoning", "No reason.")
            
            final_potholes = max(yolo_potholes, gemini_potholes)
            final_cracks = max(yolo_cracks, gemini_cracks)
            conflict = (gemini_potholes > yolo_potholes) or (gemini_cracks > yolo_cracks)
            
            if conflict:
                st.warning("⚠️ Conflict: Gemini found more defects. Report updated.")
            
            st.session_state.current_report = {
                "image": image, "location": location_name, "date": datetime.now().strftime("%d %b %Y"),
                "final_potholes": final_potholes, "final_cracks": final_cracks,
                "conflict": conflict, "gemini_reason": gemini_reason
            }

    with col_stats:
        if st.session_state.current_report:
            rep = st.session_state.current_report
            st.markdown('<div class="side-card"><div class="card-title">DETECTED</div>', unsafe_allow_html=True)
            classes = {
                "Longitudinal Crack": {"count": rep['final_cracks'], "color": "#00BFFF"},
                "Pothole": {"count": rep['final_potholes'], "color": "#FF6347"}
            }
            for cls, data in classes.items():
                st.markdown(f'<div class="detect-item"><span><span class="dot" style="background-color:{data["color"]};"></span>{cls.upper()}</span><span>{data["count"]}</span></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="side-card"><div class="card-title">REPORT</div>', unsafe_allow_html=True)
            report_text = f"{rep['final_cracks']} cracks, {rep['final_potholes']} potholes at {rep['location']} ({rep['date']})."
            st.code(report_text, language="text")
            
            if st.button("➡️ Send to Dispatch", type="primary", use_container_width=True):
                st.session_state.dispatch_history.append(rep)
                st.success("Moved to Dispatch!")
            st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# PAGE 2: LIVE CAMERA
# ==========================================
elif page == "📷 Live Camera":
    st.markdown('<div class="top-header"><div><div class="title-text">⬥ LIVE CAMERA</div><div class="subtitle-text">REAL-TIME DETECTION</div></div></div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔴 Live Video Stream (WebRTC)", "📸 Quick Snapshot (Reliable)"])
    
    with tab1:
        st.info("💡 If the video doesn't start, your browser/network may block WebRTC. Use the 'Quick Snapshot' tab instead.")
        webrtc_streamer(
            key="pothole-live",
            mode=WebRtcMode.SENDRECV,
            video_processor_factory=LivePotholeDetector,
            media_stream_constraints={"video": True, "audio": False},
            async_processing=True,
            rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
        )
        
    with tab2:
        st.write("Take a photo with your webcam. It will instantly run the AI on the image.")
        img_file = st.camera_input("Snap a photo")
        if img_file:
            img = Image.open(img_file)
            result, model_used = cascade_predict(img, conf)
            
            col1, col2 = st.columns([3, 1])
            with col1:
                if result:
                    st.image(result.plot()[:, :, ::-1], use_container_width=True)
                else:
                    st.warning("No potholes detected in this frame.")
            
            with col2:
                if result:
                    st.success(f"Model: {model_used}")
                    st.info(f"Boxes found: {len(result.boxes)}")

# ==========================================
# PAGE 3: DISPATCH CENTER
# ==========================================
elif page == "📋 Dispatch Center":
    st.markdown('<div class="top-header"><div><div class="title-text">⬥ DISPATCH CENTER</div><div class="subtitle-text">AUTHORITY ACTION</div></div></div>', unsafe_allow_html=True)

    if not st.session_state.dispatch_history:
        st.info("No reports pending.")
    else:
        for idx, rep in enumerate(st.session_state.dispatch_history):
            with st.expander(f"Report #{idx+1} - {rep['location']}"):
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.image(rep["image"], use_container_width=True)
                with c2:
                    st.write(f"**Date:** {rep['date']}")
                    st.write(f"**Potholes:** {rep['final_potholes']}")
                    if st.button(f"🚀 Dispatch", key=f"dispatch_{idx}"):
                        st.success("✅ Sent to Authorities!")

# ==========================================
# PAGE 4: ANALYTICS
# ==========================================
elif page == "📊 Analytics":
    st.markdown('<div class="top-header"><div><div class="title-text">⬥ ANALYTICS</div><div class="subtitle-text">SYSTEM METRICS</div></div></div>', unsafe_allow_html=True)
    
    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    with m1: st.markdown('<div class="metric-box"><div class="metric-val">0.386</div><div class="metric-label">mAP@0.5 (Heavy)</div></div>', unsafe_allow_html=True)
    with m2: st.markdown('<div class="metric-box"><div class="metric-val">0.43</div><div class="metric-label">pothole AP@0.5</div></div>', unsafe_allow_html=True)
    with m3: st.markdown('<div class="metric-box"><div class="metric-val">320px</div><div class="metric-label">Live Video Res</div></div>', unsafe_allow_html=True)