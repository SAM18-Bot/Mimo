"""
APScheduler jobs:
  1. EOD report       — fires at 10 PM every day
  2. Reminder checker — fires every 15 minutes via ReminderLoop
  3. Stats pusher     — fires every 60 seconds, pushes live stats to dashboard
  4. Morning Q&A      — fires at 8 AM, asks accountability questions
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

import config
from modules.assignments.reminder import ReminderLoop

log = logging.getLogger(__name__)

_scheduler:      BackgroundScheduler = None
_reminder_loop:  ReminderLoop        = None


def start_scheduler(speak_fn=None, broadcast_fn=None):
    global _scheduler, _reminder_loop

    from db.database import get_db_ctx
    from db.models import ScheduleProfile
    tz_str = "UTC"
    try:
        with get_db_ctx() as db:
            profile = db.query(ScheduleProfile).filter(ScheduleProfile.active == True).first()
            if profile and profile.timezone:
                tz_str = profile.timezone
    except Exception as e:
        log.warning("Could not fetch timezone from profile, defaulting to UTC: %s", e)

    import pytz
    if tz_str not in pytz.all_timezones:
        log.warning("Invalid timezone '%s', defaulting to UTC", tz_str)
        tz_str = "UTC"

    _scheduler = BackgroundScheduler(timezone=tz_str)

    # ── EOD report @ configured hour ──────────────────────────────────────
    _scheduler.add_job(
        func             = _run_eod,
        trigger          = CronTrigger(hour=config.EOD_REPORT_HOUR, minute=0),
        id               = "eod_report",
        name             = "End-of-day report",
        replace_existing = True,
        kwargs           = {"speak_fn": speak_fn, "broadcast_fn": broadcast_fn},
    )

    # ── Morning accountability Q&A @ 8 AM ────────────────────────────────
    _scheduler.add_job(
        func             = _morning_accountability,
        trigger          = CronTrigger(hour=8, minute=0),
        id               = "morning_qa",
        name             = "Morning accountability Q&A",
        replace_existing = True,
        kwargs           = {"speak_fn": speak_fn, "broadcast_fn": broadcast_fn},
    )

    # ── Live stats push every 60 seconds ──────────────────────────────────
    _scheduler.add_job(
        func             = _push_live_stats,
        trigger          = IntervalTrigger(seconds=60),
        id               = "live_stats",
        name             = "Live stats pusher",
        replace_existing = True,
        kwargs           = {"broadcast_fn": broadcast_fn},
    )

    # ── Reminder loop — driven by ReminderLoop as background thread ───────
    _reminder_loop = ReminderLoop(
        speak_fn     = speak_fn,
        broadcast_fn = broadcast_fn,
        poll_minutes = config.REMINDER_CHECK_INTERVAL_MINUTES,
    )
    _reminder_loop.start()

    _scheduler.start()
    log.info("Scheduler started.")
    return _scheduler


def stop_scheduler():
    global _scheduler, _reminder_loop
    if _reminder_loop:
        _reminder_loop.stop()
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        log.info("Scheduler stopped.")


# ── job implementations ────────────────────────────────────────────────────

def _run_eod(speak_fn=None, broadcast_fn=None):
    log.info("Running scheduled EOD report...")
    try:
        from modules.ai_layer.daily_report import run_eod_report
        run_eod_report(speak_fn=speak_fn, broadcast_fn=broadcast_fn)
    except Exception as e:
        log.error("EOD report job error: %s", e)


def _morning_accountability(speak_fn=None, broadcast_fn=None):
    log.info("Running morning accountability questions...")
    try:
        if speak_fn:
            speak_fn("Good morning. Let's plan your day. I'll ask you a few questions.")
        if broadcast_fn:
            broadcast_fn({
                "type":      "morning_qa",
                "questions": config.ACCOUNTABILITY_QUESTIONS,
            })
    except Exception as e:
        log.error("Morning Q&A job error: %s", e)


def _push_live_stats(broadcast_fn=None):
    if not broadcast_fn:
        return
    try:
        from db.database import get_db_ctx
        from modules.behavior_engine.aggregator import get_daily_stats
        with get_db_ctx() as db:
            stats = get_daily_stats(db)
        broadcast_fn({"type": "stats_update", "stats": stats})
    except Exception as e:
        log.error("Stats push error: %s", e)
