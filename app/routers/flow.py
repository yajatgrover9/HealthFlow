from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import require_api_key
from app.db.db import get_db
from app.models.models import VisitTask
from app.models.schemas import AssignmentOut, CompleteTaskIn, TaskOut
from app.services.optimizer import mark_task_done, recompute_assignments

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.post("/flow/recompute", response_model=list[AssignmentOut])
def recompute_flow(db: Session = Depends(get_db)):
    return recompute_assignments(db)


@router.post("/flow/complete", response_model=list[AssignmentOut])
def complete_and_recompute(payload: CompleteTaskIn, db: Session = Depends(get_db)):
    task = mark_task_done(db, payload.task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return recompute_assignments(db)


@router.get("/flow/tasks", response_model=list[TaskOut])
def list_tasks(db: Session = Depends(get_db)):
    tasks = db.execute(select(VisitTask).order_by(VisitTask.id.asc())).scalars().all()
    # Pydantic will read ORM attributes (from_attributes=True). Convert Enum to its value.
    for t in tasks:
        t.status = t.status.value
    return tasks
