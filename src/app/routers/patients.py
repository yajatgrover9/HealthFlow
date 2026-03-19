import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.app.auth.security import require_api_key
from src.app.db.db import get_db
from src.app.models.models import Patient, Station, VisitTask
from src.app.models.schemas import PatientCreate, PatientOut
from src.app.services.optimizer import next_arrival_order, recompute_assignments

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.post("/patients", response_model=PatientOut)
def create_patient(payload: PatientCreate, db: Session = Depends(get_db)):
    try:
        existing_row = db.execute(
            select(Patient.id).where(Patient.external_id == payload.external_id)
        ).first()
        if existing_row is not None:
            logger.info("patients.create conflict external_id=%s", payload.external_id)
            raise HTTPException(
                status_code=409, detail="Patient external_id already exists"
            )

        stations = (
            db.execute(
                select(Station.id).where(Station.id.in_(payload.station_ids_in_order))
            )
            .scalars()
            .all()
        )
        if len(stations) != len(set(payload.station_ids_in_order)):
            logger.info(
                "patients.create invalid_station_ids external_id=%s",
                payload.external_id,
            )
            raise HTTPException(
                status_code=400, detail="One or more station_ids are invalid"
            )

        patient = Patient(
            external_id=payload.external_id,
            arrival_order=next_arrival_order(db),
            checked_out_at=None,
        )
        db.add(patient)
        db.flush()

        patient_id = int(getattr(patient, "id"))

        for idx, station_id in enumerate(payload.station_ids_in_order, start=1):
            db.add(
                VisitTask(
                    patient_id=patient_id, station_id=int(station_id), sequence_no=idx
                )
            )

        db.commit()
        db.refresh(patient)

        recompute_assignments(db)
        logger.info(
            "patients.create ok patient_id=%s external_id=%s",
            patient_id,
            payload.external_id,
        )
        return patient
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.error(
            "patients.create error external_id=%s err=%s", payload.external_id, e
        )
        raise


@router.get("/patients", response_model=list[PatientOut])
def list_patients(db: Session = Depends(get_db)):
    try:
        rows = (
            db.execute(select(Patient).order_by(Patient.arrival_order.asc()))
            .scalars()
            .all()
        )
        logger.info("patients.list count=%s", len(rows))
        return rows
    except Exception as e:  # noqa: BLE001
        logger.error("patients.list error=%s", e)
        raise
