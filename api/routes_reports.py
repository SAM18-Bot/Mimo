from datetime import date
from typing import Optional, List

from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import DailySummary, AccountabilityLog, RoastLog, User
from modules.behavior_engine.aggregator import get_daily_stats
from api.websocket import push_event
from api.routes_auth import current_user

router = APIRouter(prefix="/reports", tags=["reports"])


class AccountabilityAnswer(BaseModel):
    question: str
    answer:   str


# ── stats ─────────────────────────────────────────────────────────────────
@router.get("/stats")
def today_stats(target_date: Optional[date] = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Live aggregated stats for the dashboard. Called on page load + periodically."""
    stats = get_daily_stats(db, target_date, user_id=user.id)
    return stats


@router.get("/history")
def history(days: int = 7, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Last N days of daily summaries for trend charts."""
    rows = (
        db.query(DailySummary)
        .filter(DailySummary.user_id == user.id)
        .order_by(DailySummary.date.desc())
        .limit(days)
        .all()
    )
    return [
        {
            "date":             str(r.date),
            "focus_score":      r.focus_score,
            "productive_min":   (r.productive_time_s or 0) // 60,
            "distracting_min":  (r.distracted_time_s or 0) // 60,
            "assignments_done": r.assignments_done,
            "assignments_due":  r.assignments_due,
        }
        for r in rows
    ]


# ── EOD report ────────────────────────────────────────────────────────────
@router.post("/eod")
def trigger_eod(background_tasks: BackgroundTasks, user: User = Depends(current_user)):
    """Manually trigger the end-of-day report (useful for testing)."""
    from modules.ai_layer.daily_report import run_eod_report
    from modules.voice.speaker import speak

    def _run(u_id: int):
        report = run_eod_report(
            user_id      = u_id,
            speak_fn     = speak,
            broadcast_fn = push_event,
        )
        return report

    background_tasks.add_task(_run, user.id)
    return {"ok": True, "message": "EOD report generating in background..."}


@router.get("/eod/latest")
def latest_eod(user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.query(DailySummary).filter(DailySummary.user_id == user.id).order_by(DailySummary.date.desc()).first()
    if not row:
        return {"message": "No report yet"}
    return {
        "date":           str(row.date),
        "focus_score":    row.focus_score,
        "productive_min": (row.productive_time_s or 0) // 60,
        "ai_report":      row.ai_report_text,
    }


# ── accountability Q&A ────────────────────────────────────────────────────
@router.post("/accountability", status_code=201)
def log_accountability(payload: AccountabilityAnswer, user: User = Depends(current_user), db: Session = Depends(get_db)):
    entry = AccountabilityLog(
        user_id  = user.id,
        date     = date.today(),
        question = payload.question,
        answer   = payload.answer,
    )
    db.add(entry)
    db.commit()
    return {"ok": True}


@router.get("/accountability/today")
def today_accountability(user: User = Depends(current_user), db: Session = Depends(get_db)):
    logs = (
        db.query(AccountabilityLog)
        .filter(AccountabilityLog.user_id == user.id)
        .filter(AccountabilityLog.date == date.today())
        .all()
    )
    return [{"question": l.question, "answer": l.answer} for l in logs]


# ── roast log ─────────────────────────────────────────────────────────────
@router.get("/roasts")
def today_roasts(user: User = Depends(current_user), db: Session = Depends(get_db)):
    roasts = (
        db.query(RoastLog)
        .filter(RoastLog.user_id == user.id)
        .filter(RoastLog.session_date == date.today())
        .order_by(RoastLog.timestamp.desc())
        .all()
    )
    return [{"trigger": r.trigger, "message": r.message, "ts": str(r.timestamp)} for r in roasts]


@router.get("/patterns")
def weekly_patterns(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """
    7-day behavioral pattern analysis:
    peak productive hours, distraction trends, worst day, subject avoidance.
    """
    from modules.behavior_engine.pattern_detector import get_weekly_patterns
    return get_weekly_patterns(db, user_id=user.id)


@router.get("/score/breakdown")
def score_breakdown(target_date: Optional[date] = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """
    Detailed focus score breakdown:
    productive_pts, presence_pts, penalty, bonus, letter_grade, verdict.
    """
    from modules.behavior_engine.aggregator import get_daily_stats
    from modules.behavior_engine.scorer import ProductivityScorer
    from db.models import CVEvent, ScreenSession

    target_date = target_date or date.today()

    sessions  = db.query(ScreenSession).filter(ScreenSession.user_id == user.id).filter(ScreenSession.session_date == target_date).all()
    cv_events = db.query(CVEvent).filter(CVEvent.user_id == user.id).filter(CVEvent.session_date == target_date).all()

    productive_s  = sum(s.duration_s or 0 for s in sessions if s.category == "productive")
    total_s       = sum(s.duration_s or 0 for s in sessions)
    present_ev    = sum(1 for e in cv_events if e.event_type in ("present", "returned"))
    dist_count    = sum(1 for e in cv_events if e.event_type == "distracted")
    longest       = max((s.duration_s or 0 for s in sessions if s.category == "productive"), default=0)

    scorer = ProductivityScorer()
    bd     = scorer.compute(productive_s, total_s, present_ev, len(cv_events), dist_count, longest)

    return {
        "date":             target_date.isoformat(),
        "final_score":      bd.final_score,
        "letter_grade":     bd.letter_grade,
        "verdict":          bd.verdict,
        "productive_pts":   bd.productive_pts,
        "presence_pts":     bd.presence_pts,
        "switch_penalty":   bd.switch_penalty,
        "focus_bonus":      bd.focus_bonus,
        "productive_ratio": bd.productive_ratio,
        "longest_focus_min": bd.longest_focus_min,
        "distraction_count": bd.distraction_count,
    }
