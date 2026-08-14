"""
Roast engine — decides WHEN to roast and triggers the roast.
Sits between the event bus (screen tracker + CV pipeline) and the AI client.

Rules:
- Don't roast more than once per MIN_ROAST_INTERVAL seconds
- Only roast on distracting apps after DISTRACTION_ROAST_AFTER_MINUTES
- Only roast absence after ABSENCE_ROAST_AFTER_MINUTES
- Log every roast to the DB
- Speak via TTS + broadcast to WebSocket dashboard
"""

import logging
import threading
import time
from datetime import datetime, date
from typing import Optional, Callable

from db.database import get_db_ctx
from db.models import Assignment, RoastLog
from modules.ai_layer.client import generate_roast
import config

log = logging.getLogger(__name__)


class RoastEngine:
    def __init__(
        self,
        speak_fn:     Optional[Callable] = None,
        broadcast_fn: Optional[Callable] = None,
        notify_fn:    Optional[Callable] = None,
    ):
        """
        speak_fn(text)     — TTS callback (from voice module)
        broadcast_fn(data) — WebSocket broadcast callback
        notify_fn(text)    — native OS notification callback (from desktop.notifications)
        """
        self._speak     = speak_fn
        self._broadcast = broadcast_fn
        self._notify    = notify_fn
        self._lock      = threading.Lock()

        # tracking state per user
        self._last_roast_time: dict[int, float] = {}
        self._distraction_start: dict[int, float] = {}
        self._absence_start: dict[int, float] = {}
        self._current_distracting_app: dict[int, str] = {}

    # ── called by screen tracker ──────────────────────────────────────────
    def on_window_change(self, app: str, title: str, category: str, user_id: int = 1):
        if category == "distracting":
            if self._distraction_start.get(user_id) is None:
                self._distraction_start[user_id] = time.time()
                self._current_distracting_app[user_id] = app
            else:
                # Still on distracting content — check threshold
                elapsed_min = (time.time() - self._distraction_start[user_id]) / 60
                if elapsed_min >= config.DISTRACTION_ROAST_AFTER_MINUTES:
                    self._fire_roast("distraction", app, int(elapsed_min), user_id=user_id)
        else:
            self._distraction_start[user_id] = None
            self._current_distracting_app[user_id] = ""

    # ── called by CV pipeline ─────────────────────────────────────────────
    def on_cv_event(self, event_type: str, user_id: int = 1):
        if event_type == "absent":
            if self._absence_start.get(user_id) is None:
                self._absence_start[user_id] = time.time()
        elif event_type in ("present", "returned"):
            self._absence_start[user_id] = None
        
        if self._absence_start.get(user_id):
            elapsed_min = (time.time() - self._absence_start[user_id]) / 60
            if elapsed_min >= config.ABSENCE_ROAST_AFTER_MINUTES:
                self._fire_roast("absent", "desk", int(elapsed_min), user_id=user_id)

    # ── core fire logic ───────────────────────────────────────────────────
    def trigger_roast(self, trigger: str, app: str = "desk", minutes: int = 0, user_id: int = 1):
        self._fire_roast(trigger, app, minutes, user_id=user_id)

    def _fire_roast(self, trigger: str, app: str, minutes: int, user_id: int = 1):
        with self._lock:
            now = time.time()
            if now - self._last_roast_time.get(user_id, 0.0) < config.MIN_ROAST_INTERVAL_SECONDS:
                return   # cooldown active
            self._last_roast_time[user_id] = now
            # Reset the start so the same trigger doesn't keep firing immediately
            self._distraction_start[user_id] = None
            self._absence_start[user_id] = None

        # Gather context from DB (don't hold the lock during DB/AI calls)
        context = self._get_context(user_id=user_id)
        
        roast_text = generate_roast(
            trigger             = trigger,
            app_name            = app,
            time_spent_min      = minutes,
            pending_assignments = context["pending_assignments"],
            days_until_deadline = context["days_until_deadline"],
        )

        log.info(f"ROAST [{trigger}]: {roast_text}")

        # Persist
        self._save_roast(trigger, roast_text, user_id=user_id)

        # Speak
        if self._speak:
            threading.Thread(
                target=self._speak, args=(roast_text,), daemon=True
            ).start()

        # Native OS notification (desktop app)
        if self._notify:
            threading.Thread(
                target=self._notify, args=(roast_text,), daemon=True
            ).start()

        # Broadcast to dashboard
        if self._broadcast:
            self._broadcast({
                "type":    "roast",
                "message": roast_text,
                "trigger": trigger,
                "app":     app,
                "ts":      datetime.now().isoformat(),
                "user_id": user_id,
            })

    def _get_context(self, user_id: int = 1) -> dict:
        try:
            with get_db_ctx() as db:
                from datetime import timedelta
                upcoming = (
                    db.query(Assignment)
                    .filter(Assignment.user_id == user_id)
                    .filter(Assignment.status != "done")
                    .filter(Assignment.due_date >= date.today())
                    .order_by(Assignment.due_date)
                    .limit(3)
                    .all()
                )
                if upcoming:
                    names  = ", ".join(a.title for a in upcoming[:3])
                    days   = (upcoming[0].due_date - date.today()).days
                else:
                    names = "none"
                    days  = 999
                return {"pending_assignments": names, "days_until_deadline": days}
        except Exception as e:
            log.error(f"Context fetch error: {e}")
            return {"pending_assignments": "unknown", "days_until_deadline": 99}

    def _save_roast(self, trigger: str, message: str, user_id: int = 1):
        try:
            with get_db_ctx() as db:
                db.add(RoastLog(
                    user_id      = user_id,
                    trigger      = trigger,
                    message      = message,
                    session_date = date.today(),
                ))
        except Exception as e:
            log.error(f"Roast save error: {e}")
