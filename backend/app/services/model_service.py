import os
import sys
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from ultralytics import YOLO
from huggingface_hub import hf_hub_download

from backend.app.core.config import settings, PROJECT_ROOT

# Ensure project root is in sys.path so existing modules can be imported
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import video_detector as vd

class ModelService:
    _instance = None
    _models: Dict[str, YOLO] = {}
    _device_info: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelService, cls).__new__(cls)
            cls._instance._init_models()
        return cls._instance

    def _init_models(self):
        self._device_info = vd.get_device_info()
        models = {}
        local_t1 = settings.TIER1_WEIGHTS
        local_t2 = settings.TIER2_WEIGHTS

        # Tier 1: General RDD2022 multi-class model
        try:
            if local_t1.exists():
                models["Tier 1 (RDD2022)"] = YOLO(str(local_t1))
            else:
                t1_path = hf_hub_download(repo_id="dronefreak/rdd2022-yolov8m", filename="best.pt")
                models["Tier 1 (RDD2022)"] = YOLO(t1_path)
        except Exception as e:
            print(f"[ModelService] Failed to load Tier 1: {e}")

        # Tier 2: Pothole-specific model
        try:
            if local_t2.exists():
                models["Tier 2 (Pothole)"] = YOLO(str(local_t2))
            else:
                t2_path = hf_hub_download(repo_id="samdutse/pothole-yolov8", filename="best.pt")
                models["Tier 2 (Pothole)"] = YOLO(t2_path)
        except Exception as e:
            print(f"[ModelService] Failed to load Tier 2: {e}")

        self._models = models

    def get_models(self) -> Dict[str, YOLO]:
        return self._models

    def get_device_info(self) -> Dict[str, Any]:
        return self._device_info

    def cascade_predict(self, image_source, conf_threshold: float = 0.20) -> Tuple[Any, str, Dict[str, Any]]:
        """
        Ensemble inference for image input.
        Runs Tier 1 and Tier 2, returning result, model_name, and class counts.
        """
        if not self._models:
            return None, "No models loaded", {"potholes": 0, "longitudinal": 0, "transverse": 0, "alligator": 0, "error": "No models loaded"}

        last_result = None
        errors = []

        for model_name, model in self._models.items():
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
            except Exception as e:
                errors.append(f"{model_name}: {e}")

        if last_result is None and errors:
            err_msg = "; ".join(errors)
            return None, f"Inference Error: {err_msg}", {
                "potholes": 0, "longitudinal": 0, "transverse": 0, "alligator": 0, "error": err_msg
            }

        return last_result, "No detections (All Tiers)", {
            "potholes": 0, "longitudinal": 0, "transverse": 0, "alligator": 0
        }

model_service = ModelService()
