"""
Session stitching and analytics.

Problem this solves:
  Without stitching: user on VS Code → alt-tabs to Google for 4s → back to VS Code
  Result: three separate DB rows (code 2h, chrome 4s, code 1h)

  With stitching: brief gaps below SESSION_GAP_THRESHOLD are absorbed into the
  parent session. The two VS Code windows become one 3h session with 1 gap_event.

Also provides session analytics:
  - Longest focused stretch
  - Productive streaks (consecutive productive sessions < 5min apart)
  - Session quality score per session
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

import config

log = logging.getLogger(__name__)

STREAK_GAP_S = 300  # 5 minutes — gap allowed between sessions in a streak


# ── data classes ──────────────────────────────────────────────────────────

@dataclass
class RawWindowEvent:
    app:       str
    title:     str
    category:  str
    timestamp: datetime


@dataclass
class Session:
    app:        str
    title:      str
    category:   str
    started_at: datetime
    ended_at:   datetime | None = None
    duration_s: int = 0
    gap_events: int = 0   # times user briefly left and came back within gap threshold

    @property
    def is_complete(self) -> bool:
        return self.ended_at is not None

    def close(self, ended_at: datetime) -> None:
        self.ended_at  = ended_at
        self.duration_s = max(0, int((ended_at - self.started_at).total_seconds()))

    def quality_score(self) -> float:
        """
        0–100 score for this individual session.
        Rewards: long productive sessions, penalises short distracting ones.
        """
        if self.category == "productive":
            # 60 min = 100, scales linearly
            return min(100.0, (self.duration_s / 3600) * 100)
        elif self.category == "distracting":
            # 10 min = 0, every minute less gives +10
            return max(0.0, 100.0 - (self.duration_s / 60) * 10)
        else:
            return 50.0


# ── stitcher ──────────────────────────────────────────────────────────────

class SessionStitcher:
    """
    Converts raw window-change events into stitched sessions.
    If the user returns to the same app within SESSION_GAP_THRESHOLD seconds,
    the gap is absorbed rather than starting a new session.
    """

    def __init__(self, gap_threshold_s: int | None = None):
        self._gap        = gap_threshold_s or config.SESSION_GAP_THRESHOLD
        self._pending:    Session | None = None
        self._completed:  list[Session] = []

        # Interruption tracking
        self._int_app:      str | None = None
        self._int_title:    str | None = None
        self._int_category: str | None = None
        self._int_start:    datetime | None = None

    # ── public API ────────────────────────────────────────────────────────

    def on_window_change(
        self,
        app: str,
        title: str,
        category: str,
        ts: datetime,
    ) -> list[Session]:
        """
        Call every time the active window changes.
        Returns a list of completed Sessions.
        """
        if self._pending is None:
            self._pending = Session(app=app, title=title, category=category, started_at=ts)
            return []

        if self._int_app is None:
            # Normal state, no interruption buffered
            if app == self._pending.app:
                # Same app — update title
                self._pending.title = title
                return []
            else:
                # Started an interruption
                self._int_app      = app
                self._int_title    = title
                self._int_category = category
                self._int_start    = ts
                return []
        else:
            # We are currently buffering an interruption
            gap_s = (ts - self._int_start).total_seconds()

            if app == self._pending.app:
                # Returned to the original app
                if gap_s < self._gap:
                    # Absorb the gap!
                    self._pending.gap_events += 1
                    self._pending.title = title
                    self._int_app = None
                    log.debug(f"Gap absorbed: {app!r} returned after {gap_s:.0f}s (threshold {self._gap}s)")
                    return []
                else:
                    # Gap too large. Close the pending session at the time interruption started
                    self._pending.close(self._int_start)
                    c1 = self._pending
                    self._completed.append(c1)
                    
                    # Close the interruption itself at 'ts'
                    c2 = Session(app=self._int_app, title=self._int_title, category=self._int_category, started_at=self._int_start)
                    c2.close(ts)
                    self._completed.append(c2)
                    
                    # Start fresh pending for the app we just returned to
                    self._pending = Session(app=app, title=title, category=category, started_at=ts)
                    self._int_app = None
                    return [c1, c2]
            else:
                # Did not return to the original app
                if app == self._int_app:
                    # Still in the same interrupting app, maybe title changed
                    self._int_title = title
                    # Did we exceed the gap threshold while in the interrupting app?
                    if gap_s >= self._gap:
                        # Exceeded gap. The original pending session is officially dead.
                        self._pending.close(self._int_start)
                        c1 = self._pending
                        self._completed.append(c1)
                        
                        # The interruption becomes the new pending session!
                        self._pending = Session(app=self._int_app, title=self._int_title, category=self._int_category, started_at=self._int_start)
                        self._int_app = None
                        return [c1]
                    return []
                else:
                    # Switched to a THIRD app!
                    if gap_s < self._gap:
                        # We just update the interruption to the new app. The gap continues ticking!
                        self._int_app = app
                        self._int_title = title
                        self._int_category = category
                        # DO NOT update _int_start, because the total gap since we left the FIRST app is what matters.
                        return []
                    else:
                        # Exceeded gap. Original is dead, interruption is dead.
                        self._pending.close(self._int_start)
                        c1 = self._pending
                        self._completed.append(c1)
                        
                        c2 = Session(app=self._int_app, title=self._int_title, category=self._int_category, started_at=self._int_start)
                        c2.close(ts)
                        self._completed.append(c2)
                        
                        # The third app becomes pending
                        self._pending = Session(app=app, title=title, category=category, started_at=ts)
                        self._int_app = None
                        return [c1, c2]

    def flush(self, ts: datetime | None = None) -> list[Session]:
        """Close the pending session. Call on stop() or at end of day."""
        ts = ts or datetime.now()
        closed = []
        if self._pending and not self._pending.is_complete:
            if self._int_app is None:
                self._pending.close(ts)
                closed.append(self._pending)
                self._completed.append(self._pending)
            else:
                # We have an open interruption
                gap_s = (ts - self._int_start).total_seconds()
                if gap_s < self._gap:
                    # Discard the brief interruption, close original pending at int_start
                    self._pending.close(self._int_start)
                    closed.append(self._pending)
                    self._completed.append(self._pending)
                else:
                    # Flush both
                    self._pending.close(self._int_start)
                    closed.append(self._pending)
                    self._completed.append(self._pending)
                    
                    c2 = Session(app=self._int_app, title=self._int_title, category=self._int_category, started_at=self._int_start)
                    c2.close(ts)
                    closed.append(c2)
                    self._completed.append(c2)
        self._pending = None
        self._int_app = None
        return closed

    def get_completed(self) -> list[Session]:
        return list(self._completed)

    def get_pending(self) -> Session | None:
        return self._pending

    def reset(self) -> None:
        self._pending = None
        self._completed = []
        self._int_app = None
        self._int_start = None


# ── analytics ─────────────────────────────────────────────────────────────

def analyze_sessions(sessions: list[Session]) -> dict:
    """
    Compute session analytics from a list of completed sessions.
    Called by the behavior engine aggregator.
    """
    if not sessions:
        return {
            "longest_focus_s":       0,
            "longest_focus_min":     0,
            "best_streak_min":       0,
            "productive_streaks":    [],
            "total_sessions":        0,
            "productive_session_count": 0,
            "avg_session_quality":   0.0,
        }

    prod_sessions = [s for s in sessions if s.category == "productive"]

    # Longest single productive session
    longest_s = max((s.duration_s for s in prod_sessions), default=0)

    # Productive streaks: consecutive productive sessions with < STREAK_GAP_S between them
    streaks: list[int] = []
    current_s          = 0
    prev_end: datetime | None = None

    for s in sorted(prod_sessions, key=lambda x: x.started_at):
        if prev_end is None:
            current_s = s.duration_s
        else:
            gap = (s.started_at - prev_end).total_seconds()
            if gap <= STREAK_GAP_S:
                current_s += s.duration_s
            else:
                if current_s > 0:
                    streaks.append(current_s)
                current_s = s.duration_s
        prev_end = s.ended_at

    if current_s > 0:
        streaks.append(current_s)

    quality_scores = [s.quality_score() for s in sessions if s.duration_s > 5]
    avg_quality    = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

    return {
        "longest_focus_s":       longest_s,
        "longest_focus_min":     longest_s // 60,
        "best_streak_min":       max(streaks, default=0) // 60,
        "productive_streaks":    streaks,
        "total_sessions":        len(sessions),
        "productive_session_count": len(prod_sessions),
        "avg_session_quality":   round(avg_quality, 1),
    }
