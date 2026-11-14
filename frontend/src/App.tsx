import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import { AuthProvider } from './context/AuthContext';
import { MainLayout } from './layouts/MainLayout';

// Pages
import { Dashboard } from './pages/Dashboard';
import { ImageDetection } from './pages/ImageDetection';
import { VideoDetection } from './pages/VideoDetection';
import { VerificationQueue } from './pages/VerificationQueue';
import { DamageMap } from './pages/DamageMap';
import { WorkerPortal } from './pages/WorkerPortal';
import { StatusCheck } from './pages/StatusCheck';
import { DetectionHistory } from './pages/DetectionHistory';
import { Analytics } from './pages/Analytics';
import { AIEvaluation } from './pages/AIEvaluation';
import { Reports } from './pages/Reports';
import { Settings } from './pages/Settings';

export const App: React.FC = () => {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<MainLayout />}>
              <Route index element={<Dashboard />} />
              <Route path="image-detection" element={<ImageDetection />} />
              <Route path="video-detection" element={<VideoDetection />} />
              <Route path="verification" element={<VerificationQueue />} />
              <Route path="damage-map" element={<DamageMap />} />
              <Route path="worker" element={<WorkerPortal />} />
              <Route path="track" element={<StatusCheck />} />
              <Route path="history" element={<DetectionHistory />} />
              <Route path="analytics" element={<Analytics />} />
              <Route path="ai-evaluation" element={<AIEvaluation />} />
              <Route path="reports" element={<Reports />} />
              <Route path="settings" element={<Settings />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
};

export default App;
