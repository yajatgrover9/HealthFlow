from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.db.db import Base


class TaskStatus(str, Enum):
    pending = "pending"
    assigned = "assigned"
    in_progress = "in_progress"
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
        DateTime, default=datetime.now(), index=True
    )
    checked_out_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(), index=True
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
        SAEnum(
            TaskStatus,
            # IMPORTANT for Postgres: persist enum *values* (e.g. 'in_progress')
            # not enum *names* (e.g. 'in_progress' vs 'in_progress' can still
            # drift depending on defaults). This avoids InvalidTextRepresentation.
            values_callable=lambda e: [i.value for i in e],
            name="taskstatus",
            native_enum=True,
            create_constraint=False,
        ),
        default=TaskStatus.pending,
        index=True,
    )

    # Task-level timestamps (UTC)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
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


class AIInsight(Base):
    __tablename__ = "ai_insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)

    kind: Mapped[str] = mapped_column(String(64), index=True)  # e.g. 'patient_summary'
    prompt_version: Mapped[str] = mapped_column(String(32), default="v1", index=True)
    model: Mapped[str] = mapped_column(String(64), default="", index=True)

    input_json: Mapped[str] = mapped_column(Text, default="{}")
    output_text: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )

    patient: Mapped["Patient"] = relationship()
