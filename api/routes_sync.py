from datetime import date as CalendarDate, datetime, time

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from api.routes_auth import current_user
from db.database import get_db
from db.models import DailySummary, ScreenSession, SyncReceipt, User
from modules.assignments.manager import get_upcoming
from modules.behavior_engine.aggregator import get_daily_stats

router = APIRouter(prefix="/sync", tags=["Sync"])

class AssignmentModel(BaseModel):
    id: int
    title: str
    subject: str | None = None
    due_date: str
    due_time: str | None = None
    priority: str = "medium"
    status: str = "pending"
    notes: str | None = None

class DailyStatsModel(BaseModel):
    date: str
    productive_min: int
    distracting_min: int
    neutral_min: int
    focus_score: float

class SyncPayload(BaseModel):
    date: CalendarDate
    mobileProductiveMin: int = Field(ge=0, le=1440)
    mobileDistractingMin: int = Field(ge=0, le=1440)
    mobileNeutralMin: int = Field(ge=0, le=1440)
    sync_id: str | None = Field(default=None, min_length=8, max_length=64)
    app_name: str | None = Field(default=None, min_length=1, max_length=200)
    assignments: list[AssignmentModel] = []
    mergedStats: DailyStatsModel | None = None

@router.post("/push")
def push_sync(
    payload: SyncPayload,
    user: User = Depends(current_user),
    db: Session = Depends(get_db)
):
    """Merge one batch of mobile usage into reportable screen time."""
    insert = pg_insert if db.get_bind().dialect.name == "postgresql" else sqlite_insert
    if payload.sync_id:
        claim = insert(SyncReceipt).values(
            user_id=user.id, sync_id=payload.sync_id, summary_date=payload.date
        ).on_conflict_do_nothing(index_elements=["user_id", "sync_id"])
        if db.execute(claim).rowcount == 0:
            return {"status": "ok", "duplicate": True}

    seconds = {
        "productive": payload.mobileProductiveMin * 60,
        "distracting": payload.mobileDistractingMin * 60,
        "neutral": payload.mobileNeutralMin * 60,
    }
    started_at = datetime.combine(payload.date, time.min)
    db.add_all([
        ScreenSession(
            user_id=user.id, device="android", app_name=payload.app_name or "Android usage", category=category,
            started_at=started_at, duration_s=duration, session_date=payload.date,
        )
        for category, duration in seconds.items() if duration
    ])

    totals = {
        "productive_time_s": seconds["productive"],
        "distracted_time_s": seconds["distracting"],
        "neutral_time_s": seconds["neutral"],
        "desk_time_s": sum(seconds.values()),
    }
    summary = insert(DailySummary).values(user_id=user.id, date=payload.date, **totals)
    db.execute(summary.on_conflict_do_update(
        index_elements=["user_id", "date"],
        set_={
            name: func.coalesce(getattr(DailySummary, name), 0) + getattr(summary.excluded, name)
            for name in totals
        },
    ))
    db.commit()
    return {"status": "ok", "duplicate": False}

@router.get("/pull", response_model=SyncPayload)
def pull_sync(
    user: User = Depends(current_user),
    db: Session = Depends(get_db)
):
    """
    Returns the merged assignments and stats to the Android app.
    """
    stats_dict = get_daily_stats(db, user_id=user.id)
    merged_stats = DailyStatsModel(
        date=stats_dict["date"],
        productive_min=stats_dict["productive_min"],
        distracting_min=stats_dict["distracting_min"],
        neutral_min=stats_dict["neutral_min"],
        focus_score=stats_dict["focus_score"]
    )
    
    tasks = get_upcoming(db, user_id=user.id, days=7)
    assignments_list = []
    for t in tasks:
        assignments_list.append(AssignmentModel(
            id=t.id,
            title=t.title,
            subject=t.subject,
            due_date=str(t.due_date),
            due_time=t.due_time,
            priority=t.priority,
            status=t.status,
            notes=t.notes
        ))
        
    return SyncPayload(
        date=stats_dict["date"],
        mobileProductiveMin=0,
        mobileDistractingMin=0,
        mobileNeutralMin=0,
        assignments=assignments_list,
        mergedStats=merged_stats
    )
