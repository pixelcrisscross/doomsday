import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  Home,
  UserCheck,
  Shield,
  HardHat,
  Map,
  Camera,
  Video,
  CheckSquare,
  Activity,
  BarChart3,
  FileText,
  Settings,
  Plus
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const Sidebar: React.FC = () => {
  const { role } = useAuth();
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);

  const getDashboardPath = () => {
    if (role === 'citizen') return '/citizen';
    if (role === 'worker') return '/contractor';
    return '/authority';
  };

  const getDashboardIcon = () => {
    if (role === 'citizen') return UserCheck;
    if (role === 'worker') return HardHat;
    return Shield;
  };

  const DashboardIcon = getDashboardIcon();

  const navItems = [
    { path: '/', label: 'Landing Page & Role Selection', icon: Home },
    { path: getDashboardPath(), label: `My Dashboard (${role.toUpperCase()})`, icon: DashboardIcon, activeHighlight: true },
    { path: '/damage-map', label: 'Damage Map & Thermography', icon: Map, badge: 'Live' },
    { path: '/track', label: 'Pothole Progress Tracker', icon: Activity },
    { path: '/image-detection', label: 'Image Detection Studio', icon: Camera },
    { path: '/video-detection', label: 'Video Detection Engine', icon: Video },
    { path: '/verification', label: 'Verification & Dispatch', icon: CheckSquare },
    { path: '/analytics', label: 'Analytics & Trends', icon: BarChart3 },
    { path: '/reports', label: 'Inspection Reports', icon: FileText },
  ];

  return (
    <aside className="w-16 sm:w-20 shrink-0 bg-[#0c0d10] border-r border-white/[0.06] flex flex-col items-center justify-between py-5 select-none z-30">
      {/* Top: Brand Logo */}
      <div className="flex flex-col items-center gap-6">
        <NavLink
          to="/"
          className="w-11 h-11 rounded-2xl bg-[#16181e] border border-white/10 flex items-center justify-center text-[#d4f933] shadow-md hover:scale-105 transition-all group"
          title="Return to Landing Page"
        >
          <div className="relative flex items-center justify-center">
            <Plus className="w-6 h-6 stroke-[3] text-[#d4f933] group-hover:rotate-90 transition-transform duration-300" />
            <span className="absolute w-2 h-2 rounded-full bg-[#d4f933] blur-[6px] opacity-75"></span>
          </div>
        </NavLink>

        {/* Center: Navigation Dock */}
        <nav className="flex flex-col items-center gap-2">
          {navItems.map((item) => {
            const Icon = item.icon;

            return (
              <div
                key={item.path}
                className="relative flex items-center justify-center"
                onMouseEnter={() => setHoveredItem(item.path)}
                onMouseLeave={() => setHoveredItem(null)}
              >
                <NavLink
                  to={item.path}
                  end={item.path === '/' || item.path === '/citizen' || item.path === '/authority' || item.path === '/contractor'}
                  className={({ isActive }) =>
                    `w-11 h-11 rounded-2xl flex items-center justify-center transition-all duration-200 relative ${
                      isActive
                        ? 'bg-white text-black shadow-lg shadow-white/10 font-bold scale-100'
                        : item.activeHighlight
                        ? 'bg-[#1e2129] text-[#d4f933] border border-[#d4f933]/30'
                        : 'text-slate-400 hover:text-white hover:bg-white/[0.06]'
                    }`
                  }
                >
                  {({ isActive }) => (
                    <>
                      <Icon className={`w-5 h-5 ${isActive ? 'stroke-[2.5]' : 'stroke-[1.8]'}`} />
                      {item.badge && !isActive && (
                        <span className="absolute top-2 right-2 w-1.5 h-1.5 rounded-full bg-[#d4f933] shadow-[0_0_6px_#d4f933]"></span>
                      )}
                    </>
                  )}
                </NavLink>

                {/* Floating Tooltip */}
                {hoveredItem === item.path && (
                  <div className="absolute left-16 z-50 px-3 py-1.5 rounded-xl bg-[#181a20] border border-white/10 text-white text-xs font-medium whitespace-nowrap shadow-2xl backdrop-blur-md pointer-events-none flex items-center gap-2 animate-in fade-in slide-in-from-left-1 duration-150">
                    <span>{item.label}</span>
                    {item.badge && (
                      <span className="text-[10px] uppercase font-bold px-1.5 py-0.2 rounded bg-[#d4f933]/20 text-[#d4f933]">
                        {item.badge}
                      </span>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </nav>
      </div>

      {/* Bottom Dock: Settings */}
      <div className="flex flex-col items-center gap-2 pt-4 border-t border-white/[0.06] w-full">
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            `w-11 h-11 rounded-2xl flex items-center justify-center transition-all ${
              isActive
                ? 'bg-white text-black shadow-lg font-bold'
                : 'text-slate-400 hover:text-white hover:bg-white/[0.06]'
            }`
          }
          title="System Settings"
        >
          <Settings className="w-5 h-5 stroke-[1.8]" />
        </NavLink>
      </div>
    </aside>
  );
};
