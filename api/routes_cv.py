from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import CVEvent, User
from api.routes_auth import current_user

router = APIRouter(prefix="/cv", tags=["cv"])


@router.get("/events")
def get_cv_events(target_date: Optional[date] = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    target_date = target_date or date.today()
    events = (
        db.query(CVEvent)
        .filter(CVEvent.user_id == user.id)
        .filter(CVEvent.session_date == target_date)
        .order_by(CVEvent.timestamp.desc())
        .limit(100)
        .all()
    )
    return [{"event": e.event_type, "ts": str(e.timestamp)} for e in events]


@router.get("/presence")
def current_presence():
    """
    Returns the last known CV state. Polled by dashboard as REST fallback.
    Real-time updates come via WebSocket cv_event messages.
    """
    from modules.cv_pipeline.presence import PresenceMonitor
    # The singleton state is maintained in the running PresenceMonitor instance.
    # This endpoint is a simple fallback — the dashboard uses WebSocket primarily.
    return {"status": "check websocket for live state"}


@router.get("/focus/today")
def focus_today(user: User = Depends(current_user), db: Session = Depends(get_db)):
    from modules.behavior_engine.aggregator import get_daily_stats
    stats = get_daily_stats(db, user_id=user.id)
    return {
        "focus_score":      stats["focus_score"],
        "distraction_count": stats["distraction_count"],
        "absent_count":     stats["absent_count"],
        "productive_min":   stats["productive_min"],
    }


# ── MOCK endpoint (no hardware needed for testing) ────────────────────────
from pydantic import BaseModel as _BM

class MockCVEvent(_BM):
    event: str   # present | absent | distracted | returned

@router.post("/mock")
def mock_cv_event(payload: MockCVEvent, user: User = Depends(current_user)):
    """
    Inject a fake CV event for testing without ESP32-CAM.
    Called by mock_cv.py or manually via /docs.
    """
    from datetime import datetime, date as _date
    from db.database import get_db_ctx
    from db.models import CVEvent
    from api.websocket import push_event

    valid = {"present", "absent", "distracted", "returned"}
    if payload.event not in valid:
        from fastapi import HTTPException
        raise HTTPException(400, f"event must be one of {valid}")

    now = datetime.now()
    with get_db_ctx() as db:
        db.add(CVEvent(
            user_id      = user.id,
            event_type   = payload.event,
            timestamp    = now,
            session_date = now.date(),
        ))

    push_event({
        "type":  "cv_event",
        "event": payload.event,
        "ts":    now.isoformat(),
    })

    # Also trigger roast engine if applicable
    try:
        from schedulers.background_tasks import roast_engine
        if roast_engine:
            roast_engine.on_cv_event(payload.event)
    except Exception:
        pass

    return {"ok": True, "event": payload.event}
