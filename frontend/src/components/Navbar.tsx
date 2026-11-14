import React, { useEffect, useState } from 'react';
import { useLocation, Link } from 'react-router-dom';
import {
  Search,
  Bell,
  ChevronDown,
  Layers,
  Users,
  AlertTriangle,
  Activity,
  CheckCircle2,
  Calendar,
  Sparkles,
  LogIn,
  Sun,
  Moon,
  Shield,
  HardHat,
  UserCheck
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { api } from '../services/api';
import { UserRole, CityPotholeSummary } from '../types';
import { Modal } from './Modal';

export const Navbar: React.FC = () => {
  const { user, role, loginAs, googleLogin } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();

  const [stats, setStats] = useState<CityPotholeSummary | null>(null);
  const [roleDropdownOpen, setRoleDropdownOpen] = useState(false);
  const [googleModalOpen, setGoogleModalOpen] = useState(false);
  const [showRoutes, setShowRoutes] = useState(true);
  const [showAlerts, setShowAlerts] = useState(true);

  // Custom Google Login form state
  const [googleEmail, setGoogleEmail] = useState('');
  const [googleName, setGoogleName] = useState('');
  const [googleRole, setGoogleRole] = useState<UserRole>('authority');
  const [googleSubmitting, setGoogleSubmitting] = useState(false);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await api.getCityStats('Bengaluru Urban');
        setStats(res);
      } catch (err) {
        // Fallback default stats
        setStats({
          city: 'Bengaluru Urban',
          total_potholes: 18,
          active_hazards: 12,
          under_repair: 4,
          repaired_count: 6,
          critical_potholes: 5,
          last_updated: 'Just now'
        });
      }
    };
    fetchStats();
  }, []);

  const handleRoleSelect = async (selectedRole: UserRole) => {
    setRoleDropdownOpen(false);
    await loginAs(selectedRole);
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
      setGoogleEmail('');
      setGoogleName('');
    } catch (err) {
      console.error('Google Auth Failed', err);
    } finally {
      setGoogleSubmitting(false);
    }
  };

  const roleConfig: Record<UserRole, { title: string; color: string; icon: any }> = {
    citizen: { title: 'Citizen Reporter', color: 'text-blue-400', icon: UserCheck },
    authority: { title: 'Municipal Validator', color: 'text-[#d4f933]', icon: Shield },
    worker: { title: 'Field Contractor', color: 'text-amber-400', icon: HardHat }
  };

  const activeRole = roleConfig[role] || roleConfig.authority;
  const RoleIcon = activeRole.icon;

  return (
    <header className="h-16 px-6 bg-[#0c0d10] border-b border-white/[0.06] flex items-center justify-between shrink-0 gap-4 z-20 select-none">
      {/* Left: Top Telemetry Metrics Pills (Mirroring HAULIX top pills) */}
      <div className="hidden xl:flex items-center gap-2">
        <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#16181e] border border-white/[0.06] text-xs text-slate-300">
          <Layers className="w-3.5 h-3.5 text-slate-400" />
          <span>Active:</span>
          <span className="font-semibold text-white">{stats?.active_hazards ?? 12}/18</span>
        </div>

        <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#16181e] border border-white/[0.06] text-xs text-slate-300">
          <Users className="w-3.5 h-3.5 text-slate-400" />
          <span>Crews:</span>
          <span className="font-semibold text-white">6/8</span>
        </div>

        <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#16181e] border border-white/[0.06] text-xs text-slate-300">
          <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
          <span>Critical:</span>
          <span className="font-semibold text-rose-400">{stats?.critical_potholes ?? 5}</span>
        </div>

        <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#16181e] border border-white/[0.06] text-xs text-slate-300">
          <CheckCircle2 className="w-3.5 h-3.5 text-[#d4f933]" />
          <span>Resolution:</span>
          <span className="font-semibold text-[#d4f933]">94.2%</span>
        </div>
      </div>

      {/* Center: Search Bar with Hotkey */}
      <div className="flex-1 max-w-md relative">
        <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          placeholder="Search hazards, coordinates, work orders..."
          className="w-full pl-9 pr-12 py-1.5 text-xs rounded-full bg-[#16181e] border border-white/[0.08] text-white placeholder-slate-500 focus:outline-none focus:border-[#d4f933]/50 focus:ring-1 focus:ring-[#d4f933]/50 transition-all"
        />
        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/[0.06] text-slate-400 border border-white/[0.04]">
          ⌘K
        </span>
      </div>

      {/* Right Controls: Toggles, Notifications, User Persona */}
      <div className="flex items-center gap-3">
        {/* Route / Alerts Toggles (Like in Image 1-4) */}
        <div className="hidden lg:flex items-center gap-4 text-xs font-medium text-slate-300 px-2">
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <span className="text-[11px] text-slate-400">Show routes</span>
            <button
              type="button"
              onClick={() => setShowRoutes(!showRoutes)}
              className={`w-9 h-5 rounded-full p-0.5 transition-colors duration-200 ease-in-out ${
                showRoutes ? 'bg-[#d4f933]' : 'bg-slate-700'
              }`}
            >
              <div
                className={`w-4 h-4 rounded-full bg-black shadow-md transform transition-transform duration-200 ease-in-out ${
                  showRoutes ? 'translate-x-4' : 'translate-x-0'
                }`}
              />
            </button>
          </label>

          <label className="flex items-center gap-2 cursor-pointer select-none">
            <span className="text-[11px] text-slate-400">Show alerts</span>
            <button
              type="button"
              onClick={() => setShowAlerts(!showAlerts)}
              className={`w-9 h-5 rounded-full p-0.5 transition-colors duration-200 ease-in-out ${
                showAlerts ? 'bg-[#d4f933]' : 'bg-slate-700'
              }`}
            >
              <div
                className={`w-4 h-4 rounded-full bg-black shadow-md transform transition-transform duration-200 ease-in-out ${
                  showAlerts ? 'translate-x-4' : 'translate-x-0'
                }`}
              />
            </button>
          </label>
        </div>

        {/* Date Filter Pill */}
        <button className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#16181e] border border-white/[0.08] text-xs text-slate-300 hover:border-white/20 transition-colors">
          <Calendar className="w-3.5 h-3.5 text-slate-400" />
          <span>Last 7 days</span>
          <ChevronDown className="w-3 h-3 text-slate-400" />
        </button>

        {/* Notification Bell with Badge */}
        <button
          className="relative w-9 h-9 rounded-full bg-[#16181e] border border-white/[0.08] flex items-center justify-center text-slate-300 hover:text-white transition-colors"
          title="Notifications"
        >
          <Bell className="w-4 h-4" />
          <span className="absolute -top-1 -right-1 px-1.5 py-0.2 rounded-full bg-[#ff5500] text-[9px] font-bold text-white shadow-md">
            +8
          </span>
        </button>

        {/* User Profile & Persona Switcher */}
        <div className="relative">
          <button
            onClick={() => setRoleDropdownOpen(!roleDropdownOpen)}
            className="flex items-center gap-2.5 p-1 pr-3 rounded-full bg-[#16181e] border border-white/[0.08] hover:border-white/20 transition-all text-left"
          >
            <div className="w-7 h-7 rounded-full bg-[#20242e] border border-white/10 flex items-center justify-center text-xs font-bold text-[#d4f933] overflow-hidden">
              {user?.avatar_url ? (
                <img src={user.avatar_url} alt="Avatar" className="w-full h-full object-cover" />
              ) : (
                user?.name?.substring(0, 2).toUpperCase() || 'RS'
              )}
            </div>
            <div className="hidden md:block">
              <div className="text-xs font-semibold text-white leading-none">
                {user?.name || 'Lisa Nguyen'}
              </div>
              <div className="text-[10px] text-slate-400 leading-tight mt-0.5">
                {activeRole.title}
              </div>
            </div>
            <ChevronDown className="w-3 h-3 text-slate-400 ml-0.5" />
          </button>

          {/* Persona Switcher Dropdown */}
          {roleDropdownOpen && (
            <div className="absolute right-0 mt-2 w-64 bg-[#181a20] border border-white/10 rounded-2xl shadow-2xl z-50 p-2 space-y-1 backdrop-blur-xl animate-in fade-in zoom-in-95 duration-150">
              <div className="px-3 py-1.5 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                Select Persona (RBAC)
              </div>
              <button
                onClick={() => handleRoleSelect('authority')}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-left text-xs transition-colors ${
                  role === 'authority'
                    ? 'bg-[#22252e] text-[#d4f933] font-semibold border border-[#d4f933]/30'
                    : 'text-slate-300 hover:bg-white/[0.06]'
                }`}
              >
                <Shield className="w-4 h-4 text-[#d4f933] shrink-0" />
                <div>
                  <div className="font-medium">Municipal Authority</div>
                  <div className="text-[10px] text-slate-400">Validate AI & dispatch repair work</div>
                </div>
              </button>

              <button
                onClick={() => handleRoleSelect('worker')}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-left text-xs transition-colors ${
                  role === 'worker'
                    ? 'bg-[#22252e] text-amber-400 font-semibold border border-amber-400/30'
                    : 'text-slate-300 hover:bg-white/[0.06]'
                }`}
              >
                <HardHat className="w-4 h-4 text-amber-400 shrink-0" />
                <div>
                  <div className="font-medium">Field Contractor</div>
                  <div className="text-[10px] text-slate-400">View tasks & submit repair proof</div>
                </div>
              </button>

              <button
                onClick={() => handleRoleSelect('citizen')}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-left text-xs transition-colors ${
                  role === 'citizen'
                    ? 'bg-[#22252e] text-blue-400 font-semibold border border-blue-400/30'
                    : 'text-slate-300 hover:bg-white/[0.06]'
                }`}
              >
                <UserCheck className="w-4 h-4 text-blue-400 shrink-0" />
                <div>
                  <div className="font-medium">Citizen Reporter</div>
                  <div className="text-[10px] text-slate-400">Report distress & track progress</div>
                </div>
              </button>

              <div className="pt-2 border-t border-white/[0.06]">
                <button
                  onClick={() => {
                    setRoleDropdownOpen(false);
                    setGoogleModalOpen(true);
                  }}
                  className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/[0.06] hover:bg-white/[0.1] text-xs text-white font-medium transition-colors"
                >
                  <LogIn className="w-3.5 h-3.5 text-[#d4f933]" />
                  <span>Google OAuth Sign-In</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Google OAuth Modal */}
      <Modal isOpen={googleModalOpen} onClose={() => setGoogleModalOpen(false)} title="Google OAuth 2.0 Sign-In">
        <div className="space-y-4">
          <div className="p-3 bg-[#1e222a] border border-white/10 rounded-xl text-xs text-slate-300 flex items-start gap-2">
            <Sparkles className="w-4 h-4 shrink-0 text-[#d4f933] mt-0.5" />
            <div>
              <b>MongoDB Atlas Cloud Integration</b>: Sign in with Google to synchronize role permissions, repair dispatch logs, and field reports directly to your Atlas cluster.
            </div>
          </div>

          <div>
            <div className="text-xs font-semibold text-slate-300 mb-2">
              One-Click Quick Persona Sign-In:
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => {
                  googleLogin({
                    email: 'inspector.kavya@bbmp.gov.in',
                    name: 'Kavya Patel',
                    role: 'authority',
                    avatar_url: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Kavya'
                  });
                  setGoogleModalOpen(false);
                }}
                className="p-2.5 bg-[#16181e] border border-white/10 rounded-xl text-left hover:border-[#d4f933] hover:bg-[#1a1d24] transition-all text-xs"
              >
                <div className="font-semibold text-[#d4f933]">Kavya (Authority)</div>
                <div className="text-[10px] text-slate-400 truncate">inspector.kavya@bbmp.gov.in</div>
              </button>

              <button
                type="button"
                onClick={() => {
                  googleLogin({
                    email: 'contractor.ramesh@gmail.com',
                    name: 'Ramesh Kumar',
                    role: 'worker',
                    avatar_url: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Ramesh'
                  });
                  setGoogleModalOpen(false);
                }}
                className="p-2.5 bg-[#16181e] border border-white/10 rounded-xl text-left hover:border-amber-400 hover:bg-[#1a1d24] transition-all text-xs"
              >
                <div className="font-semibold text-amber-400">Ramesh (Worker)</div>
                <div className="text-[10px] text-slate-400 truncate">contractor.ramesh@gmail.com</div>
              </button>

              <button
                type="button"
                onClick={() => {
                  googleLogin({
                    email: 'citizen.aarav@gmail.com',
                    name: 'Aarav Sharma',
                    role: 'citizen',
                    avatar_url: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Aarav'
                  });
                  setGoogleModalOpen(false);
                }}
                className="p-2.5 bg-[#16181e] border border-white/10 rounded-xl text-left hover:border-blue-400 hover:bg-[#1a1d24] transition-all text-xs"
              >
                <div className="font-semibold text-blue-400">Aarav (Citizen)</div>
                <div className="text-[10px] text-slate-400 truncate">citizen.aarav@gmail.com</div>
              </button>
            </div>
          </div>

          <form onSubmit={handleGoogleSubmit} className="space-y-3 pt-2">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Google Email Address
              </label>
              <input
                type="email"
                required
                value={googleEmail}
                onChange={(e) => setGoogleEmail(e.target.value)}
                placeholder="name@gmail.com"
                className="w-full text-xs p-2.5 rounded-xl border border-white/10 bg-[#16181e] text-white focus:outline-none focus:border-[#d4f933]"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Full Name
                </label>
                <input
                  type="text"
                  value={googleName}
                  onChange={(e) => setGoogleName(e.target.value)}
                  placeholder="e.g. Lisa Nguyen"
                  className="w-full text-xs p-2.5 rounded-xl border border-white/10 bg-[#16181e] text-white focus:outline-none focus:border-[#d4f933]"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Designated Role
                </label>
                <select
                  value={googleRole}
                  onChange={(e) => setGoogleRole(e.target.value as UserRole)}
                  className="w-full text-xs p-2.5 rounded-xl border border-white/10 bg-[#16181e] text-white focus:outline-none focus:border-[#d4f933]"
                >
                  <option value="authority">Municipal Authority</option>
                  <option value="worker">Field Contractor</option>
                  <option value="citizen">Citizen Reporter</option>
                </select>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-3">
              <button
                type="button"
                onClick={() => setGoogleModalOpen(false)}
                className="px-3.5 py-1.5 rounded-xl border border-white/10 text-xs text-slate-300 hover:bg-white/[0.06]"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={googleSubmitting || !googleEmail}
                className="px-4 py-1.5 rounded-xl bg-[#d4f933] hover:bg-[#bef264] text-black font-semibold text-xs transition-colors"
              >
                {googleSubmitting ? 'Authenticating...' : 'Sign In with Google'}
              </button>
            </div>
          </form>
        </div>
      </Modal>
    </header>
  );
};
