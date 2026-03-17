from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.app.models.models import Station, TaskStatus, VisitTask

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc_aware(dt: datetime | None) -> datetime | None:
    """Normalize DB datetimes to timezone-aware UTC.

    SQLite and some Postgres configurations can return naive datetimes.
    Our API uses UTC-aware 'now', so we normalize to avoid:
    TypeError: can't subtract offset-naive and offset-aware datetimes
    """

    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _is_eligible(db: Session, patient_id: int, sequence_no: int) -> bool:
    try:
        if sequence_no == 1:
            return True
        prev_status = db.execute(
            select(VisitTask.status).where(
                VisitTask.patient_id == patient_id,
                VisitTask.sequence_no == sequence_no - 1,
            )
        ).scalar_one_or_none()
        return prev_status == TaskStatus.done
    except Exception as e:  # noqa: BLE001
        logger.error("eta.is_eligible err=%s", e)
        raise


def station_status(db: Session) -> list[dict]:
    try:
        stations = (
            db.execute(
                select(Station).where(Station.active == 1).order_by(Station.id.asc())
            )
            .scalars()
            .all()
        )

        now = _utcnow()
        results: list[dict] = []

        for st in stations:
            st_id = int(getattr(st, "id"))

            in_progress_task = (
                db.execute(
                    select(VisitTask)
                    .where(
                        VisitTask.station_id == st_id,
                        VisitTask.status == TaskStatus.in_progress,
                    )
                    .order_by(VisitTask.started_at.desc().nulls_last())
                )
                .scalars()
                .first()
            )

            assigned_task = (
                db.execute(
                    select(VisitTask)
                    .where(
                        VisitTask.station_id == st_id,
                        VisitTask.status == TaskStatus.assigned,
                    )
                    .order_by(VisitTask.assigned_at.desc().nulls_last())
                )
                .scalars()
                .first()
            )

            busy = in_progress_task is not None
            current_task_id = (
                int(getattr(in_progress_task, "id"))
                if in_progress_task is not None
                else None
            )

            avg = int(getattr(st, "avg_duration_min", 0) or 0)
            remaining_min = 0
            free_at: datetime | None = None
            if busy and avg > 0:
                started_at = _as_utc_aware(
                    getattr(in_progress_task, "started_at", None)
                )
                if started_at is None:
                    remaining_min = avg
                else:
                    elapsed = (now - started_at).total_seconds() / 60.0
                    remaining_min = max(0, int(round(avg - elapsed)))
                free_at = now + timedelta(minutes=remaining_min)

            pending_tasks = (
                db.execute(
                    select(VisitTask)
                    .where(
                        VisitTask.station_id == st_id,
                        VisitTask.status == TaskStatus.pending,
                    )
                    .order_by(VisitTask.sequence_no.asc(), VisitTask.patient_id.asc())
                )
                .scalars()
                .all()
            )

            eligible_pending = []
            for t in pending_tasks:
                pid = int(getattr(t, "patient_id"))
                seq = int(getattr(t, "sequence_no"))
                if _is_eligible(db, pid, seq):
                    eligible_pending.append(t)

            reserved = 1 if assigned_task is not None else 0
            queue_len = reserved + len(eligible_pending)
            eta_queue_min = queue_len * avg

            results.append(
                {
                    "station_id": st_id,
                    "station_name": getattr(st, "name"),
                    "busy": busy,
                    "current_task_id": current_task_id,
                    "estimated_minutes_to_free": remaining_min if busy else 0,
                    "estimated_free_at": free_at,
                    "queue_length": queue_len,
                    "estimated_queue_wait_min": eta_queue_min,
                }
            )

        logger.info("eta.station_status count=%s", len(results))
        return results
    except Exception as e:  # noqa: BLE001
        logger.error("eta.station_status err=%s", e)
        raise
