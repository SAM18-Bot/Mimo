"""
Behavior aggregator — pulls today's raw data from DB and computes
a clean stats dict ready for the AI report or the dashboard.
Now uses ProductivityScorer from scorer.py for consistent scoring.
"""

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from db.models import ScreenSession, CVEvent, Assignment, DailySummary
from modules.behavior_engine.scorer import ProductivityScorer

log = logging.getLogger(__name__)

_scorer = ProductivityScorer()


def get_daily_stats(db: Session, target_date: Optional[date] = None, user_id: int = 1) -> dict:
    if target_date is None:
        from db.models import ScheduleProfile
        import zoneinfo
        from datetime import datetime
        profile = db.query(ScheduleProfile).filter(ScheduleProfile.active == True, ScheduleProfile.user_id == user_id).first()
        if profile and profile.timezone:
            try:
                tz = zoneinfo.ZoneInfo(profile.timezone)
                target_date = datetime.now(tz).date()
            except Exception:
                target_date = date.today()
        else:
            target_date = date.today()

    # ── screen sessions ───────────────────────────────────────────────────
    sessions = (
        db.query(ScreenSession)
        .filter(ScreenSession.user_id == user_id)
        .filter(ScreenSession.session_date == target_date)
        .all()
    )

    productive_s  = sum(s.duration_s or 0 for s in sessions if s.category == "productive")
    distracting_s = sum(s.duration_s or 0 for s in sessions if s.category == "distracting")
    neutral_s     = sum(s.duration_s or 0 for s in sessions if s.category == "neutral")
    total_s       = productive_s + distracting_s + neutral_s

    prod_apps = _top_apps(sessions, "productive")
    dist_apps = _top_apps(sessions, "distracting")

    # Peak productive hour
    hourly = defaultdict(int)
    for s in sessions:
        if s.category == "productive" and s.started_at:
            hourly[s.started_at.hour] += (s.duration_s or 0)
    peak_hour = max(hourly, key=hourly.get) if hourly else None

    longest_focus = _longest_consecutive_productive(sessions)

    # ── CV events ─────────────────────────────────────────────────────────
    cv_events = (
        db.query(CVEvent)
        .filter(CVEvent.user_id == user_id)
        .filter(CVEvent.session_date == target_date)
        .all()
    )
    present_events    = sum(1 for e in cv_events if e.event_type in ("present", "returned"))
    distraction_count = sum(1 for e in cv_events if e.event_type == "distracted")
    absent_count      = sum(1 for e in cv_events if e.event_type == "absent")
    total_cv          = len(cv_events)

    # ── focus score via scorer ─────────────────────────────────────────────
    breakdown = _scorer.compute(
        productive_s      = productive_s,
        total_screen_s    = total_s,
        present_events    = present_events,
        total_cv_events   = total_cv,
        distraction_count = distraction_count,
        longest_focus_s   = longest_focus,
    )

    # ── assignments ───────────────────────────────────────────────────────
    due_today = db.query(Assignment).filter(Assignment.user_id == user_id, Assignment.due_date == target_date).all()
    done_today = [a for a in due_today if a.status == "done"]
    overdue = (
        db.query(Assignment)
        .filter(Assignment.user_id == user_id)
        .filter(Assignment.due_date < target_date)
        .filter(Assignment.status != "done")
        .all()
    )
    upcoming_3d = (
        db.query(Assignment)
        .filter(Assignment.due_date > target_date)
        .filter(Assignment.due_date <= target_date + timedelta(days=3))
        .filter(Assignment.status != "done")
        .all()
    )

    return {
        "date":               target_date.isoformat(),
        "productive_s":       productive_s,
        "productive_min":     productive_s // 60,
        "distracting_s":      distracting_s,
        "distracting_min":    distracting_s // 60,
        "neutral_s":          neutral_s,
        "neutral_min":        neutral_s // 60,
        "desk_time_min":      total_s // 60,
        "productive_apps":    prod_apps,
        "distracting_apps":   dist_apps,
        "focus_score":        breakdown.final_score,
        "letter_grade":       breakdown.letter_grade,
        "score_verdict":      breakdown.verdict,
        "distraction_count":  distraction_count,
        "absent_count":       absent_count,
        "longest_focus_min":  longest_focus // 60,
        "peak_hour":          peak_hour,
        "due_today":          [a.title for a in due_today],
        "submitted_today":    [a.title for a in done_today],
        "overdue_list":       [f"{a.title} (due {a.due_date})" for a in overdue],
        "upcoming_list":      [f"{a.title} (due {a.due_date})" for a in upcoming_3d],
    }


def save_daily_summary(db: Session, stats: dict):
    """Upsert a DailySummary row for the date."""
    target   = date.fromisoformat(stats["date"])
    existing = db.query(DailySummary).filter(DailySummary.date == target).first()
    row      = existing or DailySummary(date=target)

    row.productive_time_s = stats["productive_s"]
    row.distracted_time_s = stats["distracting_s"]
    row.neutral_time_s    = stats["neutral_s"]
    row.desk_time_s       = stats["desk_time_min"] * 60
    row.focus_score       = stats["focus_score"]
    row.distraction_count = stats["distraction_count"]
    row.assignments_due   = len(stats["due_today"])
    row.assignments_done  = len(stats["submitted_today"])
    row.peak_hour         = stats.get("peak_hour")

    if not existing:
        db.add(row)
    db.commit()


# ── private helpers ──────────────────────────────────────────────────────

def _top_apps(sessions, category: str, n: int = 3) -> str:
    totals = defaultdict(int)
    for s in sessions:
        if s.category == category:
            totals[s.app_name] += (s.duration_s or 0)
    if not totals:
        return "none"
    top = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:n]
    return ", ".join(f"{app} ({dur//60}m)" for app, dur in top)


def _longest_consecutive_productive(sessions) -> int:
    prod = [s for s in sessions if s.category == "productive" and s.duration_s]
    return max((s.duration_s for s in prod), default=0)


def _compute_focus_score(
    productive_s: int, total_screen_s: int, distraction_count: int
) -> float:
    """Backward-compatible simple score for callers that pass 3 args."""
    return _scorer.simple_score(productive_s, total_screen_s, distraction_count)
