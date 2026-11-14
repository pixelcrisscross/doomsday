import React, { useEffect, useState } from 'react';
import { FileText, Download, Filter, RefreshCw, Printer } from 'lucide-react';
import { api } from '../services/api';
import { InspectionRecord } from '../types';
import { SeverityBadge } from '../components/SeverityBadge';
import { StatusBadge } from '../components/StatusBadge';

export const Reports: React.FC = () => {
  const [reports, setReports] = useState<InspectionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [severity, setSeverity] = useState('ALL');
  const [mediaType, setMediaType] = useState('ALL');

  const fetchReports = async () => {
    setLoading(true);
    try {
      const data = await api.getReports({
        severity: severity !== 'ALL' ? severity : undefined,
        media_type: mediaType !== 'ALL' ? mediaType : undefined,
        limit: 100
      });
      setReports(data.records || []);
    } catch (err) {
      console.error('Failed to load reports:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, [severity, mediaType]);

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="space-y-6">
      {/* Export Bar */}
      <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">Dispatch Center Exports</div>
          <div className="text-sm font-semibold text-slate-900 dark:text-white mt-0.5">
            {reports.length} Road Damage Record(s) Ready for Dispatch
          </div>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <select
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
            className="text-xs px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="SEVERE">Severe</option>
            <option value="MODERATE">Moderate</option>
            <option value="MINOR">Minor</option>
          </select>

          <a
            href={api.getCsvExportUrl()}
            download="roadsentinel_inspections.csv"
            className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-medium flex items-center gap-2 transition-colors shadow-sm"
          >
            <Download className="w-4 h-4" /> Export CSV
          </a>

          <button
            onClick={handlePrint}
            className="p-2 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
            title="Print Report"
          >
            <Printer className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Reports Grid */}
      <div className="space-y-4">
        {loading ? (
          <div className="text-center p-8 text-xs text-slate-400">Loading reports...</div>
        ) : reports.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-400 border border-slate-200 dark:border-slate-800 rounded-xl bg-white dark:bg-slate-900">
            No inspection reports match the selected filters.
          </div>
        ) : (
          reports.map((r) => (
            <div
              key={r.inspection_id}
              className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-bold text-slate-900 dark:text-white">#{r.inspection_id}</span>
                  <span className="text-[11px] font-sans text-slate-400">({r.media_type.toUpperCase()})</span>
                  <SeverityBadge severity={r.overall_severity} />
                  <StatusBadge verificationStatus={r.verification?.status} />
                </div>
                <div className="text-xs text-slate-600 dark:text-slate-300 font-sans">{r.location}</div>
                <div className="text-[11px] text-slate-400 font-mono">
                  GPS: {r.latitude ? `${r.latitude.toFixed(6)}, ${r.longitude?.toFixed(6)}` : 'UNAVAILABLE'} | Date: {r.date}
                </div>
              </div>

              <div className="flex items-center gap-4 text-xs font-mono">
                <div className="text-right">
                  <div className="font-bold text-rose-600">{r.final_potholes} Pothole(s)</div>
                  <div className="text-amber-600">{r.final_cracks} Crack(s)</div>
                </div>
                {r.annotated_filename && (
                  <a
                    href={`/outputs/${r.annotated_filename}`}
                    target="_blank"
                    rel="noreferrer"
                    className="p-2 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300"
                    title="View Media"
                  >
                    <FileText className="w-4 h-4" />
                  </a>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
