"""
Assignment manager — CRUD + reminder generation.
Used by both the FastAPI routes and the voice intent router.
"""

import logging
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from server.db.models import Assignment, Reminder
from server.modules.assignments.parser import normalize_due_time
from server.modules.schedule.manager import get_active_profile, schedule_zone

log = logging.getLogger(__name__)


def create_assignment(
    db: Session,
    user_id: int,
    title: str,
    due_date: date,
    due_time: str | None = None,
    subject: str | None = None,
    priority: str = "medium",
    notes: str | None = None,
    request_id: str | None = None,
) -> Assignment:
    a = Assignment(
        user_id  = user_id,
        request_id = request_id,
        title    = title,
        subject  = subject,
        due_date = due_date,
        due_time = normalize_due_time(due_time),
        priority = priority,
        notes    = notes,
        status   = "pending",
    )
    db.add(a)
    db.flush()   # get the id before commit

    _schedule_reminders(db, a)

    db.commit()
    db.refresh(a)
    log.info(f"Assignment created: {a.title!r} due {a.due_date}")
    return a


def get_all_assignments(db: Session, user_id: int, status: str | None = None) -> list[Assignment]:
    q = db.query(Assignment).filter(Assignment.user_id == user_id)
    if status:
        q = q.filter(Assignment.status == status)
    return q.order_by(Assignment.due_date, Assignment.due_time.asc().nulls_last(), Assignment.id).all()


def get_upcoming(db: Session, user_id: int, days: int = 7) -> list[Assignment]:
    cutoff = datetime.now(schedule_zone(get_active_profile(db, user_id))).date() + timedelta(days=days)
    return (
        db.query(Assignment)
        .filter(Assignment.user_id == user_id)
        .filter(Assignment.due_date <= cutoff)
        .filter(Assignment.status != "done")
        .order_by(Assignment.due_date, Assignment.due_time.asc().nulls_last(), Assignment.id)
        .all()
    )


def get_overdue(db: Session, user_id: int) -> list[Assignment]:
    now = datetime.now(schedule_zone(get_active_profile(db, user_id)))
    return (
        db.query(Assignment)
        .filter(Assignment.user_id == user_id)
        .filter(or_(Assignment.due_date < now.date(), and_(
            Assignment.due_date == now.date(), Assignment.due_time < now.strftime("%H:%M")
        )))
        .filter(Assignment.status != "done")
        .all()
    )


def mark_done(db: Session, assignment_id: int, user_id: int) -> Assignment | None:
    a = db.query(Assignment).filter_by(id=assignment_id, user_id=user_id).first()
    if a:
        a.status = "done"
        db.commit()
        db.refresh(a)
    return a


def update_status(db: Session, assignment_id: int, status: str, user_id: int) -> Assignment | None:
    a = db.query(Assignment).filter_by(id=assignment_id, user_id=user_id).first()
    if a:
        a.status = status
        db.commit()
        db.refresh(a)
    return a


def delete_assignment(db: Session, assignment_id: int, user_id: int) -> bool:
    a = db.query(Assignment).filter_by(id=assignment_id, user_id=user_id).first()
    if a:
        db.delete(a)
        db.commit()
        return True
    return False


# ── reminders ────────────────────────────────────────────────────────────

def _schedule_reminders(db: Session, assignment: Assignment) -> int:
    """
    Create one reminder per day, every day, starting 7 days before the due
    date (or from today, if the assignment was added with less than 7 days
    left) through the day it's due. Tone escalates as the date gets closer.
    """
    due = datetime.combine(assignment.due_date, datetime.min.time())
    zone = schedule_zone(get_active_profile(db, assignment.user_id))
    now = datetime.now(timezone.utc)
    today = datetime.combine(now.astimezone(zone).date(), time.min)

    window_start = max(due - timedelta(days=7), today)
    remind_hour  = timedelta(hours=9)   # send each day's nudge at 9am local

    deadline_time = time.fromisoformat(assignment.due_time) if assignment.due_time else None
    added = 0
    cursor = window_start
    while cursor <= due:
        days_left = (due - cursor).days
        if days_left <= 0:
            message = f"TODAY is the deadline for '{assignment.title}'. Submit it."
        elif days_left == 1:
            message = f"Tomorrow is the deadline for '{assignment.title}'. Start if you haven't."
        else:
            message = f"'{assignment.title}' is due in {days_left} days."

        remind_at = cursor + remind_hour
        if deadline_time:
            message += f" Deadline: {assignment.due_time}."
            if days_left == 0:
                remind_at = datetime.combine(cursor.date(), deadline_time)
        remind_at = remind_at.replace(tzinfo=zone).astimezone(timezone.utc)
        if remind_at > now:
            db.add(Reminder(
                assignment_id = assignment.id,
                remind_at     = remind_at.replace(tzinfo=None),
                message       = message,
            ))
            added += 1
        cursor += timedelta(days=1)
    return added


def get_pending_reminders(db: Session) -> list[Reminder]:
    """Reminders that are due now and not yet delivered."""
    return (
        db.query(Reminder)
        .filter(Reminder.remind_at <= datetime.now(timezone.utc).replace(tzinfo=None))
        .filter(~Reminder.assignment.has(Assignment.status == "done"))
        .filter(Reminder.delivered == False)
        .all()
    )


def mark_reminder_delivered(db: Session, reminder_id: int):
    r = db.get(Reminder, reminder_id)
    if r:
        r.delivered = True
        db.commit()
