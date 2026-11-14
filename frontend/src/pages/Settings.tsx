import React, { useState } from 'react';
import { Settings as SettingsIcon, Moon, Sun, Server, Database, Save, CheckCircle } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

export const Settings: React.FC = () => {
  const { theme, toggleTheme } = useTheme();
  const [apiUrl, setApiUrl] = useState(import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000');
  const [saved, setSaved] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    localStorage.setItem('roadsentinel_api_url', apiUrl);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="max-w-2xl space-y-6">
      <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-4">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Display & Appearance
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium text-slate-900 dark:text-white">Application Theme</div>
            <div className="text-xs text-slate-500">Toggle between Light and Dark interface modes</div>
          </div>
          <button
            onClick={toggleTheme}
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
          >
            {theme === 'dark' ? (
              <>
                <Sun className="w-4 h-4 text-amber-400" /> Light Mode
              </>
            ) : (
              <>
                <Moon className="w-4 h-4 text-slate-600" /> Dark Mode
              </>
            )}
          </button>
        </div>
      </div>

      <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-4">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Backend Service Connection
        </div>

        <form onSubmit={handleSave} className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              FastAPI Base URL
            </label>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
                placeholder="http://127.0.0.1:8000"
                className="flex-1 px-3 py-2 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-emerald-500"
              />
              <button
                type="submit"
                className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-medium flex items-center gap-1.5 transition-colors shadow-sm"
              >
                <Save className="w-3.5 h-3.5" /> Save
              </button>
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              Default for local development is <code>http://127.0.0.1:8000</code>.
            </div>
          </div>
        </form>

        {saved && (
          <div className="p-2.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 text-xs flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-600" />
            <span>Settings saved successfully.</span>
          </div>
        )}
      </div>

      <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-3">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Storage Architecture
        </div>
        <div className="text-xs text-slate-600 dark:text-slate-400 space-y-1">
          <div>• Storage Engine: <b>Atomic Local JSON Store</b> (Zero database/MongoDB dependencies)</div>
          <div>• Storage File: <code>data/inspections.json</code></div>
          <div>• Cropped Defect Assets: <code>data/pothole_crops/</code></div>
          <div>• Processed Video Outputs: <code>outputs/</code></div>
        </div>
      </div>
    </div>
  );
};
