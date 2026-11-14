import React, { useEffect, useState } from 'react';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid
} from 'recharts';
import { Activity, ShieldCheck, AlertTriangle, Layers } from 'lucide-react';

import { api } from '../services/api';
import { OverviewAnalytics } from '../types';

const SEVERITY_COLORS = ['#10b981', '#f59e0b', '#f97316', '#ef4444'];
const VERIFICATION_COLORS = ['#38bdf8', '#10b981', '#ef4444'];

export const Analytics: React.FC = () => {
  const [analytics, setAnalytics] = useState<OverviewAnalytics | null>(null);
  const [trends, setTrends] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [aData, tData] = await Promise.all([
          api.getOverviewAnalytics(),
          api.getTrends()
        ]);
        setAnalytics(aData);
        setTrends(tData || []);
      } catch (err) {
        console.error('Failed to load analytics:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return <div className="text-xs text-slate-400 p-8 text-center">Loading analytics data...</div>;
  }

  const sevData = analytics?.severity_breakdown
    ? [
        { name: 'Minor', value: analytics.severity_breakdown.MINOR || 0 },
        { name: 'Moderate', value: analytics.severity_breakdown.MODERATE || 0 },
        { name: 'Severe', value: analytics.severity_breakdown.SEVERE || 0 },
        { name: 'Critical', value: analytics.severity_breakdown.CRITICAL || 0 },
      ]
    : [];

  const verData = analytics?.verification_counts
    ? [
        { name: 'AI Pending', value: analytics.verification_counts.AI_PENDING || 0 },
        { name: 'Verified', value: analytics.verification_counts.VERIFIED || 0 },
        { name: 'Rejected', value: analytics.verification_counts.REJECTED || 0 },
      ]
    : [];

  const defectComparisonData = [
    { category: 'Potholes', count: analytics?.total_potholes || 0, fill: '#ef4444' },
    { category: 'Cracks', count: analytics?.total_cracks || 0, fill: '#f59e0b' },
    { category: 'Unique Tracked', count: analytics?.unique_hazards || 0, fill: '#10b981' }
  ];

  return (
    <div className="space-y-6">
      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 shadow-sm">
          <div className="text-xs text-slate-500 font-semibold uppercase">Total Inspections</div>
          <div className="text-2xl font-bold font-mono text-slate-900 dark:text-white mt-1">
            {analytics?.total_inspections || 0}
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 shadow-sm">
          <div className="text-xs text-slate-500 font-semibold uppercase">Total Potholes</div>
          <div className="text-2xl font-bold font-mono text-rose-600 mt-1">
            {analytics?.total_potholes || 0}
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 shadow-sm">
          <div className="text-xs text-slate-500 font-semibold uppercase">Total Cracks</div>
          <div className="text-2xl font-bold font-mono text-amber-600 mt-1">
            {analytics?.total_cracks || 0}
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 shadow-sm">
          <div className="text-xs text-slate-500 font-semibold uppercase">Unique Tracked</div>
          <div className="text-2xl font-bold font-mono text-emerald-600 mt-1">
            {analytics?.unique_hazards || 0}
          </div>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Defect Category Comparison */}
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-4">
            Defect Quantity Comparison
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={defectComparisonData}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                <XAxis dataKey="category" stroke="#94a3b8" fontSize={11} tickLine={false} />
                <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} />
                <Tooltip />
                <Bar dataKey="count" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Severity Distribution */}
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-4">
            Visual Severity Share
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={sevData} cx="50%" cy="50%" innerRadius={55} outerRadius={85} paddingAngle={4} dataKey="value">
                  {sevData.map((_, index) => (
                    <Cell key={`sev-cell-${index}`} fill={SEVERITY_COLORS[index % SEVERITY_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Verification Status Distribution */}
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-4">
            Human-In-The-Loop QA Status
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={verData} cx="50%" cy="50%" innerRadius={55} outerRadius={85} paddingAngle={4} dataKey="value">
                  {verData.map((_, index) => (
                    <Cell key={`ver-cell-${index}`} fill={VERIFICATION_COLORS[index % VERIFICATION_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chronological Trends */}
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-4">
            Chronological Damage Volume Trend
          </div>
          <div className="h-64">
            {trends.length === 0 ? (
              <div className="flex h-full items-center justify-center text-xs text-slate-400">
                Insufficient chronological data for trend graphing
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trends}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                  <XAxis dataKey="period" stroke="#94a3b8" fontSize={11} tickLine={false} />
                  <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="potholes" stroke="#ef4444" strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="cracks" stroke="#f59e0b" strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
