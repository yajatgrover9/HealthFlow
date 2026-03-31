import React, { useEffect, useMemo, useState } from 'react';
import { api } from '../services/api';
import type { AIInsightOut, PatientOut, StationOut } from '../types';

export default function ReceptionPage() {
  const [stations, setStations] = useState<StationOut[]>([]);
  const [patients, setPatients] = useState<PatientOut[]>([]);
  const [externalId, setExternalId] = useState('P-001');
  const [selectedStationIds, setSelectedStationIds] = useState<number[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Summary modal state
  const [summaryOpen, setSummaryOpen] = useState(false);
  const [summaryPatient, setSummaryPatient] = useState<PatientOut | null>(null);
  const [summaryReportText, setSummaryReportText] = useState('');
  const [summaryBusy, setSummaryBusy] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [summaryResult, setSummaryResult] = useState<AIInsightOut | null>(null);

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

  const [patientsToday, setPatientsToday] = useState<PatientsTodayOut | null>(null);
  const [patientsTodayError, setPatientsTodayError] = useState<string | null>(null);
  const [statsFilterDate, setStatsFilterDate] = useState<string>('');

  const activePatients = useMemo(
    () => patients.filter((p) => p.checked_out_at == null),
    [patients]
  );

  async function refreshAll() {
    const [st, pt] = await Promise.all([api.listStations(), api.listPatients()]);
    setStations(st);
    setPatients(pt);
  }

  async function refreshPatientsToday() {
    try {
      setPatientsTodayError(null);
      const base = (import.meta.env.VITE_API_BASE_URL as string).replace(/\/$/, '');
      const res = await fetch(`${base}/v1/stats/today`, {
        headers: {
          'content-type': 'application/json',
          'x-api-key': import.meta.env.VITE_API_KEY as string,
        },
      });
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(`${res.status} ${res.statusText}: ${txt}`);
      }
      const data = (await res.json()) as PatientsTodayOut;
      setPatientsToday(data);
      // initialise filter date to today's date from backend
      setStatsFilterDate(data.date);
    } catch (e) {
      setPatientsTodayError(e instanceof Error ? e.message : String(e));
    }
  }

  useEffect(() => {
    refreshAll().catch((e) => setError(String(e)));
    refreshPatientsToday().catch(() => undefined);
  }, []);

  function toggleStation(id: number) {
    setSelectedStationIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  }

  async function checkIn() {
    setError(null);
    setBusy(true);
    try {
      if (!externalId.trim()) throw new Error('external_id is required');
      if (selectedStationIds.length === 0) throw new Error('Select at least 1 station');

      await api.createPatient({ external_id: externalId.trim(), station_ids_in_order: selectedStationIds });
      await api.recompute();
      await refreshAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  function openSummary(p: PatientOut) {
    setSummaryPatient(p);
    setSummaryReportText('');
    setSummaryError(null);
    setSummaryResult(null);
    setSummaryOpen(true);
  }

  async function generateSummary(forceRegenerate: boolean) {
    if (!summaryPatient) return;
    setSummaryBusy(true);
    setSummaryError(null);
    try {
      const res = await api.generatePatientSummary(summaryPatient.id, {
        report_text: summaryReportText.trim() ? summaryReportText.trim() : null,
        language: 'en',
        force_regenerate: forceRegenerate,
      });
      setSummaryResult(res);
    } catch (e) {
      setSummaryError(e instanceof Error ? e.message : String(e));
    } finally {
      setSummaryBusy(false);
    }
  }

  async function checkout(p: PatientOut) {
    setBusy(true);
    setError(null);
    try {
      await api.checkoutPatient(p.id);
      await refreshAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  // derive filtered rows (date filter is simple here because backend returns one date per call)
  const filteredTodayRows = useMemo(() => {
    if (!patientsToday) return [];
    if (!statsFilterDate || statsFilterDate === patientsToday.date) return patientsToday.rows;
    // if user changes date away from today, we currently have no historical API; return empty
    return [];
  }, [patientsToday, statsFilterDate]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {/* Top row: check-in (wider) + active patients (narrower) side by side */}
      <div className="grid" style={{ gridTemplateColumns: '4fr 2fr' }}>
        {/* Check-in section */}
        <section className="card">
          <h2>Reception: Check-in</h2>
          <div className="row">
            <label className="label">
              Patient external id
              <input value={externalId} onChange={(e) => setExternalId(e.target.value)} />
            </label>
          </div>

          <div>
            <div className="label" style={{ marginBottom: 8 }}>Select stations in order (click to add/remove)</div>
            <div className="chips">
              {stations.map((s) => {
                const active = selectedStationIds.includes(s.id);
                return (
                  <button
                    key={s.id}
                    type="button"
                    className={active ? 'chip chipActive' : 'chip'}
                    onClick={() => toggleStation(s.id)}
                  >
                    {s.name} ({s.avg_duration_min}m)
                  </button>
                );
              })}
            </div>
            <div style={{ marginTop: 8, fontSize: 12, opacity: 0.8 }}>
              Current order: {selectedStationIds.join(' → ') || '(none)'}
            </div>
          </div>

          <div className="row" style={{ marginTop: 12, gap: 8 }}>
            <button className="primaryBtn" disabled={busy} onClick={checkIn}>Check-in & recompute</button>
            <button disabled={busy} onClick={() => api.recompute().then(refreshAll)}>Recompute</button>
            <button disabled={busy} onClick={() => refreshAll()}>Refresh</button>
          </div>

          {error && <div className="error">{error}</div>}
        </section>

        {/* Active patients section */}
        <section className="card">
          <h2>Active patients</h2>
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>external_id</th>
                <th>checked_in_at</th>
                <th>checked_out_at</th>
                <th style={{ width: 260 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {activePatients.map((p) => (
                <tr key={p.id}>
                  <td>{p.id}</td>
                  <td>{p.external_id}</td>
                  <td>{new Date(p.checked_in_at).toLocaleString()}</td>
                  <td>{p.checked_out_at ? new Date(p.checked_out_at).toLocaleString() : '-'}</td>
                  <td>
                    <button onClick={() => openSummary(p)} disabled={busy}>Generate summary</button>
                    <button onClick={() => checkout(p)} disabled={busy} style={{ marginLeft: 8 }}>
                      Check-out
                    </button>
                  </td>
                </tr>
              ))}
              {activePatients.length === 0 && (
                <tr>
                  <td colSpan={5} style={{ opacity: 0.8 }}>No active patients</td>
                </tr>
              )}
            </tbody>
          </table>
        </section>
      </div>

      {/* Bottom row: stats full width */}
      <section className="card" style={{ width: '100%' }}>
        {/* Today’s patients stats section */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            gap: 12,
            flexWrap: 'wrap',
          }}
        >
          <div>
            <h2 style={{ margin: 0 }}>Today’s patients</h2>
            <div style={{ fontSize: 12, opacity: 0.8 }}>UTC date: {patientsToday?.date ?? '-'}</div>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <label style={{ fontSize: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
              <span>Date (UTC, today only):</span>
              <input
                type="date"
                value={statsFilterDate}
                onChange={(e) => setStatsFilterDate(e.target.value)}
                style={{ maxWidth: 150 }}
              />
            </label>
            <button onClick={() => refreshPatientsToday().catch(() => undefined)}>Refresh</button>
          </div>
        </div>

        {patientsTodayError && <div className="error">{patientsTodayError}</div>}

        <div style={{ marginTop: 4 }}>
          {patientsToday && (
            <div className="row" style={{ alignItems: 'center', marginBottom: 8 }}>
              <div><b>Total:</b> {patientsToday.total_patients}</div>
              <div><b>Active:</b> {patientsToday.active_patients}</div>
              <div><b>Checked out:</b> {patientsToday.checked_out_patients}</div>
            </div>
          )}

          <div style={{ marginTop: 4, overflowX: 'auto', minHeight: 140 }}>
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
                {filteredTodayRows.map((r) => {
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
                {filteredTodayRows.length === 0 && (
                  <tr>
                    <td colSpan={6} style={{ opacity: 0.8 }}>No patients for selected date.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* existing summary modal */}
      {summaryOpen && summaryPatient && (
        <div className="modalOverlay" role="dialog" aria-modal="true">
          <div className="modal">
            <div className="modalHeader">
              <div>
                <div style={{ fontSize: 16, fontWeight: 800 }}>Patient Summary</div>
                <div style={{ fontSize: 12, opacity: 0.8 }}>
                  Patient #{summaryPatient.id} • ticket: {summaryPatient.external_id}
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button className="ghostBtn" onClick={() => setSummaryOpen(false)} disabled={summaryBusy}>Close</button>
              </div>
            </div>

            <div className="modalBody">
              <div style={{ fontSize: 13, opacity: 0.85, marginBottom: 8 }}>
                Paste report text (optional). If empty, the summary will be generic until you integrate real lab values.
              </div>
              <textarea
                className="textarea"
                value={summaryReportText}
                onChange={(e) => setSummaryReportText(e.target.value)}
                placeholder="e.g., Total cholesterol 212 mg/dL, HDL 41 mg/dL, BP 138/88..."
              />

              <div className="row" style={{ marginTop: 12, gap: 8, alignItems: 'center' }}>
                <button
                  className="primaryBtn"
                  disabled={summaryBusy}
                  onClick={() => generateSummary(false)}
                >
                  {summaryBusy ? 'Generating…' : 'Generate'}
                </button>
                <button
                  disabled={summaryBusy}
                  onClick={() => generateSummary(true)}
                  title="Forces a new summary even if one is cached"
                >
                  Regenerate
                </button>
                {summaryResult && (
                  <div style={{ fontSize: 12, opacity: 0.75 }}>
                    model: {summaryResult.model} • {new Date(summaryResult.created_at).toLocaleString()}
                  </div>
                )}
              </div>

              {summaryError && <div className="error">{summaryError}</div>}

              {summaryResult && (
                <div style={{ marginTop: 14 }}>
                  <div style={{ fontWeight: 800, marginBottom: 8 }}>Generated summary</div>
                  <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>
                    {summaryResult.output_text}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

