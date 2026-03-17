import React, { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../services/api';
import type { AssignmentOut, StationFlowSnapshotOut, StationOut, StationStatusOut } from '../types';

export default function StationPage() {
  const params = useParams();
  const stationId = params.stationId ? Number(params.stationId) : null;

  const [stations, setStations] = useState<StationOut[]>([]);
  const [status, setStatus] = useState<StationStatusOut[]>([]);
  const [assignments, setAssignments] = useState<AssignmentOut[]>([]);
  const [snapshot, setSnapshot] = useState<StationFlowSnapshotOut | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const chosenStation = useMemo(
    () => (stationId ? stations.find((s) => s.id === stationId) : null),
    [stations, stationId]
  );

  const chosenStatus = useMemo(
    () => (stationId ? status.find((s) => s.station_id === stationId) : null),
    [status, stationId]
  );

  const chosenAssignment = useMemo(
    () => (stationId ? assignments.find((a) => a.station_id === stationId) : null),
    [assignments, stationId]
  );

  async function refresh() {
    const [st, ss] = await Promise.all([api.listStations(), api.stationStatus()]);
    setStations(st);
    setStatus(ss);

    if (stationId) {
      try {
        const snap = await api.stationFlowSnapshot(stationId);
        setSnapshot(snap);
      } catch {
        // snapshot is best-effort; keep old
      }
    }
  }

  async function refreshAssignments() {
    // recompute returns the latest assignments snapshot
    const a = await api.recompute();
    setAssignments(a);
    if (stationId) {
      try {
        const snap = await api.stationFlowSnapshot(stationId);
        setSnapshot(snap);
      } catch {
        // ignore
      }
    }
  }

  useEffect(() => {
    refresh().catch((e) => setError(String(e)));
    refreshAssignments().catch(() => undefined);
    const t = window.setInterval(() => {
      refresh().catch(() => undefined);
    }, 4000);
    return () => window.clearInterval(t);
  }, [stationId]);

  async function startAssigned() {
    if (!stationId) return;

    // Choose next patient from snapshot first (truth source), fallback to recompute list.
    const next = snapshot?.next ?? null;
    const fallback = chosenAssignment ? { patient_id: chosenAssignment.patient_id } : null;
    const patientId = next?.patient_id ?? fallback?.patient_id;
    if (!patientId) return;

    setBusy(true);
    setError(null);
    try {
      await api.startTask({ patient_id: patientId, station_id: stationId });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function completeCurrent() {
    if (!stationId) return;

    // Complete current in-progress patient if available; fallback to assigned patient.
    const current = snapshot?.current ?? null;
    const next = snapshot?.next ?? null;
    const fallback = chosenAssignment ? { patient_id: chosenAssignment.patient_id } : null;

    const patientId = current?.patient_id ?? next?.patient_id ?? fallback?.patient_id;
    if (!patientId) return;

    setBusy(true);
    setError(null);
    try {
      const a = await api.completeTask({ patient_id: patientId, station_id: stationId });
      setAssignments(a);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid">
      <section className="card">
        <h2>Station device</h2>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          {stations.map((s) => (
            <Link key={s.id} to={`/station/${s.id}`} className="chip">
              #{s.id} {s.name}
            </Link>
          ))}
        </div>

        {!stationId && (
          <div style={{ marginTop: 12, opacity: 0.8 }}>
            Pick a station above (each station tablet opens its own URL).
          </div>
        )}
      </section>

      {stationId && (
        <section className="card">
          <h2>
            Station #{stationId} {chosenStation ? `- ${chosenStation.name}` : ''}
          </h2>

          <div className="row" style={{ justifyContent: 'space-between' }}>
            <div>
              <div><b>Busy:</b> {chosenStatus?.busy ? 'YES' : 'NO'}</div>
              <div><b>Est. minutes to free:</b> {chosenStatus?.estimated_minutes_to_free ?? '-'} </div>
              <div><b>Queue length:</b> {chosenStatus?.queue_length ?? '-'} </div>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button disabled={busy} onClick={() => refreshAssignments()}>Recompute</button>
              <button disabled={busy} onClick={() => refresh()}>Refresh</button>
            </div>
          </div>

          <hr />

          <div>
            <h3>Now serving</h3>
            {snapshot?.current ? (
              <div>
                <div><b>patient_id:</b> {snapshot.current.patient_id}</div>
                <div><b>external_id:</b> {snapshot.current.patient_external_id ?? '-'}</div>
                <div><b>task_id:</b> {snapshot.current.task_id}</div>
              </div>
            ) : (
              <div style={{ opacity: 0.8 }}>No in-progress patient at this station.</div>
            )}

            <hr />

            <h3>Next patient (assigned)</h3>
            {snapshot?.next ? (
              <div>
                <div><b>patient_id:</b> {snapshot.next.patient_id}</div>
                <div><b>external_id:</b> {snapshot.next.patient_external_id ?? '-'}</div>
                <div><b>sequence:</b> {snapshot.next.sequence_no}</div>
                <div><b>task_id:</b> {snapshot.next.task_id}</div>
              </div>
            ) : chosenAssignment ? (
              <div>
                <div><b>patient_id:</b> {chosenAssignment.patient_id}</div>
                <div><b>external_id:</b> {chosenAssignment.patient_external_id}</div>
                <div><b>sequence:</b> {chosenAssignment.sequence_no}</div>
              </div>
            ) : (
              <div style={{ opacity: 0.8 }}>No assignment for this station yet.</div>
            )}

            <div className="row" style={{ marginTop: 12, gap: 8 }}>
              <button disabled={busy} onClick={startAssigned}>Start</button>
              <button disabled={busy} onClick={completeCurrent}>Complete</button>
            </div>
          </div>

          {error && <div className="error">{error}</div>}
        </section>
      )}
    </div>
  );
}
