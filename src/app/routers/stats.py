from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.app.auth.security import require_api_key
from src.app.db.db import get_db
from src.app.models.models import Patient, Station, TaskStatus, VisitTask
from src.app.models.schemas import PatientsTodayOut

router = APIRouter(dependencies=[Depends(require_api_key)])


def _utc_today_bounds() -> tuple[datetime, datetime, str]:
    now = datetime.now(timezone.utc)
    start = datetime(year=now.year, month=now.month, day=now.day, tzinfo=timezone.utc)
    end = start.replace(hour=23, minute=59, second=59, microsecond=999999)
    return start, end, start.date().isoformat()


@router.get("/stats/today", response_model=PatientsTodayOut)
def stats_today(db: Session = Depends(get_db)):
    start, end, date_str = _utc_today_bounds()

    patients = (
        db.execute(
            select(Patient)
            .where(Patient.checked_in_at >= start, Patient.checked_in_at <= end)
            .order_by(Patient.checked_in_at.asc())
        )
        .scalars()
        .all()
    )

    rows = []
    for p in patients:
        tasks = (
            db.execute(
                select(VisitTask)
                .where(VisitTask.patient_id == p.id)
                .order_by(VisitTask.sequence_no.asc())
            )
            .scalars()
            .all()
        )

        station_ids = [t.station_id for t in tasks]
        stations = (
            db.execute(select(Station).where(Station.id.in_(station_ids)))
            .scalars()
            .all()
        )
        station_by_id = {s.id: s for s in stations}
        stations_in_order = [
            (
                station_by_id.get(t.station_id).name
                if station_by_id.get(t.station_id)
                else f"#{t.station_id}"
            )
            for t in tasks
        ]

        total = len(tasks)
        done = sum(1 for t in tasks if t.status == TaskStatus.done)
        pending = sum(1 for t in tasks if t.status == TaskStatus.pending)
        assigned = sum(1 for t in tasks if t.status == TaskStatus.assigned)
        in_progress = sum(1 for t in tasks if t.status == TaskStatus.in_progress)

        rows.append(
            {
                "patient_id": p.id,
                "external_id": p.external_id,
                "checked_in_at": p.checked_in_at,
                "checked_out_at": p.checked_out_at,
                "stations_in_order": stations_in_order,
                "total_tasks": total,
                "done_tasks": done,
                "pending_tasks": pending,
                "assigned_tasks": assigned,
                "in_progress_tasks": in_progress,
            }
        )

    checked_out = sum(1 for p in patients if p.checked_out_at is not None)
    return {
        "date": date_str,
        "total_patients": len(patients),
        "checked_out_patients": checked_out,
        "active_patients": len(patients) - checked_out,
        "rows": rows,
    }
