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

  const activePatients = useMemo(
    () => patients.filter((p) => p.checked_out_at == null),
    [patients]
  );

  async function refreshAll() {
    const [st, pt] = await Promise.all([api.listStations(), api.listPatients()]);
    setStations(st);
    setPatients(pt);
  }

  useEffect(() => {
    refreshAll().catch((e) => setError(String(e)));
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

  return (
    <div className="grid">
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

      <section className="card">
        <h2>Active patients</h2>
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>external_id</th>
              <th>checked_in_at</th>
              <th>checked_out_at</th>
              <th style={{ width: 220 }}>Actions</th>
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
                  <button onClick={() => openSummary(p)}>Generate summary</button>
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

