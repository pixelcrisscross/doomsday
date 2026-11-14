import React, { useEffect, useState } from 'react';
import { Cpu, Server, CheckCircle2, ShieldCheck, Zap, Database, GitBranch } from 'lucide-react';
import { api } from '../services/api';
import { OverviewAnalytics } from '../types';

export const AIEvaluation: React.FC = () => {
  const [analytics, setAnalytics] = useState<OverviewAnalytics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await api.getOverviewAnalytics();
        setAnalytics(data);
      } catch (err) {
        console.error('Failed to load AI evaluation data:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const deviceInfo = analytics?.device_info;

  return (
    <div className="space-y-6">
      {/* Hardware & Acceleration Status */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-emerald-50 text-emerald-600 dark:bg-emerald-950 dark:text-emerald-400">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs text-slate-500 font-semibold uppercase">Inference Hardware</div>
              <div className="text-sm font-bold text-slate-900 dark:text-white truncate">
                {deviceInfo?.device_name || 'CPU (Universal Fallback)'}
              </div>
            </div>
          </div>
          <div className="mt-3 text-xs text-slate-500 flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${deviceInfo?.cuda_available ? 'bg-emerald-500' : 'bg-sky-500'}`}></span>
            CUDA Acceleration: <b>{deviceInfo?.cuda_available ? 'Active (NVIDIA GPU)' : 'CPU Threaded'}</b>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-sky-50 text-sky-600 dark:bg-sky-950 dark:text-sky-400">
              <Zap className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs text-slate-500 font-semibold uppercase">Offline Mode</div>
              <div className="text-sm font-bold text-slate-900 dark:text-white">
                100% Autonomous
              </div>
            </div>
          </div>
          <div className="mt-3 text-xs text-slate-500 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
            No external cloud LLM dependencies required
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-purple-50 text-purple-600 dark:bg-purple-950 dark:text-purple-400">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs text-slate-500 font-semibold uppercase">Inspection Store</div>
              <div className="text-sm font-bold text-slate-900 dark:text-white">
                Atomic Local JSON
              </div>
            </div>
          </div>
          <div className="mt-3 text-xs text-slate-500 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
            data/inspections.json ({analytics?.total_inspections ?? 0} records)
          </div>
        </div>
      </div>

      {/* Model Hierarchy Card */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm space-y-4">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Neural Model Cascade Hierarchy
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 space-y-2">
            <div className="flex items-center justify-between">
              <div className="font-semibold text-xs text-slate-900 dark:text-white flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                Tier 1: Multi-Class Road Distress (RDD2022)
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-400">
                ACTIVE
              </span>
            </div>
            <div className="text-xs text-slate-500">
              Weights: <code className="text-slate-700 dark:text-slate-300">weights/rdd2022_yolov8m.pt</code>
            </div>
            <div className="text-xs text-slate-600 dark:text-slate-400">
              Detects: Potholes, Longitudinal Cracks, Transverse Cracks, Alligator Cracks.
            </div>
          </div>

          <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 space-y-2">
            <div className="flex items-center justify-between">
              <div className="font-semibold text-xs text-slate-900 dark:text-white flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                Tier 2: Specialized Pothole Detector
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-400">
                ACTIVE
              </span>
            </div>
            <div className="text-xs text-slate-500">
              Weights: <code className="text-slate-700 dark:text-slate-300">weights/pothole_yolov8.pt</code>
            </div>
            <div className="text-xs text-slate-600 dark:text-slate-400">
              Specialized high-recall pothole verification model cascading on primary scan.
            </div>
          </div>
        </div>
      </div>

      {/* Duplicate Engine Metrics */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm space-y-3">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Duplicate Pothole Identification Engine
        </div>
        <div className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed space-y-1.5">
          <div>• <b>Geographic Proximity:</b> Haversine distance threshold of <b>25.0 meters</b> to prevent false duplicate grouping across street blocks.</div>
          <div>• <b>Perceptual Hash:</b> 64-bit gradient difference hash (dHash) computed on isolated pothole bounding-box crops (margin ratio 0.15).</div>
          <div>• <b>Composite Scoring:</b> Blends normalized Hamming distance and image feature similarity for physical pothole re-identification.</div>
          <div>• <b>Manual Review Queue:</b> Submissions missing authentic GPS fall back automatically to human QA review rather than generating false negatives.</div>
        </div>
      </div>
    </div>
  );
};
