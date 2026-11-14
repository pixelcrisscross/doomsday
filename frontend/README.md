# RoadSentinel AI — React + TypeScript Frontend

This directory houses the independent **React 18 + Vite + TypeScript + Tailwind CSS** frontend application for RoadSentinel AI.

---

## 📦 Installation

```bash
cd frontend
npm install
```

> **WASM Rollup Note:**  
> The project is pre-configured with `@rollup/wasm-node` and an automatic `postinstall` hook to guarantee smooth builds across all Windows environments without triggering Application Control DLL blocks.

---

## 🚀 Development Server

```bash
cd frontend
npm run dev
```

- App runs at: `http://localhost:5173`
- The Vite development server automatically proxies API requests (`/api/*` and `/outputs/*`) to the FastAPI backend running at `http://127.0.0.1:8000`.

---

## 🏗️ Production Build

```bash
cd frontend
npm run build
```
Generates optimized static production assets in `frontend/dist/`.

---

## 📁 10 Implemented Pages

1. **Dashboard** (`/`): Overview metrics, KPI cards, recent inspections, and severity breakdown charts.
2. **Image Detection** (`/image-detection`): Drag-and-drop road photo uploader, browser geolocation capture, YOLO cascade inference, and duplicate detection alerts.
3. **Video Detection** (`/video-detection`): Video hazard analysis, persistent IoU tracking, summary statistics, and MP4 video download.
4. **Verification Queue** (`/verification`): Review pending detections, approve, reject with reason, or correct classification.
5. **Damage Map** (`/damage-map`): Interactive Leaflet map with color-coded severity markers and 25m duplicate proximity geofences.
6. **Detection History** (`/history`): Filterable historical inspection table with deep-inspection modal view.
7. **Analytics** (`/analytics`): Charts and trends (Recharts) covering damage types, severity, and risk scores.
8. **AI Evaluation** (`/ai-evaluation`): YOLOv8m & Pothole model architecture, cascades, and hardware acceleration status.
9. **Reports** (`/reports`): Filterable query table, Python-stdlib CSV export, and record deletion.
10. **Settings** (`/settings`): Detection thresholds, tracking IoU, duplicate distance radius, and hardware info.
