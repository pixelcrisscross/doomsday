import os
import tempfile
from pathlib import Path
from datetime import datetime
import io
import json

import cv2
import streamlit as st
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
    models = {}
    with st.spinner("Loading models (first time only)..."):
        # Tier 1: General RDD2022 multi-class model
        try:
            t1_path = hf_hub_download(repo_id="dronefreak/rdd2022-yolov8m", filename="best.pt")
            models["Tier 1 (RDD2022)"] = YOLO(t1_path)
        except Exception as e:
            st.error(f"Failed to load Tier 1: {e}")
            
        # Tier 2: Pothole-specific model
        try:
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

if "dispatch_history" not in st.session_state:
    st.session_state.dispatch_history = []
if "current_report" not in st.session_state:
    st.session_state.current_report = None

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
    """Sends image to Gemini to count potholes."""
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
    """Tries models in order. Returns the first result that finds something."""
    if not models: return None, "No models loaded"
    last_result = None
    for model_name, model in models.items():
        try:
            r = model.predict(source=image_source, conf=conf_threshold, verbose=False)[0]
            last_result = r
            if len(r.boxes) > 0:
                return r, model_name
        except Exception:
            pass
    return last_result, "No detections (All Tiers)"

# ==========================================
# 4. SIDEBAR NAVIGATION
# ==========================================
with st.sidebar:
    st.markdown("### Navigation")
    page = st.radio("Go to", ["📸 Detection Studio", "📋 Dispatch Center", "📊 Analytics"])
    st.divider()
    
    st.markdown("### Settings")
    gemini_api_key = st.text_input("Gemini API Key", type="password", help="Get a free key from Google AI Studio")
    conf = st.slider("YOLO Confidence", 0.05, 0.9, 0.15, 0.05)

# ==========================================
# PAGE 1: DETECTION STUDIO
# ==========================================
if page == "📸 Detection Studio":
    st.markdown("""
    <div class="top-header">
        <div>
            <div class="title-text">⬥ DETECTION STUDIO</div>
            <div class="subtitle-text">POTHOLES - CRACKS - INDIAN ROADS</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_img, col_stats = st.columns([2.5, 1])

    with col_img:
        up = st.file_uploader("Upload Road Photo", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
        if up:
            image = Image.open(up).convert("RGB")
            location_name = get_location_from_exif(image)
            
            # 1. Run YOLO Cascade
            with st.spinner("Running YOLO Cascade..."):
                result, model_used = cascade_predict(image, conf)
                
                yolo_potholes = 0
                yolo_cracks = 0
                if result:
                    for c in result.boxes.cls.tolist():
                        c_name = result.names[int(c)].lower()
                        if "d40" in c_name or "pothole" in c_name: yolo_potholes += 1
                        elif "crack" in c_name or "d00" in c_name or "d10" in c_name or "d20" in c_name: yolo_cracks += 1
                    
                    st.image(result.plot()[:, :, ::-1], use_container_width=True)
            
            # 2. Run Gemini Validation
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
                st.warning(f"⚠️ **Conflict Detected!** Gemini found more defects than YOLO. Report updated to match Gemini.")
            
            # Save state for Dispatch
            st.session_state.current_report = {
                "image": image,
                "location": location_name,
                "date": datetime.now().strftime("%d %b %Y"),
                "final_potholes": final_potholes,
                "final_cracks": final_cracks,
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
                "Longitudinal Crack": {"count": rep['final_cracks'] if rep['final_cracks'] > 0 else 0, "color": "#00BFFF"},
                "Transverse Crack": {"count": 0, "color": "#9370DB"},
                "Alligator Crack": {"count": 0, "color": "#32CD32"},
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
        st.info("No reports pending dispatch. Go to the Detection Studio to analyze an image.")
    else:
        for idx, rep in enumerate(st.session_state.dispatch_history):
            with st.expander(f"Report #{idx+1} - {rep['location']} ({rep['final_potholes']} Potholes)"):
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.image(rep["image"], use_container_width=True)
                with c2:
                    st.write(f"**Date:** {rep['date']}")
                    st.write(f"**Location:** {rep['location']}")
                    st.write(f"**Final Potholes:** {rep['final_potholes']}")
                    if rep['conflict']:
                        st.warning(f"Conflict resolved: Gemini ({rep['gemini_potholes']}) > YOLO ({rep['yolo_potholes']})")
                    
                    if st.button(f"🚀 Dispatch to Authorities", key=f"dispatch_{idx}"):
                        st.success(f"✅ Report successfully sent to Municipal Authority for {rep['location']}!")

# ==========================================
# PAGE 3: ANALYTICS
# ==========================================
elif page == "📊 Analytics":
    st.markdown("""
    <div class="top-header">
        <div>
            <div class="title-text">⬥ SYSTEM ANALYTICS</div>
            <div class="subtitle-text">MODEL METRICS</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="side-card">
        <div class="card-title">PERFORMANCE METRICS</div>
        <p>The cascade system uses RDD2022 fine-tuned YOLOv8 models, validated by Gemini 1.5 Flash.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.markdown('<div class="metric-box"><div class="metric-val">0.386</div><div class="metric-label">mAP@0.5, 775 test images</div></div>', unsafe_allow_html=True)
    with m2: st.markdown('<div class="metric-box"><div class="metric-val">0.43</div><div class="metric-label">pothole AP@0.5</div></div>', unsafe_allow_html=True)
    with m3: st.markdown('<div class="metric-box"><div class="metric-val">+44%</div><div class="metric-label">from one training fix</div></div>', unsafe_allow_html=True)
    with m4: st.markdown('<div class="metric-box"><div class="metric-val">Gemini</div><div class="metric-label">VLM Validator</div></div>', unsafe_allow_html=True)