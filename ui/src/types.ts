export type StationCreate = {
  name: string;
  avg_duration_min?: number;
};

export type StationOut = {
  id: number;
  name: string;
  avg_duration_min: number;
  active: number;
};

export type PatientCreate = {
  external_id: string;
  station_ids_in_order: number[];
};

export type PatientOut = {
  id: number;
  external_id: string;
  arrival_order: number;
  checked_in_at: string;
  checked_out_at: string | null;
};

export type AssignmentOut = {
  station_id: number;
  station_name: string;
  task_id: number;
  patient_id: number;
  patient_external_id: string;
  sequence_no: number;
};

export type StartTaskIn = {
  patient_id: number;
  station_id: number;
};

export type CompleteTaskIn = {
  patient_id: number;
  station_id?: number | null;
};

export type StationStatusOut = {
  station_id: number;
  station_name: string;
  active: number;
  busy: boolean;
  reserved?: boolean;
  current_task_id: number | null;
  next_task_id?: number | null;
  estimated_minutes_to_free: number;
  estimated_free_at: string | null;
  queue_length: number;
  estimated_queue_wait_min: number;
};

export type PatientSummaryGenerateIn = {
  report_text?: string | null;
  report_data?: Record<string, unknown> | null;
  language?: string;
  force_regenerate?: boolean;
};

export type AIInsightOut = {
  id: number;
  patient_id: number;
  kind: string;
  prompt_version: string;
  model: string;
  output_text: string;
  created_at: string;
};

export type StationTaskMini = {
  task_id: number;
  patient_id: number;
  patient_external_id: string | null;
  sequence_no: number;
  status: string;
};

export type StationFlowSnapshotOut = {
  station_id: number;
  station_name: string;
  busy: boolean;
  current: StationTaskMini | null;
  next: StationTaskMini | null;
};
