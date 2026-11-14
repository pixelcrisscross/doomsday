import React, { useState } from 'react';
import { MapPin, CheckCircle, AlertCircle, X, RefreshCw } from 'lucide-react';
import { api } from '../services/api';

interface Props {
  onLocationChange: (loc: { latitude: number | null; longitude: number | null; address: string; source: string }) => void;
}

export const LocationPicker: React.FC<Props> = ({ onLocationChange }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [captured, setCaptured] = useState<{ latitude: number; longitude: number; address: string } | null>(null);

  const handleCaptureLocation = () => {
    if (!navigator.geolocation) {
      setError('Geolocation is not supported by your browser.');
      return;
    }

    setLoading(true);
    setError(null);

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        try {
          const res = await api.reverseGeocode(lat, lon);
          const addr = res.address || `GPS: ${lat.toFixed(6)}, ${lon.toFixed(6)}`;
          setCaptured({ latitude: lat, longitude: lon, address: addr });
          onLocationChange({ latitude: lat, longitude: lon, address: addr, source: 'DEVICE_GEOLOCATION' });
        } catch {
          const fallback = `GPS: ${lat.toFixed(6)}, ${lon.toFixed(6)}`;
          setCaptured({ latitude: lat, longitude: lon, address: fallback });
          onLocationChange({ latitude: lat, longitude: lon, address: fallback, source: 'DEVICE_GEOLOCATION' });
        } finally {
          setLoading(false);
        }
      },
      (err) => {
        setLoading(false);
        if (err.code === err.PERMISSION_DENIED) {
          setError('Location access denied by user. Please grant permission in your browser.');
        } else if (err.code === err.TIMEOUT) {
          setError('Location request timed out. Please retry.');
        } else {
          setError('Unable to retrieve device coordinates.');
        }
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  };

  const handleRemove = () => {
    setCaptured(null);
    setError(null);
    onLocationChange({ latitude: null, longitude: null, address: 'Location unavailable', source: 'UNAVAILABLE' });
  };

  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 p-3.5 my-2">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
          <MapPin className="w-3.5 h-3.5 text-brand-600 dark:text-brand-500" />
          Location Attachment (Optional)
        </span>
        {captured && (
          <button
            onClick={handleRemove}
            className="text-xs text-rose-600 dark:text-rose-400 hover:underline flex items-center gap-1"
          >
            <X className="w-3 h-3" /> Remove
          </button>
        )}
      </div>

      {!captured ? (
        <div>
          <button
            type="button"
            onClick={handleCaptureLocation}
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 text-xs font-medium rounded-md bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 transition-colors disabled:opacity-50"
          >
            {loading ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-brand-600" />
                Querying Device Geolocation...
              </>
            ) : (
              <>
                <MapPin className="w-3.5 h-3.5 text-brand-600 dark:text-brand-500" />
                Use My Current Location
              </>
            )}
          </button>
          {error && (
            <div className="mt-2 text-xs text-rose-600 dark:text-rose-400 flex items-start gap-1.5 bg-rose-50 dark:bg-rose-950/30 p-2 rounded border border-rose-200 dark:border-rose-900/40">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}
        </div>
      ) : (
        <div className="bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-900/40 rounded-md p-2.5 text-xs">
          <div className="flex items-center gap-1.5 text-emerald-800 dark:text-emerald-300 font-medium">
            <CheckCircle className="w-4 h-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
            <span>Location Captured</span>
          </div>
          <div className="mt-1.5 text-slate-700 dark:text-slate-300 font-mono text-[11px]">
            <div>Lat: <b>{captured.latitude.toFixed(6)}</b>, Lon: <b>{captured.longitude.toFixed(6)}</b></div>
            <div className="text-slate-500 dark:text-slate-400 font-sans mt-0.5 truncate">{captured.address}</div>
          </div>
        </div>
      )}
    </div>
  );
};
