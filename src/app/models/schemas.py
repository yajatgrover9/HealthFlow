from datetime import datetime

from pydantic import BaseModel, Field


class StationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    avg_duration_min: int = Field(default=10, ge=1, le=240)


class StationOut(BaseModel):
    id: int
    name: str
    avg_duration_min: int
    active: int

    class Config:
        from_attributes = True


class PatientCreate(BaseModel):
    external_id: str = Field(min_length=1, max_length=64)
    station_ids_in_order: list[int] = Field(min_length=1)


class PatientOut(BaseModel):
    id: int
    external_id: str
    arrival_order: int
    checked_in_at: datetime
    checked_out_at: datetime | None = None

    class Config:
        from_attributes = True


class TaskOut(BaseModel):
    id: int
    patient_id: int
    station_id: int
    sequence_no: int
    status: str

    created_at: datetime
    assigned_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    class Config:
        from_attributes = True


class AssignmentOut(BaseModel):
    station_id: int
    station_name: str
    task_id: int
    patient_id: int
    patient_external_id: str
    sequence_no: int


class CompleteTaskIn(BaseModel):
    patient_id: int
    station_id: int | None = None


class StationStatusOut(BaseModel):
    station_id: int
    station_name: str
    busy: bool
    current_task_id: int | None = None

    estimated_minutes_to_free: int
    estimated_free_at: datetime | None = None

    queue_length: int
    estimated_queue_wait_min: int


class StartTaskIn(BaseModel):
    patient_id: int
    station_id: int


class PatientSummaryGenerateIn(BaseModel):
    # In MVP we accept free-form notes or structured key-values.
    # Keep it flexible for integrations.
    report_text: str | None = Field(default=None, max_length=20000)
    report_data: dict | None = None
    language: str = Field(default="en", min_length=2, max_length=10)
    force_regenerate: bool = False


class AIInsightOut(BaseModel):
    id: int
    patient_id: int
    kind: str
    prompt_version: str
    model: str
    output_text: str
    created_at: datetime

    class Config:
        from_attributes = True


class StationTaskMini(BaseModel):
    task_id: int
    patient_id: int
    patient_external_id: str | None = None
    sequence_no: int
    status: str


class StationFlowSnapshotOut(BaseModel):
    station_id: int
    station_name: str
    busy: bool
    current: StationTaskMini | None = None
    next: StationTaskMini | None = None


class PatientTodayRow(BaseModel):
    patient_id: int
    external_id: str
    checked_in_at: datetime
    checked_out_at: datetime | None = None

    stations_in_order: list[str]

    total_tasks: int
    done_tasks: int
    pending_tasks: int
    assigned_tasks: int
    in_progress_tasks: int


class PatientsTodayOut(BaseModel):
    date: str  # YYYY-MM-DD (UTC)
    total_patients: int
    checked_out_patients: int
    active_patients: int
    rows: list[PatientTodayRow]
