import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Plus,
  HardHat,
  MapPin,
  FileDown,
  AlertTriangle,
  Flame,
  CheckCircle2,
  Clock,
  ArrowUpRight,
  Filter,
  Layers,
  ChevronRight,
  ShieldCheck,
  TrendingUp,
  Activity
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  AreaChart,
  Area
} from 'recharts';

import { api } from '../services/api';
import { OverviewAnalytics, InspectionRecord } from '../types';

interface AlertItem {
  id: string;
  type: string;
  badge: 'Warning' | 'Critical';
  title: string;
  desc: string;
  inspectionId?: string;
  timestamp: string;
  resolved?: boolean;
}

const mockAlerts: AlertItem[] = [
  {
    id: 'alt-1',
    type: 'Critical Pothole Cluster',
    badge: 'Critical',
    title: 'Severe Impact Hazard on Outer Ring Road',
    desc: 'Cluster of 3 deep potholes detected near Bellandur flyover. Severe risk to two-wheelers.',
    inspectionId: 'RS-20261114-36B4F2',
    timestamp: '12 min ago'
  },
  {
    id: 'alt-2',
    type: 'Structural Surface Failure',
    badge: 'Critical',
    title: 'Bridge Expansion Joint Subsidence',
    desc: 'Transverse cracking and asphalt depression exceeding 65mm on Hebbal flyover ramp.',
    inspectionId: 'RS-20261114-AA7720',
    timestamp: '42 min ago'
  },
  {
    id: 'alt-3',
    type: 'Geofence Proximity Alert',
    badge: 'Warning',
    title: 'Duplicate Defect Proximity Trigger',
    desc: 'New report matches candidate within 25m duplicate radius on Indiranagar 100ft Road.',
    inspectionId: 'RS-20261114-539817',
    timestamp: '1 hr ago'
  }
];

const mockActivity = [
  {
    id: 'act-1',
    title: 'Geofence duplicate trigger resolved for #RS-20261114-36B4F2',
    time: 'Today 06:21 AM',
    actor: 'Auto-Deduplication'
  },
  {
    id: 'act-2',
    title: 'Repair proof submitted by Contractor Ramesh Kumar (#WO-8821)',
    time: 'Today 05:45 AM',
    actor: 'Field Contractor'
  },
  {
    id: 'act-3',
    title: 'YOLOv8 detected 4 high-risk potholes on Bannerghatta Road',
    time: 'Today 04:15 AM',
    actor: 'YOLOv8 Engine'
  },
  {
    id: 'act-4',
    title: 'Work Order #WO-3914 approved & marked closed by Municipal Authority',
    time: 'Yesterday 11:30 PM',
    actor: 'Authority'
  }
];

const trendData = [
  { day: 'Sun', count: 14, fixed: 12 },
  { day: 'Mon', count: 28, fixed: 24 },
  { day: 'Tue', count: 42, fixed: 38 },
  { day: 'Wed', count: 32, fixed: 30 },
  { day: 'Thu', count: 56, fixed: 50 },
  { day: 'Fri', count: 68, fixed: 62 },
  { day: 'Sat', count: 45, fixed: 42 }
];

const performanceData = [
  { time: '00:00', rate: 70 },
  { time: '04:00', rate: 75 },
  { time: '08:00', rate: 84 },
  { time: '12:00', rate: 92 },
  { time: '16:00', rate: 88 },
  { time: '20:00', rate: 95 },
  { time: '23:59', rate: 94 }
];

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [analytics, setAnalytics] = useState<OverviewAnalytics | null>(null);
  const [recentReports, setRecentReports] = useState<InspectionRecord[]>([]);
  const [filterTab, setFilterTab] = useState<'all' | 'active' | 'repair' | 'closed'>('all');
  const [alerts, setAlerts] = useState<AlertItem[]>(mockAlerts);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [aData, rData] = await Promise.all([
          api.getOverviewAnalytics(),
          api.getReports({ limit: 6 })
        ]);
        setAnalytics(aData);
        setRecentReports(rData.records || []);
      } catch (err) {
        console.error('Failed to load dashboard data:', err);
      }
    };
    fetchData();
  }, []);

  const handleResolveAlert = (id: string) => {
    setAlerts(alerts.map(a => a.id === id ? { ...a, resolved: true } : a));
  };

  return (
    <div className="space-y-6">
      {/* Page Header (Matching Haulix Operations Dashboard title) */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white flex items-center gap-3">
            Operations Dashboard
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time road distress intelligence, AI inference telemetry & contractor dispatch
          </p>
        </div>

        {/* Filter Pills Bar (All 10, Active 6, Idle 2, Maintenance 1, etc.) */}
        <div className="flex items-center gap-1.5 p-1 rounded-2xl bg-[#14161b] border border-white/[0.06] overflow-x-auto max-w-full">
          <button
            onClick={() => setFilterTab('all')}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
              filterTab === 'all'
                ? 'bg-white text-black shadow-md'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            All <span className="ml-1 opacity-70">10</span>
          </button>
          <button
            onClick={() => setFilterTab('active')}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
              filterTab === 'active'
                ? 'bg-white text-black shadow-md'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Active <span className="ml-1 opacity-70">6</span>
          </button>
          <button
            onClick={() => setFilterTab('repair')}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
              filterTab === 'repair'
                ? 'bg-white text-black shadow-md'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Under Repair <span className="ml-1 opacity-70">3</span>
          </button>
          <button
            onClick={() => setFilterTab('closed')}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
              filterTab === 'closed'
                ? 'bg-white text-black shadow-md'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Closed <span className="ml-1 opacity-70">1</span>
          </button>
          <button
            className="w-8 h-8 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] flex items-center justify-center text-slate-400 hover:text-white transition-colors"
            title="Filter parameters"
          >
            <Filter className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Main Grid: Left Column (Quick Actions + Alerts + Activity) | Right Column (Utilization + Performance) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT COLUMN (7 Cols) */}
        <div className="lg:col-span-7 space-y-6">
          {/* Quick Actions Panel (Image 5 style) */}
          <div className="p-5 rounded-3xl bg-[#14161b] border border-white/[0.06] shadow-xl">
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
              Quick Actions
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <Link
                to="/image-detection"
                className="p-3.5 rounded-2xl bg-[#1b1e25] border border-white/[0.06] hover:border-[#d4f933]/50 hover:bg-[#20242e] transition-all flex items-center gap-3 group"
              >
                <div className="w-8 h-8 rounded-xl bg-[#d4f933]/10 text-[#d4f933] flex items-center justify-center font-bold">
                  <Plus className="w-4 h-4 group-hover:scale-110 transition-transform" />
                </div>
                <div>
                  <div className="text-xs font-semibold text-white">Report Distress</div>
                  <div className="text-[10px] text-slate-400">Image / Video Upload</div>
                </div>
              </Link>

              <Link
                to="/verification"
                className="p-3.5 rounded-2xl bg-[#1b1e25] border border-white/[0.06] hover:border-purple-400/50 hover:bg-[#20242e] transition-all flex items-center gap-3 group"
              >
                <div className="w-8 h-8 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center">
                  <HardHat className="w-4 h-4 group-hover:scale-110 transition-transform" />
                </div>
                <div>
                  <div className="text-xs font-semibold text-white">Assign Crew</div>
                  <div className="text-[10px] text-slate-400">Dispatch Work Order</div>
                </div>
              </Link>

              <Link
                to="/damage-map"
                className="p-3.5 rounded-2xl bg-[#1b1e25] border border-white/[0.06] hover:border-cyan-400/50 hover:bg-[#20242e] transition-all flex items-center gap-3 group"
              >
                <div className="w-8 h-8 rounded-xl bg-cyan-500/10 text-cyan-400 flex items-center justify-center">
                  <MapPin className="w-4 h-4 group-hover:scale-110 transition-transform" />
                </div>
                <div>
                  <div className="text-xs font-semibold text-white">Live Heatmap</div>
                  <div className="text-[10px] text-slate-400">City Thermography</div>
                </div>
              </Link>
            </div>
          </div>

          {/* Alert Priority Queue (Image 5 style) */}
          <div className="p-5 rounded-3xl bg-[#14161b] border border-white/[0.06] shadow-xl space-y-3">
            <div className="flex items-center justify-between">
              <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                Alert Priority Queue
              </div>
              <Link to="/verification" className="text-xs text-[#d4f933] hover:underline font-medium">
                See all
              </Link>
            </div>

            <div className="space-y-2.5">
              {alerts.map((alert) => (
                <div
                  key={alert.id}
                  className={`p-3.5 rounded-2xl bg-[#181a20] border transition-all flex items-start justify-between gap-3 ${
                    alert.resolved
                      ? 'border-white/[0.04] opacity-50'
                      : alert.badge === 'Critical'
                      ? 'border-l-4 border-l-[#ff3366] border-white/[0.06] hover:bg-[#1e2129]'
                      : 'border-l-4 border-l-[#fbbf24] border-white/[0.06] hover:bg-[#1e2129]'
                  }`}
                >
                  <div className="space-y-1 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-white">{alert.type}</span>
                      <span
                        className={`text-[9px] uppercase font-bold px-1.5 py-0.2 rounded-full ${
                          alert.badge === 'Critical'
                            ? 'bg-[#ff3366]/20 text-[#ff3366]'
                            : 'bg-amber-400/20 text-amber-400'
                        }`}
                      >
                        {alert.badge}
                      </span>
                      <span className="text-[10px] text-slate-500 font-mono">
                        {alert.timestamp}
                      </span>
                    </div>
                    <div className="text-xs text-slate-300 font-medium">{alert.title}</div>
                    <p className="text-[11px] text-slate-400 leading-relaxed">{alert.desc}</p>
                  </div>

                  <div className="flex items-center gap-1.5 pt-1">
                    {!alert.resolved && (
                      <button
                        onClick={() => handleResolveAlert(alert.id)}
                        className="w-7 h-7 rounded-xl bg-white/[0.06] hover:bg-[#d4f933] text-slate-300 hover:text-black flex items-center justify-center transition-colors"
                        title="Mark verified"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                    {alert.inspectionId && (
                      <Link
                        to={`/track?id=${alert.inspectionId}`}
                        className="w-7 h-7 rounded-xl bg-white/[0.06] hover:bg-white/20 text-slate-300 flex items-center justify-center transition-colors"
                        title="Inspect telemetry"
                      >
                        <ArrowUpRight className="w-3.5 h-3.5" />
                      </Link>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Recent Activity Feed (Image 5 style) */}
          <div className="p-5 rounded-3xl bg-[#14161b] border border-white/[0.06] shadow-xl space-y-3">
            <div className="flex items-center justify-between">
              <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                Recent Activity
              </div>
              <Link to="/history" className="text-xs text-[#d4f933] hover:underline font-medium">
                See all
              </Link>
            </div>

            <div className="space-y-2">
              {mockActivity.map((act) => (
                <div
                  key={act.id}
                  className="p-3 rounded-2xl bg-[#181a20] border border-white/[0.04] flex items-center justify-between text-xs"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-[#d4f933]"></div>
                    <div>
                      <div className="text-slate-200 font-medium">{act.title}</div>
                      <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                        {act.time} · {act.actor}
                      </div>
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-600" />
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN (5 Cols: Trend Bar Chart + Performance Wave Chart) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Fleet / Distress Trend (Cyan glowing bars, Image 5 style) */}
          <div className="p-5 rounded-3xl bg-[#14161b] border border-white/[0.06] shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                  Distress Distribution Trend
                </div>
                <div className="text-[11px] text-slate-500 mt-0.5">
                  Weekly defect count & resolved repairs
                </div>
              </div>
              <span className="text-xs font-bold text-[#00f0ff] bg-[#00f0ff]/10 px-2 py-0.5 rounded-full">
                +14.2%
              </span>
            </div>

            <div className="h-56 w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={trendData} barGap={4}>
                  <XAxis
                    dataKey="day"
                    stroke="#555b68"
                    fontSize={10}
                    tickLine={false}
                    axisLine={{ stroke: '#20242e' }}
                  />
                  <YAxis
                    stroke="#555b68"
                    fontSize={10}
                    tickLine={false}
                    axisLine={{ stroke: '#20242e' }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#181a20',
                      borderColor: 'rgba(255,255,255,0.1)',
                      borderRadius: '12px',
                      color: '#fff',
                      fontSize: '11px'
                    }}
                  />
                  <Bar
                    dataKey="count"
                    fill="#00f0ff"
                    radius={[6, 6, 0, 0]}
                    name="Detected Hazards"
                  />
                  <Bar
                    dataKey="fixed"
                    fill="#d4f933"
                    radius={[6, 6, 0, 0]}
                    name="Contractor Repaired"
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="flex items-center justify-center gap-6 pt-2 border-t border-white/[0.04] text-[11px]">
              <span className="flex items-center gap-2 text-slate-400">
                <span className="w-2 h-2 rounded-full bg-[#00f0ff]"></span> Hazards Detected
              </span>
              <span className="flex items-center gap-2 text-slate-400">
                <span className="w-2 h-2 rounded-full bg-[#d4f933]"></span> Repairs Completed
              </span>
            </div>
          </div>

          {/* On-Time Resolution Performance (Violet/Purple Wave Chart, Image 5 style) */}
          <div className="p-5 rounded-3xl bg-[#14161b] border border-white/[0.06] shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                  On-Time Repair Performance
                </div>
                <div className="text-[11px] text-slate-500 mt-0.5">
                  Resolution rate under SLA deadlines
                </div>
              </div>
              <span className="text-xs font-bold text-[#d4f933] bg-[#d4f933]/10 px-2 py-0.5 rounded-full">
                94.2% SLA
              </span>
            </div>

            <div className="h-52 w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={performanceData}>
                  <defs>
                    <linearGradient id="purpleGlow" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.6} />
                      <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <XAxis
                    dataKey="time"
                    stroke="#555b68"
                    fontSize={10}
                    tickLine={false}
                    axisLine={{ stroke: '#20242e' }}
                  />
                  <YAxis
                    stroke="#555b68"
                    fontSize={10}
                    domain={[60, 100]}
                    tickLine={false}
                    axisLine={{ stroke: '#20242e' }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#181a20',
                      borderColor: 'rgba(255,255,255,0.1)',
                      borderRadius: '12px',
                      color: '#fff',
                      fontSize: '11px'
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="rate"
                    stroke="#a78bfa"
                    strokeWidth={2.5}
                    fillOpacity={1}
                    fill="url(#purpleGlow)"
                    name="On-Time Rate %"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className="p-3 rounded-2xl bg-[#181a20] border border-white/[0.04] flex items-center justify-between text-xs">
              <div className="flex items-center gap-2 text-slate-400">
                <ShieldCheck className="w-4 h-4 text-[#d4f933]" />
                <span>Mean Time to Repair (MTTR):</span>
              </div>
              <span className="font-bold text-white">4.8 hours</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
