from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from api.routes_auth import current_user
from db.database import get_db
from db.models import ScreenSession, User

router = APIRouter(prefix="/screen", tags=["screen"])


# ── schemas ───────────────────────────────────────────────────────────────

class SessionOut(BaseModel):
    id:           int
    app_name:     str
    window_title: str | None
    category:     str | None
    duration_s:   int | None
    session_date: date | None

    model_config = ConfigDict(from_attributes=True)


class DailyBreakdown(BaseModel):
    productive_min:  int
    distracting_min: int
    neutral_min:     int
    total_min:       int
    top_productive:  list[dict]
    top_distracting: list[dict]


class MockWindowEvent(BaseModel):
    app:      str
    title:    str = ""
    category: str = ""   # leave blank to auto-detect


# ── endpoints ─────────────────────────────────────────────────────────────

@router.get("/sessions", response_model=list[SessionOut])
def get_sessions(
    target_date: date | None = Query(default=None),
    category:    str | None  = Query(default=None),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    q = db.query(ScreenSession).filter(ScreenSession.user_id == user.id)
    if target_date:
        q = q.filter(ScreenSession.session_date == target_date)
    if category:
        q = q.filter(ScreenSession.category == category)
    return q.order_by(ScreenSession.started_at.desc()).limit(200).all()


@router.get("/breakdown", response_model=DailyBreakdown)
def daily_breakdown(
    target_date: date | None = Query(default=None),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    target_date = target_date or date.today()
    sessions = db.query(ScreenSession).filter(
        ScreenSession.user_id == user.id,
        ScreenSession.session_date == target_date
    ).all()

    prod_s = sum(s.duration_s or 0 for s in sessions if s.category == "productive")
    dist_s = sum(s.duration_s or 0 for s in sessions if s.category == "distracting")
    neut_s = sum(s.duration_s or 0 for s in sessions if s.category == "neutral")

    def top_apps(cat, n=5):
        from collections import defaultdict
        totals = defaultdict(int)
        for s in sessions:
            if s.category == cat:
                totals[s.app_name] += (s.duration_s or 0)
        return sorted(
            [{"app": k, "minutes": v // 60} for k, v in totals.items()],
            key=lambda x: x["minutes"], reverse=True,
        )[:n]

    return {
        "productive_min":  prod_s // 60,
        "distracting_min": dist_s // 60,
        "neutral_min":     neut_s // 60,
        "total_min":       (prod_s + dist_s + neut_s) // 60,
        "top_productive":  top_apps("productive"),
        "top_distracting": top_apps("distracting"),
    }


@router.get("/live")
def live_status(user: User = Depends(current_user)):
    """Returns the most recently tracked app (REST fallback for dashboard)."""
    from modules.screen_tracker.categorizer import categorize_app
    from modules.screen_tracker.tracker import get_active_window
    app, title = get_active_window()
    cat = categorize_app(app, title)
    return {"app": app, "title": title[:80], "category": cat}


@router.post("/mock")
def mock_window_change(payload: MockWindowEvent, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """
    Inject a fake window-change event for testing without real OS hooks.
    Called by mock_screen.py or /docs.
    """
    from datetime import datetime

    from api.websocket import push_event
    from modules.screen_tracker.categorizer import categorize_app

    cat = payload.category or categorize_app(payload.app, payload.title)
    now = datetime.now()

    # No fake session insertion here anymore! Android uses /sync/push for stats.

    event = {
        "type":     "window_change",
        "app":      payload.app,
        "title":    payload.title,
        "category": cat,
        "ts":       now.isoformat(),
    }
    push_event(event)

    # Trigger roast engine
    try:
        from schedulers.background_tasks import roast_engine
        if roast_engine:
            roast_engine.on_window_change(payload.app, payload.title, cat)
    except Exception:
        pass

    return {"ok": True, "app": payload.app, "category": cat}

class StitchedSession(BaseModel):
    app_name: str
    window_title: str
    category: str
    started_at: str
    ended_at: str | None = None
    duration_s: int
    session_date: str

@router.post("/session")
def save_session(payload: StitchedSession, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from datetime import date, datetime
    db.add(ScreenSession(
        user_id      = user.id,
        app_name     = payload.app_name,
        window_title = payload.window_title,
        category     = payload.category,
        started_at   = datetime.fromisoformat(payload.started_at),
        ended_at     = datetime.fromisoformat(payload.ended_at) if payload.ended_at else None,
        duration_s   = payload.duration_s,
        session_date = date.fromisoformat(payload.session_date),
    ))
    db.commit()
    return {"ok": True}
