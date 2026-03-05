import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.db import Base, engine
from app.routers import flow, patients, stations

app = FastAPI(title=settings.app_name, version="0.1.0")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d) - %(message)s",
)
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up...")
    Base.metadata.create_all(bind=engine)
    print("DB initialized successfully.")
    yield
    print("Shutting down...")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(stations.router, prefix="/v1", tags=["stations"])
app.include_router(patients.router, prefix="/v1", tags=["patients"])
app.include_router(flow.router, prefix="/v1", tags=["flow"])
