from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.app.core.config import settings

engine = create_engine(
    settings.DB_URL,
    connect_args={"options": f"-csearch_path={settings.DB_SCHEMA}"},
    pool_pre_ping=True,
    pool_recycle=1800,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
