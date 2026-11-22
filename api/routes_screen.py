from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from api.routes_auth import current_user
from db.database import get_db
from db.models import ScreenSession, User

router = APIRouter(prefix="/screen", tags=["screen"])


# ── schemas ───────────────────────────────────────────────────────────────

class SessionOut(BaseModel):
    id:           int
    device:       str
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
    device_minutes:  dict[str, int]
    top_productive:  list[dict]
    top_distracting: list[dict]


class MockWindowEvent(BaseModel):
    app:      str
    title:    str = ""
    category: Literal["", "productive", "distracting", "neutral"] = ""


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

    device_seconds = {}
    for session in sessions:
        device_seconds[session.device] = device_seconds.get(session.device, 0) + (session.duration_s or 0)

    return {
        "device_minutes": {device: seconds // 60 for device, seconds in device_seconds.items()},
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
    from db.database import get_db_ctx

    with get_db_ctx() as db:
        latest = db.query(ScreenSession).filter(
            ScreenSession.user_id == user.id, ScreenSession.ended_at.is_not(None)
        ).order_by(ScreenSession.started_at.desc()).first()
        if latest is None:
            return {"app": "Unknown", "title": "", "category": "neutral"}
        return {
            "app": latest.app_name, "title": (latest.window_title or "")[:80],
            "category": latest.category or "neutral",
        }


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
        "user_id":  user.id,
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
            roast_engine.on_window_change(payload.app, payload.title, cat, user_id=user.id)
    except Exception:
        pass

    from modules.schedule.manager import active_study_block
    return {"ok": True, "app": payload.app, "category": cat,
            "study_block_active": cat == "distracting" and active_study_block(db, user.id)}

class StitchedSession(BaseModel):
    app_name: str = Field(min_length=1, max_length=200)
    window_title: str = Field(max_length=500)
    category: Literal["productive", "distracting", "neutral"]
    started_at: datetime
    ended_at: datetime | None = None
    duration_s: int = Field(ge=0, le=86400)
    session_date: date

    @model_validator(mode="after")
    def validate_session(self):
        if self.session_date != self.started_at.date():
            raise ValueError("Session date must match its start date")
        if self.ended_at is not None:
            try:
                if self.ended_at < self.started_at:
                    raise ValueError("Session end precedes its start")
            except TypeError as exc:
                raise ValueError("Session timestamps must use consistent timezone offsets") from exc
        return self


@router.post("/session")
def save_session(payload: StitchedSession, user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.add(ScreenSession(
        user_id      = user.id,
        device       = "desktop",
        app_name     = payload.app_name,
        window_title = payload.window_title,
        category     = payload.category,
        started_at   = payload.started_at,
        ended_at     = payload.ended_at,
        duration_s   = payload.duration_s,
        session_date = payload.session_date,
    ))
    db.commit()
    return {"ok": True}
