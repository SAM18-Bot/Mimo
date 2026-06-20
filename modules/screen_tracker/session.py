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
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict

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
    ended_at:   Optional[datetime] = None
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

    def __init__(self, gap_threshold_s: Optional[int] = None):
        self._gap        = gap_threshold_s or config.SESSION_GAP_THRESHOLD
        self._pending:    Optional[Session] = None
        self._prev_close: Optional[datetime] = None
        self._completed:  List[Session] = []

    # ── public API ────────────────────────────────────────────────────────

    def on_window_change(
        self,
        app: str,
        title: str,
        category: str,
        ts: datetime,
    ) -> Optional[Session]:
        """
        Call every time the active window changes.
        Returns the completed Session if one was just closed, else None.
        """
        if self._pending is None:
            self._pending = Session(app=app, title=title, category=category, started_at=ts)
            return None

        if app == self._pending.app:
            # Same app — update title in case it changed (e.g. VS Code opened new file)
            self._pending.title = title
            return None

        # ── different app: decide whether to stitch ───────────────────────
        gap_s = (ts - (self._prev_close or ts)).total_seconds() if self._prev_close else 0

        if (
            self._prev_close is not None
            and gap_s < self._gap
            and app == self._pending.app   # returning to same app
        ):
            # Absorb the gap — user briefly left and came back
            self._pending.gap_events += 1
            log.debug(
                f"Gap absorbed: {app!r} returned after {gap_s:.0f}s "
                f"(threshold {self._gap}s)"
            )
            return None

        # Close current session, start new one
        self._pending.close(ts)
        completed        = self._pending
        self._prev_close = ts
        self._completed.append(completed)

        log.debug(
            f"Session closed: [{completed.category}] {completed.app!r} "
            f"{completed.duration_s}s"
        )

        self._pending = Session(app=app, title=title, category=category, started_at=ts)
        return completed

    def flush(self, ts: Optional[datetime] = None) -> Optional[Session]:
        """Close the pending session. Call on stop() or at end of day."""
        if self._pending and not self._pending.is_complete:
            self._pending.close(ts or datetime.now())
            completed = self._pending
            self._completed.append(completed)
            self._pending = None
            return completed
        return None

    def get_completed(self) -> List[Session]:
        return list(self._completed)

    def get_pending(self) -> Optional[Session]:
        return self._pending

    def reset(self) -> None:
        self._pending    = None
        self._prev_close = None
        self._completed  = []


# ── analytics ─────────────────────────────────────────────────────────────

def analyze_sessions(sessions: List[Session]) -> Dict:
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
    streaks: List[int] = []
    current_s          = 0
    prev_end: Optional[datetime] = None

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
