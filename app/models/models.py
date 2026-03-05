from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.db import Base


class TaskStatus(str, Enum):
    pending = "pending"
    assigned = "assigned"
    done = "done"


class Station(Base):
    __tablename__ = "stations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    avg_duration_min: Mapped[int] = mapped_column(Integer, default=10)
    active: Mapped[int] = mapped_column(Integer, default=1)


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    external_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    arrival_order: Mapped[int] = mapped_column(Integer, index=True)

    # Check-in/Check-out timestamps (UTC)
    checked_in_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    checked_out_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True
    )

    tasks: Mapped[list["VisitTask"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )


class VisitTask(Base):
    __tablename__ = "visit_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id"), index=True)
    sequence_no: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[TaskStatus] = mapped_column(
        SAEnum(TaskStatus), default=TaskStatus.pending, index=True
    )

    # Task-level timestamps (UTC)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True
    )

    patient: Mapped[Patient] = relationship(back_populates="tasks")
    station: Mapped[Station] = relationship()
