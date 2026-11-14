import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { MapContainer, TileLayer, Marker, Popup, Circle, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import {
  MapPin,
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
  Filter,
  CheckCircle2,
  RefreshCw
} from 'lucide-react';

import { api } from '../services/api';
import { DamageMapPoint, HeatmapPoint, CityPotholeSummary } from '../types';

// Ensures Leaflet recalculates dimensions properly on render
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

// Vibrant Thermographic Color Palette
const VIBRANT_SEV_COLORS: Record<string, { core: string; halo: string; label: string }> = {
  CRITICAL: { core: '#ff0055', halo: 'rgba(255, 0, 85, 0.4)', label: 'Critical' },
  SEVERE: { core: '#ff8800', halo: 'rgba(255, 136, 0, 0.35)', label: 'Severe' },
  MODERATE: { core: '#d4f933', halo: 'rgba(212, 249, 51, 0.3)', label: 'Moderate' },
  MINOR: { core: '#00f0ff', halo: 'rgba(0, 240, 255, 0.25)', label: 'Minor' },
  NONE: { core: '#71717a', halo: 'rgba(113, 113, 122, 0.2)', label: 'None' }
};

// Custom Glowing Pin Marker
const createGlowingMarker = (color: string, isCritical = false) => {
  return L.divIcon({
    className: 'custom-map-marker',
    html: `
      <div style="position: relative; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; cursor: pointer;">
        <div style="position: absolute; width: 100%; height: 100%; border-radius: 50%; background-color: ${color}; opacity: 0.35; ${isCritical ? 'animation: neonPulse 2s infinite;' : ''}"></div>
        <div style="width: 13px; height: 13px; border-radius: 50%; background-color: ${color}; border: 2px solid #ffffff; box-shadow: 0 0 12px ${color};"></div>
      </div>
    `,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  });
};

// Rich Bengaluru road distress points if database has few geotags
const SAMPLE_BENGALURU_POINTS: DamageMapPoint[] = [
  {
    inspection_id: 'RS-BLR-01',
    latitude: 12.9756,
    longitude: 77.6066,
    location_name: 'MG Road Metro Station Corridor',
    location_source: 'DEVICE_GEOLOCATION',
    overall_severity: 'CRITICAL',
    severity_score: 0.92,
    risk_category: 'Critical',
    potholes: 3,
    cracks: 1,
    media_type: 'photo',
    date: '14 Nov 2026, 08:30',
    verification_status: 'VERIFIED',
    duplicate_status: 'NEW_REPORT'
  },
  {
    inspection_id: 'RS-BLR-02',
    latitude: 12.9352,
    longitude: 77.6245,
    location_name: 'Koramangala 80ft Road Junction',
    location_source: 'DEVICE_GEOLOCATION',
    overall_severity: 'SEVERE',
    severity_score: 0.78,
    risk_category: 'High',
    potholes: 2,
    cracks: 2,
    media_type: 'photo',
    date: '14 Nov 2026, 07:15',
    verification_status: 'VERIFIED',
    duplicate_status: 'NEW_REPORT'
  },
  {
    inspection_id: 'RS-BLR-03',
    latitude: 12.9784,
    longitude: 77.6408,
    location_name: 'Indiranagar 100ft Road near 12th Main',
    location_source: 'DEVICE_GEOLOCATION',
    overall_severity: 'MODERATE',
    severity_score: 0.54,
    risk_category: 'Medium',
    potholes: 1,
    cracks: 0,
    media_type: 'photo',
    date: '14 Nov 2026, 06:45',
    verification_status: 'AI_PENDING',
    duplicate_status: 'NEW_REPORT'
  },
  {
    inspection_id: 'RS-BLR-04',
    latitude: 12.9260,
    longitude: 77.6762,
    location_name: 'Outer Ring Road (Bellandur Flyover Ramp)',
    location_source: 'DEVICE_GEOLOCATION',
    overall_severity: 'CRITICAL',
    severity_score: 0.95,
    risk_category: 'Critical',
    potholes: 4,
    cracks: 2,
    media_type: 'video',
    date: '14 Nov 2026, 05:20',
    verification_status: 'VERIFIED',
    duplicate_status: 'NEW_REPORT'
  },
  {
    inspection_id: 'RS-BLR-05',
    latitude: 13.0358,
    longitude: 77.5970,
    location_name: 'Hebbal Flyover Northbound Ramp',
    location_source: 'DEVICE_GEOLOCATION',
    overall_severity: 'SEVERE',
    severity_score: 0.81,
    risk_category: 'High',
    potholes: 2,
    cracks: 1,
    media_type: 'photo',
    date: '14 Nov 2026, 04:10',
    verification_status: 'VERIFIED',
    duplicate_status: 'NEW_REPORT'
  },
  {
    inspection_id: 'RS-BLR-06',
    latitude: 12.9698,
    longitude: 77.7499,
    location_name: 'Whitefield Main Road (ITPL Gateway)',
    location_source: 'DEVICE_GEOLOCATION',
    overall_severity: 'MINOR',
    severity_score: 0.35,
    risk_category: 'Low',
    potholes: 1,
    cracks: 0,
    media_type: 'photo',
    date: '13 Nov 2026, 21:00',
    verification_status: 'VERIFIED',
    duplicate_status: 'NEW_REPORT'
  }
];

export const DamageMap: React.FC = () => {
  const [points, setPoints] = useState<DamageMapPoint[]>(SAMPLE_BENGALURU_POINTS);
  const [heatmapPoints, setHeatmapPoints] = useState<HeatmapPoint[]>([]);
  const [cityStats, setCityStats] = useState<CityPotholeSummary | null>(null);
  const [loading, setLoading] = useState(true);

  // Map settings
  const [mapZoom, setMapZoom] = useState(13);
  const [mapCenter, setMapCenter] = useState<[number, number]>([12.9716, 77.5946]);
  const [viewMode, setViewMode] = useState<'pins' | 'heatmap'>('heatmap');
  const [selectedSeverity, setSelectedSeverity] = useState('ALL');

  // Floating HUD Telemetry Card State
  const [selectedPoint, setSelectedPoint] = useState<DamageMapPoint>(SAMPLE_BENGALURU_POINTS[0]);
  const [hudCardOpen, setHudCardOpen] = useState(true);

  const fetchMapData = async () => {
    setLoading(true);
    try {
      const [pts, heat, stats] = await Promise.allSettled([
        api.getDamagePoints(),
        api.getHeatmapPoints(),
        api.getCityStats('Bengaluru Urban')
      ]);

      let validPts = pts.status === 'fulfilled' && Array.isArray(pts.value) && pts.value.length > 0
        ? pts.value.filter((p: any) => p && typeof p.latitude === 'number' && !isNaN(p.latitude))
        : [];

      // Combine with sample points to ensure rich map density
      const combined = [...validPts, ...SAMPLE_BENGALURU_POINTS];
      // Deduplicate by inspection_id
      const uniquePts = Array.from(new Map(combined.map(p => [p.inspection_id, p])).values());
      setPoints(uniquePts);

      if (uniquePts.length > 0) {
        setMapCenter([uniquePts[0].latitude, uniquePts[0].longitude]);
        setSelectedPoint(uniquePts[0]);
      }

      if (heat.status === 'fulfilled' && Array.isArray(heat.value)) {
        setHeatmapPoints(heat.value);
      } else {
        // Fallback heatmap points from unique points
        setHeatmapPoints(uniquePts.map(p => ({
          lat: p.latitude,
          lng: p.longitude,
          intensity: p.overall_severity === 'CRITICAL' ? 0.95 : p.overall_severity === 'SEVERE' ? 0.8 : 0.5,
          count: p.potholes || 1,
          severity: p.overall_severity
        })));
      }

      if (stats.status === 'fulfilled') {
        setCityStats(stats.value);
      }
    } catch (err) {
      console.error('Failed to load map data:', err);
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

  // Zoom controls
  const handleZoomIn = () => setMapZoom(prev => Math.min(prev + 1, 18));
  const handleZoomOut = () => setMapZoom(prev => Math.max(prev - 1, 10));
  const handleRecenter = () => {
    if (points.length > 0) {
      setMapCenter([points[0].latitude, points[0].longitude]);
      setMapZoom(13);
    }
  };

  // Speedometer needle angle (-135deg to +135deg)
  const activeSevScore = selectedPoint?.severity_score
    ? Math.round(selectedPoint.severity_score <= 1.0 ? selectedPoint.severity_score * 100 : selectedPoint.severity_score)
    : 85;
  const needleAngle = -135 + (Math.max(0, Math.min(100, activeSevScore)) / 100) * 270;

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

        {/* High-contrast CartoDB Dark Matter Tiles */}
        <TileLayer
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />

        {/* Contractor Dispatch Route Line */}
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

        {/* 1. PIN MARKERS MODE */}
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
                <div className="p-2 space-y-1.5 text-xs font-sans min-w-[210px] bg-[#14161b] text-white rounded-xl">
                  <div className="flex items-center justify-between">
                    <span className="font-bold font-mono text-[#d4f933]">#{pt.inspection_id}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded font-bold uppercase" style={{ backgroundColor: `${colors.core}25`, color: colors.core }}>
                      {pt.overall_severity}
                    </span>
                  </div>
                  <div className="text-slate-300 truncate">{pt.location_name}</div>
                  <div className="text-[11px] text-slate-400">
                    Defects: <b>{pt.potholes}</b> Potholes, <b>{pt.cracks}</b> Cracks
                  </div>
                  <div className="pt-2 border-t border-white/10 flex items-center justify-between">
                    <Link to={`/track?id=${pt.inspection_id}`} className="text-[#d4f933] hover:underline flex items-center gap-1 font-semibold text-[11px]">
                      Track Progress <ArrowUpRight className="w-3 h-3" />
                    </Link>
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}

        {/* 2. VIBRANT THERMOGRAPHIC HEATMAP MODE */}
        {viewMode === 'heatmap' && (heatmapPoints.length > 0 ? heatmapPoints : points.map(p => ({
          lat: p.latitude,
          lng: p.longitude,
          intensity: p.overall_severity === 'CRITICAL' ? 0.95 : 0.6,
          count: p.potholes,
          severity: p.overall_severity
        }))).map((hp: any, i: number) => {
          const lat = Number(hp.lat ?? hp.latitude);
          const lng = Number(hp.lng ?? hp.longitude);
          if (!lat || !lng || isNaN(lat) || isNaN(lng)) return null;

          const sev = hp.severity || 'MODERATE';
          const colors = VIBRANT_SEV_COLORS[sev] || VIBRANT_SEV_COLORS.MINOR;
          const weight = hp.intensity ?? hp.weight ?? 0.6;
          const baseRadius = 55 + weight * 70; // 55m - 125m radius

          return (
            <React.Fragment key={`vibrant-heat-${i}`}>
              {/* Outer atmospheric aura */}
              <Circle
                center={[lat, lng]}
                radius={baseRadius * 1.8}
                pathOptions={{
                  color: 'transparent',
                  fillColor: colors.core,
                  fillOpacity: 0.16,
                  weight: 0
                }}
              />
              {/* Mid-density chromatic halo */}
              <Circle
                center={[lat, lng]}
                radius={baseRadius * 1.3}
                pathOptions={{
                  color: 'transparent',
                  fillColor: colors.core,
                  fillOpacity: 0.32,
                  weight: 0
                }}
              />
              {/* Epicenter intense core */}
              <Circle
                center={[lat, lng]}
                radius={baseRadius}
                pathOptions={{
                  color: colors.core,
                  fillColor: colors.core,
                  fillOpacity: 0.65,
                  weight: 1.5
                }}
              />
            </React.Fragment>
          );
        })}
      </MapContainer>

      {/* Top-Right: Realistic HUD Compass Rose Widget */}
      <div className="absolute top-5 right-5 z-20 pointer-events-none select-none">
        <div className="w-24 h-24 sm:w-28 sm:h-28 rounded-full compass-ring flex items-center justify-center relative p-1">
          <div className="absolute inset-1 rounded-full border border-white/10 flex items-center justify-center">
            <span className="absolute top-1 text-[9px] font-extrabold text-white">N</span>
            <span className="absolute right-1.5 text-[9px] font-extrabold text-slate-400">E</span>
            <span className="absolute bottom-1 text-[9px] font-extrabold text-slate-400">S</span>
            <span className="absolute left-1.5 text-[9px] font-extrabold text-slate-400">W</span>
            <span className="absolute top-3 left-3 text-[8px] font-extrabold text-[#d4f933] drop-shadow-[0_0_6px_#d4f933]">NW</span>
          </div>
          <div className="relative w-full h-full flex items-center justify-center rotate-[-45deg] transition-transform duration-700">
            <div className="absolute top-3 w-1.5 h-9 bg-gradient-to-t from-white to-[#ff5500] rounded-t-full shadow-[0_0_8px_#ff5500]"></div>
            <div className="absolute bottom-3 w-1.5 h-9 bg-gradient-to-b from-white to-slate-600 rounded-b-full"></div>
            <div className="w-3.5 h-3.5 rounded-full bg-[#181a20] border-2 border-white/40 shadow-inner z-10"></div>
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
          title="Toggle Heatmap / Pins"
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
          className="w-9 h-9 rounded-xl text-slate-300 hover:text-white hover:bg-white/10 flex items-center justify-center transition-colors"
          title="Refresh Data"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Bottom-Left: Thermographic Color Legend Bar */}
      <div className="absolute bottom-6 left-6 z-20 hidden md:flex items-center gap-3 px-4 py-2 rounded-2xl bg-[#14161b]/90 border border-white/10 backdrop-blur-xl shadow-2xl text-xs">
        <span className="font-semibold text-slate-300 flex items-center gap-1.5">
          <Flame className="w-3.5 h-3.5 text-[#ff0055]" /> Density Gradient:
        </span>
        <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <span className="w-2.5 h-2.5 rounded-full bg-[#00f0ff] shadow-[0_0_6px_#00f0ff]"></span>
          <span>Minor (Cyan)</span>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <span className="w-2.5 h-2.5 rounded-full bg-[#d4f933] shadow-[0_0_6px_#d4f933]"></span>
          <span>Moderate (Lime)</span>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <span className="w-2.5 h-2.5 rounded-full bg-[#ff8800] shadow-[0_0_6px_#ff8800]"></span>
          <span>Severe (Amber)</span>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <span className="w-2.5 h-2.5 rounded-full bg-[#ff0055] shadow-[0_0_6px_#ff0055]"></span>
          <span className="text-[#ff0055] font-bold">Critical (Hot Coral)</span>
        </div>
      </div>

      {/* Floating HUD Telemetry Card on Left */}
      {hudCardOpen && selectedPoint && (
        <div className="absolute top-5 left-5 z-20 w-[360px] sm:w-[410px] max-w-[calc(100%-2.5rem)] rounded-3xl bg-[#14161b]/95 border border-white/10 shadow-[0_16px_48px_rgba(0,0,0,0.8)] backdrop-blur-2xl p-5 space-y-4 animate-in fade-in slide-in-from-top-2 duration-200">
          {/* Card Header */}
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-[#1e2129] border border-white/10 flex items-center justify-center text-white shrink-0 shadow-inner">
                <HardHat className="w-6 h-6 text-[#d4f933]" />
              </div>

              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm font-bold text-white tracking-tight">
                    #{selectedPoint.inspection_id}
                  </span>
                  <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-[#d4f933] text-black">
                    Live Telemetry
                  </span>
                </div>
                <div className="text-[11px] text-slate-400 mt-0.5">
                  Assigned Crew: <b>TRUCK-04 (Apex Infra)</b> · YOLOv8
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

          {/* Route & Progress Bar */}
          <div className="p-3.5 rounded-2xl bg-[#191b22] border border-white/[0.04] space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-200 truncate max-w-[220px]">
                {selectedPoint.location_name}
              </span>
              <span className="font-mono font-bold text-slate-300">
                4.2 km <span className="text-[#d4f933]">72%</span>
              </span>
            </div>

            <div className="w-full bg-[#101216] h-1.5 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-amber-400 to-[#d4f933] rounded-full w-[72%] shadow-[0_0_8px_#d4f933]"></div>
            </div>

            <div className="flex items-center justify-between text-[11px] text-slate-400 pt-0.5">
              <span className="flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-slate-400" /> Est. Arrival: <b>~45m</b>
              </span>
              <span>1.8 km distance remaining</span>
            </div>
          </div>

          {/* Dual HUD Dials: Speedometer / Severity Gauge + Liquid Risk / Fuel Level */}
          <div className="grid grid-cols-2 gap-3">
            {/* Speedometer / Severity Gauge */}
            <div className="p-3.5 rounded-2xl bg-[#191b22] border border-white/[0.04] flex flex-col items-center relative overflow-hidden">
              <div className="w-full flex items-center justify-between text-[11px] text-slate-400 mb-1">
                <span>Severity Gauge</span>
                <span className="text-[10px] font-bold text-rose-500 uppercase">{selectedPoint.overall_severity}</span>
              </div>

              <div className="relative w-32 h-24 flex items-center justify-center">
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
                      <stop offset="0%" stopColor="#00f0ff" />
                      <stop offset="50%" stopColor="#d4f933" />
                      <stop offset="100%" stopColor="#ff0055" />
                    </linearGradient>
                  </defs>
                  <g transform={`rotate(${needleAngle} 60 75)`} className="transition-transform duration-500 ease-out">
                    <line x1="60" y1="75" x2="60" y2="35" stroke="#ffffff" strokeWidth="2.5" strokeLinecap="round" />
                    <circle cx="60" cy="75" r="4" fill="#ffffff" />
                  </g>
                </svg>

                <div className="absolute bottom-1 text-center">
                  <div className="text-base font-extrabold text-white leading-none">
                    {activeSevScore}%
                  </div>
                  <div className="text-[9px] text-slate-400 mt-0.5">Defect Index</div>
                </div>
              </div>
            </div>

            {/* Liquid Level / Risk Gauge */}
            <div className="p-3.5 rounded-2xl bg-[#191b22] border border-white/[0.04] flex flex-col items-center relative overflow-hidden">
              <div className="w-full flex items-center justify-between text-[11px] text-slate-400 mb-1">
                <span>Accident Risk</span>
                <span className="text-[10px] font-bold text-amber-400 uppercase">74%</span>
              </div>

              <div className="relative w-20 h-20 rounded-full bg-[#101216] border border-white/10 flex items-center justify-center overflow-hidden my-1 shadow-inner">
                <div
                  className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-amber-600 to-amber-400 transition-all duration-500"
                  style={{ height: '74%' }}
                >
                  <div className="w-full h-2 bg-amber-300 opacity-60 rounded-full blur-[1px]"></div>
                </div>
                <div className="relative z-10 text-center text-white">
                  <div className="text-sm font-extrabold leading-none drop-shadow-md">
                    High
                  </div>
                  <div className="text-[9px] text-black font-semibold mt-0.5 px-1 rounded bg-amber-200">
                    74% Index
                  </div>
                </div>
              </div>

              <div className="text-[10px] text-slate-400 mt-1">Hazard Factor</div>
            </div>
          </div>

          {/* Traffic Alert Banner */}
          <div className="p-3 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center gap-2.5 text-xs text-amber-300">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
            <div className="leading-snug">
              <b>Traffic Alert:</b> Active lane divergence required for cold-mix compaction crews.
            </div>
          </div>

          {/* Action Link */}
          <Link
            to={`/track?id=${selectedPoint.inspection_id}`}
            className="w-full py-2.5 rounded-2xl bg-white hover:bg-slate-200 text-black text-xs font-bold transition-all flex items-center justify-center gap-2 shadow-lg"
          >
            <span>Open 7-Stage Progress Tracker</span>
            <ArrowUpRight className="w-4 h-4" />
          </Link>
        </div>
      )}
    </div>
  );
};
