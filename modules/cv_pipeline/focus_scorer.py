"""
Focus scorer — computes a rolling focus score from CV events.
Used by routes/cv.py and the behavior engine.
"""

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from db.models import CVEvent, ScreenSession


def compute_live_focus_score(db: Session, target_date: Optional[date] = None) -> float:
    """
    Returns 0–100 live focus score for the given date.
    Formula:
      base_score = productive_time / total_screen_time
      cv_bonus   = presence_ratio  (how much of desk time was actually present)
      penalty    = distraction_count * 3 points each (max 30)

    Final = clamp(base*60 + cv_bonus*40 - penalty, 0, 100)
    """
    target_date = target_date or date.today()

    # Screen stats
    sessions = db.query(ScreenSession).filter(ScreenSession.session_date == target_date).all()
    productive_s  = sum(s.duration_s or 0 for s in sessions if s.category == "productive")
    total_s       = sum(s.duration_s or 0 for s in sessions)

    screen_ratio = productive_s / total_s if total_s > 0 else 0.0

    # CV stats
    events = db.query(CVEvent).filter(CVEvent.session_date == target_date).all()
    present_count    = sum(1 for e in events if e.event_type in ("present", "returned"))
    distracted_count = sum(1 for e in events if e.event_type == "distracted")
    absent_count     = sum(1 for e in events if e.event_type == "absent")
    total_cv         = len(events)

    presence_ratio = present_count / total_cv if total_cv > 0 else 0.5  # default neutral

    penalty = min(distracted_count * 3, 30)

    score = (screen_ratio * 60) + (presence_ratio * 40) - penalty
    return round(max(0.0, min(100.0, score)), 1)
