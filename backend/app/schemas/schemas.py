from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field

# ----------------- Core Detections -----------------

class DefectDetection(BaseModel):
    class_name: str
    box: List[int]
    confidence: float
    severity_category: str
    severity_score: float
    risk_score: Optional[float] = 0.0
    risk_category: Optional[str] = "Low"
    crop_path: Optional[str] = None
    dhash: Optional[Union[str, int]] = None

class DefectBreakdown(BaseModel):
    potholes: int = 0
    longitudinal: int = 0
    transverse: int = 0
    alligator: int = 0

class SeverityBreakdown(BaseModel):
    MINOR: int = 0
    MODERATE: int = 0
    SEVERE: int = 0
    CRITICAL: int = 0

class RiskDistribution(BaseModel):
    Low: int = 0
    Medium: int = 0
    High: int = 0
    Critical: int = 0

# ----------------- Image Detection -----------------

class DuplicateCandidate(BaseModel):
    original_report_id: str
    distance_m: Optional[float] = None
    similarity_score: Optional[float] = 0.0
    decision: str
    reasons: List[str] = []
    original_crop_path: Optional[str] = None

class ImageDetectionResponse(BaseModel):
    inspection_id: str
    status: str  # "COMPLETED", "NO_DEFECTS", "FAILED"
    model_used: str
    total_defects: int
    potholes: int
    cracks: int
    breakdown: DefectBreakdown
    overall_severity: str
    average_severity_score: float
    risk_category: str
    annotated_image_url: str
    detections: List[DefectDetection] = []
    location: Optional[str] = "Location unavailable"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_source: Optional[str] = "UNAVAILABLE"
    duplicate_status: str = "NEW_REPORT"
    duplicate_of: Optional[str] = None
    duplicate_candidates: List[DuplicateCandidate] = []
    date: str
    timestamp: str

# ----------------- Video Detection -----------------

class VideoMetadataResponse(BaseModel):
    file_name: str
    file_size_mb: float
    duration_sec: float
    duration_str: str
    fps: float
    total_frames: int
    width: int
    height: int
    resolution: str
    codec: str

class VideoDetectionResponse(BaseModel):
    inspection_id: str
    status: str
    video_url: str
    download_url: str
    source_metadata: Dict[str, Any]
    total_detections: int
    unique_hazard_count: int
    potholes_count: int
    cracks_count: int
    breakdown: DefectBreakdown
    overall_severity: str
    average_severity_score: float
    risk_category: str
    risk_distribution: Dict[str, int]
    table_rows: List[Dict[str, Any]] = []
    date: str
    timestamp: str

# ----------------- Verification -----------------

class VerifyActionRequest(BaseModel):
    verified_by: Optional[str] = "QA Inspector"
    notes: Optional[str] = None

class RejectActionRequest(BaseModel):
    rejection_reason: str = Field(..., min_length=3, description="Mandatory reason for rejection")
    rejected_by: Optional[str] = "QA Inspector"

class CorrectActionRequest(BaseModel):
    corrected_class: Optional[str] = None
    corrected_severity: Optional[str] = None
    notes: Optional[str] = None
    corrected_by: Optional[str] = "QA Inspector"

# ----------------- Analytics -----------------

class OverviewAnalyticsResponse(BaseModel):
    total_inspections: int
    total_potholes: int
    total_cracks: int
    unique_hazards: int
    severity_breakdown: SeverityBreakdown
    risk_distribution: RiskDistribution
    verification_counts: Dict[str, int]
    duplicate_counts: Dict[str, int]
    device_info: Dict[str, Any]

class TrendDataPoint(BaseModel):
    period: str
    inspections: int
    potholes: int
    cracks: int
    critical_defects: int

# ----------------- Location & Damage Map -----------------

class DamageMapPoint(BaseModel):
    inspection_id: str
    latitude: float
    longitude: float
    location_name: Optional[str] = "Road Section"
    location_source: Optional[str] = "UNAVAILABLE"
    overall_severity: Optional[str] = "MODERATE"
    severity_score: Optional[float] = 50.0
    risk_category: Optional[str] = "Medium"
    potholes: Optional[int] = 0
    cracks: Optional[int] = 0
    media_type: Optional[str] = "photo"
    date: Optional[str] = ""
    verification_status: Optional[str] = "AI_PENDING"
    duplicate_status: Optional[str] = "NEW_REPORT"
    duplicate_of: Optional[str] = None
    repair_status: Optional[str] = "REPORTED"

# ----------------- Auth & Users -----------------

class UserProfile(BaseModel):
    id: Optional[str] = None
    email: str
    name: str
    role: str = "citizen"  # "citizen", "authority", "worker"
    avatar: Optional[str] = None
    provider: str = "local"  # "google", "local"
    department: Optional[str] = None
    skills: Optional[List[str]] = None
    bio: Optional[str] = None
    created_at: Optional[str] = None

class GoogleAuthRequest(BaseModel):
    token: Optional[str] = None
    email: str
    name: str
    avatar: Optional[str] = None
    role: Optional[str] = "citizen"
    google_id: Optional[str] = None

class LocalLoginRequest(BaseModel):
    email: str
    role: Optional[str] = None

# ----------------- Work Orders & Repair Lifecycle -----------------

class AssignWorkOrderRequest(BaseModel):
    inspection_id: str
    assigned_worker_email: str
    priority: str = "MEDIUM"  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    target_date: Optional[str] = None
    repair_notes: Optional[str] = None
    estimated_cost: Optional[float] = None
    dispatched_by: Optional[str] = "Municipal Authority"

class UpdateWorkOrderStatusRequest(BaseModel):
    status: str  # "IN_PROGRESS", "REPAIRED"
    worker_notes: Optional[str] = None
    materials_used: Optional[str] = None
    actual_cost: Optional[float] = None
    proof_image_url: Optional[str] = None
    completion_date: Optional[str] = None

class ReviewWorkOrderRequest(BaseModel):
    decision: str  # "APPROVED", "REJECTED"
    feedback: Optional[str] = None
    reviewed_by: Optional[str] = "Municipal Authority"

class WorkOrderResponse(BaseModel):
    order_id: str
    inspection_id: str
    assigned_worker_email: str
    assigned_worker_name: str
    priority: str
    status: str  # "ASSIGNED", "IN_PROGRESS", "REPAIRED", "CLOSED"
    target_date: Optional[str] = None
    repair_notes: Optional[str] = None
    worker_notes: Optional[str] = None
    materials_used: Optional[str] = None
    proof_image_url: Optional[str] = None
    estimated_cost: Optional[float] = None
    actual_cost: Optional[float] = None
    created_at: str
    updated_at: str
    location_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    pothole_crop_url: Optional[str] = None

# ----------------- Progress & Heatmap -----------------

class TimelineStep(BaseModel):
    step_key: str
    title: str
    description: str
    timestamp: Optional[str] = None
    completed: bool
    current: bool
    actor: Optional[str] = None
    badge: Optional[str] = None

class InspectionStatusCheckResponse(BaseModel):
    inspection_id: str
    media_filename: str
    current_status: str  # "REPORTED", "VERIFIED", "ASSIGNED", "IN_PROGRESS", "REPAIRED", "CLOSED"
    location_name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    severity: str
    risk_category: str
    potholes_count: int
    cracks_count: int
    assigned_worker: Optional[str] = None
    annotated_image_url: Optional[str] = None
    proof_image_url: Optional[str] = None
    timeline: List[TimelineStep] = []

class HeatmapPoint(BaseModel):
    lat: float
    lng: float
    intensity: Optional[float] = 0.5  # 0.1 to 1.0
    count: Optional[int] = 1
    severity: Optional[str] = "MODERATE"
    inspection_id: Optional[str] = ""
    repair_status: Optional[str] = "REPORTED"

class CityPotholeSummary(BaseModel):
    city_name: str = "Bengaluru Urban"
    total_potholes: int = 0
    active_hazards: int = 0
    under_repair: int = 0
    repaired_count: int = 0
    verified_count: int = 0
    pending_count: int = 0
    repair_completion_rate: float = 0.0
