# HealthFlow FastAPI MVP

Production-leaning FastAPI backend for patient-flow orchestration with PostgreSQL-ready configuration.

## What is included

- FastAPI app with modular routers
- SQLAlchemy models for stations, patients, and visit tasks
- Deterministic real-time recompute endpoint for station assignments
- Task completion endpoint that triggers immediate recompute
- API key protection for all `/v1/*` endpoints
- Pytest tests covering protected API flow

## Project structure

- `app/main.py` - FastAPI app entrypoint
- `app/config.py` - settings loaded from `.env`
- `app/security.py` - API key auth dependency
- `app/db.py` - SQLAlchemy engine/session
- `app/models.py` - domain models
- `app/routers/` - API routes
- `app/services/optimizer.py` - assignment logic
- `app/startup.py` - local table bootstrap helper
- `tests/test_app.py` - API tests
- `.env.example` - environment variable template

## Environment setup

Copy `.env.example` to `.env` and set strong secrets.

Required keys:
- `APP_API_KEY`
- `DATABASE_URL`

## Quick start (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env before starting
python -c "from app.startup import init_db; init_db()"
uvicorn app.main:app --reload
```

## API authentication

All `/v1/*` endpoints require this header:

- `x-api-key: <APP_API_KEY>`

`/health` is intentionally public.

## Run tests

```powershell
pytest -q
```

## Core API endpoints

- `GET /health`
- `POST /v1/stations`
- `GET /v1/stations`
- `POST /v1/patients`
- `GET /v1/patients`
- `POST /v1/flow/recompute`
- `POST /v1/flow/complete`
- `GET /v1/flow/tasks`

## Notes for production hardening

- Add Alembic migrations and remove `create_all` bootstrap in runtime paths.
- Add rotation policy for API keys and eventually migrate to OAuth2/JWT + RBAC.
- Move recompute to event queue (Redis/Kafka + worker) for high-throughput facilities.
- Add observability (OpenTelemetry traces, metrics, structured logs).
- Add tenant isolation and audit logging for healthcare compliance.

## UI (React) screens

A minimal client-ready UI lives in `ui/` (separate from the FastAPI backend).

### Screens

- `Reception` (`/reception`): receptionist checks patients in (creates tasks) and triggers recompute.
- `Station` (`/station/:stationId`): station operator starts/completes the assigned patient.
- `Display` (`/display`): read-only screen for waiting area (busy/free + ETA + queue).

### Configure UI env

Copy `ui/.env.example` to `ui/.env` and set:

- `VITE_API_BASE_URL` (e.g. `http://localhost:8000`)
- `VITE_API_KEY` (must match backend `APP_API_KEY`)

### Run UI (PowerShell)

```powershell
cd ui
npm install
Copy-Item .env.example .env
# edit ui/.env
npm run dev
```

Then open:

- http://localhost:5173/reception
- http://localhost:5173/station/1
- http://localhost:5173/display
