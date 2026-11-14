import axios from 'axios';
import {
  ImageDetectionResult,
  VideoDetectionResult,
  InspectionRecord,
  OverviewAnalytics,
  DamageMapPoint,
  UserProfile,
  WorkOrder,
  AssignWorkOrderRequest,
  UpdateWorkOrderStatusRequest,
  ReviewWorkOrderRequest,
  InspectionStatusCheckResponse,
  HeatmapPoint,
  CityPotholeSummary
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Accept': 'application/json',
  },
});

export const api = {
  // Health
  checkHealth: async () => {
    const res = await client.get('/api/health');
    return res.data;
  },

  // Image Detection
  detectImage: async (formData: FormData): Promise<ImageDetectionResult> => {
    const res = await client.post('/api/image/detect', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  // Video Detection
  detectVideo: async (formData: FormData, onUploadProgress?: (progressEvent: any) => void): Promise<VideoDetectionResult> => {
    const res = await client.post('/api/video/detect', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress,
    });
    return res.data;
  },

  // Verification Queue
  getPendingVerifications: async (): Promise<InspectionRecord[]> => {
    const res = await client.get('/api/verification/pending');
    return res.data;
  },

  verifyInspection: async (id: string, verifiedBy = 'QA Inspector', notes?: string) => {
    const res = await client.post(`/api/verification/${id}/verify`, { verified_by: verifiedBy, notes });
    return res.data;
  },

  rejectInspection: async (id: string, rejectionReason: string, rejectedBy = 'QA Inspector') => {
    const res = await client.post(`/api/verification/${id}/reject`, { rejection_reason: rejectionReason, rejected_by: rejectedBy });
    return res.data;
  },

  correctInspection: async (id: string, payload: { corrected_class?: string; corrected_severity?: string; notes?: string; corrected_by?: string }) => {
    const res = await client.post(`/api/verification/${id}/correct`, payload);
    return res.data;
  },

  // Analytics
  getOverviewAnalytics: async (): Promise<OverviewAnalytics> => {
    const res = await client.get('/api/analytics/overview');
    return res.data;
  },

  getTrends: async () => {
    const res = await client.get('/api/analytics/trends');
    return res.data;
  },

  // Reports
  getReports: async (params?: { media_type?: string; verification_status?: string; severity?: string; search?: string; limit?: number; offset?: number }) => {
    const res = await client.get('/api/reports/', { params });
    return res.data;
  },

  getReportById: async (id: string): Promise<InspectionRecord> => {
    const res = await client.get(`/api/reports/${id}`);
    return res.data;
  },

  deleteReport: async (id: string) => {
    const res = await client.delete(`/api/reports/${id}`);
    return res.data;
  },

  getCsvExportUrl: () => `${API_BASE_URL}/api/reports/export/csv`,

  // Location & Map
  getDamagePoints: async (): Promise<DamageMapPoint[]> => {
    const res = await client.get('/api/location/damage-points');
    return res.data;
  },

  getGeofences: async () => {
    const res = await client.get('/api/location/geofences');
    return res.data;
  },

  reverseGeocode: async (latitude: number, longitude: number) => {
    const res = await client.get('/api/location/reverse-geocode', { params: { latitude, longitude } });
    return res.data;
  },

  // Progress Monitoring
  getProgressLocations: async () => {
    const res = await client.get('/api/progress/locations');
    return res.data;
  },

  compareProgress: async (location: string) => {
    const res = await client.get('/api/progress/compare', { params: { location } });
    return res.data;
  },

  getStatusCheck: async (inspectionId: string): Promise<InspectionStatusCheckResponse> => {
    const res = await client.get(`/api/progress/status/${inspectionId}`);
    return res.data;
  },

  // Heatmap & City Statistics
  getHeatmapPoints: async (): Promise<HeatmapPoint[]> => {
    const res = await client.get('/api/location/heatmap');
    return res.data;
  },

  getCityStats: async (city = 'Bengaluru Urban'): Promise<CityPotholeSummary> => {
    const res = await client.get('/api/location/city-stats', { params: { city } });
    return res.data;
  },

  // Authentication & Users (MongoDB Atlas & Google OAuth)
  loginWithGoogle: async (payload: { credential?: string; email: string; name: string; avatar_url?: string; role?: string }): Promise<UserProfile> => {
    const res = await client.post('/api/auth/google', payload);
    return res.data;
  },

  loginLocal: async (payload: { email: string; role?: string }): Promise<UserProfile> => {
    const res = await client.post('/api/auth/login', payload);
    return res.data;
  },

  getCurrentUser: async (email = 'citizen@roadsentinel.ai'): Promise<UserProfile> => {
    const res = await client.get('/api/auth/me', { params: { email } });
    return res.data;
  },

  getUsers: async (role?: string): Promise<UserProfile[]> => {
    const res = await client.get('/api/auth/users', { params: { role } });
    return res.data;
  },

  // Work Orders & Repair Dispatch
  getWorkOrders: async (params?: { worker_email?: string; status?: string }): Promise<WorkOrder[]> => {
    const res = await client.get('/api/work-orders', { params });
    return res.data;
  },

  assignWorkOrder: async (payload: AssignWorkOrderRequest): Promise<WorkOrder> => {
    const res = await client.post('/api/work-orders/assign', payload);
    return res.data;
  },

  updateWorkOrderStatus: async (orderId: string, payload: UpdateWorkOrderStatusRequest): Promise<WorkOrder> => {
    const res = await client.post(`/api/work-orders/${orderId}/status`, payload);
    return res.data;
  },

  reviewWorkOrder: async (orderId: string, payload: ReviewWorkOrderRequest): Promise<WorkOrder> => {
    const res = await client.post(`/api/work-orders/${orderId}/review`, payload);
    return res.data;
  },

  uploadProofPhoto: async (formData: FormData): Promise<{ proof_image_url: string; filename: string }> => {
    const res = await client.post('/api/work-orders/upload-proof', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  }
};
