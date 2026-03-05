from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Patient, Station, TaskStatus, VisitTask


def recompute_assignments(db: Session) -> list[dict]:
    """Assign one eligible pending task per active station using arrival-order fairness."""
    stations = db.execute(select(Station).where(Station.active == 1)).scalars().all()

    # Reset assigned tasks that were not completed so recompute stays deterministic.
    assigned_tasks = (
        db.execute(select(VisitTask).where(VisitTask.status == TaskStatus.assigned))
        .scalars()
        .all()
    )
    for t in assigned_tasks:
        t.status = TaskStatus.pending
        t.assigned_at = None

    assignments: list[dict] = []
    for station in stations:
        pending_for_station = (
            db.execute(
                select(VisitTask)
                .options(joinedload(VisitTask.patient))
                .where(
                    VisitTask.station_id == station.id,
                    VisitTask.status == TaskStatus.pending,
                )
                .order_by(VisitTask.sequence_no.asc())
            )
            .scalars()
            .all()
        )

        eligible = None
        for task in pending_for_station:
            if _is_eligible(db, task.patient_id, task.sequence_no):
                eligible = task
                break

        if eligible is None:
            continue

        eligible.status = TaskStatus.assigned
        eligible.assigned_at = datetime.now()
        assignments.append(
            {
                "station_id": station.id,
                "station_name": station.name,
                "task_id": eligible.id,
                "patient_id": eligible.patient_id,
                "patient_external_id": eligible.patient.external_id,
                "sequence_no": eligible.sequence_no,
            }
        )

    db.commit()
    return sorted(assignments, key=lambda a: (a["sequence_no"], a["patient_id"]))


def _is_eligible(db: Session, patient_id: int, sequence_no: int) -> bool:
    if sequence_no == 1:
        return True
    previous_task = db.execute(
        select(VisitTask).where(
            VisitTask.patient_id == patient_id,
            VisitTask.sequence_no == sequence_no - 1,
        )
    ).scalar_one_or_none()
    return previous_task is not None and previous_task.status == TaskStatus.done


def mark_task_done(db: Session, task_id: int) -> VisitTask | None:
    task = db.get(VisitTask, task_id)
    if task is None:
        return None
    task.status = TaskStatus.done
    task.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return task


def next_arrival_order(db: Session) -> int:
    max_order = (
        db.execute(select(Patient.arrival_order).order_by(Patient.arrival_order.desc()))
        .scalars()
        .first()
    )
    return (max_order or 0) + 1
