# RoadSentinel AI — Road Distress & Pothole Detection System

Enterprise-grade AI-powered road distress, damage, and pothole detection platform featuring decoupled **FastAPI backend**, **React (Vite + TypeScript) frontend**, and a dedicated standalone **Streamlit application**.

---

## 📁 Repository Directory Structure

```text
doomsday/
│
├── 🚀 backend/                      # Decoupled FastAPI Backend (REST API)
│   ├── app/                         # Routes, services, schemas, and core config
│   │   ├── api/                     # REST API controllers
│   │   ├── core/                    # Environment & dynamic path resolution
│   │   ├── schemas/                 # Pydantic data models
│   │   └── services/                # AI orchestration (YOLO, tracking, duplicate detection)
│   ├── requirements.txt             # Backend-only dependencies for uv / pip
│   └── README.md                    # Backend setup & API documentation
│
├── ⚛️ frontend/                     # Decoupled React + Vite + TypeScript Frontend
│   ├── src/                         # 10 complete UI pages & reusable components
│   ├── package.json                 # Node dependencies (with WASM Rollup support)
│   ├── vite.config.ts               # Vite proxy to backend (:8000)
│   └── README.md                    # Frontend build & dev guide
│
├── 🎈 streamlit_app/                # Standalone Streamlit Application
│   ├── app.py                       # Streamlit web application
│   ├── location_picker.py           # Geolocation picker Python bridge
│   ├── components/                  # Custom HTML5 geolocation picker component
│   │   └── location_picker/
│   │       └── index.html
│   ├── requirements.txt             # Streamlit-only dependencies for uv / pip
│   └── README.md                    # Streamlit quickstart guide
│
├── 💾 data/                         # Shared atomic JSON store & pothole crops
├── 🧠 weights/                      # Shared YOLO models (RDD2022 & Pothole)
├── 🎬 outputs/                      # Rendered video & image outputs
│
├── requirements.txt                 # Unified master dependencies file for uv / pip
├── app.py                           # Preserved root fallback (100% test suite compatibility)
├── test_roadsentinel.py             # 18-suite master regression test harness (18/18 PASS)
└── README.md                        # Master project documentation
```

---

## ⚡ Quick Start: Installation with `uv`

### 1. Install Backend Dependencies
```powershell
uv pip install -r backend/requirements.txt
```

### 2. Install Streamlit App Dependencies
```powershell
uv pip install -r streamlit_app/requirements.txt
```

### 3. Install All Dependencies (Master)
```powershell
uv pip install -r requirements.txt
```

> **Windows Application Control Compliance:**  
> All requirements files are 100% free of `pandas` and `pyarrow`, eliminating DLL load blocks.

---

## 🍃 MongoDB Atlas Cloud Database & Application Server

RoadSentinel AI connects directly to MongoDB Atlas cluster `roadsentinel_db`.

### 1. Launch with `server.py`
The unified entrypoint initializes the database, verifies cloud connectivity, synchronizes local inspection records, seeds RBAC profiles, and launches the FastAPI REST API:

```powershell
.\.venv\Scripts\python.exe server.py
```

- **MongoDB Atlas URI**: `mongodb+srv://laxmikanthjanaradhan2323_db_user:4s2w7FkfnKQ3lusf@cluster0.p23thyx.mongodb.net/`
- **Cloud Collections**:
  - `inspections`: Synced AI detection records, geolocations, and severity assessments.
  - `users`: User profiles with Google OAuth and RBAC permissions.
  - `work_orders`: Repair assignments dispatched from authorities to field contractors.
  - `repair_logs`: Field audit trail with materials used, repair costs, and photographic proof.

---

## 👥 Role-Based Access Control (RBAC) & Workflows

1. **👤 Citizen / Reporter**:
   - Report road hazards (photo / video + GPS metadata).
   - View personal report history and city damage maps.
   - Real-time tracking of pothole repair lifecycle via reference ID (`/track`).

2. **🏛️ Municipal Authority (Validator)**:
   - Validate and verify AI-detected road hazards (`/verification`).
   - Dispatch repair work orders to field contractors with instructions, priorities, and deadlines.
   - Review contractor-submitted repair proofs and approve/close or request rework.

3. **👷 Field Worker (Contractor)**:
   - Dedicated Contractor Portal (`/worker`).
   - View assigned road repair tasks and location coordinates.
   - Update repair status to `IN_PROGRESS`.
   - Submit completed repair work with materials used, incurred cost, and proof photo.

---

## 🗺️ City Pothole Density & Heatmap Layer

- **City Statistics**: Real-time totals of potholes in Bengaluru Urban, active hazards, and repaired counts.
- **Interactive Heatmap**: Visualizes high-density hazard clusters with severity-weighted intensity radiuses (Crimson red for Critical, Deep orange for Severe, Amber for Moderate, Emerald for Minor).

---

## 🚀 Running the Applications

### 1. Run Backend Server (MongoDB Atlas + FastAPI)
```powershell
.\.venv\Scripts\python.exe server.py
```
- **Backend API:** `http://127.0.0.1:8000`
- **Swagger Documentation:** `http://127.0.0.1:8000/docs`

### 2. Run the React Frontend
```powershell
cd frontend
npm run dev
```
- **Web UI:** `http://localhost:5173`

### 3. Run the Streamlit Application
```powershell
streamlit run streamlit_app/app.py
```
- **Streamlit Web UI:** `http://localhost:8501`

---

## 🧪 Automated Test Suite

Run the full automated test suite verifying all 18 end-to-end regression tests:
```powershell
.\.venv\Scripts\python.exe test_roadsentinel.py
```
**18 / 18 Tests Passed (100% PASS)**
