import React from 'react';
import { Link, Navigate, Route, Routes } from 'react-router-dom';
import ReceptionPage from './ReceptionPage';
import StationPage from './StationPage';
import DisplayPage from './DisplayPage';

// Top-level app shell and route configuration for Reception, Station, and Display screens.
export default function App() {
  return (
    <div style={{ padding: 16, maxWidth: 1400, margin: '0 auto' }}>
      <header style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 32 }}>
        <h1 style={{ margin: 0, fontSize: 26 }}>HealthFlow</h1>
        <nav style={{ display: 'flex', gap: 12 }}>
          <Link to="/reception">Reception</Link>
          <Link to="/station">Station</Link>
          <Link to="/display">Display</Link>
        </nav>
      </header>

      {/* Route configuration: root redirects to /reception; /station and /station/:stationId share StationPage. */}
      <Routes>
        <Route path="/" element={<Navigate to="/reception" replace />} />
        <Route path="/reception" element={<ReceptionPage />} />
        <Route path="/station" element={<StationPage />} />
        <Route path="/station/:stationId" element={<StationPage />} />
        <Route path="/display" element={<DisplayPage />} />
      </Routes>
    </div>
  );
}
