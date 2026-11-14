import React, { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  Search,
  CheckCircle2,
  Clock,
  AlertCircle,
  MapPin,
  Calendar,
  HardHat,
  ShieldCheck,
  Camera,
  Activity,
  ArrowRight,
  ExternalLink,
  Sparkles
} from 'lucide-react';

import { api } from '../services/api';
import { InspectionStatusCheckResponse, InspectionRecord } from '../types';
import { SeverityBadge } from '../components/SeverityBadge';

export const StatusCheck: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialId = searchParams.get('id') || '';

  const [inspectionId, setInspectionId] = useState(initialId);
  const [data, setData] = useState<InspectionStatusCheckResponse | null>(null);
  const [recentReports, setRecentReports] = useState<InspectionRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchRecent = async () => {
      try {
        const res = await api.getReports({ limit: 6 });
        setRecentReports(res.records || []);
        if (!initialId && res.records && res.records.length > 0) {
          handleSearch(res.records[0].inspection_id);
        }
      } catch (err) {
        console.error('Failed to load recent reports:', err);
      }
    };
    fetchRecent();
  }, []);

  useEffect(() => {
    if (initialId) {
      handleSearch(initialId);
    }
  }, [initialId]);

  const handleSearch = async (targetId: string) => {
    const cleanId = targetId.trim().toUpperCase();
    if (!cleanId) return;

    setLoading(true);
    setError(null);
    setInspectionId(cleanId);
    setSearchParams({ id: cleanId });

    try {
      const res = await api.getStatusCheck(cleanId);
      setData(res);
    } catch (err: any) {
      setData(null);
      setError(err.response?.data?.detail || `No inspection found with ID: ${cleanId}`);
    } finally {
      setLoading(false);
    }
  };

  const getStepStatusStyle = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return {
          icon: CheckCircle2,
          color: 'text-[#d4f933]',
          bg: 'bg-[#d4f933]/15 border-[#d4f933]',
          line: 'bg-[#d4f933]'
        };
      case 'IN_PROGRESS':
        return {
          icon: Clock,
          color: 'text-amber-400',
          bg: 'bg-amber-400/15 border-amber-400 animate-pulse',
          line: 'bg-white/10'
        };
      case 'REJECTED':
        return {
          icon: AlertCircle,
          color: 'text-[#ff0055]',
          bg: 'bg-[#ff0055]/15 border-[#ff0055]',
          line: 'bg-[#ff0055]/30'
        };
      default:
        return {
          icon: Clock,
          color: 'text-slate-600',
          bg: 'bg-[#181a20] border-white/10',
          line: 'bg-white/5'
        };
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
          <Activity className="w-6 h-6 text-[#d4f933]" /> Pothole Repair Lifecycle Tracker
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          End-to-end transparent audit trail from AI distress detection to contractor dispatch and municipal sign-off
        </p>
      </div>

      {/* Search Input Bar (Carbon rounded-3xl) */}
      <div className="p-5 rounded-3xl border border-white/[0.06] bg-[#14161b] shadow-xl space-y-3">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSearch(inspectionId);
          }}
          className="flex items-center gap-2"
        >
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={inspectionId}
              onChange={(e) => setInspectionId(e.target.value)}
              placeholder="Enter Inspection Reference ID (e.g. RS-20261114-36B4F2)..."
              className="w-full pl-11 pr-4 py-2.5 text-xs font-mono rounded-2xl border border-white/10 bg-[#16181e] text-white uppercase placeholder-slate-500 focus:outline-none focus:border-[#d4f933]"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !inspectionId.trim()}
            className="px-5 py-2.5 rounded-2xl bg-[#d4f933] hover:bg-[#bef264] text-black text-xs font-bold flex items-center gap-2 transition-all shadow-lg"
          >
            {loading ? 'Searching...' : 'Track Status'}
          </button>
        </form>

        {/* Quick select recent IDs */}
        {recentReports.length > 0 && (
          <div className="flex items-center gap-2 pt-1 overflow-x-auto text-xs">
            <span className="text-[11px] text-slate-400 font-medium shrink-0">Recent Inspections:</span>
            {recentReports.map((r) => (
              <button
                key={r.inspection_id}
                type="button"
                onClick={() => handleSearch(r.inspection_id)}
                className={`px-3 py-1 rounded-xl font-mono text-[11px] shrink-0 transition-colors ${
                  inspectionId === r.inspection_id
                    ? 'bg-[#d4f933] text-black font-bold shadow-md'
                    : 'bg-[#181a20] text-slate-300 hover:bg-white/[0.08]'
                }`}
              >
                #{r.inspection_id}
              </button>
            ))}
          </div>
        )}
      </div>

      {error && (
        <div className="p-4 rounded-3xl border border-rose-500/20 bg-rose-500/10 text-rose-300 text-xs flex items-center gap-2.5">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Main Status Display */}
      {data && (
        <div className="space-y-6">
          {/* Progress Overview Card */}
          <div className="p-6 rounded-3xl border border-white/[0.06] bg-[#14161b] shadow-2xl space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2.5">
                  <span className="text-base font-extrabold font-mono text-white">
                    #{data.inspection_id}
                  </span>
                  <span className="text-xs font-bold px-3 py-0.5 rounded-full bg-[#d4f933]/20 text-[#d4f933] border border-[#d4f933]/30">
                    {data.current_status}
                  </span>
                  <SeverityBadge severity={data.overall_severity} />
                </div>
                <div className="text-xs text-slate-400 mt-1.5 flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-[#ff0055] shrink-0" />
                  <span>{data.location}</span>
                </div>
              </div>

              {/* Progress Percentage Badge */}
              <div className="flex sm:flex-col items-center sm:items-end justify-between">
                <div className="text-xs text-slate-400">Resolution Progress</div>
                <div className="text-3xl font-extrabold text-[#d4f933] drop-shadow-[0_0_12px_#d4f933]">
                  {data.progress_percent}%
                </div>
              </div>
            </div>

            {/* Progress Bar */}
            <div className="space-y-1.5">
              <div className="w-full bg-[#181a20] h-2.5 rounded-full overflow-hidden border border-white/[0.04]">
                <div
                  className="bg-gradient-to-r from-cyan-400 to-[#d4f933] h-full rounded-full transition-all duration-500 shadow-[0_0_10px_#d4f933]"
                  style={{ width: `${data.progress_percent}%` }}
                />
              </div>
              <div className="flex justify-between text-[10px] text-slate-500 pt-0.5">
                <span>Reported ({data.reported_at?.split('T')[0] || 'Day 1'})</span>
                <span>Assigned Contractor</span>
                <span>Repaired & Approved</span>
              </div>
            </div>

            {/* Details Pills */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-white/[0.06] text-xs">
              <div className="p-3 rounded-2xl bg-[#181a20] border border-white/[0.04]">
                <span className="text-slate-400 block text-[10px]">Potholes Detected</span>
                <span className="font-bold text-white text-sm">{data.potholes}</span>
              </div>
              <div className="p-3 rounded-2xl bg-[#181a20] border border-white/[0.04]">
                <span className="text-slate-400 block text-[10px]">Cracks Detected</span>
                <span className="font-bold text-white text-sm">{data.cracks}</span>
              </div>
              <div className="p-3 rounded-2xl bg-[#181a20] border border-white/[0.04]">
                <span className="text-slate-400 block text-[10px]">Assigned Contractor</span>
                <span className="font-bold text-white truncate block">
                  {data.assigned_worker || 'Municipal Dispatch Pending'}
                </span>
              </div>
              <div className="p-3 rounded-2xl bg-[#181a20] border border-white/[0.04]">
                <span className="text-slate-400 block text-[10px]">Interactive Map</span>
                <Link to="/damage-map" className="text-[#d4f933] font-bold hover:underline flex items-center gap-1">
                  View Pin <ExternalLink className="w-3 h-3" />
                </Link>
              </div>
            </div>
          </div>

          {/* Side-by-Side Visual Proof (Before vs After) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="p-5 rounded-3xl border border-white/[0.06] bg-[#14161b] shadow-xl space-y-3">
              <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
                <span className="flex items-center gap-1.5">
                  <Camera className="w-4 h-4 text-[#ff0055]" /> Detected Hazard (Before)
                </span>
                <span className="text-[10px] text-slate-500 font-mono">AI Annotated</span>
              </div>
              <div className="rounded-2xl overflow-hidden border border-white/10 bg-black aspect-video flex items-center justify-center">
                <img
                  src={`/outputs/${data.inspection_id}_annotated.jpg`}
                  onError={(e: any) => {
                    e.target.src = 'https://images.unsplash.com/photo-1515162816999-a0c47dc192f7?w=600&auto=format&fit=crop';
                  }}
                  alt="Original Defect"
                  className="w-full h-full object-contain"
                />
              </div>
            </div>

            <div className="p-5 rounded-3xl border border-white/[0.06] bg-[#14161b] shadow-xl space-y-3">
              <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
                <span className="flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-[#d4f933]" /> Completed Field Repair (After)
                </span>
                <span className="text-[10px] text-slate-500 font-mono">Contractor Verification</span>
              </div>
              {data.proof_image_url ? (
                <div className="rounded-2xl overflow-hidden border border-white/10 bg-black aspect-video flex items-center justify-center">
                  <img
                    src={data.proof_image_url}
                    alt="Repaired Road"
                    className="w-full h-full object-contain"
                  />
                </div>
              ) : (
                <div className="rounded-2xl border border-dashed border-white/10 bg-[#181a20] aspect-video flex flex-col items-center justify-center text-xs text-slate-400 p-4 text-center">
                  <Clock className="w-8 h-8 text-amber-400 mb-2" />
                  <span className="font-semibold text-slate-200">Repair Proof Pending</span>
                  <span className="text-[11px] text-slate-500 mt-1 max-w-xs">
                    Contractor crew will upload photographic proof once resurfacing and compaction are complete.
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* 7-Step Audit Lifecycle Timeline */}
          <div className="p-6 rounded-3xl border border-white/[0.06] bg-[#14161b] shadow-2xl space-y-6">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Auditable 7-Stage Repair Lifecycle
            </h3>

            <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-white/10">
              {data.timeline.map((step, idx) => {
                const config = getStepStatusStyle(step.status);
                const IconComponent = config.icon;

                return (
                  <div key={idx} className="relative flex items-start gap-4">
                    {/* Stepper Bullet */}
                    <div
                      className={`absolute -left-6 mt-0.5 w-6 h-6 rounded-full border-2 flex items-center justify-center bg-[#14161b] ${config.bg}`}
                    >
                      <IconComponent className={`w-3.5 h-3.5 ${config.color}`} />
                    </div>

                    {/* Step Content */}
                    <div className="space-y-1 flex-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-white">
                          Stage {step.step_index}: {step.title}
                        </span>
                        {step.timestamp && (
                          <span className="text-[11px] font-mono text-slate-400">
                            {step.timestamp.split('T')[0]} {step.timestamp.split('T')[1]?.substring(0, 5)}
                          </span>
                        )}
                      </div>

                      <p className="text-xs text-slate-300 leading-relaxed">
                        {step.description}
                      </p>

                      {step.actor && (
                        <div className="text-[10px] text-slate-500 font-medium">
                          Actor: <span className="text-slate-300">{step.actor}</span>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
