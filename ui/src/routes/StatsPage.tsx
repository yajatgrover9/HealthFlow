import React, { useEffect, useState } from 'react';
import { api } from '../services/api';

type PatientTodayRow = {
  patient_id: number;
  external_id: string;
  checked_in_at: string;
  checked_out_at: string | null;
  stations_in_order: string[];
  total_tasks: number;
  done_tasks: number;
  pending_tasks: number;
  assigned_tasks: number;
  in_progress_tasks: number;
};

type PatientsTodayOut = {
  date: string;
  total_patients: number;
  checked_out_patients: number;
  active_patients: number;
  rows: PatientTodayRow[];
};

export default function StatsPage() {
  const [data, setData] = useState<PatientsTodayOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    // lightweight: call backend directly through api.http wrapper isn't exported, so we add a tiny method here
    const res = await fetch(`${(import.meta.env.VITE_API_BASE_URL as string).replace(/\/$/, '')}/v1/stats/today`, {
      headers: {
        'content-type': 'application/json',
        'x-api-key': import.meta.env.VITE_API_KEY as string,
      },
    });
    if (!res.ok) {
      const txt = await res.text();
      throw new Error(`${res.status} ${res.statusText}: ${txt}`);
    }
    setData(await res.json());
  }

  useEffect(() => {
    refresh().catch((e) => setError(String(e)));
    const t = window.setInterval(() => {
      refresh().catch(() => undefined);
    }, 8000);
    return () => window.clearInterval(t);
  }, []);

  return (
    <section className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <div>
          <h2 style={{ margin: 0 }}>Today’s patients</h2>
          <div style={{ fontSize: 12, opacity: 0.8 }}>UTC date: {data?.date ?? '-'}</div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={() => refresh().catch((e) => setError(String(e)))}>Refresh</button>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      {data && (
        <div style={{ marginTop: 12 }}>
          <div className="row" style={{ alignItems: 'center' }}>
            <div><b>Total:</b> {data.total_patients}</div>
            <div><b>Active:</b> {data.active_patients}</div>
            <div><b>Checked out:</b> {data.checked_out_patients}</div>
          </div>

          <div style={{ marginTop: 12, overflowX: 'auto' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Ticket</th>
                  <th>Check-in</th>
                  <th>Check-out</th>
                  <th>Plan</th>
                  <th>Progress</th>
                </tr>
              </thead>
              <tbody>
                {data.rows.map((r) => {
                  const pct = r.total_tasks > 0 ? Math.round((r.done_tasks / r.total_tasks) * 100) : 0;
                  return (
                    <tr key={r.patient_id}>
                      <td>{r.patient_id}</td>
                      <td>{r.external_id}</td>
                      <td>{new Date(r.checked_in_at).toLocaleTimeString()}</td>
                      <td>{r.checked_out_at ? new Date(r.checked_out_at).toLocaleTimeString() : '-'}</td>
                      <td style={{ minWidth: 360 }}>
                        {r.stations_in_order.join(' → ')}
                      </td>
                      <td style={{ minWidth: 220 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <span>{r.done_tasks}/{r.total_tasks} done</span>
                          <span style={{ opacity: 0.75 }}>{pct}%</span>
                        </div>
                        <div style={{ height: 10, borderRadius: 999, background: 'rgba(15,23,42,0.08)', marginTop: 6 }}>
                          <div
                            style={{
                              height: 10,
                              borderRadius: 999,
                              width: `${pct}%`,
                              background: pct === 100 ? 'rgba(22,163,74,0.8)' : 'rgba(37,99,235,0.8)',
                            }}
                          />
                        </div>
                        <div style={{ fontSize: 12, opacity: 0.8, marginTop: 6 }}>
                          pending {r.pending_tasks} • assigned {r.assigned_tasks} • in_progress {r.in_progress_tasks}
                        </div>
                      </td>
                    </tr>
                  );
                })}
                {data.rows.length === 0 && (
                  <tr>
                    <td colSpan={6} style={{ opacity: 0.8 }}>No patients checked in today (UTC).</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}

