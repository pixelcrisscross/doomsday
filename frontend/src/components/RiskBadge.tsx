import React from 'react';
import { RiskLevel } from '../types';

interface Props {
  risk: RiskLevel | string;
  size?: 'sm' | 'md';
}

export const RiskBadge: React.FC<Props> = ({ risk, size = 'sm' }) => {
  const r = (risk || 'None').toLowerCase();
  const padding = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm';

  switch (r) {
    case 'critical':
      return (
        <span className={`inline-flex items-center gap-1 font-semibold rounded-full bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-400 border border-red-200 dark:border-red-800/60 ${padding}`}>
          🔴 Critical
        </span>
      );
    case 'high':
      return (
        <span className={`inline-flex items-center gap-1 font-semibold rounded-full bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-400 border border-orange-200 dark:border-orange-800/60 ${padding}`}>
          🟠 High
        </span>
      );
    case 'medium':
      return (
        <span className={`inline-flex items-center gap-1 font-semibold rounded-full bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300 border border-amber-200 dark:border-amber-800/60 ${padding}`}>
          🟡 Medium
        </span>
      );
    case 'low':
      return (
        <span className={`inline-flex items-center gap-1 font-semibold rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/60 ${padding}`}>
          🟢 Low
        </span>
      );
    case 'none':
      return (
        <span className={`inline-flex items-center gap-1 font-medium rounded-full bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border border-slate-200 dark:border-slate-700 ${padding}`}>
          🟢 None (Safe)
        </span>
      );
    default:
      return (
        <span className={`inline-flex items-center gap-1 font-medium rounded-full bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400 border border-slate-200 dark:border-slate-700 ${padding}`}>
          ⚪ {risk}
        </span>
      );
  }
};
