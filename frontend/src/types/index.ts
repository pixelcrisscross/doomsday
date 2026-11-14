export type SeverityLevel = 'MINOR' | 'MODERATE' | 'SEVERE' | 'CRITICAL' | 'NONE';
export type RiskLevel = 'Low' | 'Medium' | 'High' | 'Critical' | 'None';
export type VerificationStatus = 'AI_PENDING' | 'VERIFIED' | 'REJECTED';
export type DuplicateStatus = 'NEW_REPORT' | 'POSSIBLE_DUPLICATE' | 'CONFIRMED_DUPLICATE' | 'MARKED_AS_UNIQUE' | 'NEEDS_MANUAL_REVIEW';

export type UserRole = 'citizen' | 'authority' | 'worker';
export type WorkOrderStatus = 'ASSIGNED' | 'IN_PROGRESS' | 'REPAIRED' | 'CLOSED';
export type WorkOrderPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'EMERGENCY';

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  avatar_url?: string;
  organization?: string;
  phone?: string;
  assigned_zones?: string[];
  provider: 'google' | 'local';
  created_at: string;
}

export interface WorkOrder {
  order_id: string;
  inspection_id: string;
  assigned_worker_email: string;
  assigned_worker_name: string;
  assigned_by: string;
  assigned_at: string;
  priority: WorkOrderPriority;
  status: WorkOrderStatus;
  instructions?: string;
  deadline?: string;
  repair_materials?: string;
  repair_cost?: number;
  repair_notes?: string;
  completed_at?: string;
  proof_image_url?: string;
  authority_review_notes?: string;
  reviewed_at?: string;
  location: string;
  latitude?: number;
  longitude?: number;
  potholes_count: number;
  severity: SeverityLevel;
}

export interface AssignWorkOrderRequest {
  inspection_id: string;
  assigned_worker_email: string;
  assigned_worker_name: string;
  assigned_by?: string;
  priority?: WorkOrderPriority;
  instructions?: string;
  deadline?: string;
}

export interface UpdateWorkOrderStatusRequest {
  status: 'IN_PROGRESS' | 'REPAIRED';
  repair_materials?: string;
  repair_cost?: number;
  repair_notes?: string;
  proof_image_url?: string;
}

export interface ReviewWorkOrderRequest {
  status: 'CLOSED' | 'IN_PROGRESS';
  authority_review_notes: string;
  reviewed_by?: string;
}

export interface TimelineStep {
  step_index: number;
  title: string;
  description: string;
  status: 'COMPLETED' | 'IN_PROGRESS' | 'PENDING' | 'REJECTED';
  timestamp?: string;
  actor?: string;
}

export interface InspectionStatusCheckResponse {
  inspection_id: string;
  current_status: string;
  progress_percent: number;
  reported_at: string;
  location: string;
  latitude?: number;
  longitude?: number;
  overall_severity: SeverityLevel;
  potholes: number;
  cracks: number;
  assigned_worker?: string;
  proof_image_url?: string;
  timeline: TimelineStep[];
}

export interface HeatmapPoint {
  lat?: number;
  lng?: number;
  intensity?: number;
  count?: number;
  latitude?: number;
  longitude?: number;
  weight?: number;
  severity: SeverityLevel;
  potholes_count?: number;
  inspection_id?: string;
  repair_status?: string;
}

export interface CityPotholeSummary {
  city_name?: string;
  city?: string;
  total_potholes: number;
  active_hazards: number;
  under_repair: number;
  repaired_count: number;
  verified_count?: number;
  pending_count?: number;
  repair_completion_rate?: number;
  critical_potholes?: number;
  last_updated?: string;
}

export interface DefectDetection {
  class_name: string;
  box: number[];
  confidence: number;
  severity_category: SeverityLevel;
  severity_score: number;
  risk_score?: number;
  risk_category?: RiskLevel;
  crop_path?: string;
  dhash?: string;
}

export interface DefectBreakdown {
  potholes: number;
  longitudinal: number;
  transverse: number;
  alligator: number;
}

export interface DuplicateCandidate {
  original_report_id: string;
  distance_m?: number;
  similarity_score: number;
  decision: string;
  reasons: string[];
  original_crop_path?: string;
}

export interface ImageDetectionResult {
  inspection_id: string;
  status: 'COMPLETED' | 'NO_DEFECTS' | 'FAILED';
  model_used: string;
  total_defects: number;
  potholes: number;
  cracks: number;
  breakdown: DefectBreakdown;
  overall_severity: SeverityLevel;
  average_severity_score: number;
  risk_category: RiskLevel;
  annotated_image_url: string;
  detections: DefectDetection[];
  location: string;
  latitude?: number;
  longitude?: number;
  location_source?: string;
  duplicate_status: DuplicateStatus;
  duplicate_of?: string;
  duplicate_candidates: DuplicateCandidate[];
  date: string;
  timestamp: string;
}

export interface VideoDetectionResult {
  inspection_id: string;
  status: string;
  video_url: string;
  download_url: string;
  source_metadata: {
    file_size_mb: number;
    resolution: string;
    fps: number;
    total_frames: number;
    duration_str: string;
    codec: string;
  };
  total_detections: number;
  unique_hazard_count: number;
  potholes_count: number;
  cracks_count: number;
  breakdown: DefectBreakdown;
  overall_severity: SeverityLevel;
  average_severity_score: number;
  risk_category: RiskLevel;
  risk_distribution: Record<string, number>;
  table_rows: Array<{
    frame_idx: number;
    timestamp_sec: number;
    track_id: number;
    class_name: string;
    confidence: number;
    severity_category: string;
    box: number[];
  }>;
  date: string;
  timestamp: string;
}

export interface InspectionRecord {
  inspection_id: string;
  type: string;
  media_type: 'photo' | 'video';
  media_filename?: string;
  annotated_filename?: string;
  location: string;
  latitude?: number;
  longitude?: number;
  location_source?: string;
  date: string;
  timestamp: string;
  final_potholes: number;
  final_cracks: number;
  longitudinal_cracks?: number;
  transverse_cracks?: number;
  alligator_cracks?: number;
  overall_severity: SeverityLevel;
  average_severity_score?: number;
  risk_category: RiskLevel;
  model_used: string;
  unique_hazard_count?: number;
  total_detections?: number;
  duplicate_status: DuplicateStatus;
  duplicate_of?: string;
  verification?: {
    status: VerificationStatus;
    verified_by?: string;
    verified_at?: string;
    rejection_reason?: string;
    corrected_class?: string;
    corrected_severity?: string;
    notes?: string;
    original_ai_prediction?: {
      potholes: number;
      cracks: number;
      overall_severity: string;
    };
  };
  detections?: DefectDetection[];
}

export interface OverviewAnalytics {
  total_inspections: number;
  total_potholes: number;
  total_cracks: number;
  unique_hazards: number;
  severity_breakdown: Record<string, number>;
  risk_distribution: Record<string, number>;
  verification_counts: Record<string, number>;
  duplicate_counts: Record<string, number>;
  device_info: {
    device_name: string;
    cuda_available: boolean;
  };
}

export interface DamageMapPoint {
  inspection_id: string;
  latitude: number;
  longitude: number;
  location_name: string;
  location_source: string;
  overall_severity: SeverityLevel;
  severity_score: number;
  risk_category: RiskLevel;
  potholes: number;
  cracks: number;
  media_type: string;
  date: string;
  verification_status: VerificationStatus;
  duplicate_status: DuplicateStatus;
  duplicate_of?: string;
}
