from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import require_api_key
from app.db.db import get_db
from app.models.models import Station
from app.models.schemas import StationCreate, StationOut

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.post("/stations", response_model=StationOut)
def create_station(payload: StationCreate, db: Session = Depends(get_db)):
    existing = db.execute(
        select(Station).where(Station.name == payload.name)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Station name already exists")

    station = Station(name=payload.name, avg_duration_min=payload.avg_duration_min)
    db.add(station)
    db.commit()
    db.refresh(station)
    return station


@router.get("/stations", response_model=list[StationOut])
def list_stations(db: Session = Depends(get_db)):
    return db.execute(select(Station).order_by(Station.id.asc())).scalars().all()
