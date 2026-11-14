import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import { MainLayout } from './layouts/MainLayout';

// Pages
import { LandingPage } from './pages/LandingPage';
import { CitizenDashboard } from './pages/dashboards/CitizenDashboard';
import { AuthorityDashboard } from './pages/dashboards/AuthorityDashboard';
import { ContractorDashboard } from './pages/dashboards/ContractorDashboard';
import { ImageDetection } from './pages/ImageDetection';
import { VideoDetection } from './pages/VideoDetection';
import { VerificationQueue } from './pages/VerificationQueue';
import { DamageMap } from './pages/DamageMap';
import { StatusCheck } from './pages/StatusCheck';
import { DetectionHistory } from './pages/DetectionHistory';
import { Analytics } from './pages/Analytics';
import { AIEvaluation } from './pages/AIEvaluation';
import { Reports } from './pages/Reports';
import { Settings } from './pages/Settings';

const DashboardRedirect: React.FC = () => {
  const { role } = useAuth();
  if (role === 'citizen') return <Navigate to="/citizen" replace />;
  if (role === 'worker') return <Navigate to="/contractor" replace />;
  return <Navigate to="/authority" replace />;
};

export const App: React.FC = () => {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* 1. Dedicated Landing Page with Persona Portal Selection */}
            <Route path="/" element={<LandingPage />} />

            {/* 2. Main Operational Layout for Dedicated Dashboards */}
            <Route element={<MainLayout />}>
              <Route path="dashboard" element={<DashboardRedirect />} />
              <Route path="citizen" element={<CitizenDashboard />} />
              <Route path="authority" element={<AuthorityDashboard />} />
              <Route path="contractor" element={<ContractorDashboard />} />
              <Route path="worker" element={<Navigate to="/contractor" replace />} />

              {/* Dedicated Core Modules */}
              <Route path="damage-map" element={<DamageMap />} />
              <Route path="track" element={<StatusCheck />} />
              <Route path="verification" element={<VerificationQueue />} />
              <Route path="image-detection" element={<ImageDetection />} />
              <Route path="video-detection" element={<VideoDetection />} />
              <Route path="history" element={<DetectionHistory />} />
              <Route path="analytics" element={<Analytics />} />
              <Route path="ai-evaluation" element={<AIEvaluation />} />
              <Route path="reports" element={<Reports />} />
              <Route path="settings" element={<Settings />} />

              {/* Fallback */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
};

export default App;
