from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from db.database import get_db
from sqlalchemy.orm import Session
from datetime import date
from db.models import Assignment, DailySummary, User
from api.routes_auth import current_user
from modules.behavior_engine.aggregator import get_daily_stats
from modules.assignments.manager import get_upcoming

router = APIRouter(prefix="/sync", tags=["Sync"])

class AssignmentModel(BaseModel):
    id: int
    title: str
    subject: Optional[str] = None
    due_date: str
    priority: str = "medium"
    status: str = "pending"
    notes: Optional[str] = None

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
    assignments: List[AssignmentModel] = []
    mergedStats: Optional[DailyStatsModel] = None

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
        stats_record.productive_time_s += payload.mobileProductiveMin * 60
        stats_record.distracted_time_s += payload.mobileDistractingMin * 60
        stats_record.neutral_time_s += payload.mobileNeutralMin * 60
        stats_record.desk_time_s += (payload.mobileProductiveMin + payload.mobileDistractingMin + payload.mobileNeutralMin) * 60
    
    db.commit()
    return {"status": "ok"}

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
