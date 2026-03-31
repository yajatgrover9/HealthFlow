from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.app.models.models import Station, TaskStatus, VisitTask
from src.app.services.eta import station_status

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def auto_reroute_pending_tasks(db: Session) -> list[dict]:
    """Auto-rerouting: move pending tasks between *equivalent* stations by ETA.

    Behavior:
    - Only considers tasks in `pending` status.
    - Never touches `assigned`, `in_progress`, or `done` tasks.
    - Stations are considered equivalent if they share the same exact name prefix
      before the first space (e.g. "Blood A" and "Blood B"), or identical names.
    - Uses ETA data from `eta.station_status` to compare *queue wait* and busy state
      for a *new* eligible task at each station.
      * If a station is busy but an equivalent station is idle (busy == False), we
        prefer the idle one.
      * Otherwise we compare `estimated_queue_wait_min` and prefer lower values.

    NOTE: This is intentionally simple and local (per-task, per-group) rather
    than a global optimizer. It is designed to be predictable and cheap to run
    on every recompute/complete.
    """

    try:
        # Build quick lookup of station ETA info. This already accounts for
        # in-progress tasks, one reserved assigned task, and all *eligible*
        # pending tasks at each station.
        eta_list = station_status(db)
        eta_by_station: dict[int, dict] = {int(e["station_id"]): e for e in eta_list}

        # Load all active stations
        stations = (
            db.execute(select(Station).where(Station.active == 1)).scalars().all()
        )

        # Group stations by a simple "equivalence key" so we only reroute within groups
        def _group_key(st: Station) -> str:
            name = getattr(st, "name") or ""
            # simple heuristic: use first token as group (e.g. "Blood" from "Blood A")
            return name.split()[0] if name else ""

        groups: dict[str, list[Station]] = {}
        for st in stations:
            g = _group_key(st)
            groups.setdefault(g, []).append(st)

        decisions: list[dict] = []

        # For each group that has more than one station, try to rebalance pending tasks
        for group_stations in groups.values():
            if len(group_stations) < 2:
                continue

            # For each station in group, fetch its pending tasks (ordered by sequence/patient)
            for st in group_stations:
                st_id = int(getattr(st, "id"))

                pending_tasks = (
                    db.execute(
                        select(VisitTask)
                        .where(
                            VisitTask.station_id == st_id,
                            VisitTask.status == TaskStatus.pending,
                        )
                        .order_by(
                            VisitTask.sequence_no.asc(), VisitTask.patient_id.asc()
                        )
                    )
                    .scalars()
                    .all()
                )

                for task in pending_tasks:
                    # For each pending task, see if another station in the group is less loaded
                    best_station = st
                    current_eta = eta_by_station.get(st_id, {})
                    best_busy = bool(current_eta.get("busy", False))
                    best_wait = int(current_eta.get("estimated_queue_wait_min", 0) or 0)

                    for other in group_stations:
                        other_id = int(getattr(other, "id"))
                        if other_id == st_id:
                            continue

                        other_eta = eta_by_station.get(other_id, {})
                        other_busy = bool(other_eta.get("busy", False))
                        other_wait = int(
                            other_eta.get("estimated_queue_wait_min", 0) or 0
                        )

                        # Prefer idle stations over busy ones when possible
                        if best_busy and not other_busy:
                            best_station = other
                            best_busy = other_busy
                            best_wait = other_wait
                            continue

                        # If busy state is the same, pick the one with lower queue wait
                        if other_busy == best_busy and other_wait < best_wait:
                            best_station = other
                            best_busy = other_busy
                            best_wait = other_wait

                    if best_station is st:
                        continue

                    # Apply reroute: move task to best_station
                    new_station_id = int(getattr(best_station, "id"))
                    old_station_id = st_id
                    setattr(task, "station_id", new_station_id)

                    decisions.append(
                        {
                            "task_id": int(getattr(task, "id")),
                            "from_station_id": old_station_id,
                            "to_station_id": new_station_id,
                            "reason": "prefer_idle_or_better_eta",
                        }
                    )

        if decisions:
            db.commit()
        logger.info("rerouter.auto decisions=%s", len(decisions))
        return decisions
    except Exception as e:  # noqa: BLE001
        logger.error("rerouter.auto err=%s", e)
        raise
