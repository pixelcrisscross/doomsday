import React, { useEffect, useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import { MapContainer, TileLayer, Marker, Popup, Circle, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import {
  MapPin,
  Flame,
  Layers,
  Compass,
  Plus,
  Minus,
  RotateCcw,
  Maximize2,
  X,
  Clock,
  AlertTriangle,
  HardHat,
  ChevronRight,
  Shield,
  Activity,
  ArrowUpRight,
  Filter
} from 'lucide-react';

import { api } from '../services/api';
import { DamageMapPoint, HeatmapPoint, CityPotholeSummary } from '../types';

// Custom Map Controller to hook into zoom/pan actions from HUD buttons
const MapController: React.FC<{ center: [number, number]; zoom: number }> = ({ center, zoom }) => {
  const map = useMap();
  useEffect(() => {
    map.setView(center, zoom);
  }, [center, zoom, map]);
  return null;
};

// Vibrant Thermographic Color Gradient Palette
const VIBRANT_SEV_COLORS: Record<string, { core: string; halo: string; label: string }> = {
  CRITICAL: { core: '#ff0055', halo: 'rgba(255, 0, 85, 0.35)', label: 'Critical' },
  SEVERE: { core: '#ff8800', halo: 'rgba(255, 136, 0, 0.32)', label: 'Severe' },
  MODERATE: { core: '#d4f933', halo: 'rgba(212, 249, 51, 0.28)', label: 'Moderate' },
  MINOR: { core: '#00f0ff', halo: 'rgba(0, 240, 255, 0.25)', label: 'Minor' },
  NONE: { core: '#71717a', halo: 'rgba(113, 113, 122, 0.2)', label: 'None' }
};

// Custom Vibrant Glowing Marker
const createGlowingMarker = (color: string, isCritical = false) => {
  return L.divIcon({
    className: 'custom-map-marker',
    html: `
      <div style="position: relative; width: 22px; height: 22px; display: flex; align-items: center; justify-content: center;">
        <div style="position: absolute; width: 100%; height: 100%; border-radius: 50%; background-color: ${color}; opacity: 0.35; ${isCritical ? 'animation: neonPulse 2s infinite;' : ''}"></div>
        <div style="width: 12px; height: 12px; border-radius: 50%; background-color: ${color}; border: 2px solid #ffffff; box-shadow: 0 0 10px ${color};"></div>
      </div>
    `,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  });
};

export const DamageMap: React.FC = () => {
  const [points, setPoints] = useState<DamageMapPoint[]>([]);
  const [heatmapPoints, setHeatmapPoints] = useState<HeatmapPoint[]>([]);
  const [cityStats, setCityStats] = useState<CityPotholeSummary | null>(null);
  const [loading, setLoading] = useState(true);

  // Map state
  const [mapZoom, setMapZoom] = useState(13);
  const [mapCenter, setMapCenter] = useState<[number, number]>([12.9716, 77.5946]);
  const [viewMode, setViewMode] = useState<'pins' | 'heatmap'>('heatmap');
  const [selectedSeverity, setSelectedSeverity] = useState('ALL');

  // Floating HUD Telemetry Card State (Mirroring HAULIX card)
  const [selectedPoint, setSelectedPoint] = useState<DamageMapPoint | null>(null);
  const [hudCardOpen, setHudCardOpen] = useState(true);

  useEffect(() => {
    const fetchMapData = async () => {
      try {
        const [pts, heat, stats] = await Promise.all([
          api.getDamagePoints(),
          api.getHeatmapPoints(),
          api.getCityStats('Bengaluru Urban')
        ]);
        setPoints(pts);
        setHeatmapPoints(heat);
        setCityStats(stats);

        if (pts.length > 0) {
          setMapCenter([pts[0].latitude, pts[0].longitude]);
          setSelectedPoint(pts[0]);
        }
      } catch (err) {
        console.error('Failed to load damage map:', err);
      } finally {
        setLoading(false);
      }
    };
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

  // Severity Gauge Calculation (-135deg to +135deg)
  const getSpeedometerAngle = (score: number) => {
    const clamped = Math.max(0, Math.min(100, score));
    return -135 + (clamped / 100) * 270;
  };

  const activeSevScore = selectedPoint?.severity_score ? Math.round(selectedPoint.severity_score * 100) : 78;
  const needleAngle = getSpeedometerAngle(activeSevScore);

  return (
    <div className="relative w-full h-[calc(100vh-6rem)] rounded-3xl overflow-hidden border border-white/[0.08] shadow-2xl bg-[#0c0d10]">
      {/* 1. Leaflet Interactive Map Canvas */}
      {loading ? (
        <div className="flex h-full w-full items-center justify-center text-xs text-slate-400 bg-[#0c0d10]">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-[#d4f933] animate-ping"></span>
            Loading CartoDB Dark Matter GIS canvas...
          </div>
        </div>
      ) : (
        <MapContainer
          center={mapCenter}
          zoom={mapZoom}
          zoomControl={false}
          scrollWheelZoom={true}
          className="h-full w-full bg-[#0c0d10]"
        >
          <MapController center={mapCenter} zoom={mapZoom} />

          {/* CartoDB Dark Matter Tiles (high-contrast roads & structures) */}
          <TileLayer
            attribution='&copy; <a href="https://carto.com/">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          />

          {/* Simulated Contractor Fleet Dispatch Route (like in Haulix image) */}
          {points.length >= 2 && (
            <Polyline
              positions={[
                [points[0].latitude, points[0].longitude],
                [points[0].latitude + 0.008, points[0].longitude + 0.006],
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

          {/* VIEW MODE 1: Standard Individual Markers */}
          {viewMode === 'pins' && filteredPoints.map((pt) => {
            const isCrit = pt.overall_severity === 'CRITICAL';
            const colors = VIBRANT_SEV_COLORS[pt.overall_severity] || VIBRANT_SEV_COLORS.MINOR;
            return (
              <Marker
                key={pt.inspection_id}
                position={[pt.latitude, pt.longitude]}
                icon={createGlowingMarker(colors.core, isCrit)}
                eventHandlers={{
                  click: () => {
                    setSelectedPoint(pt);
                    setHudCardOpen(true);
                  }
                }}
              >
                <Popup className="dark-popup">
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

          {/* VIEW MODE 2: Vibrant Thermographic Heatmap Overlay */}
          {viewMode === 'heatmap' && heatmapPoints.map((hp, i) => {
            const colors = VIBRANT_SEV_COLORS[hp.severity] || VIBRANT_SEV_COLORS.MINOR;
            const baseRadius = 45 + hp.weight * 60; // 45m - 105m radius

            return (
              <React.Fragment key={`vibrant-heat-${i}`}>
                {/* Outermost atmospheric halo */}
                <Circle
                  center={[hp.latitude, hp.longitude]}
                  radius={baseRadius * 1.8}
                  pathOptions={{
                    color: 'transparent',
                    fillColor: colors.core,
                    fillOpacity: 0.16,
                    weight: 0
                  }}
                />
                {/* Secondary chromatic ring */}
                <Circle
                  center={[hp.latitude, hp.longitude]}
                  radius={baseRadius * 1.3}
                  pathOptions={{
                    color: 'transparent',
                    fillColor: colors.core,
                    fillOpacity: 0.32,
                    weight: 0
                  }}
                />
                {/* High-intensity dense epicenter */}
                <Circle
                  center={[hp.latitude, hp.longitude]}
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
      )}

      {/* 2. Top-Right: Realistic HUD Compass Rose Widget (Mirroring HAULIX Image 1-4) */}
      <div className="absolute top-5 right-5 z-20 pointer-events-none select-none">
        <div className="w-24 h-24 sm:w-28 sm:h-28 rounded-full compass-ring flex items-center justify-center relative p-1">
          {/* Compass outer bezel markings */}
          <div className="absolute inset-1 rounded-full border border-white/10 flex items-center justify-center">
            {/* Cardinal direction labels */}
            <span className="absolute top-1 text-[9px] font-extrabold text-white">N</span>
            <span className="absolute right-1.5 text-[9px] font-extrabold text-slate-400">E</span>
            <span className="absolute bottom-1 text-[9px] font-extrabold text-slate-400">S</span>
            <span className="absolute left-1.5 text-[9px] font-extrabold text-slate-400">W</span>

            {/* Intercardinal tick marks */}
            <span className="absolute top-3 right-3 text-[7px] font-mono text-slate-500">NE</span>
            <span className="absolute bottom-3 right-3 text-[7px] font-mono text-slate-500">SE</span>
            <span className="absolute bottom-3 left-3 text-[7px] font-mono text-slate-500">SW</span>
            <span className="absolute top-3 left-3 text-[8px] font-extrabold text-[#d4f933] drop-shadow-[0_0_6px_#d4f933]">NW</span>
          </div>

          {/* Compass Needle (rotated towards NW ~315 deg) */}
          <div className="relative w-full h-full flex items-center justify-center rotate-[-45deg] transition-transform duration-700">
            {/* North pointing needle (bright lime/orange) */}
            <div className="absolute top-3 w-1.5 h-9 bg-gradient-to-t from-white to-[#ff5500] rounded-t-full shadow-[0_0_8px_#ff5500]"></div>
            {/* South pointing needle (dark silver) */}
            <div className="absolute bottom-3 w-1.5 h-9 bg-gradient-to-b from-white to-slate-600 rounded-b-full"></div>
            {/* Center Hub */}
            <div className="w-3.5 h-3.5 rounded-full bg-[#181a20] border-2 border-white/40 shadow-inner z-10"></div>
          </div>
        </div>
      </div>

      {/* 3. Bottom-Right: Vertical Glass Map Controls Pill (Mirroring HAULIX Image 1-4) */}
      <div className="absolute bottom-6 right-5 z-20 flex flex-col items-center gap-1.5 p-1.5 rounded-2xl bg-[#14161b]/90 border border-white/10 backdrop-blur-xl shadow-2xl">
        <button
          onClick={() => setViewMode(viewMode === 'pins' ? 'heatmap' : 'pins')}
          className={`w-9 h-9 rounded-xl flex items-center justify-center transition-colors ${
            viewMode === 'heatmap' ? 'bg-[#d4f933] text-black font-bold' : 'text-slate-300 hover:bg-white/10'
          }`}
          title="Toggle Heatmap"
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
      </div>

      {/* 4. Bottom-Left: Heatmap Color Legend Bar */}
      <div className="absolute bottom-6 left-6 z-20 hidden md:flex items-center gap-3 px-4 py-2 rounded-2xl bg-[#14161b]/90 border border-white/10 backdrop-blur-xl shadow-2xl text-xs">
        <span className="font-semibold text-slate-300 flex items-center gap-1.5">
          <Flame className="w-3.5 h-3.5 text-[#ff0055]" /> Thermographic Density:
        </span>
        <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <span className="w-2.5 h-2.5 rounded-full bg-[#00f0ff] shadow-[0_0_6px_#00f0ff]"></span>
          <span>Minor</span>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <span className="w-2.5 h-2.5 rounded-full bg-[#d4f933] shadow-[0_0_6px_#d4f933]"></span>
          <span>Moderate</span>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <span className="w-2.5 h-2.5 rounded-full bg-[#ff8800] shadow-[0_0_6px_#ff8800]"></span>
          <span>Severe</span>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <span className="w-2.5 h-2.5 rounded-full bg-[#ff0055] shadow-[0_0_6px_#ff0055]"></span>
          <span className="text-[#ff0055] font-bold">Critical</span>
        </div>
      </div>

      {/* 5. Left Floating HUD Telemetry Card (Directly mirroring HAULIX Image 1-4) */}
      {hudCardOpen && selectedPoint && (
        <div className="absolute top-5 left-5 z-20 w-[360px] sm:w-[410px] max-w-[calc(100%-2.5rem)] rounded-3xl bg-[#14161b]/95 border border-white/10 shadow-[0_16px_48px_rgba(0,0,0,0.8)] backdrop-blur-2xl p-5 space-y-4 animate-in fade-in slide-in-from-top-2 duration-200">
          {/* Card Header (Vehicle / Inspection ID + Model info + Close) */}
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-3">
              {/* Vehicle / Hazard Icon container */}
              <div className="w-12 h-12 rounded-2xl bg-[#1e2129] border border-white/10 flex items-center justify-center text-white shrink-0 shadow-inner">
                <HardHat className="w-6 h-6 text-[#d4f933]" />
              </div>

              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm font-bold text-white tracking-tight">
                    #{selectedPoint.inspection_id}
                  </span>
                  <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-[#d4f933] text-black">
                    Active
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

          {/* Route & Progress Bar (Mirroring "Dallas, TX -> Memphis, TN, 282.1 mi 72%") */}
          <div className="p-3.5 rounded-2xl bg-[#191b22] border border-white/[0.04] space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-200 truncate max-w-[220px]">
                {selectedPoint.location_name}
              </span>
              <span className="font-mono font-bold text-slate-300">
                4.2 km <span className="text-[#d4f933]">72%</span>
              </span>
            </div>

            {/* Glowing progress line */}
            <div className="w-full bg-[#101216] h-1.5 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-amber-400 to-[#d4f933] rounded-full w-[72%] shadow-[0_0_8px_#d4f933]"></div>
            </div>

            <div className="flex items-center justify-between text-[11px] text-slate-400 pt-0.5">
              <span className="flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-slate-400" /> Est. Completion: <b>~45m</b>
              </span>
              <span>1.8 km to depot</span>
            </div>
          </div>

          {/* Dual HUD Dials: Speedometer / Severity Gauge + Liquid Risk / Fuel Level (Image 1-4) */}
          <div className="grid grid-cols-2 gap-3">
            {/* DIAL 1: Visual Speedometer / Severity Gauge */}
            <div className="p-3.5 rounded-2xl bg-[#191b22] border border-white/[0.04] flex flex-col items-center relative overflow-hidden">
              <div className="w-full flex items-center justify-between text-[11px] text-slate-400 mb-1">
                <span>Severity</span>
                <span className="text-[10px] font-bold text-rose-500 uppercase">High</span>
              </div>

              {/* Curved SVG Speedometer Dial */}
              <div className="relative w-32 h-24 flex items-center justify-center">
                <svg viewBox="0 0 120 90" className="w-full h-full overflow-visible">
                  {/* Gauge Arc Track */}
                  <path
                    d="M 20 80 A 45 45 0 1 1 100 80"
                    fill="none"
                    stroke="#22252e"
                    strokeWidth="8"
                    strokeLinecap="round"
                  />
                  {/* Gauge Gradient Color Fill Arc */}
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

                  {/* Needle Pointer */}
                  <g transform={`rotate(${needleAngle} 60 75)`} className="transition-transform duration-500 ease-out">
                    <line x1="60" y1="75" x2="60" y2="35" stroke="#ffffff" strokeWidth="2.5" strokeLinecap="round" />
                    <circle cx="60" cy="75" r="4" fill="#ffffff" />
                  </g>
                </svg>

                {/* Score Text in Center */}
                <div className="absolute bottom-1 text-center">
                  <div className="text-base font-extrabold text-white leading-none">
                    {activeSevScore}%
                  </div>
                  <div className="text-[9px] text-slate-400 mt-0.5">Defect Index</div>
                </div>
              </div>
            </div>

            {/* DIAL 2: Liquid Level / Accident Risk Gauge (Image 1-4) */}
            <div className="p-3.5 rounded-2xl bg-[#191b22] border border-white/[0.04] flex flex-col items-center relative overflow-hidden">
              <div className="w-full flex items-center justify-between text-[11px] text-slate-400 mb-1">
                <span>Accident Risk</span>
                <span className="text-[10px] font-bold text-amber-400 uppercase">74%</span>
              </div>

              {/* Liquid Wave Tank Circle */}
              <div className="relative w-20 h-20 rounded-full bg-[#101216] border border-white/10 flex items-center justify-center overflow-hidden my-1 shadow-inner">
                {/* Yellow/Amber Liquid Wave Reservoir */}
                <div
                  className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-amber-600 to-amber-400 transition-all duration-500"
                  style={{ height: '74%' }}
                >
                  {/* Subtle top ripple curve */}
                  <div className="w-full h-2 bg-amber-300 opacity-60 rounded-full blur-[1px]"></div>
                </div>

                {/* Dial Value Center Text */}
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

          {/* Bottom Alert Banner (Image 1-4 "Required Break: 30 min...") */}
          <div className="p-3 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center gap-2.5 text-xs text-amber-300">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
            <div className="leading-snug">
              <b>Traffic Alert:</b> Active lane divergence required for cold-mix compaction crews.
            </div>
          </div>

          {/* Action Link to Full 7-Stage Audit Stepper */}
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
