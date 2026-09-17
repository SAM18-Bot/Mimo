from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.routes_auth import current_user
from db.database import get_db
from db.models import DailySummary, SyncReceipt, User
from modules.assignments.manager import get_upcoming
from modules.behavior_engine.aggregator import get_daily_stats

router = APIRouter(prefix="/sync", tags=["Sync"])

class AssignmentModel(BaseModel):
    id: int
    title: str
    subject: str | None = None
    due_date: str
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
    date: str
    mobileProductiveMin: int
    mobileDistractingMin: int
    mobileNeutralMin: int
    sync_id: str | None = Field(default=None, min_length=8, max_length=64)
    assignments: list[AssignmentModel] = []
    mergedStats: DailyStatsModel | None = None

@router.post("/push")
def push_sync(
    payload: SyncPayload,
    user: User = Depends(current_user),
    db: Session = Depends(get_db)
):
    """
    Receives mobile screen time usage and adds it to the PC screen time usage.
    """
    # Parse payload.date string to date object
    if isinstance(payload.date, str):
        try:
            summary_date = date.fromisoformat(payload.date)
        except ValueError:
            summary_date = date.today()
    else:
        summary_date = payload.date

    if payload.sync_id:
        receipt = db.query(SyncReceipt).filter(
            SyncReceipt.user_id == user.id,
            SyncReceipt.sync_id == payload.sync_id,
        ).first()
        if receipt:
            return {"status": "ok", "duplicate": True}

    # 1. Update Daily Stats with mobile usage
    stats_record = db.query(DailySummary).filter(
        DailySummary.user_id == user.id,
        DailySummary.date == summary_date
    ).first()
    if not stats_record:
        stats_record = DailySummary(
            user_id=user.id,
            date=summary_date,
            productive_time_s=payload.mobileProductiveMin * 60,
            distracted_time_s=payload.mobileDistractingMin * 60,
            neutral_time_s=payload.mobileNeutralMin * 60,
            desk_time_s=(payload.mobileProductiveMin + payload.mobileDistractingMin + payload.mobileNeutralMin) * 60,
        )
        db.add(stats_record)
    else:
        stats_record.productive_time_s = (stats_record.productive_time_s or 0) + payload.mobileProductiveMin * 60
        stats_record.distracted_time_s = (stats_record.distracted_time_s or 0) + payload.mobileDistractingMin * 60
        stats_record.neutral_time_s = (stats_record.neutral_time_s or 0) + payload.mobileNeutralMin * 60
        stats_record.desk_time_s = (stats_record.desk_time_s or 0) + (
            payload.mobileProductiveMin + payload.mobileDistractingMin + payload.mobileNeutralMin
        ) * 60

    if payload.sync_id:
        db.add(SyncReceipt(
            user_id=user.id,
            sync_id=payload.sync_id,
            summary_date=summary_date,
        ))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if payload.sync_id and db.query(SyncReceipt).filter(
            SyncReceipt.user_id == user.id,
            SyncReceipt.sync_id == payload.sync_id,
        ).first():
            return {"status": "ok", "duplicate": True}
        raise
    return {"status": "ok", "duplicate": False}

@router.get("/pull", response_model=SyncPayload)
def pull_sync(
    user: User = Depends(current_user),
    db: Session = Depends(get_db)
):
    """
    Returns the merged assignments and stats to the Android app.
    """
    today_str = date.today().isoformat()
    
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
            priority=t.priority,
            status=t.status,
            notes=t.notes
        ))
        
    return SyncPayload(
        date=today_str,
        mobileProductiveMin=0,
        mobileDistractingMin=0,
        mobileNeutralMin=0,
        assignments=assignments_list,
        mergedStats=merged_stats
    )
