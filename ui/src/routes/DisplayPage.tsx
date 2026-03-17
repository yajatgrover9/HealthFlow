import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { StationStatusOut } from '../types';

export default function DisplayPage() {
  const [status, setStatus] = useState<StationStatusOut[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    const s = await api.stationStatus();
    setStatus(s);
  }

  useEffect(() => {
    refresh().catch((e) => setError(String(e)));
    const t = window.setInterval(() => {
      refresh().catch(() => undefined);
    }, 3000);
    return () => window.clearInterval(t);
  }, []);

  return (
    <section className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <h2 style={{ margin: 0 }}>Patient Display</h2>
        <div style={{ opacity: 0.8, fontSize: 12 }}>Auto-refresh every 3s</div>
      </div>

      {error && <div className="error">{error}</div>}

      <div className="cards">
        {status.map((s) => (
          <div key={s.station_id} className="card" style={{ minWidth: 240 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontSize: 18, fontWeight: 700 }}>{s.station_name}</div>
                <div style={{ opacity: 0.9 }}>Station #{s.station_id}</div>
              </div>
              <div className={s.busy ? 'badge badgeBusy' : 'badge badgeFree'}>
                {s.busy ? 'BUSY' : 'FREE'}
              </div>
            </div>

            <div style={{ marginTop: 12 }}>
              <div><b>Minutes to free:</b> {s.estimated_minutes_to_free}</div>
              <div><b>Queue length:</b> {s.queue_length}</div>
              <div><b>Est. queue wait:</b> {s.estimated_queue_wait_min} min</div>
            </div>
          </div>
        ))}
        {status.length === 0 && <div style={{ opacity: 0.8 }}>No stations yet.</div>}
      </div>
    </section>
  );
}

