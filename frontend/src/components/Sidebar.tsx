import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutGrid,
  Map,
  Camera,
  Video,
  CheckSquare,
  HardHat,
  Activity,
  BarChart3,
  FileText,
  Settings,
  HelpCircle,
  Plus
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface NavItem {
  path: string;
  label: string;
  icon: any;
  badge?: string;
  roleHighlight?: string;
}

const navItems: NavItem[] = [
  { path: '/', label: 'Operations Dashboard', icon: LayoutGrid },
  { path: '/damage-map', label: 'Damage Map & Heatmap', icon: Map, badge: 'Live' },
  { path: '/image-detection', label: 'Image Studio', icon: Camera },
  { path: '/video-detection', label: 'Video Engine', icon: Video },
  { path: '/verification', label: 'Verification & Dispatch', icon: CheckSquare },
  { path: '/worker', label: 'Contractor Portal', icon: HardHat, roleHighlight: 'worker' },
  { path: '/track', label: 'Progress Tracker', icon: Activity },
  { path: '/analytics', label: 'Analytics & Trends', icon: BarChart3 },
  { path: '/reports', label: 'Reports', icon: FileText },
];

export const Sidebar: React.FC = () => {
  const { role } = useAuth();
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);

  return (
    <aside className="w-16 sm:w-20 shrink-0 bg-[#0c0d10] border-r border-white/[0.06] flex flex-col items-center justify-between py-5 select-none z-30">
      {/* Top: Brand Logo */}
      <div className="flex flex-col items-center gap-6">
        <NavLink
          to="/"
          className="w-11 h-11 rounded-2xl bg-[#16181e] border border-white/10 flex items-center justify-center text-[#d4f933] shadow-md hover:scale-105 transition-all group"
          title="RoadSentinel AI"
        >
          {/* Custom cyber plus/star emblem like in Haulix */}
          <div className="relative flex items-center justify-center">
            <Plus className="w-6 h-6 stroke-[3] text-[#d4f933] group-hover:rotate-90 transition-transform duration-300" />
            <span className="absolute w-2 h-2 rounded-full bg-[#d4f933] blur-[6px] opacity-75"></span>
          </div>
        </NavLink>

        {/* Center: Navigation Dock */}
        <nav className="flex flex-col items-center gap-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isRoleActive = item.roleHighlight === role;

            return (
              <div
                key={item.path}
                className="relative flex items-center justify-center"
                onMouseEnter={() => setHoveredItem(item.path)}
                onMouseLeave={() => setHoveredItem(null)}
              >
                <NavLink
                  to={item.path}
                  end={item.path === '/'}
                  className={({ isActive }) =>
                    `w-11 h-11 rounded-2xl flex items-center justify-center transition-all duration-200 relative ${
                      isActive
                        ? 'bg-white text-black shadow-lg shadow-white/10 scale-100 font-bold'
                        : isRoleActive
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

                {/* Floating Tooltip Pill */}
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

      {/* Bottom Dock: Help & Settings */}
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
