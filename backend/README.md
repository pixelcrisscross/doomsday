# RoadSentinel AI — FastAPI Backend

This directory houses the independent **FastAPI REST API Backend** for RoadSentinel AI.

---

## 📦 Installation with `uv`

Install all backend dependencies using `uv`:

```bash
# From repository root
uv pip install -r backend/requirements.txt

# Or from inside this directory
cd backend
uv pip install -r requirements.txt
```

---

## 🚀 Running the Backend

From the repository root:
```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Or from inside this directory:
```bash
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- **API Base URL**: `http://127.0.0.1:8000`
- **Interactive Swagger Docs**: `http://127.0.0.1:8000/docs`
- **Redoc Documentation**: `http://127.0.0.1:8000/redoc`
- **Health Check**: `http://127.0.0.1:8000/api/health`

---

## 📁 Architecture & Layout

- `app/main.py`: FastAPI application instance, CORS configuration, static asset routing, and API router registrations.
- `app/api/`: REST API route controllers:
  - `image_routes.py` (`POST /api/image/detect`)
  - `video_routes.py` (`POST /api/video/detect`)
  - `verification_routes.py` (Queue, verify, reject, correct)
  - `analytics_routes.py` (Overview, trends)
  - `reports_routes.py` (List, detail, CSV export, delete)
  - `location_routes.py` (Damage points, 25m duplicate geofences, reverse geocode)
  - `progress_routes.py` (Location clusters, multi-temporal comparison)
- `app/services/`: Modular service layer wrapping YOLO inference, video processing, IoU tracking, duplicate detection, and storage.
- `app/schemas/`: Strongly-typed Pydantic schemas for requests and responses.
- `app/core/config.py`: Environment configuration and dynamic path resolution.
- `requirements.txt`: Python package requirements tailored for `uv`.
