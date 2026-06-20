"""
Assignment manager — CRUD + reminder generation.
Used by both the FastAPI routes and the voice intent router.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional, List

from sqlalchemy.orm import Session

from db.models import Assignment, Reminder

log = logging.getLogger(__name__)


def create_assignment(
    db: Session,
    title: str,
    due_date: date,
    subject: Optional[str] = None,
    priority: str = "medium",
    notes: Optional[str] = None,
) -> Assignment:
    a = Assignment(
        title    = title,
        subject  = subject,
        due_date = due_date,
        priority = priority,
        notes    = notes,
    )
    db.add(a)
    db.flush()   # get the id before commit

    # Auto-create reminders at 3 days, 1 day, and day-of
    _schedule_reminders(db, a)

    db.commit()
    db.refresh(a)
    log.info(f"Assignment created: {a.title!r} due {a.due_date}")
    return a


def get_all_assignments(db: Session, status: Optional[str] = None) -> List[Assignment]:
    q = db.query(Assignment)
    if status:
        q = q.filter(Assignment.status == status)
    return q.order_by(Assignment.due_date).all()


def get_upcoming(db: Session, days: int = 7) -> List[Assignment]:
    cutoff = date.today() + timedelta(days=days)
    return (
        db.query(Assignment)
        .filter(Assignment.due_date <= cutoff)
        .filter(Assignment.status != "done")
        .order_by(Assignment.due_date)
        .all()
    )


def get_overdue(db: Session) -> List[Assignment]:
    return (
        db.query(Assignment)
        .filter(Assignment.due_date < date.today())
        .filter(Assignment.status != "done")
        .all()
    )


def mark_done(db: Session, assignment_id: int) -> Optional[Assignment]:
    a = db.get(Assignment, assignment_id)
    if a:
        a.status = "done"
        db.commit()
        db.refresh(a)
    return a


def update_status(db: Session, assignment_id: int, status: str) -> Optional[Assignment]:
    a = db.get(Assignment, assignment_id)
    if a:
        a.status = status
        db.commit()
        db.refresh(a)
    return a


def delete_assignment(db: Session, assignment_id: int) -> bool:
    a = db.get(Assignment, assignment_id)
    if a:
        db.delete(a)
        db.commit()
        return True
    return False


# ── reminders ────────────────────────────────────────────────────────────

def _schedule_reminders(db: Session, assignment: Assignment):
    """Create reminder rows at 3d, 1d, and day-of for an assignment."""
    due = datetime.combine(assignment.due_date, datetime.min.time())

    schedule = [
        (due - timedelta(days=3),  f"Heads up: '{assignment.title}' is due in 3 days."),
        (due - timedelta(days=1),  f"Tomorrow is the deadline for '{assignment.title}'. Start if you haven't."),
        (due,                       f"TODAY is the deadline for '{assignment.title}'. Submit it."),
    ]

    for remind_at, message in schedule:
        if remind_at > datetime.now():
            db.add(Reminder(
                assignment_id = assignment.id,
                remind_at     = remind_at,
                message       = message,
            ))


def get_pending_reminders(db: Session) -> List[Reminder]:
    """Reminders that are due now and not yet delivered."""
    return (
        db.query(Reminder)
        .filter(Reminder.remind_at <= datetime.now())
        .filter(Reminder.delivered == False)  # noqa: E712
        .all()
    )


def mark_reminder_delivered(db: Session, reminder_id: int):
    r = db.get(Reminder, reminder_id)
    if r:
        r.delivered = True
        db.commit()
