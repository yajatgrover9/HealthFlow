from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.app.models.models import Patient, Station, TaskStatus, VisitTask

logger = logging.getLogger(__name__)


def station_flow_snapshot(db: Session, station_id: int) -> dict:
    """Return station runtime snapshot: busy/current task and next assigned."""

    try:
        station = db.get(Station, station_id)
        if station is None:
            logger.info("flow_snapshot.not_found station_id=%s", station_id)
            raise ValueError("station not found")

        in_progress = (
            db.execute(
                select(VisitTask)
                .where(
                    VisitTask.station_id == station_id,
                    VisitTask.status == TaskStatus.in_progress,
                )
                .order_by(VisitTask.started_at.desc().nulls_last())
            )
            .scalars()
            .first()
        )

        assigned = (
            db.execute(
                select(VisitTask)
                .where(
                    VisitTask.station_id == station_id,
                    VisitTask.status == TaskStatus.assigned,
                )
                .order_by(VisitTask.assigned_at.desc().nulls_last())
            )
            .scalars()
            .first()
        )

        def _task_to_dict(task) -> dict | None:
            if task is None:
                return None
            patient = db.get(Patient, int(getattr(task, "patient_id")))
            status = getattr(task, "status")
            status_str = getattr(status, "value", str(status))
            return {
                "task_id": int(getattr(task, "id")),
                "patient_id": int(getattr(task, "patient_id")),
                "patient_external_id": (
                    getattr(patient, "external_id", None) if patient else None
                ),
                "sequence_no": int(getattr(task, "sequence_no")),
                "status": status_str,
            }

        snap = {
            "station_id": int(getattr(station, "id")),
            "station_name": getattr(station, "name"),
            "busy": in_progress is not None,
            "current": _task_to_dict(in_progress),
            "next": _task_to_dict(assigned),
        }
        logger.info("flow_snapshot.ok station_id=%s busy=%s", station_id, snap["busy"])
        return snap
    except Exception as e:  # noqa: BLE001
        logger.error("flow_snapshot.error station_id=%s err=%s", station_id, e)
        raise
