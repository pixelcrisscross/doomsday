import React from 'react';
import { SeverityLevel } from '../types';

interface Props {
  severity: SeverityLevel | string;
  size?: 'sm' | 'md';
}

export const SeverityBadge: React.FC<Props> = ({ severity, size = 'sm' }) => {
  const sev = (severity || 'NONE').toUpperCase();
  const padding = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm';

  switch (sev) {
    case 'CRITICAL':
      return (
        <span className={`inline-flex items-center gap-1 font-semibold rounded-full bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-400 border border-red-200 dark:border-red-800/60 ${padding}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-red-600"></span>
          CRITICAL
        </span>
      );
    case 'SEVERE':
      return (
        <span className={`inline-flex items-center gap-1 font-semibold rounded-full bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-400 border border-orange-200 dark:border-orange-800/60 ${padding}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-orange-500"></span>
          SEVERE
        </span>
      );
    case 'MODERATE':
      return (
        <span className={`inline-flex items-center gap-1 font-semibold rounded-full bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300 border border-amber-200 dark:border-amber-800/60 ${padding}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
          MODERATE
        </span>
      );
    case 'MINOR':
      return (
        <span className={`inline-flex items-center gap-1 font-semibold rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/60 ${padding}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
          MINOR
        </span>
      );
    case 'NONE':
      return (
        <span className={`inline-flex items-center gap-1 font-semibold rounded-full bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border border-slate-200 dark:border-slate-700 ${padding}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
          NONE (Intact)
        </span>
      );
    default:
      return (
        <span className={`inline-flex items-center gap-1 font-medium rounded-full bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400 border border-slate-200 dark:border-slate-700 ${padding}`}>
          {sev}
        </span>
      );
  }
};
