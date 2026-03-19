import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.app.core.config import settings
from src.app.db.db import Base, engine
from src.app.db.migrations import (
    ensure_taskstatus_enum,
    fix_patient_checked_out_default,
)
from src.app.routers import flow, insights, patients, stations, stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d) - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")

    # Keep DB enum types consistent (dev/MVP). In production, use Alembic.
    ensure_taskstatus_enum(engine, schema=settings.DB_SCHEMA)

    # Fix earlier MVP bug where patients were immediately checked out.
    fix_patient_checked_out_default(engine)

    # MVP convenience: auto-create tables.
    Base.metadata.create_all(bind=engine)

    logger.info("DB initialized successfully.")
    yield
    logger.info("Shutting down...")


app = FastAPI(title=settings.APP_NAME, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,  # type: ignore[arg-type]
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(stations.router, prefix="/v1", tags=["stations"])
app.include_router(patients.router, prefix="/v1", tags=["patients"])
app.include_router(flow.router, prefix="/v1", tags=["flow"])
app.include_router(insights.router, prefix="/v1", tags=["insights"])
app.include_router(stats.router, prefix="/v1", tags=["stats"])
