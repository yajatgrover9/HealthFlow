import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.app.auth.security import require_api_key
from src.app.db.db import get_db
from src.app.models.models import Patient, TaskStatus, VisitTask
from src.app.models.schemas import (
    AssignmentOut,
    CompleteTaskIn,
    StartTaskIn,
    StationFlowSnapshotOut,
    TaskOut,
)
from src.app.services.flow_snapshot import station_flow_snapshot
from src.app.services.optimizer import (
    mark_patient_current_task_done,
    mark_patient_task_started,
    recompute_assignments,
)
from src.app.services.rerouter import auto_reroute_pending_tasks

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.post("/flow/recompute", response_model=list[AssignmentOut])
def recompute_flow(db: Session = Depends(get_db)):
    try:
        assignments = recompute_assignments(db)
        # run lightweight auto-reroute after base assignments
        auto_reroute_pending_tasks(db)
        logger.info("flow.recompute assignments=%s", len(assignments))
        return assignments
    except Exception as e:  # noqa: BLE001
        logger.error("flow.recompute err=%s", e)
        raise


@router.post("/flow/start")
def start_task(payload: StartTaskIn, db: Session = Depends(get_db)):
    logger.info(
        "flow.start requested patient_id=%s station_id=%s",
        payload.patient_id,
        payload.station_id,
    )
    try:
        started = mark_patient_task_started(db, payload.patient_id, payload.station_id)
        if started is None:
            logger.info(
                "flow.start not_found patient_id=%s station_id=%s",
                payload.patient_id,
                payload.station_id,
            )
            raise HTTPException(
                status_code=404, detail="no assigned task found to start"
            )

        task_id = int(getattr(started, "id"))
        logger.info("flow.start ok task_id=%s", task_id)
        return {"status": "started", "task_id": task_id}
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.error("flow.start err=%s", e)
        raise


@router.post("/flow/complete", response_model=list[AssignmentOut])
def complete_and_recompute(payload: CompleteTaskIn, db: Session = Depends(get_db)):
    logger.info(
        "flow.complete requested patient_id=%s station_id=%s",
        payload.patient_id,
        payload.station_id,
    )
    try:
        completed = mark_patient_current_task_done(
            db, payload.patient_id, payload.station_id
        )
        if completed is None:
            logger.info(
                "flow.complete not_found patient_id=%s station_id=%s",
                payload.patient_id,
                payload.station_id,
            )
            raise HTTPException(
                status_code=404, detail="no assigned task found for patient"
            )

        patient = db.get(Patient, payload.patient_id)
        if patient is not None and getattr(patient, "checked_out_at", None) is None:
            remaining = (
                db.execute(
                    select(VisitTask.id).where(
                        VisitTask.patient_id == payload.patient_id,
                        VisitTask.status != TaskStatus.done,
                    )
                )
                .scalars()
                .first()
            )
            if remaining is None:
                patient.checked_out_at = datetime.now(timezone.utc)
                db.commit()
                logger.info("patient.checked_out patient_id=%s", payload.patient_id)

        assignments = recompute_assignments(db)
        # run lightweight auto-reroute after recomputation
        auto_reroute_pending_tasks(db)
        logger.info("flow.complete ok new_assignments=%s", len(assignments))
        return assignments
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.error("flow.complete err=%s", e)
        raise


@router.get("/flow/tasks", response_model=list[TaskOut])
def list_tasks(db: Session = Depends(get_db)):
    try:
        tasks = (
            db.execute(select(VisitTask).order_by(VisitTask.id.asc())).scalars().all()
        )
        logger.info("flow.tasks count=%s", len(tasks))
        # Convert to dicts to keep status as string and avoid ORM typing issues
        out = []
        for t in tasks:
            status = getattr(getattr(t, "status"), "value", str(getattr(t, "status")))
            out.append(
                {
                    "id": int(getattr(t, "id")),
                    "patient_id": int(getattr(t, "patient_id")),
                    "station_id": int(getattr(t, "station_id")),
                    "sequence_no": int(getattr(t, "sequence_no")),
                    "status": status,
                    "created_at": getattr(t, "created_at"),
                    "assigned_at": getattr(t, "assigned_at"),
                    "started_at": getattr(t, "started_at"),
                    "completed_at": getattr(t, "completed_at"),
                }
            )
        return out
    except Exception as e:  # noqa: BLE001
        logger.error("flow.tasks err=%s", e)
        raise


@router.get("/flow/stations/{station_id}", response_model=StationFlowSnapshotOut)
def station_snapshot(station_id: int, db: Session = Depends(get_db)):
    try:
        snap = station_flow_snapshot(db, station_id)
        logger.info(
            "flow.station_snapshot station_id=%s busy=%s", station_id, snap.get("busy")
        )
        return snap
    except ValueError as e:
        logger.info("flow.station_snapshot not_found station_id=%s", station_id)
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        logger.error("flow.station_snapshot err=%s", e)
        raise
