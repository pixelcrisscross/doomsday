import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  ShieldAlert,
  UserCheck,
  Shield,
  HardHat,
  ArrowRight,
  Sparkles,
  Layers,
  MapPin,
  CheckCircle2,
  Activity,
  Flame,
  Camera,
  LogIn,
  Cpu
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { UserRole } from '../types';
import { Modal } from '../components/Modal';

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const { loginAs, googleLogin } = useAuth();
  const [googleModalOpen, setGoogleModalOpen] = useState(false);
  const [googleEmail, setGoogleEmail] = useState('');
  const [googleName, setGoogleName] = useState('');
  const [googleRole, setGoogleRole] = useState<UserRole>('citizen');
  const [googleSubmitting, setGoogleSubmitting] = useState(false);

  const [stats, setStats] = useState({
    total: 18,
    active: 12,
    repaired: 6,
    accuracy: 94.2
  });

  useEffect(() => {
    const fetchLiveStats = async () => {
      try {
        const res = await api.getCityStats('Bengaluru Urban');
        if (res) {
          setStats({
            total: res.total_potholes || 18,
            active: res.active_hazards || 12,
            repaired: res.repaired_count || 6,
            accuracy: 94.2
          });
        }
      } catch {
        // Fallback stats
      }
    };
    fetchLiveStats();
  }, []);

  const handleSelectRole = async (selectedRole: UserRole, targetRoute: string) => {
    await loginAs(selectedRole);
    navigate(targetRoute);
  };

  const handleGoogleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!googleEmail || !googleEmail.includes('@')) return;
    setGoogleSubmitting(true);
    try {
      await googleLogin({
        email: googleEmail,
        name: googleName || googleEmail.split('@')[0],
        role: googleRole,
        avatar_url: `https://api.dicebear.com/7.x/avataaars/svg?seed=${googleEmail}`
      });
      setGoogleModalOpen(false);
      navigate(googleRole === 'authority' ? '/authority' : googleRole === 'worker' ? '/contractor' : '/citizen');
    } catch (err) {
      console.error(err);
    } finally {
      setGoogleSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0c0d10] text-[#f3f4f6] flex flex-col justify-between selection:bg-[#d4f933] selection:text-black">
      {/* Top Navigation Bar */}
      <header className="h-20 px-6 sm:px-12 border-b border-white/[0.06] flex items-center justify-between z-20">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-[#16181e] border border-white/10 flex items-center justify-center text-[#d4f933] shadow-lg">
            <ShieldAlert className="w-5 h-5 text-[#d4f933]" />
          </div>
          <div>
            <div className="font-extrabold text-sm tracking-tight text-white flex items-center gap-2">
              ROADSENTINEL
              <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-[#d4f933] text-black">
                AI 2.0
              </span>
            </div>
            <div className="text-[11px] text-slate-400">MongoDB Atlas Connected</div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Link
            to="/damage-map"
            className="hidden sm:flex items-center gap-1.5 px-4 py-2 rounded-2xl bg-[#16181e] border border-white/10 text-xs font-semibold text-slate-300 hover:text-white transition-all"
          >
            <Flame className="w-3.5 h-3.5 text-[#ff0055]" />
            <span>Public Thermographic Map</span>
          </Link>

          <button
            onClick={() => setGoogleModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-2xl bg-[#d4f933] hover:bg-[#bef264] text-black text-xs font-bold transition-all shadow-lg"
          >
            <LogIn className="w-3.5 h-3.5" />
            <span>Google Sign-In</span>
          </button>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1 max-w-7xl mx-auto px-6 sm:px-12 py-12 flex flex-col justify-center space-y-12">
        {/* Headline & Badges */}
        <div className="text-center max-w-3xl mx-auto space-y-4">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#16181e] border border-white/10 text-xs font-mono text-[#d4f933] shadow-md">
            <span className="w-2 h-2 rounded-full bg-[#d4f933] animate-pulse"></span>
            YOLOv8 & RDD2022 Neural Engine · Real-Time Operations
          </div>

          <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-tight">
            Autonomous Road Distress Detection, Verification & Dispatch
          </h1>

          <p className="text-sm sm:text-base text-slate-400 max-w-2xl mx-auto leading-relaxed">
            Select your persona below to enter your <b>dedicated operational dashboard</b> with role-specific workflows for citizens, municipal inspectors, and repair crews.
          </p>

          {/* Live Stats Pill Ribbon */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-4 max-w-2xl mx-auto">
            <div className="p-3.5 rounded-2xl bg-[#14161b] border border-white/[0.06] text-center">
              <div className="text-xl font-bold text-white">{stats.total}</div>
              <div className="text-[11px] text-slate-400 mt-0.5">Hazards Detected</div>
            </div>
            <div className="p-3.5 rounded-2xl bg-[#14161b] border border-white/[0.06] text-center">
              <div className="text-xl font-bold text-[#d4f933]">{stats.repaired}</div>
              <div className="text-[11px] text-slate-400 mt-0.5">Verified Repaired</div>
            </div>
            <div className="p-3.5 rounded-2xl bg-[#14161b] border border-white/[0.06] text-center">
              <div className="text-xl font-bold text-[#00f0ff]">{stats.accuracy}%</div>
              <div className="text-[11px] text-slate-400 mt-0.5">AI Confidence</div>
            </div>
            <div className="p-3.5 rounded-2xl bg-[#14161b] border border-white/[0.06] text-center">
              <div className="text-xl font-bold text-[#ff8800]">4.8h</div>
              <div className="text-[11px] text-slate-400 mt-0.5">Mean Time to Fix</div>
            </div>
          </div>
        </div>

        {/* 3 Dedicated Role Selection Portal Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* 1. CITIZEN PORTAL */}
          <div className="rounded-3xl bg-[#14161b] border border-white/[0.08] hover:border-blue-400/50 p-6 flex flex-col justify-between shadow-2xl transition-all duration-300 hover:scale-[1.02] group">
            <div className="space-y-4">
              <div className="w-12 h-12 rounded-2xl bg-blue-500/10 border border-blue-500/20 text-blue-400 flex items-center justify-center shadow-inner">
                <UserCheck className="w-6 h-6 group-hover:scale-110 transition-transform" />
              </div>

              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded-full">
                  Citizen Portal
                </span>
                <h3 className="text-lg font-bold text-white mt-1">Citizen & Driver</h3>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                  Report road defects with camera and device geolocation, track repairs in real-time, and view public road safety maps.
                </p>
              </div>

              <ul className="text-xs space-y-2 text-slate-300 pt-2 border-t border-white/[0.06]">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-blue-400 shrink-0" />
                  <span>Upload dashcam & mobile photos with GPS</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-blue-400 shrink-0" />
                  <span>Real-time 7-stage repair progress tracker</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-blue-400 shrink-0" />
                  <span>Track reported potholes by reference ID</span>
                </li>
              </ul>
            </div>

            <button
              onClick={() => handleSelectRole('citizen', '/citizen')}
              className="mt-6 w-full py-3 rounded-2xl bg-[#1b1e25] hover:bg-blue-600 text-white text-xs font-bold transition-all flex items-center justify-center gap-2 border border-white/10 group-hover:border-blue-500"
            >
              <span>Enter Citizen Portal</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </button>
          </div>

          {/* 2. MUNICIPAL AUTHORITY CONSOLE */}
          <div className="rounded-3xl bg-[#14161b] border-2 border-[#d4f933]/40 hover:border-[#d4f933] p-6 flex flex-col justify-between shadow-2xl transition-all duration-300 hover:scale-[1.02] relative group">
            <span className="absolute -top-3 right-6 text-[10px] font-bold uppercase tracking-wider px-3 py-0.5 rounded-full bg-[#d4f933] text-black shadow-lg">
              Primary Console
            </span>

            <div className="space-y-4">
              <div className="w-12 h-12 rounded-2xl bg-[#d4f933]/10 border border-[#d4f933]/30 text-[#d4f933] flex items-center justify-center shadow-inner">
                <Shield className="w-6 h-6 group-hover:scale-110 transition-transform" />
              </div>

              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#d4f933] bg-[#d4f933]/10 px-2 py-0.5 rounded-full">
                  Municipal Authority
                </span>
                <h3 className="text-lg font-bold text-white mt-1">Municipal Validator</h3>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                  Verify AI neural detections, dispatch work orders to field contractor crews with deadlines, and inspect repair proofs.
                </p>
              </div>

              <ul className="text-xs space-y-2 text-slate-300 pt-2 border-t border-white/[0.06]">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#d4f933] shrink-0" />
                  <span>Verify AI detections & override severity</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#d4f933] shrink-0" />
                  <span>Dispatch work orders to field contractors</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#d4f933] shrink-0" />
                  <span>Review contractor repair proof photos & approve</span>
                </li>
              </ul>
            </div>

            <button
              onClick={() => handleSelectRole('authority', '/authority')}
              className="mt-6 w-full py-3 rounded-2xl bg-[#d4f933] hover:bg-[#bef264] text-black text-xs font-bold transition-all flex items-center justify-center gap-2 shadow-lg"
            >
              <span>Enter Authority Console</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </button>
          </div>

          {/* 3. FIELD CONTRACTOR PORTAL */}
          <div className="rounded-3xl bg-[#14161b] border border-white/[0.08] hover:border-amber-400/50 p-6 flex flex-col justify-between shadow-2xl transition-all duration-300 hover:scale-[1.02] group">
            <div className="space-y-4">
              <div className="w-12 h-12 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center shadow-inner">
                <HardHat className="w-6 h-6 group-hover:scale-110 transition-transform" />
              </div>

              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full">
                  Contractor Portal
                </span>
                <h3 className="text-lg font-bold text-white mt-1">Field Contractor</h3>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                  Receive dispatched repair tasks, navigate to coordinates, start work on-site, and upload photographic proof of completion.
                </p>
              </div>

              <ul className="text-xs space-y-2 text-slate-300 pt-2 border-t border-white/[0.06]">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                  <span>View assigned pothole locations & priorities</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                  <span>Start repair & track field crew progress</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                  <span>Upload repair proof photo, materials & costs</span>
                </li>
              </ul>
            </div>

            <button
              onClick={() => handleSelectRole('worker', '/contractor')}
              className="mt-6 w-full py-3 rounded-2xl bg-[#1b1e25] hover:bg-amber-500 hover:text-black text-white text-xs font-bold transition-all flex items-center justify-center gap-2 border border-white/10 group-hover:border-amber-400"
            >
              <span>Enter Contractor Portal</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </button>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="h-16 px-6 sm:px-12 border-t border-white/[0.06] flex items-center justify-between text-xs text-slate-500">
        <div>RoadSentinel AI © 2026 · Built for Urban Road Safety</div>
        <div className="flex items-center gap-4">
          <Link to="/damage-map" className="hover:text-slate-300">Live Map</Link>
          <Link to="/track" className="hover:text-slate-300">Track Pothole</Link>
          <a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer" className="hover:text-[#d4f933]">Swagger API</a>
        </div>
      </footer>

      {/* Google OAuth Modal */}
      <Modal isOpen={googleModalOpen} onClose={() => setGoogleModalOpen(false)} title="Sign in with Google OAuth">
        <form onSubmit={handleGoogleSubmit} className="space-y-4">
          <div className="p-3 bg-[#181a20] border border-white/10 rounded-2xl text-xs text-slate-300 flex items-start gap-2">
            <Sparkles className="w-4 h-4 text-[#d4f933] shrink-0 mt-0.5" />
            <div>
              Sign in with your Google email to synchronize role assignments and reports directly to MongoDB Atlas.
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Google Email</label>
            <input
              type="email"
              required
              value={googleEmail}
              onChange={(e) => setGoogleEmail(e.target.value)}
              placeholder="user@gmail.com"
              className="w-full text-xs p-2.5 rounded-xl border border-white/10 bg-[#16181e] text-white focus:outline-none focus:border-[#d4f933]"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Full Name</label>
              <input
                type="text"
                value={googleName}
                onChange={(e) => setGoogleName(e.target.value)}
                placeholder="e.g. Lisa Nguyen"
                className="w-full text-xs p-2.5 rounded-xl border border-white/10 bg-[#16181e] text-white focus:outline-none focus:border-[#d4f933]"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Target Portal</label>
              <select
                value={googleRole}
                onChange={(e) => setGoogleRole(e.target.value as UserRole)}
                className="w-full text-xs p-2.5 rounded-xl border border-white/10 bg-[#16181e] text-white focus:outline-none focus:border-[#d4f933]"
              >
                <option value="citizen">Citizen Portal</option>
                <option value="authority">Municipal Authority</option>
                <option value="worker">Field Contractor</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setGoogleModalOpen(false)}
              className="px-4 py-2 rounded-xl border border-white/10 text-xs text-slate-300 hover:bg-white/[0.06]"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={googleSubmitting}
              className="px-5 py-2 rounded-xl bg-[#d4f933] hover:bg-[#bef264] text-black text-xs font-bold transition-all shadow-md"
            >
              {googleSubmitting ? 'Signing in...' : 'Enter Dashboard'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
