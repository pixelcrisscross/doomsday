import sys
import os
from pathlib import Path
from typing import List

# Dynamic project root discovery
CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parent.parent.parent

def _find_repo_root(start: Path) -> Path:
    for p in [start] + list(start.parents):
        if (p / "weights").exists() and (p / "video_detector.py").exists():
            return p
    return start.parent if start.name == "backend" else start

PROJECT_ROOT = _find_repo_root(BACKEND_DIR)

# Ensure project root and backend parent are in sys.path
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_DIR.parent) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR.parent))

# Paths
WEIGHTS_DIR = PROJECT_ROOT / "weights"
DATA_DIR = PROJECT_ROOT / "data"
INSPECTIONS_FILE = DATA_DIR / "inspections.json"
CROPS_DIR = DATA_DIR / "pothole_crops"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
UPLOADS_DIR = PROJECT_ROOT / "uploads"

# Ensure runtime directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
CROPS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

class Settings:
    PROJECT_NAME: str = "RoadSentinel AI"
    PROJECT_DESCRIPTION: str = "Enterprise AI Road Distress, Damage & Pothole Detection Platform"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"
    
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]
    
    # Model Weights
    TIER1_WEIGHTS: Path = WEIGHTS_DIR / "rdd2022_yolov8m.pt"
    TIER2_WEIGHTS: Path = WEIGHTS_DIR / "pothole_yolov8.pt"

    # MongoDB Atlas Connection
    MONGODB_URI: str = os.getenv(
        "MONGODB_URI",
        "mongodb+srv://laxmikanthjanaradhan2323_db_user:4s2w7FkfnKQ3lusf@cluster0.p23thyx.mongodb.net/?retryWrites=true&w=majority"
    )
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "roadsentinel_db")

settings = Settings()
