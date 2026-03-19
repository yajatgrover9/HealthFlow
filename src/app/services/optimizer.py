from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from src.app.models import Patient, Station, TaskStatus, VisitTask

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def recompute_assignments(db: Session) -> list[dict]:
    """Assign one eligible pending task per active station using arrival-order fairness.

    Rules (MVP, production-safe):
    - We only assign tasks in `pending` state.
    - We never touch `in_progress` or `done` tasks.
    - We DO NOT blindly reset previously assigned tasks; that can corrupt station screens.
      Instead, recompute will only assign if station has no `assigned` and no `in_progress`.

    This keeps station UX stable and avoids races where a station loses its "next patient".
    """

    try:
        stations = (
            db.execute(select(Station).where(Station.active == 1)).scalars().all()
        )
        assignments: list[dict] = []

        for station in stations:
            station_id = int(getattr(station, "id"))
            existing = (
                db.execute(
                    select(VisitTask.id)
                    .where(
                        VisitTask.station_id == station_id,
                        VisitTask.status.in_(
                            [TaskStatus.assigned, TaskStatus.in_progress]
                        ),
                    )
                    .order_by(VisitTask.assigned_at.desc().nulls_last())
                )
                .scalars()
                .first()
            )
            if existing is not None:
                continue

            pending_tasks = (
                db.execute(
                    select(VisitTask)
                    .options(joinedload(VisitTask.patient))
                    .where(
                        VisitTask.station_id == station_id,
                        VisitTask.status == TaskStatus.pending,
                    )
                    .order_by(VisitTask.sequence_no.asc(), VisitTask.patient_id.asc())
                )
                .scalars()
                .all()
            )

            eligible = None
            for t in pending_tasks:
                pid = int(getattr(t, "patient_id"))
                seq = int(getattr(t, "sequence_no"))
                if _is_eligible(db, pid, seq):
                    eligible = t
                    break

            if eligible is None:
                continue

            eligible.status = TaskStatus.assigned
            eligible.assigned_at = _utcnow()

            assignments.append(
                {
                    "station_id": station_id,
                    "station_name": getattr(station, "name"),
                    "task_id": int(getattr(eligible, "id")),
                    "patient_id": int(getattr(eligible, "patient_id")),
                    "patient_external_id": getattr(
                        getattr(eligible, "patient"), "external_id", None
                    ),
                    "sequence_no": int(getattr(eligible, "sequence_no")),
                }
            )

        db.commit()
        logger.info("optimizer.recompute assignments=%s", len(assignments))
        return sorted(assignments, key=lambda a: (a["sequence_no"], a["patient_id"]))
    except Exception as e:  # noqa: BLE001
        logger.error("optimizer.recompute err=%s", e)
        raise


def _is_eligible(db: Session, patient_id: int, sequence_no: int) -> bool:
    try:
        if sequence_no == 1:
            return True
        prev = db.execute(
            select(VisitTask.status).where(
                VisitTask.patient_id == patient_id,
                VisitTask.sequence_no == sequence_no - 1,
            )
        ).scalar_one_or_none()
        return prev == TaskStatus.done
    except Exception as e:  # noqa: BLE001
        logger.error("optimizer.is_eligible err=%s", e)
        raise


def mark_task_done(db: Session, task: VisitTask) -> VisitTask:
    try:
        task.status = TaskStatus.done
        task.completed_at = _utcnow()

        pid = int(getattr(task, "patient_id"))
        patient = db.get(Patient, pid)

        if patient is not None and getattr(patient, "checked_out_at", None) is None:
            remaining = (
                db.execute(
                    select(VisitTask.id).where(
                        VisitTask.patient_id == pid,
                        VisitTask.status != TaskStatus.done,
                    )
                )
                .scalars()
                .first()
            )
            if remaining is None:
                patient.checked_out_at = _utcnow()
                logger.info("optimizer.checked_out patient_id=%s", pid)

        db.commit()
        db.refresh(task)
        if patient is not None:
            db.refresh(patient)
        return task
    except Exception as e:  # noqa: BLE001
        logger.error("optimizer.mark_task_done err=%s", e)
        raise


def next_arrival_order(db: Session) -> int:
    try:
        max_order = (
            db.execute(
                select(Patient.arrival_order).order_by(Patient.arrival_order.desc())
            )
            .scalars()
            .first()
        )
        return (max_order or 0) + 1
    except Exception as e:  # noqa: BLE001
        logger.error("optimizer.next_arrival_order err=%s", e)
        raise


def mark_patient_current_task_done(
    db: Session, patient_id: int, station_id: int | None = None
):
    try:
        q = select(VisitTask).where(
            VisitTask.patient_id == patient_id,
            VisitTask.status == TaskStatus.in_progress,
        )
        if station_id is not None:
            q = q.where(VisitTask.station_id == station_id)

        task = (
            db.execute(q.order_by(VisitTask.started_at.desc().nulls_last()))
            .scalars()
            .first()
        )

        if task is None:
            q2 = select(VisitTask).where(
                VisitTask.patient_id == patient_id,
                VisitTask.status == TaskStatus.assigned,
            )
            if station_id is not None:
                q2 = q2.where(VisitTask.station_id == station_id)
            task = (
                db.execute(q2.order_by(VisitTask.assigned_at.desc().nulls_last()))
                .scalars()
                .first()
            )

        if task is None:
            return None

        if (
            getattr(task, "status") == TaskStatus.assigned
            and getattr(task, "started_at", None) is None
        ):
            task.started_at = getattr(task, "assigned_at", None) or _utcnow()

        return mark_task_done(db, task)
    except Exception as e:  # noqa: BLE001
        logger.error("optimizer.complete_current err=%s", e)
        raise


def mark_patient_task_started(db: Session, patient_id: int, station_id: int):
    try:
        q = select(VisitTask).where(
            VisitTask.patient_id == patient_id,
            VisitTask.station_id == station_id,
            VisitTask.status == TaskStatus.assigned,
        )
        task = (
            db.execute(q.order_by(VisitTask.assigned_at.desc().nulls_last()))
            .scalars()
            .first()
        )
        if task is None:
            return None

        task.status = TaskStatus.in_progress
        task.started_at = _utcnow()
        db.commit()
        db.refresh(task)
        return task
    except Exception as e:  # noqa: BLE001
        logger.error("optimizer.start_task err=%s", e)
        raise
