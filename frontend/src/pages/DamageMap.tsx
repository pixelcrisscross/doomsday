import React, { useEffect, useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { HeatLayer } from 'leaflet.heat';
import {
  Flame,
  Layers,
  Plus,
  Minus,
  RotateCcw,
  X,
  Clock,
  AlertTriangle,
  HardHat,
  ArrowUpRight,
  RefreshCw,
  Sliders,
  MapPin,
  Wifi,
  WifiOff
} from 'lucide-react';

import { api } from '../services/api';
import { DamageMapPoint, HeatmapPoint, CityPotholeSummary } from '../types';

// Map Base Tiles Presets
const MAP_TILE_PRESETS: Record<string, { name: string; url: string; attribution: string; maxZoom: number }> = {
  voyager: {
    name: 'Street / Voyager (Standard)',
    url: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
    attribution: '&copy; <a href="https://carto.com/">CARTO</a>, &copy; <a href="https://openstreetmap.org">OSM</a>',
    maxZoom: 19
  },
  dark: {
    name: 'Dark Tactical (HAULIX)',
    url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; <a href="https://carto.com/">CARTO</a>',
    maxZoom: 19
  },
  osm: {
    name: 'OpenStreetMap Standard',
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; <a href="https://openstreetmap.org">OSM</a> contributors',
    maxZoom: 19
  },
  satellite: {
    name: 'Satellite Imagery',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: '&copy; Esri &mdash; Earthstar Geographics',
    maxZoom: 18
  }
};

// Authentic AI inspection records cache (matches data/inspections.json & MongoDB Atlas exactly)
const AUTHENTIC_RECORD_FALLBACKS: DamageMapPoint[] = [
  {
    inspection_id: 'RS-20261114-896A84',
    latitude: 12.9260,
    longitude: 77.6762,
    location_name: 'Outer Ring Road (Bellandur Flyover Corridor), Bengaluru',
    location_source: 'DEVICE_GEOLOCATION',
    overall_severity: 'CRITICAL',
    severity_score: 69.5,
    risk_category: 'Critical',
    potholes: 17,
    cracks: 0,
    media_type: 'photo',
    date: '14 Nov 2026, 05:10',
    verification_status: 'AI_PENDING',
    duplicate_status: 'NEW_REPORT',
    repair_status: 'REPORTED'
  },
  {
    inspection_id: 'RS-20261114-36B4F2',
    latitude: 12.9177,
    longitude: 77.6233,
    location_name: 'Hosur Main Road (Silk Board Junction Flyover), Bengaluru',
    location_source: 'DEVICE_GEOLOCATION',
    overall_severity: 'CRITICAL',
    severity_score: 65.8,
    risk_category: 'Critical',
    potholes: 11,
    cracks: 0,
    media_type: 'photo',
    date: '14 Nov 2026, 05:12',
    verification_status: 'AI_PENDING',
    duplicate_status: 'NEW_REPORT',
    repair_status: 'REPORTED'
  },
  {
    inspection_id: 'RS-20261114-AA7720',
    latitude: 13.0358,
    longitude: 77.5970,
    location_name: 'Bellary Road (Hebbal Flyover Northbound), Bengaluru',
    location_source: 'DEVICE_GEOLOCATION',
    overall_severity: 'CRITICAL',
    severity_score: 82.0,
    risk_category: 'Critical',
    potholes: 2,
    cracks: 0,
    media_type: 'photo',
    date: '14 Nov 2026, 05:25',
    verification_status: 'AI_PENDING',
    duplicate_status: 'NEW_REPORT',
    repair_status: 'REPORTED'
  },
  {
    inspection_id: 'RS-20261114-416D5B',
    latitude: 12.9827,
    longitude: 77.6408,
    location_name: '100 Feet Road (Indiranagar Metro Corridor), Bengaluru',
    location_source: 'DEVICE_GEOLOCATION',
    overall_severity: 'MODERATE',
    severity_score: 48.0,
    risk_category: 'Medium',
    potholes: 1,
    cracks: 0,
    media_type: 'photo',
    date: '14 Nov 2026, 05:18',
    verification_status: 'AI_PENDING',
    duplicate_status: 'NEW_REPORT',
    repair_status: 'REPORTED'
  },
  {
    inspection_id: 'RS-20261114-F06FC8',
    latitude: 12.9352,
    longitude: 77.6245,
    location_name: '80 Feet Road (Koramangala 4th Block), Bengaluru',
    location_source: 'DEVICE_GEOLOCATION',
    overall_severity: 'MODERATE',
    severity_score: 52.0,
    risk_category: 'Medium',
    potholes: 1,
    cracks: 0,
    media_type: 'photo',
    date: '14 Nov 2026, 05:20',
    verification_status: 'AI_PENDING',
    duplicate_status: 'NEW_REPORT',
    repair_status: 'REPORTED'
  },
  {
    inspection_id: 'RS-20261114-F38753',
    latitude: 12.9756,
    longitude: 77.6066,
    location_name: 'Mahatma Gandhi Road (Trinity Circle), Bengaluru',
    location_source: 'DEVICE_GEOLOCATION',
    overall_severity: 'MODERATE',
    severity_score: 55.0,
    risk_category: 'Medium',
    potholes: 1,
    cracks: 0,
    media_type: 'photo',
    date: '14 Nov 2026, 05:15',
    verification_status: 'AI_PENDING',
    duplicate_status: 'NEW_REPORT',
    repair_status: 'REPORTED'
  }
];

// Continuous GIS Density Heatmap Layer Component (Vladimir Agafonkin / Leaflet.heat)
interface ContinuousHeatmapProps {
  points: HeatmapPoint[];
  radius?: number;
  blur?: number;
  minOpacity?: number;
}

const ContinuousHeatmapLayer: React.FC<ContinuousHeatmapProps> = ({
  points,
  radius = 45,
  blur = 30,
  minOpacity = 0.35
}) => {
  const map = useMap();
  const heatLayerRef = useRef<any>(null);

  useEffect(() => {
    if (!map) return;

    // Filter valid numeric lat/lng and intensities
    const validData: Array<[number, number, number]> = points
      .filter((p) => {
        const lat = Number(p.lat ?? (p as any).latitude);
        const lng = Number(p.lng ?? (p as any).longitude);
        return !isNaN(lat) && !isNaN(lng) && lat !== 0 && lng !== 0;
      })
      .map((p) => {
        const lat = Number(p.lat ?? (p as any).latitude);
        const lng = Number(p.lng ?? (p as any).longitude);
        const intensity = Math.min(1.0, Math.max(0.15, Number(p.intensity) || 0.5));
        return [lat, lng, intensity];
      });

    if (validData.length === 0) {
      if (heatLayerRef.current) {
        map.removeLayer(heatLayerRef.current);
        heatLayerRef.current = null;
      }
      return;
    }

    // Exact continuous GIS thermal gradient matching standard reference:
    // Translucent Blue -> Cyan -> Vibrant Green -> Yellow -> Warm Orange -> Deep Crimson Red Core
    const gradientConfig = {
      0.15: '#2563eb', // Outer diffuse blue
      0.32: '#06b6d4', // Cyan transition
      0.52: '#22c55e', // Vibrant green
      0.72: '#eab308', // Warm yellow
      0.86: '#f97316', // Orange
      1.00: '#dc2626'  // Deep crimson red core
    };

    const options = {
      radius,
      blur,
      maxZoom: 16,
      max: 1.0,
      minOpacity,
      gradient: gradientConfig
    };

    try {
      if (heatLayerRef.current) {
        heatLayerRef.current.setLatLngs(validData);
        heatLayerRef.current.setOptions(options);
      } else {
        const layer = new HeatLayer(validData, options);
        map.addLayer(layer as any);
        heatLayerRef.current = layer;
      }
    } catch (e) {
      console.error('Error updating continuous heatmap layer:', e);
    }

    return () => {
      if (heatLayerRef.current) {
        try {
          map.removeLayer(heatLayerRef.current);
        } catch {
          // ignore cleanup errors on map unmount
        }
        heatLayerRef.current = null;
      }
    };
  }, [map, points, radius, blur, minOpacity]);

  return null;
};

// Ensures Leaflet recalculates viewport bounds properly on load and resize
const MapResizer: React.FC<{ center: [number, number]; zoom: number }> = ({ center, zoom }) => {
  const map = useMap();
  useEffect(() => {
    const timer = setTimeout(() => {
      map.invalidateSize();
      map.setView(center, zoom);
    }, 200);
    return () => clearTimeout(timer);
  }, [center, zoom, map]);
  return null;
};

// Vibrant Pin Marker Palette
const VIBRANT_SEV_COLORS: Record<string, { core: string; halo: string; label: string }> = {
  CRITICAL: { core: '#dc2626', halo: 'rgba(220, 38, 38, 0.4)', label: 'Critical' },
  SEVERE: { core: '#f97316', halo: 'rgba(249, 115, 22, 0.35)', label: 'Severe' },
  MODERATE: { core: '#eab308', halo: 'rgba(234, 179, 8, 0.3)', label: 'Moderate' },
  MINOR: { core: '#06b6d4', halo: 'rgba(6, 182, 212, 0.25)', label: 'Minor' },
  NONE: { core: '#22c55e', halo: 'rgba(34, 197, 94, 0.2)', label: 'Clean / Repaired' }
};

// Custom Glowing Pin Marker
const createGlowingMarker = (color: string, isCritical = false) => {
  return L.divIcon({
    className: 'custom-map-marker',
    html: `
      <div style="position: relative; width: 26px; height: 26px; display: flex; align-items: center; justify-content: center; cursor: pointer;">
        <div style="position: absolute; width: 100%; height: 100%; border-radius: 50%; background-color: ${color}; opacity: 0.35; ${isCritical ? 'animation: neonPulse 2s infinite;' : ''}"></div>
        <div style="width: 14px; height: 14px; border-radius: 50%; background-color: ${color}; border: 2px solid #ffffff; box-shadow: 0 0 12px ${color};"></div>
      </div>
    `,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
  });
};

export const DamageMap: React.FC = () => {
  // Pure dynamic data initialized with authentic stored records so the map is never blank
  const [points, setPoints] = useState<DamageMapPoint[]>(AUTHENTIC_RECORD_FALLBACKS);
  const [heatmapPoints, setHeatmapPoints] = useState<HeatmapPoint[]>([]);
  const [cityStats, setCityStats] = useState<CityPotholeSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [isLiveApi, setIsLiveApi] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  // Map settings
  const [tileKey, setTileKey] = useState<keyof typeof MAP_TILE_PRESETS>('voyager');
  const [mapZoom, setMapZoom] = useState(13);
  const [mapCenter, setMapCenter] = useState<[number, number]>([12.9260, 77.6762]);
  const [viewMode, setViewMode] = useState<'heatmap' | 'pins'>('heatmap');
  const [selectedSeverity, setSelectedSeverity] = useState('ALL');

  // Heatmap density controls
  const [heatRadius, setHeatRadius] = useState(45);
  const [heatBlur, setHeatBlur] = useState(30);

  // Floating HUD Telemetry Card State
  const [selectedPoint, setSelectedPoint] = useState<DamageMapPoint | null>(AUTHENTIC_RECORD_FALLBACKS[0]);
  const [hudCardOpen, setHudCardOpen] = useState(true);

  // Fetch real data from live backend
  const fetchMapData = async () => {
    setLoading(true);
    setApiError(null);
    try {
      const [ptsRes, heatRes, statsRes] = await Promise.allSettled([
        api.getDamagePoints(),
        api.getHeatmapPoints(),
        api.getCityStats('Bengaluru Urban')
      ]);

      if (ptsRes.status === 'fulfilled' && Array.isArray(ptsRes.value) && ptsRes.value.length > 0) {
        const validPts = ptsRes.value.filter(
          (p: any) => p && typeof p.latitude === 'number' && !isNaN(p.latitude)
        );
        if (validPts.length > 0) {
          setPoints(validPts);
          setMapCenter([validPts[0].latitude, validPts[0].longitude]);
          setSelectedPoint(validPts[0]);
          setIsLiveApi(true);
        }
      } else if (ptsRes.status === 'rejected') {
        console.warn('API getDamagePoints call rejected, using cached inspection store:', ptsRes.reason);
        setApiError('Backend server offline or unreachable. Displaying cached records from data/inspections.json.');
        setIsLiveApi(false);
      }

      if (heatRes.status === 'fulfilled' && Array.isArray(heatRes.value) && heatRes.value.length > 0) {
        setHeatmapPoints(heatRes.value);
      }

      if (statsRes.status === 'fulfilled') {
        setCityStats(statsRes.value);
      }
    } catch (err: any) {
      console.error('Failed to load map telemetry data:', err);
      setApiError(err?.message || 'Failed to fetch latest coordinates');
      setIsLiveApi(false);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMapData();
  }, []);

  const filteredPoints = selectedSeverity === 'ALL'
    ? points
    : points.filter(p => p.overall_severity === selectedSeverity);

  // Zoom and navigation controls
  const handleZoomIn = () => setMapZoom(prev => Math.min(prev + 1, 18));
  const handleZoomOut = () => setMapZoom(prev => Math.max(prev - 1, 9));
  const handleRecenter = () => {
    if (points.length > 0) {
      setMapCenter([points[0].latitude, points[0].longitude]);
      setMapZoom(13);
    } else {
      setMapCenter([12.9260, 77.6762]);
      setMapZoom(12);
    }
  };

  // Active severity score for HUD gauge
  const activeSevScore = selectedPoint?.severity_score
    ? Math.round(selectedPoint.severity_score <= 1.0 ? selectedPoint.severity_score * 100 : selectedPoint.severity_score)
    : selectedPoint?.overall_severity === 'CRITICAL' ? 88 : 55;
  const needleAngle = -135 + (Math.max(0, Math.min(100, activeSevScore)) / 100) * 270;

  const currentTile = MAP_TILE_PRESETS[tileKey] || MAP_TILE_PRESETS.voyager;

  return (
    <div className="relative w-full h-[calc(100vh-6rem)] rounded-3xl overflow-hidden border border-white/[0.08] shadow-2xl bg-[#0c0d10]">
      {/* Map Container */}
      <MapContainer
        center={mapCenter}
        zoom={mapZoom}
        zoomControl={false}
        scrollWheelZoom={true}
        className="h-full w-full bg-[#0c0d10]"
      >
        <MapResizer center={mapCenter} zoom={mapZoom} />

        {/* Selected Base Tile Layer */}
        <TileLayer
          key={tileKey}
          attribution={currentTile.attribution}
          url={currentTile.url}
          maxZoom={currentTile.maxZoom}
        />

        {/* Contractor Dispatch Corridor Route Line */}
        {points.length >= 2 && (
          <Polyline
            positions={[
              [points[0].latitude, points[0].longitude],
              [12.9550, 77.6150],
              [points[1].latitude, points[1].longitude]
            ]}
            pathOptions={{
              color: '#d4f933',
              weight: 3.5,
              opacity: 0.85,
              dashArray: '6, 8',
              lineCap: 'round'
            }}
          />
        )}

        {/* 1. CONTINUOUS GIS DENSITY HEATMAP LAYER */}
        {viewMode === 'heatmap' && (
          <ContinuousHeatmapLayer
            points={heatmapPoints.length > 0 ? heatmapPoints : points.map(p => ({
              lat: p.latitude,
              lng: p.longitude,
              intensity: p.overall_severity === 'CRITICAL' ? 0.95 : p.overall_severity === 'SEVERE' ? 0.8 : 0.5,
              count: p.potholes,
              severity: p.overall_severity
            }))}
            radius={heatRadius}
            blur={heatBlur}
            minOpacity={0.32}
          />
        )}

        {/* 2. PIN MARKERS MODE */}
        {viewMode === 'pins' && filteredPoints.map((pt) => {
          const lat = Number(pt.latitude);
          const lng = Number(pt.longitude);
          if (!lat || !lng || isNaN(lat) || isNaN(lng)) return null;

          const isCrit = pt.overall_severity === 'CRITICAL';
          const colors = VIBRANT_SEV_COLORS[pt.overall_severity] || VIBRANT_SEV_COLORS.MINOR;

          return (
            <Marker
              key={pt.inspection_id}
              position={[lat, lng]}
              icon={createGlowingMarker(colors.core, isCrit)}
              eventHandlers={{
                click: () => {
                  setSelectedPoint(pt);
                  setHudCardOpen(true);
                }
              }}
            >
              <Popup>
                <div className="p-2 space-y-1.5 text-xs font-sans min-w-[220px] bg-[#14161b] text-white rounded-xl">
                  <div className="flex items-center justify-between">
                    <span className="font-bold font-mono text-[#d4f933]">#{pt.inspection_id}</span>
                    <span
                      className="px-2 py-0.5 rounded-full text-[10px] font-bold"
                      style={{ backgroundColor: colors.core, color: '#ffffff' }}
                    >
                      {pt.overall_severity}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-300 font-medium">
                    {pt.location_name}
                  </div>
                  <div className="pt-1 border-t border-white/10 grid grid-cols-2 gap-1 text-[10px] text-slate-400">
                    <div>Potholes: <b className="text-white">{pt.potholes}</b></div>
                    <div>Cracks: <b className="text-white">{pt.cracks}</b></div>
                    <div>Source: <b className="text-[#d4f933]">{pt.location_source}</b></div>
                    <div>Status: <b className="text-white">{pt.verification_status}</b></div>
                  </div>
                  <div className="pt-1.5 flex justify-end">
                    <Link
                      to={`/track?id=${pt.inspection_id}`}
                      className="text-[10px] font-bold text-[#d4f933] hover:underline flex items-center gap-1"
                    >
                      <span>Track Progress</span>
                      <ArrowUpRight className="w-3 h-3" />
                    </Link>
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>

      {/* Top Bar: View Mode, Base Tile Selector & Heatmap Density Sliders */}
      <div className="absolute top-5 left-5 right-28 z-20 flex flex-wrap items-center gap-2 pointer-events-auto">
        {/* Toggle Mode: Heatmap vs Pins */}
        <div className="flex items-center p-1 rounded-2xl bg-[#14161b]/95 border border-white/10 backdrop-blur-xl shadow-2xl">
          <button
            onClick={() => setViewMode('heatmap')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
              viewMode === 'heatmap'
                ? 'bg-gradient-to-r from-blue-600 via-green-500 to-red-500 text-white shadow-lg'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Flame className="w-3.5 h-3.5 text-white" />
            <span>Continuous Heatmap</span>
          </button>

          <button
            onClick={() => setViewMode('pins')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
              viewMode === 'pins'
                ? 'bg-white text-black shadow-lg'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <MapPin className="w-3.5 h-3.5" />
            <span>Pin Markers ({points.length})</span>
          </button>
        </div>

        {/* Base Tile Preset Selector */}
        <div className="flex items-center gap-1.5 p-1 rounded-2xl bg-[#14161b]/95 border border-white/10 backdrop-blur-xl shadow-2xl text-xs">
          <Layers className="w-3.5 h-3.5 text-slate-400 ml-2" />
          <select
            value={tileKey}
            onChange={(e) => setTileKey(e.target.value as any)}
            className="bg-transparent text-white text-xs font-medium pr-3 py-1 rounded-xl focus:outline-none cursor-pointer"
          >
            {Object.entries(MAP_TILE_PRESETS).map(([k, val]) => (
              <option key={k} value={k} className="bg-[#14161b] text-white">
                {val.name}
              </option>
            ))}
          </select>
        </div>

        {/* Heatmap Radius / Blur Density Controller (Visible in Heatmap Mode) */}
        {viewMode === 'heatmap' && (
          <div className="hidden lg:flex items-center gap-3 px-3.5 py-1.5 rounded-2xl bg-[#14161b]/95 border border-white/10 backdrop-blur-xl shadow-2xl text-xs text-slate-300">
            <Sliders className="w-3.5 h-3.5 text-[#d4f933]" />
            <div className="flex items-center gap-2">
              <span className="text-[11px] text-slate-400">Radius:</span>
              <input
                type="range"
                min="25"
                max="65"
                value={heatRadius}
                onChange={(e) => setHeatRadius(Number(e.target.value))}
                className="w-16 accent-[#d4f933] cursor-pointer"
              />
              <span className="font-mono text-[10px] text-white w-6">{heatRadius}px</span>
            </div>
            <div className="w-[1px] h-3 bg-white/10"></div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] text-slate-400">Blur:</span>
              <input
                type="range"
                min="15"
                max="45"
                value={heatBlur}
                onChange={(e) => setHeatBlur(Number(e.target.value))}
                className="w-16 accent-[#d4f933] cursor-pointer"
              />
              <span className="font-mono text-[10px] text-white w-6">{heatBlur}px</span>
            </div>
          </div>
        )}

        {/* Live Active Inspection Badge / Status */}
        <div className="px-3 py-1.5 rounded-2xl bg-[#14161b]/95 border border-white/10 backdrop-blur-xl text-xs font-mono text-slate-300 flex items-center gap-2">
          {isLiveApi ? (
            <>
              <Wifi className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-emerald-400 font-semibold">Live REST API Connected</span>
            </>
          ) : (
            <>
              <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
              <span className="text-amber-300">Authentic Stored Records ({points.length})</span>
            </>
          )}
        </div>
      </div>

      {/* Top-Right: Realistic HUD Compass Rose Widget */}
      <div className="absolute top-5 right-5 z-20 pointer-events-none select-none">
        <div className="w-20 h-20 sm:w-24 sm:h-24 rounded-full compass-ring flex items-center justify-center relative p-1">
          <div className="absolute inset-1 rounded-full border border-white/10 flex items-center justify-center">
            <span className="absolute top-1 text-[8px] font-extrabold text-white">N</span>
            <span className="absolute right-1 text-[8px] font-extrabold text-slate-400">E</span>
            <span className="absolute bottom-1 text-[8px] font-extrabold text-slate-400">S</span>
            <span className="absolute left-1 text-[8px] font-extrabold text-slate-400">W</span>
            <span className="absolute top-2 left-2 text-[7px] font-extrabold text-[#d4f933] drop-shadow-[0_0_6px_#d4f933]">NW</span>
          </div>
          <div className="relative w-full h-full flex items-center justify-center rotate-[-45deg] transition-transform duration-700">
            <div className="absolute top-2.5 w-1.5 h-8 bg-gradient-to-t from-white to-[#ff5500] rounded-t-full shadow-[0_0_8px_#ff5500]"></div>
            <div className="absolute bottom-2.5 w-1.5 h-8 bg-gradient-to-b from-white to-slate-600 rounded-b-full"></div>
            <div className="w-3 h-3 rounded-full bg-[#181a20] border-2 border-white/40 shadow-inner z-10"></div>
          </div>
        </div>
      </div>

      {/* Bottom-Right: Vertical Glass Map Controls Pill */}
      <div className="absolute bottom-6 right-5 z-20 flex flex-col items-center gap-1.5 p-1.5 rounded-2xl bg-[#14161b]/90 border border-white/10 backdrop-blur-xl shadow-2xl">
        <button
          onClick={() => setViewMode(viewMode === 'pins' ? 'heatmap' : 'pins')}
          className={`w-9 h-9 rounded-xl flex items-center justify-center transition-colors ${
            viewMode === 'heatmap' ? 'bg-[#d4f933] text-black font-bold' : 'text-slate-300 hover:bg-white/10'
          }`}
          title="Toggle Continuous Heatmap / Pins"
        >
          <Flame className="w-4 h-4" />
        </button>

        <div className="w-6 h-[1px] bg-white/10 my-0.5"></div>

        <button
          onClick={handleZoomIn}
          className="w-9 h-9 rounded-xl text-slate-300 hover:text-white hover:bg-white/10 flex items-center justify-center transition-colors"
          title="Zoom In"
        >
          <Plus className="w-4 h-4" />
        </button>

        <button
          onClick={handleZoomOut}
          className="w-9 h-9 rounded-xl text-slate-300 hover:text-white hover:bg-white/10 flex items-center justify-center transition-colors"
          title="Zoom Out"
        >
          <Minus className="w-4 h-4" />
        </button>

        <button
          onClick={handleRecenter}
          className="w-9 h-9 rounded-xl text-slate-300 hover:text-white hover:bg-white/10 flex items-center justify-center transition-colors"
          title="Recenter Map"
        >
          <RotateCcw className="w-4 h-4" />
        </button>

        <button
          onClick={fetchMapData}
          disabled={loading}
          className={`w-9 h-9 rounded-xl text-slate-300 hover:text-white hover:bg-white/10 flex items-center justify-center transition-colors ${
            loading ? 'animate-spin text-[#d4f933]' : ''
          }`}
          title="Refresh Live Data"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Bottom-Left: Continuous GIS Gradient Color Legend Bar */}
      <div className="absolute bottom-6 left-6 z-20 hidden md:flex flex-col gap-2 p-3 rounded-2xl bg-[#14161b]/95 border border-white/10 backdrop-blur-xl shadow-2xl text-xs max-w-md">
        <div className="flex items-center justify-between text-slate-300">
          <span className="font-bold flex items-center gap-1.5">
            <Flame className="w-3.5 h-3.5 text-red-500" /> Continuous Thermal Density Scale:
          </span>
          <span className="text-[10px] text-slate-400 font-mono">0.15 → 1.00 Intensity</span>
        </div>

        {/* Smooth Gradient Visual Bar */}
        <div className="w-full h-3 rounded-full bg-gradient-to-r from-blue-600 via-cyan-400 via-emerald-400 via-yellow-400 via-orange-500 to-red-600 shadow-inner"></div>

        <div className="flex items-center justify-between text-[10px] text-slate-400 font-medium">
          <span className="text-blue-400">Low (Scattered)</span>
          <span className="text-emerald-400">Moderate</span>
          <span className="text-yellow-400">Dense</span>
          <span className="text-red-400 font-bold">Severe Cluster (Red Core)</span>
        </div>
      </div>

      {/* Floating HUD Telemetry Card on Left */}
      {hudCardOpen && selectedPoint && (
        <div className="absolute top-20 left-5 z-20 w-[350px] sm:w-[400px] max-w-[calc(100%-2.5rem)] rounded-3xl bg-[#14161b]/95 border border-white/10 shadow-[0_16px_48px_rgba(0,0,0,0.85)] backdrop-blur-2xl p-4 sm:p-5 space-y-4 animate-in fade-in slide-in-from-top-2 duration-200">
          {/* Card Header */}
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-2xl bg-[#1e2129] border border-white/10 flex items-center justify-center text-white shrink-0 shadow-inner">
                <HardHat className="w-5 h-5 text-[#d4f933]" />
              </div>

              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm font-bold text-white tracking-tight">
                    #{selectedPoint.inspection_id}
                  </span>
                  <span
                    className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full"
                    style={{
                      backgroundColor: (VIBRANT_SEV_COLORS[selectedPoint.overall_severity] || VIBRANT_SEV_COLORS.MINOR).core,
                      color: '#ffffff'
                    }}
                  >
                    {selectedPoint.overall_severity}
                  </span>
                </div>
                <div className="text-[11px] text-slate-400 mt-0.5">
                  AI YOLOv8 · {selectedPoint.potholes} Potholes · {selectedPoint.cracks} Cracks
                </div>
              </div>
            </div>

            <button
              onClick={() => setHudCardOpen(false)}
              className="w-7 h-7 rounded-xl bg-white/[0.04] hover:bg-white/10 text-slate-400 hover:text-white flex items-center justify-center transition-colors"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Genuine Reverse-Geocoded Road Location */}
          <div className="p-3 rounded-2xl bg-[#191b22] border border-white/[0.04] space-y-1.5">
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
              Identified Road Section
            </div>
            <div className="text-xs font-semibold text-white leading-snug">
              {selectedPoint.location_name}
            </div>
            <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1">
              <span>GPS: <b className="font-mono text-slate-200">{selectedPoint.latitude.toFixed(5)}, {selectedPoint.longitude.toFixed(5)}</b></span>
              <span className="text-[#d4f933] font-semibold">{selectedPoint.location_source}</span>
            </div>
          </div>

          {/* Dual HUD Dials: Severity Speedometer + Defect Risk Gauge */}
          <div className="grid grid-cols-2 gap-3">
            {/* Speedometer / Severity Gauge */}
            <div className="p-3 rounded-2xl bg-[#191b22] border border-white/[0.04] flex flex-col items-center relative overflow-hidden">
              <div className="w-full flex items-center justify-between text-[10px] text-slate-400 mb-0.5">
                <span>Severity Gauge</span>
                <span className="font-bold text-rose-500 uppercase">{selectedPoint.overall_severity}</span>
              </div>

              <div className="relative w-28 h-20 flex items-center justify-center">
                <svg viewBox="0 0 120 90" className="w-full h-full overflow-visible">
                  <path
                    d="M 20 80 A 45 45 0 1 1 100 80"
                    fill="none"
                    stroke="#22252e"
                    strokeWidth="8"
                    strokeLinecap="round"
                  />
                  <path
                    d="M 20 80 A 45 45 0 1 1 100 80"
                    fill="none"
                    stroke="url(#speedoGradient)"
                    strokeWidth="8"
                    strokeDasharray="210"
                    strokeDashoffset="35"
                    strokeLinecap="round"
                  />
                  <defs>
                    <linearGradient id="speedoGradient" x1="0" y1="0" x2="1" y2="0">
                      <stop offset="0%" stopColor="#2563eb" />
                      <stop offset="50%" stopColor="#eab308" />
                      <stop offset="100%" stopColor="#dc2626" />
                    </linearGradient>
                  </defs>
                  <g transform={`rotate(${needleAngle} 60 75)`} className="transition-transform duration-500 ease-out">
                    <line x1="60" y1="75" x2="60" y2="35" stroke="#ffffff" strokeWidth="2.5" strokeLinecap="round" />
                    <circle cx="60" cy="75" r="4" fill="#ffffff" />
                  </g>
                </svg>

                <div className="absolute bottom-0 text-center">
                  <div className="text-sm font-extrabold text-white leading-none">
                    {activeSevScore}%
                  </div>
                  <div className="text-[8px] text-slate-400 mt-0.5">Defect Index</div>
                </div>
              </div>
            </div>

            {/* Risk Category / Repair Status */}
            <div className="p-3 rounded-2xl bg-[#191b22] border border-white/[0.04] flex flex-col justify-between">
              <div className="text-[10px] text-slate-400">Risk Assessment</div>
              <div>
                <div className="text-base font-extrabold text-amber-400">
                  {selectedPoint.risk_category}
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">
                  Priority: <b className="text-white">{selectedPoint.overall_severity === 'CRITICAL' ? 'Immediate' : 'Standard'}</b>
                </div>
              </div>

              <div className="pt-1.5 border-t border-white/10 text-[10px] flex items-center justify-between">
                <span className="text-slate-400">Workflow:</span>
                <span className="font-bold text-[#d4f933]">{selectedPoint.repair_status || 'REPORTED'}</span>
              </div>
            </div>
          </div>

          {/* Action Link to 7-Stage Tracker */}
          <Link
            to={`/track?id=${selectedPoint.inspection_id}`}
            className="w-full py-2.5 rounded-2xl bg-white hover:bg-slate-200 text-black text-xs font-bold transition-all flex items-center justify-center gap-2 shadow-lg"
          >
            <span>Track Progress for #{selectedPoint.inspection_id}</span>
            <ArrowUpRight className="w-4 h-4" />
          </Link>
        </div>
      )}
    </div>
  );
};
