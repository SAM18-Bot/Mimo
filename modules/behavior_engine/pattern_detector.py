"""
Pattern detector — analyses 7-day rolling history to find behavioral patterns.
Returns plain-English insight strings used in the EOD report and study advisor.

Example outputs:
  "You are most productive between 8 AM and 10 AM."
  "Your focus score drops every day after 9 PM."
  "You consistently avoid Mathematics."
  "Your distraction rate spikes on Mondays."
"""

import logging
from collections import defaultdict
from datetime import date, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from db.models import DailySummary, ScreenSession

log = logging.getLogger(__name__)

DAYS_BACK = 7


def get_weekly_patterns(db: Session) -> dict:
    """
    Returns a dict with pattern insights and raw weekly stats.
    Used by the AI daily_report to produce personalized recommendations.
    """
    today     = date.today()
    week_ago  = today - timedelta(days=DAYS_BACK)

    summaries = (
        db.query(DailySummary)
        .filter(DailySummary.date >= week_ago)
        .order_by(DailySummary.date)
        .all()
    )

    if not summaries:
        return {"insights": ["Not enough data yet — keep tracking for 7 days."], "raw": {}}

    # ── aggregate ─────────────────────────────────────────────────────────
    avg_focus    = _avg([s.focus_score or 0 for s in summaries])
    avg_prod_min = _avg([(s.productive_time_s or 0) // 60 for s in summaries])
    avg_dist_min = _avg([(s.distracted_time_s or 0) // 60 for s in summaries])
    avg_done_rate = _avg([
        (s.assignments_done / s.assignments_due) if (s.assignments_due and s.assignments_due > 0) else 1.0
        for s in summaries
    ]) * 100

    # Peak productive hour across the week
    hourly = defaultdict(int)
    sessions_this_week = (
        db.query(ScreenSession)
        .filter(ScreenSession.session_date >= week_ago)
        .filter(ScreenSession.category == "productive")
        .all()
    )
    for s in sessions_this_week:
        if s.started_at:
            hourly[s.started_at.hour] += (s.duration_s or 0)

    peak_hour   = max(hourly, key=hourly.get) if hourly else None
    worst_hour  = min(hourly, key=hourly.get) if hourly else None

    # Weakest days (lowest focus score)
    by_day = sorted(summaries, key=lambda s: s.focus_score or 0)
    worst_day = by_day[0].date.strftime("%A") if by_day else None

    # Subject avoidance (apps NOT seen that are study-related)
    insights = _build_insights(
        avg_focus    = avg_focus,
        avg_prod_min = avg_prod_min,
        avg_dist_min = avg_dist_min,
        avg_done_rate = avg_done_rate,
        peak_hour    = peak_hour,
        worst_day    = worst_day,
        summaries    = summaries,
    )

    return {
        "insights":       insights,
        "avg_focus_score": round(avg_focus, 1),
        "avg_productive_min": round(avg_prod_min),
        "avg_distracting_min": round(avg_dist_min),
        "peak_productive_hour": peak_hour,
        "completion_rate_pct": round(avg_done_rate),
        "weekly_data": _weekly_table(summaries),
    }


def _build_insights(
    avg_focus, avg_prod_min, avg_dist_min, avg_done_rate,
    peak_hour, worst_day, summaries,
) -> List[str]:
    insights = []

    # Focus trend
    if len(summaries) >= 3:
        recent_3 = [s.focus_score or 0 for s in summaries[-3:]]
        earlier  = [s.focus_score or 0 for s in summaries[:-3]]
        if _avg(recent_3) < _avg(earlier) - 10:
            insights.append("Your focus score has been declining over the last 3 days. Concerning trend.")
        elif _avg(recent_3) > _avg(earlier) + 10:
            insights.append("Your focus has improved over the last 3 days. Keep it up.")

    # Peak hour
    if peak_hour is not None:
        end_hour = (peak_hour + 2) % 24
        insights.append(
            f"You are most productive between {_fmt_hour(peak_hour)} and {_fmt_hour(end_hour)}. "
            f"Schedule hard tasks here."
        )

    # Distraction rate
    if avg_dist_min > avg_prod_min:
        insights.append(
            f"This week you spent more time distracted ({round(avg_dist_min)}m avg) "
            f"than studying ({round(avg_prod_min)}m avg). That needs to flip."
        )

    # Worst day
    if worst_day:
        insights.append(
            f"{worst_day} is consistently your worst focus day. "
            f"Plan lighter work or schedule a review session then."
        )

    # Assignment completion
    if avg_done_rate < 70:
        insights.append(
            f"You're completing only {round(avg_done_rate)}% of assignments on time. "
            f"Start earlier — waiting until the last day is clearly not working."
        )
    elif avg_done_rate >= 90:
        insights.append("Assignment completion rate is solid this week.")

    if not insights:
        insights.append(f"7-day average focus score: {round(avg_focus)}/100.")

    return insights


def _weekly_table(summaries) -> str:
    lines = []
    for s in summaries:
        lines.append(
            f"{s.date}: focus={s.focus_score or 0:.0f}, "
            f"productive={(s.productive_time_s or 0)//60}m, "
            f"distracted={(s.distracted_time_s or 0)//60}m"
        )
    return "\n".join(lines)


def _avg(vals) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _fmt_hour(h: int) -> str:
    if h == 0:  return "12 AM"
    if h < 12:  return f"{h} AM"
    if h == 12: return "12 PM"
    return f"{h-12} PM"
