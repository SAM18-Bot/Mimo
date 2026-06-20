from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Assignment
from modules.assignments.manager import (
    create_assignment, get_all_assignments, get_upcoming,
    get_overdue, mark_done, update_status, delete_assignment,
)
from modules.assignments.parser import parse_assignment_command
from api.websocket import push_event

router = APIRouter(prefix="/assignments", tags=["assignments"])


# ── Pydantic schemas ──────────────────────────────────────────────────────
class AssignmentCreate(BaseModel):
    title:    str
    subject:  Optional[str] = None
    due_date: date
    priority: Optional[str] = "medium"
    notes:    Optional[str] = None


class AssignmentOut(BaseModel):
    id:       int
    title:    str
    subject:  Optional[str]
    due_date: date
    priority: str
    status:   str
    notes:    Optional[str]

    model_config = ConfigDict(from_attributes=True)


class NLPCreate(BaseModel):
    text: str   # raw voice/text command e.g. "Math assignment due Friday"


class StatusUpdate(BaseModel):
    status: str   # pending | in_progress | done


# ── endpoints ─────────────────────────────────────────────────────────────
@router.post("/", response_model=AssignmentOut, status_code=201)
def add_assignment(payload: AssignmentCreate, db: Session = Depends(get_db)):
    a = create_assignment(
        db       = db,
        title    = payload.title,
        subject  = payload.subject,
        due_date = payload.due_date,
        priority = payload.priority or "medium",
        notes    = payload.notes,
    )
    push_event({"type": "assignment_added", "assignment": {
        "id": a.id, "title": a.title, "due_date": str(a.due_date),
        "subject": a.subject, "priority": a.priority, "status": a.status,
    }})
    return a


@router.post("/nlp", response_model=AssignmentOut, status_code=201)
def add_assignment_nlp(payload: NLPCreate, db: Session = Depends(get_db)):
    """Parse natural language and create assignment. Used by voice commands."""
    parsed = parse_assignment_command(payload.text)
    if not parsed:
        raise HTTPException(status_code=422, detail="Could not parse assignment from text")
    a = create_assignment(db=db, **parsed)
    push_event({"type": "assignment_added", "assignment": {
        "id": a.id, "title": a.title, "due_date": str(a.due_date),
        "subject": a.subject, "priority": a.priority, "status": a.status,
    }})
    return a


@router.get("/", response_model=List[AssignmentOut])
def list_assignments(status: Optional[str] = None, db: Session = Depends(get_db)):
    return get_all_assignments(db, status=status)


@router.get("/upcoming", response_model=List[AssignmentOut])
def list_upcoming(days: int = 7, db: Session = Depends(get_db)):
    return get_upcoming(db, days=days)


@router.get("/overdue", response_model=List[AssignmentOut])
def list_overdue(db: Session = Depends(get_db)):
    return get_overdue(db)


@router.patch("/{assignment_id}/status")
def set_status(assignment_id: int, payload: StatusUpdate, db: Session = Depends(get_db)):
    a = update_status(db, assignment_id, payload.status)
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")
    push_event({"type": "assignment_updated", "id": a.id, "status": a.status, "title": a.title})
    return {"ok": True, "id": a.id, "status": a.status}


@router.post("/{assignment_id}/done")
def done(assignment_id: int, db: Session = Depends(get_db)):
    a = mark_done(db, assignment_id)
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")
    push_event({"type": "assignment_done", "id": a.id, "title": a.title})
    return {"ok": True, "message": f"'{a.title}' marked as done."}


@router.delete("/{assignment_id}", status_code=204)
def remove(assignment_id: int, db: Session = Depends(get_db)):
    if not delete_assignment(db, assignment_id):
        raise HTTPException(status_code=404, detail="Assignment not found")
