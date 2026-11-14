import React, { useState, useRef } from 'react';
import {
  UploadCloud,
  Camera,
  Play,
  RotateCcw,
  Download,
  CheckCircle,
  AlertTriangle,
  Info,
  ShieldCheck,
  FileText
} from 'lucide-react';

import { api } from '../services/api';
import { ImageDetectionResult } from '../types';
import { LocationPicker } from '../components/LocationPicker';
import { SeverityBadge } from '../components/SeverityBadge';
import { RiskBadge } from '../components/RiskBadge';
import { StatusBadge } from '../components/StatusBadge';

export const ImageDetection: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [confidence, setConfidence] = useState<number>(0.20);
  const [locationMeta, setLocationMeta] = useState<{ latitude: number | null; longitude: number | null; address: string; source: string }>({
    latitude: null,
    longitude: null,
    address: 'Location unavailable',
    source: 'UNAVAILABLE'
  });

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ImageDetectionResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setResult(null);
    setError(null);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setResult(null);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleRunDetection = async () => {
    if (!selectedFile) return;

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('confidence', confidence.toString());
    if (locationMeta.latitude !== null && locationMeta.longitude !== null) {
      formData.append('latitude', locationMeta.latitude.toString());
      formData.append('longitude', locationMeta.longitude.toString());
      formData.append('location_source', locationMeta.source);
    }

    try {
      const data = await api.detectImage(formData);
      setResult(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Inference execution failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Columns: Upload & Viewer */}
        <div className="lg:col-span-2 space-y-4">
          {/* Uploader Card */}
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm">
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3 flex items-center justify-between">
              <span>Road Surface Photo Upload</span>
              {selectedFile && (
                <button
                  onClick={handleReset}
                  className="text-xs text-slate-400 hover:text-rose-500 flex items-center gap-1 transition-colors"
                >
                  <RotateCcw className="w-3.5 h-3.5" /> Clear Photo
                </button>
              )}
            </div>

            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-slate-300 dark:border-slate-700 hover:border-emerald-500 dark:hover:border-emerald-500 rounded-xl p-6 text-center cursor-pointer transition-all bg-slate-50/50 dark:bg-slate-800/30"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".jpg,.jpeg,.png,.webp"
                className="hidden"
                onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
              />
              <UploadCloud className="w-8 h-8 mx-auto text-emerald-600 dark:text-emerald-400 mb-2" />
              <div className="text-xs font-medium text-slate-800 dark:text-slate-200">
                {selectedFile ? (
                  <span className="text-emerald-600 font-semibold">{selectedFile.name}</span>
                ) : (
                  <span>Click to browse or drag & drop road image</span>
                )}
              </div>
              <div className="text-[11px] text-slate-400 mt-1">
                Supports JPG, JPEG, PNG, WEBP (Dashcam or mobile photos)
              </div>
            </div>

            {/* Location Attachment */}
            <LocationPicker onLocationChange={setLocationMeta} />

            {/* Inference Confidence & Action */}
            <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="w-full sm:w-64">
                <div className="flex justify-between text-xs text-slate-600 dark:text-slate-400 mb-1">
                  <span>YOLO Confidence:</span>
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

              <button
                onClick={handleRunDetection}
                disabled={!selectedFile || loading}
                className="w-full sm:w-auto px-6 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-medium text-xs shadow-sm flex items-center justify-center gap-2 transition-colors"
              >
                {loading ? (
                  <>
                    <RotateCcw className="w-4 h-4 animate-spin" />
                    Running Neural Inference...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-white" />
                    Run AI Road Damage Detection
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

          {/* Visual Side-by-Side Display */}
          {previewUrl && (
            <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  Visual Comparison
                </div>
                {result && (
                  <a
                    href={result.annotated_image_url}
                    download={`roadsentinel_${result.inspection_id}_annotated.jpg`}
                    className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-600 dark:text-emerald-400 hover:underline"
                  >
                    <Download className="w-3.5 h-3.5" /> Download Annotated Photo
                  </a>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <div className="text-[11px] font-semibold text-slate-500 mb-1.5">Original Road Photo</div>
                  <div className="rounded-lg overflow-hidden border border-slate-200 dark:border-slate-800 bg-black">
                    <img src={previewUrl} alt="Original road" className="w-full h-auto max-h-80 object-contain mx-auto" />
                  </div>
                </div>

                <div>
                  <div className="text-[11px] font-semibold text-slate-500 mb-1.5">AI Annotated Detection</div>
                  <div className="rounded-lg overflow-hidden border border-slate-200 dark:border-slate-800 bg-black flex items-center justify-center min-h-[160px]">
                    {result ? (
                      <img src={result.annotated_image_url} alt="Annotated detection" className="w-full h-auto max-h-80 object-contain mx-auto" />
                    ) : (
                      <div className="text-slate-500 text-xs text-center p-6">
                        Click 'Run AI Road Damage Detection' to view bounding boxes and defect labels.
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Duplicate Alert */}
              {result && result.duplicate_candidates && result.duplicate_candidates.length > 0 && (
                <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900/60 text-xs">
                  <div className="flex items-center gap-2 font-semibold text-amber-800 dark:text-amber-300">
                    <AlertTriangle className="w-4 h-4 text-amber-600" />
                    Possible Duplicate Road Hazard Detected!
                  </div>
                  <div className="mt-1 text-slate-600 dark:text-slate-400">
                    This pothole matches physical defect in Report <b>#{result.duplicate_candidates[0].original_report_id}</b>
                    {result.duplicate_candidates[0].distance_m != null && ` located ${result.duplicate_candidates[0].distance_m.toFixed(1)}m away`}.
                    Composite similarity: <b>{(result.duplicate_candidates[0].similarity_score * 100).toFixed(0)}%</b>.
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Column: Statistics & Report Panel */}
        <div className="space-y-4">
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm space-y-4">
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Detected Defects
            </div>

            <div className="space-y-2">
              <div className="flex justify-between items-center text-xs py-1.5 px-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60">
                <span className="flex items-center gap-2 text-slate-700 dark:text-slate-300">
                  <span className="w-2 h-2 rounded-full bg-rose-500"></span> POTHOLE
                </span>
                <span className="font-mono font-bold text-slate-900 dark:text-white">
                  {result ? result.breakdown.potholes : '—'}
                </span>
              </div>

              <div className="flex justify-between items-center text-xs py-1.5 px-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60">
                <span className="flex items-center gap-2 text-slate-700 dark:text-slate-300">
                  <span className="w-2 h-2 rounded-full bg-sky-500"></span> LONGITUDINAL CRACK
                </span>
                <span className="font-mono font-bold text-slate-900 dark:text-white">
                  {result ? result.breakdown.longitudinal : '—'}
                </span>
              </div>

              <div className="flex justify-between items-center text-xs py-1.5 px-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60">
                <span className="flex items-center gap-2 text-slate-700 dark:text-slate-300">
                  <span className="w-2 h-2 rounded-full bg-purple-500"></span> TRANSVERSE CRACK
                </span>
                <span className="font-mono font-bold text-slate-900 dark:text-white">
                  {result ? result.breakdown.transverse : '—'}
                </span>
              </div>

              <div className="flex justify-between items-center text-xs py-1.5 px-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60">
                <span className="flex items-center gap-2 text-slate-700 dark:text-slate-300">
                  <span className="w-2 h-2 rounded-full bg-emerald-500"></span> ALLIGATOR CRACK
                </span>
                <span className="font-mono font-bold text-slate-900 dark:text-white">
                  {result ? result.breakdown.alligator : '—'}
                </span>
              </div>
            </div>

            {/* Individual Confidence Breakdown */}
            {result && result.detections && result.detections.length > 0 && (
              <div className="pt-3 border-t border-slate-100 dark:border-slate-800">
                <div className="text-[11px] font-semibold text-slate-500 mb-2">INDIVIDUAL DEFECT SCORES</div>
                <div className="space-y-1.5 max-h-40 overflow-y-auto">
                  {result.detections.map((d, i) => (
                    <div key={i} className="flex items-center justify-between p-1.5 rounded bg-slate-50 dark:bg-slate-800 text-[11px]">
                      <span className="font-medium text-slate-700 dark:text-slate-300">
                        #{i + 1} {d.class_name}
                      </span>
                      <span className="font-mono text-amber-600 dark:text-amber-400 font-semibold">
                        {(d.confidence * 100).toFixed(1)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="pt-3 border-t border-slate-100 dark:border-slate-800 space-y-2">
              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-500">Visual Severity:</span>
                <SeverityBadge severity={result ? result.overall_severity : 'NONE'} />
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-500">Risk Estimate:</span>
                <RiskBadge risk={result ? result.risk_category : 'None'} />
              </div>
            </div>
          </div>

          {/* Report Summary Card */}
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm space-y-3">
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Inspection Summary
            </div>

            <div className="bg-slate-50 dark:bg-slate-950 p-3 rounded-lg border border-slate-200 dark:border-slate-800 font-mono text-[11px] space-y-1 text-slate-700 dark:text-slate-300">
              {result ? (
                <>
                  <div>ID: <b>#{result.inspection_id}</b></div>
                  <div>Defects: {result.total_defects} ({result.potholes} potholes, {result.cracks} cracks)</div>
                  <div className="truncate">Loc: {result.location}</div>
                  <div>Model: {result.model_used}</div>
                  <div>Date: {result.date}</div>
                </>
              ) : (
                <div className="text-slate-400 font-sans text-xs">
                  Upload road photo and click 'Run AI Detection' to generate verified inspection summary.
                </div>
              )}
            </div>

            {result && (
              <div className="p-2.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 text-xs flex items-center gap-2">
                <CheckCircle className="w-4 h-4 shrink-0 text-emerald-600" />
                <span>Inspection record saved to JSON Store & Dispatch Center</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
