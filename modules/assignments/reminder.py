"""
reminder.py — Standalone background reminder loop.

Extracted from daily_trigger.py + manager.py into its own module.

Features:
  - Polls DB every POLL_INTERVAL_MIN for pending reminders
  - Three urgency levels with distinct messages and tones
  - Escalation: overdue items get an extra aggressive push
  - Duplicate prevention via Reminder.delivered flag
  - Can run as background thread OR be driven by APScheduler

Urgency levels:
  gentle   3+ days out  → "Heads up..."
  urgent   1 day out    → "Tomorrow is the deadline..."
  critical due today    → "TODAY. Submit. Now."
  overdue  past due     → "It's already past the deadline..."
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from datetime import date, datetime, timedelta

from db.database import get_db_ctx
from db.models import Assignment, Reminder

log = logging.getLogger(__name__)

POLL_INTERVAL_MIN = 15


class ReminderLoop:
    """
    Runs in a background thread, polls for pending reminders and delivers them.
    """

    def __init__(
        self,
        speak_fn:     Callable[[str], None] | None = None,
        broadcast_fn: Callable[[dict], None] | None = None,
        poll_minutes: int = POLL_INTERVAL_MIN,
    ):
        self._speak      = speak_fn
        self._broadcast  = broadcast_fn
        self._poll_s     = poll_minutes * 60
        self._running    = False
        self._thread:    threading.Thread | None = None

    # ── lifecycle ─────────────────────────────────────────────────────────

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(
            target=self._loop, daemon=True, name="reminder-loop"
        )
        self._thread.start()
        log.info("Reminder loop started (poll every %dm).", self._poll_s // 60)

    def stop(self):
        self._running = False
        log.info("Reminder loop stopped.")

    # ── main loop ─────────────────────────────────────────────────────────

    def _loop(self):
        # Fire immediately on start, then every POLL_INTERVAL_MIN
        while self._running:
            try:
                self.check_and_deliver()
            except Exception as e:
                log.error("Reminder loop error: %s", e)
            time.sleep(self._poll_s)

    # ── public: single pass (also called by APScheduler) ─────────────────

    def check_and_deliver(self):
        """
        One full pass: find pending reminders + overdue assignments,
        deliver each one exactly once, mark as delivered.
        """
        with get_db_ctx() as db:
            # Standard scheduled reminders
            pending = self._get_pending(db)
            for r in pending:
                msg = self._escalate_message(r, db)
                user_id = r.assignment.user_id if r.assignment else None
                self._deliver(msg, r.assignment_id, user_id=user_id)
                r.delivered = True
                db.add(r)

            # Extra: overdue assignments that never got a final reminder
            overdue = self._get_silently_overdue(db)
            for a in overdue:
                msg = _overdue_msg(a)
                self._deliver(msg, a.id, user_id=a.user_id)
                # Update reminded_at so we don't spam
                a.reminded_at = datetime.now()
                db.add(a)

            db.commit()

    # ── helpers ───────────────────────────────────────────────────────────

    def _get_pending(self, db) -> list[Reminder]:
        return (
            db.query(Reminder)
            .filter(Reminder.remind_at <= datetime.now())
            .filter(Reminder.delivered == False)
            .all()
        )

    def _get_silently_overdue(self, db) -> list[Assignment]:
        """Overdue assignments that haven't been reminded in the last 24h."""
        cutoff = datetime.now() - timedelta(hours=24)
        return (
            db.query(Assignment)
            .filter(Assignment.due_date < date.today())
            .filter(Assignment.status != "done")
            .filter(
                (Assignment.reminded_at == None) |
                (Assignment.reminded_at < cutoff)
            )
            .all()
        )

    def _escalate_message(self, reminder: Reminder, db) -> str:
        """
        Override the stored reminder message with a more urgent one
        based on current days-remaining at delivery time.
        """
        if not reminder.assignment_id:
            return reminder.message or "You have a pending deadline."

        a = db.get(Assignment, reminder.assignment_id)
        if not a:
            return reminder.message or "Deadline reminder."

        days = (a.due_date - date.today()).days

        if days < 0:
            return _overdue_msg(a)
        elif days == 0:
            return (
                f"TODAY is the deadline for '{a.title}'. "
                f"It needs to be submitted TODAY. Not tomorrow. TODAY."
            )
        elif days == 1:
            return (
                f"'{a.title}' is due TOMORROW. "
                f"If you haven't started, start RIGHT NOW. Not after dinner."
            )
        elif days <= 3:
            return (
                f"'{a.title}' is due in {days} days. "
                f"You should already be working on this."
            )
        else:
            return (
                f"Reminder: '{a.title}' is due in {days} days. "
                f"Plan your time accordingly."
            )

    def _deliver(self, message: str, assignment_id: int | None = None, user_id: int | None = None):
        log.info("Reminder: %s", message)

        if user_id is None:
            log.warning("Skipping broadcast for reminder (assignment_id=%s): no user_id resolved", assignment_id)
            return

        # Trigger desktop notification
        try:
            from desktop.notifications import notify
            notify("Reminder", message)
        except Exception:
            pass

        if self._speak:
            self._speak(message)

        if self._broadcast:
            payload = {
                "type":          "reminder",
                "message":       message,
                "assignment_id": assignment_id,
                "user_id":       user_id,
                "ts":            datetime.now().isoformat(),
            }
            self._broadcast(payload)


# ── standalone helpers ────────────────────────────────────────────────────

def _overdue_msg(a: Assignment) -> str:
    days_late = (date.today() - a.due_date).days
    if days_late == 1:
        return (
            f"'{a.title}' was due YESTERDAY and you still haven't submitted it. "
            f"This is now a problem."
        )
    return (
        f"'{a.title}' is {days_late} days overdue. "
        f"Contact your instructor if needed, but submit SOMETHING."
    )


def schedule_reminders_for(assignment: Assignment, db) -> int:
    """
    Create Reminder rows for an assignment at 3d, 1d, and day-of.
    Returns the number of reminders created.
    Skips dates already in the past.
    """
    due = datetime.combine(assignment.due_date, datetime.min.time())
    schedule = [
        (due - timedelta(days=3), "gentle"),
        (due - timedelta(days=1), "urgent"),
        (due,                      "critical"),
    ]

    count = 0
    for remind_at, level in schedule:
        if remind_at <= datetime.now():
            continue
        days = (assignment.due_date - date.today()).days
        msg  = _build_message(assignment.title, days, level)
        db.add(Reminder(
            assignment_id = assignment.id,
            remind_at     = remind_at,
            delivered     = False,
            message       = msg,
        ))
        count += 1

    return count


def _build_message(title: str, days_until: int, level: str) -> str:
    if level == "gentle":
        return f"Heads up: '{title}' is due in {days_until} days. Start planning."
    if level == "urgent":
        return f"'{title}' is due tomorrow. Start if you haven't already."
    return f"TODAY is the deadline for '{title}'. Submit it."
