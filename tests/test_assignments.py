"""
Unit tests for assignment management:
  - CRUD operations
  - Reminder auto-scheduling
  - Overdue detection
  - Status transitions
"""

import pytest
from datetime import date, timedelta

from modules.assignments.manager import (
    create_assignment, get_all_assignments, get_upcoming,
    get_overdue, mark_done, update_status, delete_assignment,
    get_pending_reminders,
)
from modules.assignments.reminder import schedule_reminders_for, ReminderLoop
from db.models import Assignment, Reminder


class TestAssignmentCRUD:

    def test_create_basic(self, db_session):
        a = create_assignment(
            db       = db_session,
            user_id  = 1,
            title    = "Math Homework",
            due_date = date.today() + timedelta(days=5),
        )
        assert a.id is not None
        assert a.title   == "Math Homework"
        assert a.status  == "pending"
        assert a.priority == "medium"

    def test_create_with_subject(self, db_session):
        a = create_assignment(
            db=db_session, user_id=1, title="Lab Report",
            subject="Physics", due_date=date.today() + timedelta(days=3),
        )
        assert a.subject == "Physics"

    def test_get_all_empty(self, db_session):
        assert get_all_assignments(db_session, user_id=1) == []

    def test_get_all_returns_all(self, db_session, seed_assignments):
        seed_assignments([
            {"title": "A", "due_date": date.today() + timedelta(days=1)},
            {"title": "B", "due_date": date.today() + timedelta(days=2)},
            {"title": "C", "due_date": date.today() + timedelta(days=3)},
        ])
        result = get_all_assignments(db_session, user_id=1)
        assert len(result) == 3

    def test_get_all_filter_by_status(self, db_session, seed_assignments):
        seed_assignments([
            {"title": "Pending", "status": "pending",     "due_date": date.today() + timedelta(days=2)},
            {"title": "Done",    "status": "done",        "due_date": date.today() + timedelta(days=3)},
            {"title": "WIP",     "status": "in_progress", "due_date": date.today() + timedelta(days=4)},
        ])
        pending = get_all_assignments(db_session, user_id=1, status="pending")
        assert len(pending) == 1
        assert pending[0].title == "Pending"

    def test_mark_done(self, db_session):
        a = create_assignment(db_session, user_id=1, title="Exam prep", due_date=date.today() + timedelta(days=2))
        done = mark_done(db_session, a.id, user_id=1)
        assert done.status == "done"

    def test_mark_done_nonexistent(self, db_session):
        result = mark_done(db_session, 99999, user_id=1)
        assert result is None

    def test_update_status(self, db_session):
        a = create_assignment(db_session, user_id=1, title="Project", due_date=date.today() + timedelta(days=7))
        updated = update_status(db_session, a.id, "in_progress", user_id=1)
        assert updated.status == "in_progress"

    def test_delete_assignment(self, db_session):
        a = create_assignment(db_session, user_id=1, title="To Delete", due_date=date.today() + timedelta(days=2))
        ok = delete_assignment(db_session, a.id, user_id=1)
        assert ok is True
        assert get_all_assignments(db_session, user_id=1) == []

    def test_delete_nonexistent(self, db_session):
        assert delete_assignment(db_session, 99999, user_id=1) is False


class TestUpcomingAndOverdue:

    def test_get_upcoming_within_window(self, db_session, seed_assignments):
        seed_assignments([
            {"title": "Soon",  "due_date": date.today() + timedelta(days=2)},
            {"title": "Later", "due_date": date.today() + timedelta(days=14)},
        ])
        upcoming = get_upcoming(db_session, user_id=1, days=7)
        titles = [a.title for a in upcoming]
        assert "Soon"  in titles
        assert "Later" not in titles

    def test_get_upcoming_excludes_done(self, db_session, seed_assignments):
        seed_assignments([
            {"title": "Done",    "status": "done",    "due_date": date.today() + timedelta(days=1)},
            {"title": "Pending", "status": "pending", "due_date": date.today() + timedelta(days=1)},
        ])
        upcoming = get_upcoming(db_session, user_id=1, days=7)
        titles = [a.title for a in upcoming]
        assert "Done"    not in titles
        assert "Pending" in titles

    def test_get_overdue(self, db_session, seed_assignments):
        seed_assignments([
            {"title": "Overdue",  "due_date": date.today() - timedelta(days=2), "status": "pending"},
            {"title": "Future",   "due_date": date.today() + timedelta(days=3), "status": "pending"},
            {"title": "OverDone", "due_date": date.today() - timedelta(days=1), "status": "done"},
        ])
        overdue = get_overdue(db_session, user_id=1)
        titles = [a.title for a in overdue]
        assert "Overdue"  in titles
        assert "Future"   not in titles
        assert "OverDone" not in titles


class TestReminders:

    def test_auto_reminders_created(self, db_session):
        """create_assignment should auto-schedule daily reminders (7 days prior + day-of = 8)."""
        a = create_assignment(
            db_session, user_id=1, title="Big Project",
            due_date=date.today() + timedelta(days=10),
        )
        reminders = db_session.query(Reminder).filter(
            Reminder.assignment_id == a.id
        ).all()
        # 7-day prior + day-of = 8 reminders
        assert len(reminders) == 8

    def test_reminders_not_created_for_past_date(self, db_session):
        """Reminders for dates already past should be skipped."""
        a = create_assignment(
            db_session, user_id=1, title="Old Assignment",
            due_date=date.today() + timedelta(days=1),
            # Only 1-day and day-of are in the future
        )
        reminders = db_session.query(Reminder).filter(
            Reminder.assignment_id == a.id
        ).all()
        # At most 2 (3-day reminder is in the past)
        assert len(reminders) <= 2

    def test_no_reminders_for_past_due_date(self, db_session):
        """If due date is in the past, no reminders should be created."""
        a = create_assignment(
            db_session, user_id=1, title="Very Late",
            due_date=date.today() - timedelta(days=5),
        )
        reminders = db_session.query(Reminder).filter(
            Reminder.assignment_id == a.id
        ).all()
        assert len(reminders) == 0

    def test_get_pending_reminders(self, db_session):
        """Only reminders with remind_at in the past and not delivered."""
        from db.models import Reminder
        from datetime import datetime, timedelta

        # Past undelivered
        r1 = Reminder(
            assignment_id = None,
            remind_at     = datetime.now() - timedelta(minutes=5),
            delivered     = False,
            message       = "Test reminder",
        )
        # Future undelivered
        r2 = Reminder(
            assignment_id = None,
            remind_at     = datetime.now() + timedelta(hours=2),
            delivered     = False,
            message       = "Future",
        )
        # Past but already delivered
        r3 = Reminder(
            assignment_id = None,
            remind_at     = datetime.now() - timedelta(minutes=10),
            delivered     = True,
            message       = "Already done",
        )
        for r in (r1, r2, r3):
            db_session.add(r)
        db_session.commit()

        pending = get_pending_reminders(db_session)
        assert len(pending) == 1
        assert pending[0].message == "Test reminder"

