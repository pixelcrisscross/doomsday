# RoadSentinel AI — Streamlit Application

This directory contains the standalone Streamlit implementation of **RoadSentinel AI**.

---

## 📦 Installation with `uv`

Install all dependencies using `uv`:

```bash
# From repository root
uv pip install -r streamlit_app/requirements.txt

# Or from inside this directory
cd streamlit_app
uv pip install -r requirements.txt
```

> **Note on Windows Security:**  
> This `requirements.txt` is 100% free of `pandas` and `pyarrow`, ensuring full compatibility with Windows Application Control policies.

---

## 🚀 Running the Streamlit App

From the repository root:
```bash
streamlit run streamlit_app/app.py
```

Or from inside this directory:
```bash
cd streamlit_app
streamlit run app.py
```

---

## 📁 Directory Layout

- `app.py`: Main Streamlit multi-tab application (Photo Studio, Video Lab, Damage Map, History & Verification, AI Model Evaluation, Progress Tracking, Inspection Reports).
- `location_picker.py`: Custom HTML5 browser geolocation component bridge.
- `components/location_picker/index.html`: Geolocation UI widget.
- `requirements.txt`: Dependencies tailored for Streamlit.
