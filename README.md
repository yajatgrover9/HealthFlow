# HealthFlow – Real‑Time Patient Flow Orchestration

HealthFlow is a small, production‑leaning FastAPI + React app that simulates how a clinic or urgent‑care center can manage patient flow in real time.

At a high level, it:

- Tracks patients as they move through stations (e.g., reception, triage, exam rooms).
- Continuously recomputes which patient should go to which station next.
- Gives staff a simple UI to check patients in, work their queue, and complete visits.
- Exposes a clean, API‑key‑protected backend that could be wired into a real hospital system.

---

## What the app does

### Domain model

- **Stations** – Work areas such as Reception, Triage, Lab, Exam Room 1, etc. Each station has a name and can have multiple tasks queued.
- **Patients** – Individuals visiting the clinic. A patient can have one or more **visit tasks** assigned.
- **Visit tasks** – Units of work that need to be performed for a patient at a given station (e.g., "Triage vitals", "Doctor consult").

The system’s goal is to keep stations productive and patients moving by always knowing:

- Which tasks are waiting.
- Which stations are free or busy.
- Which task should be worked on next at each station.

### Flow orchestration logic

The backend contains an optimizer service that acts as a simple orchestration engine:

1. **Reception creates tasks** when a patient arrives (check‑in).
2. The **optimizer recomputes assignments** whenever:
   - a new task is created, or
   - a task is completed.
3. On recompute, the service assigns waiting tasks to available stations in a deterministic, priority‑driven way.
4. Stations then fetch and work their assigned tasks until completion, triggering another recompute.

This loop approximates a real‑world flow engine while staying small enough to understand in one sitting.

---

## How the pieces fit together

### Backend (FastAPI)

Located in `src/app/`:

- `main.py` – FastAPI entrypoint and router wiring.
- `routers/` – Versioned `/v1/*` endpoints for stations, patients, flow orchestration, stats, and insights.
- `models/` – SQLAlchemy models and Pydantic schemas for stations, patients, and tasks.
- `services/optimizer.py` – Core assignment and recompute logic.
- `services/eta.py` and `services/flow_snapshot.py` – Compute ETAs and capture current flow state for the UI.
- `db/` – Database engine/session and migration helpers (PostgreSQL‑ready but works with SQLite for local dev).
- `auth/security.py` – Simple API‑key authentication.

Key capabilities:

- **Real‑time recompute** – `POST /v1/flow/recompute` recalculates station assignments based on current state.
- **Task lifecycle** – `POST /v1/flow/complete` marks tasks done and triggers a new recompute.
- **Observability hooks** – Structured logging helpers that can be extended for production telemetry.
- **Stats & insights** – Endpoints to surface basic performance metrics (queue lengths, throughput, etc.).

### Frontend (React + Vite)

Located in `ui/`:

- Built with React, TypeScript, and Vite.
- Talks to the FastAPI backend through `ui/src/services/api.ts`.

Screens:

- **Reception (`/reception`)** –
  - Check patients in (create tasks).
  - Trigger a recompute.
  - See which stations are available and who is waiting.
- **Station (`/station`, `/station/:stationId`)** –
  - Station operator’s view: see your current assignment and queue.
  - Start/complete work, which calls the backend and triggers recompute.
- **Display (`/display`)** –
  - Read‑only waiting‑room display.
  - Shows which stations are busy, which are free, and patient ETAs/queues.
- **Stats (`/stats`)** –
  - High‑level metrics about flow performance (visit counts, wait times, etc.).

The goal of the UI is to make the orchestration behavior easy to see without needing to call the API manually.

---

## Project structure (high level)

Backend (Python):

- `src/app/main.py` – FastAPI app entrypoint
- `src/app/core/` – configuration & logging
- `src/app/auth/security.py` – API key auth dependency
- `src/app/db/` – SQLAlchemy engine, session, and migrations helpers
- `src/app/models/` – domain models and Pydantic schemas
- `src/app/routers/` – API routes (stations, patients, flow, stats, insights)
- `src/app/services/` – orchestration, ETA, insights, and rerouting logic
- `tests/test_app.py` – backend tests

Frontend (TypeScript / React):

- `ui/src/main.tsx` – React entrypoint
- `ui/src/routes/App.tsx` – top‑level layout and routing
- `ui/src/routes/*.tsx` – individual pages (Reception, Station, Display, Stats)
- `ui/src/services/api.ts` – typed client for backend API

---

## Environment setup (backend)

Copy `.env.example` (if present) to `.env` and set strong secrets.

Required keys (see `src/app/core/config.py`):

- `APP_API_KEY` – shared secret for backend and UI
- `DATABASE_URL` – e.g. `sqlite+aiosqlite:///./healthflow.db` for local dev, or a PostgreSQL URL in production.

### Quick start (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Create and configure .env
Copy-Item .env.example .env
# Edit .env before starting

# Optional: run any DB bootstrap/migrations script if present
# e.g., python -m src.app.db.migrations

uvicorn src.app.main:app --reload
```

The API will be available at `http://localhost:8000`.

### API authentication

All `/v1/*` endpoints require this header:

- `x-api-key: <APP_API_KEY>`

`/health` is intentionally public.

### Run backend tests

```powershell
pytest -q
```

---

## Environment setup (UI)

From the project root:

```powershell
cd ui
npm install
Copy-Item .env.example .env
# Edit ui/.env so that VITE_API_BASE_URL and VITE_API_KEY match your backend
npm run dev
```

Required UI env keys:

- `VITE_API_BASE_URL` (e.g. `http://localhost:8000`)
- `VITE_API_KEY` (must match backend `APP_API_KEY`)

Then open in your browser:

- `http://localhost:5173/reception`
- `http://localhost:5173/station`
- `http://localhost:5173/station/1`
- `http://localhost:5173/display`
- `http://localhost:5173/stats`

---

## Core backend API endpoints (summary)

- `GET /health` – healthcheck
- `POST /v1/stations` – create stations
- `GET /v1/stations` – list stations
- `POST /v1/patients` – create patients
- `GET /v1/patients` – list patients
- `POST /v1/flow/recompute` – recompute station assignments
- `POST /v1/flow/complete` – complete a task and recompute
- `GET /v1/flow/tasks` – list current tasks & assignments
- `GET /v1/stats/*` and `/v1/insights/*` – stats and analytics endpoints

