import type {
  AssignmentOut,
  CompleteTaskIn,
  PatientCreate,
  PatientOut,
  StartTaskIn,
  StationCreate,
  StationOut,
  StationStatusOut,
  AIInsightOut,
  PatientSummaryGenerateIn,
  StationFlowSnapshotOut,
} from '../types';

const baseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '';
const apiKey = (import.meta.env.VITE_API_KEY as string | undefined) ?? '';

function url(path: string) {
  const b = baseUrl.replace(/\/$/, '');
  const p = path.startsWith('/') ? path : `/${path}`;
  return `${b}${p}`;
}

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  if (!baseUrl) {
    throw new Error('VITE_API_BASE_URL is not set. Copy ui/.env.example to ui/.env and configure it.');
  }
  if (!apiKey) {
    throw new Error('VITE_API_KEY is not set. Copy ui/.env.example to ui/.env and configure it.');
  }

  const res = await fetch(url(path), {
    ...init,
    headers: {
      'content-type': 'application/json',
      'x-api-key': apiKey,
      ...(init?.headers ?? {}),
    },
  });

  if (!res.ok) {
    let detail = '';
    try {
      const body = await res.json();
      detail = body?.detail ? `: ${body.detail}` : '';
    } catch {
      // ignore
    }
    throw new Error(`${res.status} ${res.statusText}${detail}`);
  }

  // Handle empty body
  const text = await res.text();
  return (text ? JSON.parse(text) : (undefined as unknown as T));
}

export const api = {
  // Stations
  listStations(): Promise<StationOut[]> {
    return http('/v1/stations');
  },
  createStation(payload: StationCreate): Promise<StationOut> {
    return http('/v1/stations', { method: 'POST', body: JSON.stringify(payload) });
  },
  stationStatus(): Promise<StationStatusOut[]> {
    return http('/v1/stations/status');
  },

  // Patients
  listPatients(): Promise<PatientOut[]> {
    return http('/v1/patients');
  },
  createPatient(payload: PatientCreate): Promise<PatientOut> {
    return http('/v1/patients', { method: 'POST', body: JSON.stringify(payload) });
  },

  // Flow
  recompute(): Promise<AssignmentOut[]> {
    return http('/v1/flow/recompute', { method: 'POST' });
  },
  startTask(payload: StartTaskIn): Promise<{ status: string; task_id: number }> {
    return http('/v1/flow/start', { method: 'POST', body: JSON.stringify(payload) });
  },
  completeTask(payload: CompleteTaskIn): Promise<AssignmentOut[]> {
    return http('/v1/flow/complete', { method: 'POST', body: JSON.stringify(payload) });
  },

  // Insights (GenAI)
  generatePatientSummary(patientId: number, payload: PatientSummaryGenerateIn): Promise<AIInsightOut> {
    return http(`/v1/insights/patients/${patientId}/summary`, {
      method: 'POST',
      body: JSON.stringify(payload ?? {}),
    });
  },

  // Station Flow Snapshot
  stationFlowSnapshot(stationId: number): Promise<StationFlowSnapshotOut> {
    return http(`/v1/flow/stations/${stationId}`);
  },
};
