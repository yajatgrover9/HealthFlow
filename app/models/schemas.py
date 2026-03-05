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
    task_id: int
