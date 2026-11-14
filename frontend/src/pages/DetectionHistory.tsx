import React, { useEffect, useState } from 'react';
import { Search, Filter, Trash2, Eye, Download, RefreshCw } from 'lucide-react';

import { api } from '../services/api';
import { InspectionRecord } from '../types';
import { SeverityBadge } from '../components/SeverityBadge';
import { StatusBadge } from '../components/StatusBadge';
import { Modal } from '../components/Modal';

export const DetectionHistory: React.FC = () => {
  const [reports, setReports] = useState<InspectionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [mediaType, setMediaType] = useState<string>('ALL');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');

  const [selectedReport, setSelectedReport] = useState<InspectionRecord | null>(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);

  const fetchReports = async () => {
    setLoading(true);
    try {
      const data = await api.getReports({
        search: search.trim() || undefined,
        media_type: mediaType !== 'ALL' ? mediaType : undefined,
        severity: severityFilter !== 'ALL' ? severityFilter : undefined,
      });
      setReports(data.records || []);
    } catch (err) {
      console.error('Failed to fetch reports:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, [mediaType, severityFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchReports();
  };

  const handleDelete = async (id: string) => {
    if (!confirm(`Are you sure you want to delete inspection #${id}?`)) return;
    try {
      await api.deleteReport(id);
      fetchReports();
    } catch (err) {
      alert('Failed to delete report.');
    }
  };

  const openDetails = (report: InspectionRecord) => {
    setSelectedReport(report);
    setDetailModalOpen(true);
  };

  return (
    <div className="space-y-6">
      {/* Search & Filters */}
      <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4">
        <form onSubmit={handleSearchSubmit} className="relative w-full sm:w-80">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search ID or Location..."
            className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />
        </form>

        <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto">
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">Media:</span>
            <select
              value={mediaType}
              onChange={(e) => setMediaType(e.target.value)}
              className="text-xs px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
            >
              <option value="ALL">All Media</option>
              <option value="photo">Photos</option>
              <option value="video">Videos</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">Severity:</span>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="text-xs px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
            >
              <option value="ALL">All Severities</option>
              <option value="CRITICAL">Critical</option>
              <option value="SEVERE">Severe</option>
              <option value="MODERATE">Moderate</option>
              <option value="MINOR">Minor</option>
            </select>
          </div>

          <button
            onClick={fetchReports}
            className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-600 dark:text-slate-300">
            <thead className="bg-slate-50 dark:bg-slate-800/60 text-[11px] uppercase font-semibold text-slate-500 border-b border-slate-200 dark:border-slate-800">
              <tr>
                <th className="px-5 py-3">Inspection ID</th>
                <th className="px-5 py-3">Type</th>
                <th className="px-5 py-3">Location</th>
                <th className="px-5 py-3">Potholes / Cracks</th>
                <th className="px-5 py-3">Severity</th>
                <th className="px-5 py-3">Verification</th>
                <th className="px-5 py-3">Date</th>
                <th className="px-5 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800 font-mono text-[11px]">
              {loading ? (
                <tr>
                  <td colSpan={8} className="px-5 py-8 text-center text-slate-400 font-sans text-xs">
                    Loading records from local JSON store...
                  </td>
                </tr>
              ) : reports.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-5 py-8 text-center text-slate-400 font-sans text-xs">
                    No inspection records found.
                  </td>
                </tr>
              ) : (
                reports.map((r) => (
                  <tr key={r.inspection_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                    <td className="px-5 py-3 font-semibold text-slate-900 dark:text-white">#{r.inspection_id}</td>
                    <td className="px-5 py-3 font-sans capitalize">{r.media_type}</td>
                    <td className="px-5 py-3 font-sans truncate max-w-[180px]" title={r.location}>{r.location}</td>
                    <td className="px-5 py-3">
                      <span className="text-rose-600 font-semibold">{r.final_potholes} P</span> / <span className="text-amber-600">{r.final_cracks} C</span>
                    </td>
                    <td className="px-5 py-3">
                      <SeverityBadge severity={r.overall_severity} />
                    </td>
                    <td className="px-5 py-3">
                      <StatusBadge verificationStatus={r.verification?.status} />
                    </td>
                    <td className="px-5 py-3 text-slate-400 font-sans">{r.date}</td>
                    <td className="px-5 py-3 text-right space-x-2">
                      <button
                        onClick={() => openDetails(r)}
                        className="p-1 rounded text-slate-500 hover:text-emerald-600 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                        title="View Details"
                      >
                        <Eye className="w-3.5 h-3.5 inline" />
                      </button>
                      <button
                        onClick={() => handleDelete(r.inspection_id)}
                        className="p-1 rounded text-slate-500 hover:text-rose-600 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                        title="Delete Record"
                      >
                        <Trash2 className="w-3.5 h-3.5 inline" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Details Modal */}
      <Modal
        isOpen={detailModalOpen}
        onClose={() => setDetailModalOpen(false)}
        title={`Inspection #${selectedReport?.inspection_id}`}
      >
        {selectedReport && (
          <div className="space-y-4 text-xs font-sans">
            {selectedReport.annotated_filename && (
              <div className="rounded-lg overflow-hidden border border-slate-200 dark:border-slate-800 bg-black aspect-video flex items-center justify-center">
                <img
                  src={`/outputs/${selectedReport.annotated_filename}`}
                  alt="Inspection preview"
                  className="w-full h-full object-contain"
                />
              </div>
            )}

            <div className="grid grid-cols-2 gap-3 p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
              <div><span className="text-slate-400">Type:</span> <b>{selectedReport.type}</b></div>
              <div><span className="text-slate-400">Date:</span> {selectedReport.date}</div>
              <div><span className="text-slate-400">Potholes:</span> <b className="text-rose-600">{selectedReport.final_potholes}</b></div>
              <div><span className="text-slate-400">Cracks:</span> <b className="text-amber-600">{selectedReport.final_cracks}</b></div>
              <div><span className="text-slate-400">Severity:</span> <SeverityBadge severity={selectedReport.overall_severity} /></div>
              <div><span className="text-slate-400">Risk:</span> {selectedReport.risk_category}</div>
            </div>

            <div>
              <div className="text-slate-400 font-semibold mb-1">Geographic Coordinates:</div>
              <div className="font-mono text-[11px] text-slate-700 dark:text-slate-300">
                Lat: {selectedReport.latitude ?? 'N/A'}, Lon: {selectedReport.longitude ?? 'N/A'} (Source: {selectedReport.location_source ?? 'UNAVAILABLE'})
              </div>
              <div className="text-slate-600 dark:text-slate-400 mt-0.5">{selectedReport.location}</div>
            </div>

            {selectedReport.verification && (
              <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg space-y-1">
                <div className="font-semibold text-slate-400">Verification Audit:</div>
                <div>Status: <StatusBadge verificationStatus={selectedReport.verification.status} /></div>
                {selectedReport.verification.verified_by && (
                  <div>Verified By: {selectedReport.verification.verified_by}</div>
                )}
                {selectedReport.verification.rejection_reason && (
                  <div className="text-rose-600">Rejection Reason: {selectedReport.verification.rejection_reason}</div>
                )}
                {selectedReport.verification.corrected_class && (
                  <div>Corrected Class: <b>{selectedReport.verification.corrected_class}</b></div>
                )}
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};
