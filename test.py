"""Quick manual seed runner.

Prefer using `scripts/seed_data.py` for real usage.

Run:
  python .\test.py
"""

from __future__ import annotations

from sqlalchemy import select

from src.app.db.db import Base, SessionLocal, engine
from src.app.models.models import Station

STATIONS = [
    ("Blood Collection", 8),
    ("ECG", 12),
    ("X-Ray", 15),
    ("Ultrasound", 20),
    ("Eye Check (Ophthalmology)", 10),
    ("Audiometry (Hearing)", 10),
    ("PFT / Spirometry", 15),
    ("TMT (Treadmill Test)", 25),
    ("Dietician Consultation", 15),
    ("Physician Consultation", 18),
]


def main() -> None:
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        for name, avg in STATIONS:
            existing = db.execute(
                select(Station).where(Station.name == name)
            ).scalar_one_or_none()
            if existing:
                existing.avg_duration_min = avg
                existing.active = 1
                continue
            db.add(Station(name=name, avg_duration_min=avg, active=1))
        db.commit()

        rows = db.execute(select(Station).order_by(Station.id.asc())).scalars().all()
        print(f"Stations in DB: {len(rows)}")
        for s in rows:
            print(f"{s.id:>2}  {s.name}  ({s.avg_duration_min} min)")


if __name__ == "__main__":
    main()
