import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Camera,
  MapPin,
  Upload,
  Search,
  CheckCircle2,
  Clock,
  AlertTriangle,
  ArrowRight,
  Sparkles,
  Flame,
  Activity,
  Layers,
  ExternalLink
} from 'lucide-react';
import { api } from '../../services/api';
import { InspectionRecord, ImageDetectionResult } from '../../types';
import { SeverityBadge } from '../../components/SeverityBadge';
import { LocationPicker } from '../../components/LocationPicker';

export const CitizenDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [recentReports, setRecentReports] = useState<InspectionRecord[]>([]);
  const [loading, setLoading] = useState(true);

  // Quick Report State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [coords, setCoords] = useState<{ latitude: number | null; longitude: number | null; address: string }>({
    latitude: 12.9716,
    longitude: 77.5946,
    address: 'MG Road, Bengaluru'
  });
  const [analyzing, setAnalyzing] = useState(false);
  const [detectionResult, setDetectionResult] = useState<ImageDetectionResult | null>(null);

  // Search ID
  const [searchId, setSearchId] = useState('');

  useEffect(() => {
    const fetchCitizenData = async () => {
      try {
        const res = await api.getReports({ limit: 8 });
        setRecentReports(res.records || []);
      } catch (err) {
        console.error('Failed to load citizen data:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchCitizenData();
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const f = e.target.files[0];
      setSelectedFile(f);
      setPreviewUrl(URL.createObjectURL(f));
      setDetectionResult(null);
    }
  };

  const handleRunDetection = async () => {
    if (!selectedFile) return;
    setAnalyzing(true);
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      if (coords.latitude) formData.append('latitude', coords.latitude.toString());
      if (coords.longitude) formData.append('longitude', coords.longitude.toString());
      if (coords.address) formData.append('location_name', coords.address);

      const res = await api.detectImage(formData);
      setDetectionResult(res);
      // Refresh reports table
      const updated = await api.getReports({ limit: 8 });
      setRecentReports(updated.records || []);
    } catch (err) {
      alert('AI image detection failed. Please retry.');
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-6 rounded-3xl bg-gradient-to-r from-[#14161b] to-[#1a1f2c] border border-blue-500/20 shadow-2xl">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30">
              Citizen Road User Portal
            </span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-white">
            Report Road Damage & Track Progress
          </h1>
          <p className="text-xs text-slate-400 max-w-xl">
            Help your city identify and repair potholes faster. Upload a road photo with GPS to submit a ticket directly to the municipal authority.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            to="/damage-map"
            className="px-4 py-2.5 rounded-2xl bg-white/10 hover:bg-white/20 text-white text-xs font-bold transition-all flex items-center gap-2 shadow-md"
          >
            <Flame className="w-4 h-4 text-[#ff0055]" />
            <span>View City Hazard Map</span>
          </Link>
        </div>
      </div>

      {/* Main Grid: Quick Report Card + Track By ID */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT: Quick Upload & AI Report Section (7 Cols) */}
        <div className="lg:col-span-7 p-6 rounded-3xl bg-[#14161b] border border-white/[0.06] shadow-xl space-y-4">
          <div className="flex items-center justify-between">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
              <Camera className="w-4 h-4 text-[#d4f933]" />
              <span>Instant Pothole Detection Studio</span>
            </div>
            <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full">
              YOLOv8x Active
            </span>
          </div>

          {/* Upload Area */}
          <div className="border-2 border-dashed border-white/10 rounded-2xl p-6 text-center hover:bg-white/[0.02] transition-colors">
            {previewUrl ? (
              <div className="space-y-3">
                <img src={previewUrl} alt="Road Photo" className="max-h-56 mx-auto rounded-xl object-contain shadow-md" />
                <div className="flex justify-center gap-3">
                  <label className="text-xs text-slate-400 hover:text-white cursor-pointer underline">
                    Change Photo
                    <input type="file" accept="image/*" onChange={handleFileSelect} className="hidden" />
                  </label>
                  <button
                    onClick={() => { setSelectedFile(null); setPreviewUrl(null); setDetectionResult(null); }}
                    className="text-xs text-rose-400 hover:underline"
                  >
                    Remove
                  </button>
                </div>
              </div>
            ) : (
              <label className="cursor-pointer block space-y-2">
                <Upload className="w-10 h-10 text-slate-500 mx-auto" />
                <div className="text-sm font-bold text-white">Click or Drag & Drop Road Photo</div>
                <div className="text-xs text-slate-400">JPG, PNG, WEBP from camera or dashcam</div>
                <input type="file" accept="image/*" onChange={handleFileSelect} className="hidden" />
              </label>
            )}
          </div>

          {/* Location & GPS Info */}
          <div className="p-3.5 rounded-2xl bg-[#181a20] border border-white/[0.04] space-y-2 text-xs">
            <div className="flex items-center justify-between text-slate-300">
              <span className="flex items-center gap-1.5 font-medium">
                <MapPin className="w-3.5 h-3.5 text-rose-500" /> Location: <b>{coords.address}</b>
              </span>
              <button
                type="button"
                onClick={() => {
                  if (navigator.geolocation) {
                    navigator.geolocation.getCurrentPosition((pos) => {
                      setCoords({
                        latitude: pos.coords.latitude,
                        longitude: pos.coords.longitude,
                        address: `GPS: ${pos.coords.latitude.toFixed(6)}, ${pos.coords.longitude.toFixed(6)}`
                      });
                    });
                  }
                }}
                className="text-[11px] font-bold text-[#d4f933] hover:underline"
              >
                Use My GPS
              </button>
            </div>
          </div>

          {/* Action Button */}
          <button
            onClick={handleRunDetection}
            disabled={!selectedFile || analyzing}
            className="w-full py-3 rounded-2xl bg-[#d4f933] hover:bg-[#bef264] disabled:opacity-40 text-black text-xs font-bold transition-all flex items-center justify-center gap-2 shadow-lg"
          >
            {analyzing ? (
              <span>Running YOLOv8 Neural Inference...</span>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                <span>Submit Report & Analyze Potholes</span>
              </>
            )}
          </button>

          {/* Detection Result Box */}
          {detectionResult && (
            <div className="p-4 rounded-2xl bg-[#181a20] border border-white/10 space-y-3 animate-in fade-in">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs font-bold text-white font-mono">
                    Ref ID: #{detectionResult.inspection_id}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    Defects: <b>{detectionResult.potholes}</b> Potholes, <b>{detectionResult.cracks}</b> Cracks
                  </div>
                </div>
                <SeverityBadge severity={detectionResult.overall_severity} />
              </div>

              {detectionResult.annotated_image_url && (
                <div className="rounded-xl overflow-hidden border border-white/10 bg-black aspect-video flex items-center justify-center">
                  <img src={detectionResult.annotated_image_url} alt="AI Detections" className="w-full h-full object-contain" />
                </div>
              )}

              <Link
                to={`/track?id=${detectionResult.inspection_id}`}
                className="w-full py-2 rounded-xl bg-white/10 hover:bg-white/20 text-white text-xs font-bold transition-all flex items-center justify-center gap-1.5"
              >
                <span>Track This Hazard Live</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          )}
        </div>

        {/* RIGHT: Quick Reference Search + Lifecycle Stepper Preview (5 Cols) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Quick Track Input */}
          <div className="p-6 rounded-3xl bg-[#14161b] border border-white/[0.06] shadow-xl space-y-4">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
              <Activity className="w-4 h-4 text-blue-400" />
              <span>Track Pothole By Reference ID</span>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (searchId.trim()) navigate(`/track?id=${searchId.trim().toUpperCase()}`);
              }}
              className="flex items-center gap-2"
            >
              <input
                type="text"
                value={searchId}
                onChange={(e) => setSearchId(e.target.value)}
                placeholder="e.g. RS-20261114-36B4F2"
                className="flex-1 p-2.5 text-xs font-mono rounded-xl border border-white/10 bg-[#16181e] text-white uppercase placeholder-slate-500 focus:outline-none focus:border-blue-400"
              />
              <button
                type="submit"
                className="px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold transition-all shadow-md"
              >
                Track
              </button>
            </form>
          </div>

          {/* How Progress Works (Stepper Explainer) */}
          <div className="p-6 rounded-3xl bg-[#14161b] border border-white/[0.06] shadow-xl space-y-4">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Audit Progression Workflow
            </div>
            <div className="space-y-3 text-xs">
              <div className="flex items-start gap-3">
                <span className="w-5 h-5 rounded-full bg-blue-500/20 text-blue-400 font-bold flex items-center justify-center text-[10px] shrink-0 mt-0.5">1</span>
                <div>
                  <div className="font-bold text-white">Citizen Report Uploaded</div>
                  <div className="text-slate-400 text-[11px]">Road image and device coordinates logged</div>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="w-5 h-5 rounded-full bg-[#d4f933]/20 text-[#d4f933] font-bold flex items-center justify-center text-[10px] shrink-0 mt-0.5">2</span>
                <div>
                  <div className="font-bold text-white">YOLOv8 AI Inference</div>
                  <div className="text-slate-400 text-[11px]">Automatic pothole detection & severity scoring</div>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="w-5 h-5 rounded-full bg-purple-500/20 text-purple-400 font-bold flex items-center justify-center text-[10px] shrink-0 mt-0.5">3</span>
                <div>
                  <div className="font-bold text-white">Municipal Authority Dispatch</div>
                  <div className="text-slate-400 text-[11px]">Verified and dispatched to contractor crew</div>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="w-5 h-5 rounded-full bg-amber-500/20 text-amber-400 font-bold flex items-center justify-center text-[10px] shrink-0 mt-0.5">4</span>
                <div>
                  <div className="font-bold text-white">Field Repair & Completion Proof</div>
                  <div className="text-slate-400 text-[11px]">Pothole patched and photographic proof uploaded</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* RECENT SUBMISSIONS TABLE */}
      <div className="p-6 rounded-3xl bg-[#14161b] border border-white/[0.06] shadow-xl space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Recent Hazard Inspections
            </div>
            <div className="text-xs text-slate-500 mt-0.5">Live records synchronized from MongoDB Atlas</div>
          </div>
          <Link to="/history" className="text-xs font-bold text-[#d4f933] hover:underline">
            View All History →
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-[#181a20] text-[11px] uppercase font-bold text-slate-400 border-b border-white/[0.06]">
              <tr>
                <th className="px-4 py-3">Reference ID</th>
                <th className="px-4 py-3">Location</th>
                <th className="px-4 py-3">Potholes</th>
                <th className="px-4 py-3">Severity</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04] font-mono text-[11px]">
              {recentReports.map((r) => (
                <tr key={r.inspection_id} className="hover:bg-white/[0.02] transition-colors">
                  <td className="px-4 py-3 font-bold text-white">#{r.inspection_id}</td>
                  <td className="px-4 py-3 font-sans truncate max-w-[200px]" title={r.location}>{r.location}</td>
                  <td className="px-4 py-3 text-slate-200">
                    <span className="text-rose-400 font-bold">{r.final_potholes} P</span>
                  </td>
                  <td className="px-4 py-3">
                    <SeverityBadge severity={r.overall_severity} />
                  </td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase bg-white/10 text-white font-sans">
                      {r.verification?.status || 'REPORTED'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-400 font-sans">{r.date}</td>
                  <td className="px-4 py-3 text-right font-sans">
                    <Link
                      to={`/track?id=${r.inspection_id}`}
                      className="inline-flex items-center gap-1 text-[#d4f933] font-bold hover:underline"
                    >
                      Track <ArrowRight className="w-3 h-3" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
