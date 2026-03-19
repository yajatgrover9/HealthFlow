import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.app.auth.security import require_api_key
from src.app.db.db import get_db
from src.app.models.models import Station
from src.app.models.schemas import StationCreate, StationOut, StationStatusOut
from src.app.services.eta import station_status

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.post("/stations", response_model=StationOut)
def create_station(payload: StationCreate, db: Session = Depends(get_db)):
    try:
        existing_row = db.execute(
            select(Station.id).where(Station.name == payload.name)
        ).first()
        if existing_row is not None:
            logger.info("stations.create conflict name=%s", payload.name)
            raise HTTPException(status_code=409, detail="Station name already exists")

        station = Station(name=payload.name, avg_duration_min=payload.avg_duration_min)
        db.add(station)
        db.commit()
        db.refresh(station)
        logger.info(
            "stations.create ok station_id=%s name=%s",
            int(getattr(station, "id")),
            getattr(station, "name"),
        )
        return station
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.error("stations.create error name=%s err=%s", payload.name, e)
        raise


@router.get("/stations", response_model=list[StationOut])
def list_stations(db: Session = Depends(get_db)):
    try:
        rows = db.execute(select(Station).order_by(Station.id.asc())).scalars().all()
        logger.info("stations.list count=%s", len(rows))
        return rows
    except Exception as e:  # noqa: BLE001
        logger.error("stations.list error=%s", e)
        raise


@router.get("/stations/status", response_model=list[StationStatusOut])
def list_station_status(db: Session = Depends(get_db)):
    try:
        rows = station_status(db)
        logger.info("stations.status count=%s", len(rows))
        return rows
    except Exception as e:  # noqa: BLE001
        logger.error("stations.status error=%s", e)
        raise
