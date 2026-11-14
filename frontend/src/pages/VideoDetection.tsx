import React, { useState, useRef } from 'react';
import {
  UploadCloud,
  Video,
  Play,
  RotateCcw,
  Download,
  CheckCircle,
  AlertTriangle,
  Layers,
  Clock,
  Film
} from 'lucide-react';

import { api } from '../services/api';
import { VideoDetectionResult } from '../types';
import { LocationPicker } from '../components/LocationPicker';
import { SeverityBadge } from '../components/SeverityBadge';
import { RiskBadge } from '../components/RiskBadge';

export const VideoDetection: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [videoPreviewUrl, setVideoPreviewUrl] = useState<string | null>(null);
  const [confidence, setConfidence] = useState<number>(0.20);
  const [frameSkip, setFrameSkip] = useState<number>(2);
  const [locationMeta, setLocationMeta] = useState<{ latitude: number | null; longitude: number | null; address: string; source: string }>({
    latitude: null,
    longitude: null,
    address: 'Location unavailable',
    source: 'UNAVAILABLE'
  });

  const [loading, setLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [result, setResult] = useState<VideoDetectionResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    setVideoPreviewUrl(URL.createObjectURL(file));
    setResult(null);
    setError(null);
  };

  const handleReset = () => {
    setSelectedFile(null);
    setVideoPreviewUrl(null);
    setResult(null);
    setError(null);
    setUploadProgress(0);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleRunDetection = async () => {
    if (!selectedFile) return;

    setLoading(true);
    setError(null);
    setUploadProgress(0);

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('confidence', confidence.toString());
    formData.append('frame_skip', frameSkip.toString());
    if (locationMeta.latitude !== null && locationMeta.longitude !== null) {
      formData.append('latitude', locationMeta.latitude.toString());
      formData.append('longitude', locationMeta.longitude.toString());
      formData.append('location_source', locationMeta.source);
    }

    try {
      const data = await api.detectVideo(formData, (progressEvent) => {
        if (progressEvent.total) {
          const pct = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(pct);
        }
      });
      setResult(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Video processing failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Columns: Video Upload & Player */}
        <div className="lg:col-span-2 space-y-4">
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm">
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3 flex items-center justify-between">
              <span>Road Dashcam Video Upload</span>
              {selectedFile && (
                <button
                  onClick={handleReset}
                  className="text-xs text-slate-400 hover:text-rose-500 flex items-center gap-1 transition-colors"
                >
                  <RotateCcw className="w-3.5 h-3.5" /> Clear Video
                </button>
              )}
            </div>

            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-slate-300 dark:border-slate-700 hover:border-emerald-500 dark:hover:border-emerald-500 rounded-xl p-6 text-center cursor-pointer transition-all bg-slate-50/50 dark:bg-slate-800/30"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".mp4,.avi,.mov,.mkv"
                className="hidden"
                onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
              />
              <Film className="w-8 h-8 mx-auto text-emerald-600 dark:text-emerald-400 mb-2" />
              <div className="text-xs font-medium text-slate-800 dark:text-slate-200">
                {selectedFile ? (
                  <span className="text-emerald-600 font-semibold">{selectedFile.name} ({(selectedFile.size / (1024 * 1024)).toFixed(1)} MB)</span>
                ) : (
                  <span>Click to browse road video clip (.mp4, .avi, .mov, .mkv)</span>
                )}
              </div>
              <div className="text-[11px] text-slate-400 mt-1">
                Continuous road surveys with multi-frame IoU hazard tracking
              </div>
            </div>

            {/* Location Attachment */}
            <LocationPicker onLocationChange={setLocationMeta} />

            {/* Inference Parameters */}
            <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800 grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <div className="flex justify-between text-xs text-slate-600 dark:text-slate-400 mb-1">
                  <span>Confidence Threshold:</span>
                  <span className="font-mono font-semibold text-slate-900 dark:text-white">{(confidence * 100).toFixed(0)}%</span>
                </div>
                <input
                  type="range"
                  min="0.05"
                  max="0.85"
                  step="0.05"
                  value={confidence}
                  onChange={(e) => setConfidence(parseFloat(e.target.value))}
                  className="w-full accent-emerald-600 cursor-pointer h-1.5 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs text-slate-600 dark:text-slate-400 mb-1">
                  <span>Frame Sampling Step:</span>
                  <span className="font-mono font-semibold text-slate-900 dark:text-white">Every {frameSkip} frame(s)</span>
                </div>
                <select
                  value={frameSkip}
                  onChange={(e) => setFrameSkip(parseInt(e.target.value))}
                  className="w-full px-3 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-emerald-500"
                >
                  <option value={1}>1 - Process Every Frame (Highest Precision)</option>
                  <option value={2}>2 - Process Every 2 Frames (Balanced)</option>
                  <option value={3}>3 - Process Every 3 Frames (Faster Scan)</option>
                  <option value={5}>5 - Process Every 5 Frames (Rapid Preview)</option>
                </select>
              </div>
            </div>

            <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800 flex justify-end">
              <button
                onClick={handleRunDetection}
                disabled={!selectedFile || loading}
                className="w-full sm:w-auto px-6 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-medium text-xs shadow-sm flex items-center justify-center gap-2 transition-colors"
              >
                {loading ? (
                  <>
                    <RotateCcw className="w-4 h-4 animate-spin" />
                    Processing Video Frames ({uploadProgress}%)...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-white" />
                    Run Video AI Detection
                  </>
                )}
              </button>
            </div>
          </div>

          {error && (
            <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-xs text-rose-700 dark:text-rose-400 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Video Preview & Output */}
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Video Inspection Display
              </div>
              {result && (
                <a
                  href={result.download_url}
                  download={`roadsentinel_${result.inspection_id}_annotated.mp4`}
                  className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-600 dark:text-emerald-400 hover:underline"
                >
                  <Download className="w-3.5 h-3.5" /> Download Processed Video
                </a>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div className="text-[11px] font-semibold text-slate-500 mb-1.5">Original Video Input</div>
                {videoPreviewUrl ? (
                  <div className="rounded-lg overflow-hidden border border-slate-200 dark:border-slate-800 bg-black aspect-video flex items-center justify-center">
                    <video src={videoPreviewUrl} controls className="w-full h-full object-contain" />
                  </div>
                ) : (
                  <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-100 dark:bg-slate-800/40 aspect-video flex items-center justify-center text-xs text-slate-400">
                    No video selected
                  </div>
                )}
              </div>

              <div>
                <div className="text-[11px] font-semibold text-slate-500 mb-1.5">AI Annotated Output Video</div>
                {result ? (
                  <div className="rounded-lg overflow-hidden border border-slate-200 dark:border-slate-800 bg-black aspect-video flex items-center justify-center">
                    <video src={result.video_url} controls autoPlay loop className="w-full h-full object-contain" />
                  </div>
                ) : (
                  <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-100 dark:bg-slate-800/40 aspect-video flex items-center justify-center text-xs text-slate-400 text-center p-4">
                    Annotated video with bounding boxes and hazard tracking IDs will appear here.
                  </div>
                )}
              </div>
            </div>

            {/* Frame-wise Detection Table */}
            {result && result.table_rows && result.table_rows.length > 0 && (
              <div className="pt-4 border-t border-slate-100 dark:border-slate-800">
                <div className="text-xs font-semibold text-slate-500 mb-2">FRAME-WISE HAZARD LOG</div>
                <div className="max-h-56 overflow-y-auto rounded-lg border border-slate-200 dark:border-slate-800">
                  <table className="w-full text-left text-xs text-slate-600 dark:text-slate-300">
                    <thead className="bg-slate-50 dark:bg-slate-800/60 text-[11px] uppercase font-semibold text-slate-500 sticky top-0">
                      <tr>
                        <th className="px-3 py-2">Frame</th>
                        <th className="px-3 py-2">Timestamp</th>
                        <th className="px-3 py-2">Track ID</th>
                        <th className="px-3 py-2">Defect</th>
                        <th className="px-3 py-2">Confidence</th>
                        <th className="px-3 py-2">Severity</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800 font-mono text-[11px]">
                      {result.table_rows.map((row, idx) => (
                        <tr key={idx} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                          <td className="px-3 py-1.5">{row.frame_idx}</td>
                          <td className="px-3 py-1.5">{row.timestamp_sec.toFixed(2)}s</td>
                          <td className="px-3 py-1.5 font-bold text-emerald-600">#{row.track_id}</td>
                          <td className="px-3 py-1.5 font-sans">{row.class_name}</td>
                          <td className="px-3 py-1.5">{(row.confidence * 100).toFixed(1)}%</td>
                          <td className="px-3 py-1.5 font-sans">{row.severity_category}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Video Properties & Summary */}
        <div className="space-y-4">
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm space-y-4">
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Hazard Tracking Summary
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 text-center">
                <div className="text-[11px] text-emerald-700 dark:text-emerald-400 font-medium">UNIQUE HAZARDS</div>
                <div className="text-2xl font-bold font-mono text-emerald-800 dark:text-emerald-300 mt-1">
                  {result ? result.unique_hazard_count : '—'}
                </div>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 text-center">
                <div className="text-[11px] text-slate-500 font-medium">TOTAL DETECTIONS</div>
                <div className="text-2xl font-bold font-mono text-slate-900 dark:text-white mt-1">
                  {result ? result.total_detections : '—'}
                </div>
              </div>
            </div>

            <div className="space-y-2 pt-2 border-t border-slate-100 dark:border-slate-800">
              <div className="flex justify-between items-center text-xs py-1 px-2">
                <span className="text-slate-600 dark:text-slate-400">Potholes:</span>
                <span className="font-mono font-bold text-rose-600">{result ? result.potholes_count : '—'}</span>
              </div>
              <div className="flex justify-between items-center text-xs py-1 px-2">
                <span className="text-slate-600 dark:text-slate-400">Cracks Total:</span>
                <span className="font-mono font-bold text-amber-600">{result ? result.cracks_count : '—'}</span>
              </div>
              <div className="flex justify-between items-center text-xs py-1 px-2">
                <span className="text-slate-600 dark:text-slate-400">Longitudinal:</span>
                <span className="font-mono text-slate-700 dark:text-slate-300">{result ? result.breakdown.longitudinal : '—'}</span>
              </div>
              <div className="flex justify-between items-center text-xs py-1 px-2">
                <span className="text-slate-600 dark:text-slate-400">Transverse:</span>
                <span className="font-mono text-slate-700 dark:text-slate-300">{result ? result.breakdown.transverse : '—'}</span>
              </div>
              <div className="flex justify-between items-center text-xs py-1 px-2">
                <span className="text-slate-600 dark:text-slate-400">Alligator:</span>
                <span className="font-mono text-slate-700 dark:text-slate-300">{result ? result.breakdown.alligator : '—'}</span>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-100 dark:border-slate-800 space-y-2">
              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-500">Visual Severity:</span>
                <SeverityBadge severity={result ? result.overall_severity : 'NONE'} />
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-500">Risk Category:</span>
                <RiskBadge risk={result ? result.risk_category : 'None'} />
              </div>
            </div>
          </div>

          {result && (
            <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-2">
              <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">Inspection Record</div>
              <div className="text-xs font-mono text-slate-700 dark:text-slate-300">
                ID: <b>#{result.inspection_id}</b>
              </div>
              <div className="text-[11px] text-slate-500">
                Persisted to local JSON storage & Dispatch Center automatically.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
