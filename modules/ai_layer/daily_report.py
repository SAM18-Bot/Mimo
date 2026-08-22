"""
End-of-day report pipeline.
Pulls aggregated stats + 7-day patterns + study advisor, queries OpenAI,
saves result to DB, speaks via TTS, broadcasts to dashboard.
"""

import logging
from collections.abc import Callable
from datetime import date

from db.database import get_db_ctx
from db.models import AccountabilityLog, DailySummary
from modules.ai_layer.client import generate_eod_report
from modules.behavior_engine.aggregator import get_daily_stats, save_daily_summary

log = logging.getLogger(__name__)


def run_eod_report(
    user_id:      int = 1,
    speak_fn:     Callable | None = None,
    broadcast_fn: Callable | None = None,
):
    """
    Full EOD pipeline:
    1. Aggregate today's screen + CV stats
    2. Pull 7-day behavioral patterns
    3. Get study advisor next-step recommendation
    4. Pull morning accountability answers
    5. Call OpenAI (or fallback) for report generation
    6. Save to DB, speak, broadcast to dashboard
    """
    from db.models import User
    with get_db_ctx() as db:
        user = db.get(User, user_id)
        api_key = user.api_key if user else None
        stats = get_daily_stats(db, user_id=user_id)
        accountability_answers = _get_accountability_answers(db, user_id)

        # 7-day pattern insights
        weekly_insights = ""
        weekly_data     = ""
        peak_window     = "unknown"
        try:
            from modules.behavior_engine.pattern_detector import get_weekly_patterns
            patterns       = get_weekly_patterns(db, user_id=user_id)
            weekly_insights = "\n".join(patterns.get("insights", []))
            weekly_data     = patterns.get("weekly_data", "")
            peak_window     = _fmt_peak(patterns.get("peak_productive_hour"))
        except Exception as e:
            log.debug("Pattern detector failed: %s", e)

        # Study advisor
        next_to_study = "unknown"
        try:
            from modules.ai_layer.study_advisor import StudyAdvisor
            next_to_study = StudyAdvisor(db).get_next_to_study(user_id=user_id)
        except Exception as e:
            log.debug("Study advisor failed: %s", e)

    context = {
        "date":                   stats["date"],
        "focus_score":            stats["focus_score"],
        "productive_min":         stats["productive_min"],
        "distracting_min":        stats["distracting_min"],
        "top_apps":               stats.get("top_apps", ""),
        "weekly_insights":        weekly_insights,
        "weekly_data":            weekly_data,
        "peak_productive_window": peak_window,
        "next_to_study":          next_to_study,
        "accountability_answers": accountability_answers,
    }

    log.info("Running EOD report for %s", stats["date"])
    report = generate_eod_report(context, api_key=api_key)

    if not report:
        log.warning("EOD report generation failed — using fallback")
        report = _fallback_report(stats)

    _save_report(stats, report, user_id)

    spoken = _format_spoken_report(report, stats)
    log.info("EOD Summary:\n%s", spoken)

    if speak_fn:
        speak_fn(spoken)

    # Native OS notification (desktop mode)
    try:
        from desktop.notifications import notify_eod
        notify_eod(stats["focus_score"], stats.get("letter_grade", "?"))
    except ImportError:
        pass  # not in desktop mode

    if broadcast_fn:
        broadcast_fn({
            "type":   "eod_report",
            "report": report,
            "stats":  stats,
        })

    return report


# ── helpers ───────────────────────────────────────────────────────────────

def _get_accountability_answers(db, user_id: int) -> str:
    logs = (
        db.query(AccountabilityLog)
        .filter(AccountabilityLog.user_id == user_id)
        .filter(AccountabilityLog.date == date.today())
        .all()
    )
    lines = [f"Q: {l.question}\nA: {l.answer}" for l in logs if l.answer]
    return "\n".join(lines)


def _save_report(stats: dict, report: dict, user_id: int):
    with get_db_ctx() as db:
        save_daily_summary(db, stats, user_id=user_id)
        row = db.query(DailySummary).filter(
            DailySummary.user_id == user_id,
            DailySummary.date == date.fromisoformat(stats["date"])
        ).first()
        if row:
            row.ai_report_text = str(report)
            db.commit()


def _format_spoken_report(report: dict, stats: dict) -> str:
    parts = [
        "End of day report.",
        report.get("summary", ""),
        f"Focus score: {stats['focus_score']}, grade {stats.get('letter_grade','?')}.",
        report.get("roast_or_praise", ""),
        f"Tomorrow: {report.get('tomorrow_priority', 'check your assignments')}.",
    ]
    return " ".join(p for p in parts if p)


def _fallback_report(stats: dict) -> dict:
    prod_h = stats["productive_min"] // 60
    stats["distracting_min"] // 60
    grade  = stats.get("letter_grade", "?")
    return {
        "summary":              f"You studied for {prod_h} hours. Grade: {grade}.",
        "focus_score_comment":  f"Focus score: {stats['focus_score']}/100.",
        "biggest_win":          "You showed up.",
        "biggest_fail":         f"{stats['distracting_min']} minutes wasted on distractions.",
        "tomorrow_priority":    "Start assignments earlier.",
        "study_recommendation": "Study your weakest subject first.",
        "roast_or_praise":      "Tomorrow, do better." if stats["focus_score"] < 60 else "Decent day.",
    }


def _fmt_peak(hour) -> str:
    if hour is None:
        return "unknown"
    suffix = "AM" if hour < 12 else "PM"
    h = hour if hour <= 12 else hour - 12
    return f"{h}:00 {suffix}"
