from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import require_api_key
from app.db.db import get_db
from app.models.models import Patient, Station, VisitTask
from app.models.schemas import PatientCreate, PatientOut
from app.services.optimizer import next_arrival_order

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.post("/patients", response_model=PatientOut)
def create_patient(payload: PatientCreate, db: Session = Depends(get_db)):
    existing = db.execute(
        select(Patient).where(Patient.external_id == payload.external_id)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409, detail="Patient external_id already exists"
        )

    stations = (
        db.execute(select(Station).where(Station.id.in_(payload.station_ids_in_order)))
        .scalars()
        .all()
    )
    if len(stations) != len(set(payload.station_ids_in_order)):
        raise HTTPException(
            status_code=400, detail="One or more station_ids are invalid"
        )

    patient = Patient(
        external_id=payload.external_id, arrival_order=next_arrival_order(db)
    )
    db.add(patient)
    db.flush()

    for idx, station_id in enumerate(payload.station_ids_in_order, start=1):
        db.add(VisitTask(patient_id=patient.id, station_id=station_id, sequence_no=idx))

    db.commit()
    db.refresh(patient)
    return patient


@router.get("/patients", response_model=list[PatientOut])
def list_patients(db: Session = Depends(get_db)):
    return (
        db.execute(select(Patient).order_by(Patient.arrival_order.asc()))
        .scalars()
        .all()
    )
