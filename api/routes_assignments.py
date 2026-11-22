from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.routes_auth import current_user
from api.websocket import push_event
from db.database import get_db
from db.models import Assignment, User
from modules.assignments.manager import (
    create_assignment,
    delete_assignment,
    get_all_assignments,
    get_overdue,
    get_upcoming,
    mark_done,
    update_status,
)
from modules.assignments.parser import normalize_due_time, parse_assignment_command

router = APIRouter(prefix="/assignments", tags=["assignments"])


# ── Pydantic schemas ──────────────────────────────────────────────────────
class AssignmentCreate(BaseModel):
    request_id: UUID | None = None
    title: str = Field(min_length=1, max_length=300)
    subject: str | None = Field(default=None, max_length=100)
    due_date: date
    due_time: str | None = None
    priority: Literal["low", "medium", "high"] | None = "medium"
    notes:    str | None = None


    _validate_due_time = field_validator("due_time")(normalize_due_time)


class AssignmentOut(BaseModel):
    id:       int
    title:    str
    subject:  str | None
    due_date: date
    due_time: str | None
    priority: str
    status:   str
    notes:    str | None

    model_config = ConfigDict(from_attributes=True)


class NLPCreate(BaseModel):
    due_time: str | None = None
    _validate_due_time = field_validator("due_time")(normalize_due_time)

    text: str   # raw voice/text command e.g. "Math assignment due Friday"


class StatusUpdate(BaseModel):
    status: Literal["pending", "in_progress", "done"]


# ── endpoints ─────────────────────────────────────────────────────────────
@router.post("", response_model=AssignmentOut, status_code=201)
@router.post("/", response_model=AssignmentOut, status_code=201, include_in_schema=False)
def add_assignment(payload: AssignmentCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    request_id = str(payload.request_id) if payload.request_id else None
    user_id = user.id
    try:
        a = create_assignment(
            db=db, user_id=user_id, title=payload.title, subject=payload.subject,
            due_date=payload.due_date, due_time=payload.due_time,
            priority=payload.priority or "medium", notes=payload.notes, request_id=request_id,
        )
    except IntegrityError:
        db.rollback()
        if request_id:
            existing = db.query(Assignment).filter_by(user_id=user_id, request_id=request_id).one_or_none()
            if existing is not None:
                return existing
        raise
    push_event({"user_id": user.id, "type": "assignment_added", "assignment": {
        "id": a.id, "title": a.title, "due_date": str(a.due_date), "due_time": a.due_time,
        "subject": a.subject, "priority": a.priority, "status": a.status,
    }})
    return a


@router.post("/nlp", response_model=AssignmentOut, status_code=201)
def add_assignment_nlp(payload: NLPCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Parse natural language and create assignment. Used by voice commands."""
    parsed = parse_assignment_command(payload.text)
    if not parsed:
        raise HTTPException(status_code=422, detail="Could not parse assignment from text")
    if payload.due_time:
        parsed["due_time"] = payload.due_time
    a = create_assignment(db=db, user_id=user.id, **parsed)
    push_event({"user_id": user.id, "type": "assignment_added", "assignment": {
        "id": a.id, "title": a.title, "due_date": str(a.due_date), "due_time": a.due_time,
        "subject": a.subject, "priority": a.priority, "status": a.status,
    }})
    return a


@router.get("", response_model=list[AssignmentOut])
@router.get("/", response_model=list[AssignmentOut], include_in_schema=False)
def list_assignments(status: str | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return get_all_assignments(db, user_id=user.id, status=status)


@router.get("/upcoming", response_model=list[AssignmentOut])
def list_upcoming(days: int = 7, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return get_upcoming(db, user_id=user.id, days=days)


@router.get("/overdue", response_model=list[AssignmentOut])
def list_overdue(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return get_overdue(db, user_id=user.id)


@router.patch("/{assignment_id}/status")
def set_status(assignment_id: int, payload: StatusUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    a = update_status(db, assignment_id, payload.status, user_id=user.id)
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")
    push_event({"user_id": user.id, "type": "assignment_updated", "id": a.id, "status": a.status, "title": a.title})
    return {"ok": True, "id": a.id, "status": a.status}


@router.post("/{assignment_id}/done")
def done(assignment_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    a = mark_done(db, assignment_id, user_id=user.id)
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")
    push_event({"user_id": user.id, "type": "assignment_done", "id": a.id, "title": a.title})
    return {"ok": True, "message": f"'{a.title}' marked as done."}


@router.delete("/{assignment_id}", status_code=204)
def remove(assignment_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not delete_assignment(db, assignment_id, user_id=user.id):
        raise HTTPException(status_code=404, detail="Assignment not found")
