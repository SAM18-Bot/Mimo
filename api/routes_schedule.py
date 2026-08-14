from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from api.routes_auth import current_user
from db.models import User

from api.websocket import push_event
from db.database import get_db
from modules.schedule.manager import (
    boost_subject_priority,
    build_onboarding_schedule,
    get_active_profile,
    get_day_schedule,
    get_weekly_schedule,
    onboarding_questions,
    reschedule_missed_blocks,
    schedule_status,
    smart_suggestions,
    update_block_status,
)

router = APIRouter(prefix="/schedule", tags=["schedule"])


class SubjectPreferenceIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    priority: Literal["low", "medium", "high"] = "medium"
    target_minutes: Optional[int] = Field(default=None, ge=0, le=600)


class FixedBlockIn(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6)
    title: str = Field(..., min_length=1, max_length=200)
    start_time: str
    end_time: str
    kind: str = "fixed"


class ScheduleOnboardingIn(BaseModel):
    wake_time: str = "06:30"
    sleep_time: str = "22:30"
    timezone: str = "local"
    school_days: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4])
    school_start: Optional[str] = None
    school_end: Optional[str] = None
    study_goal_minutes: int = Field(default=120, ge=1, le=600)
    session_minutes: int = Field(default=50, ge=15, le=180)
    break_minutes: int = Field(default=10, ge=0, le=60)
    subjects: list[SubjectPreferenceIn] = Field(default_factory=list)
    fixed_blocks: list[FixedBlockIn] = Field(default_factory=list)
    notes: Optional[str] = None


class ScheduleBlockOut(BaseModel):
    id: int
    day_of_week: int
    block_date: Optional[date]
    start_time: str
    end_time: str
    kind: str
    title: str
    subject: Optional[str]
    flexibility: str
    source: str
    priority: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class ScheduleProfileOut(BaseModel):
    id: int
    timezone: str
    wake_time: str
    sleep_time: str
    school_start: Optional[str]
    school_end: Optional[str]
    study_goal_minutes: int
    session_minutes: int
    break_minutes: int
    active: bool
    notes: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class ScheduleOnboardingOut(BaseModel):
    profile: ScheduleProfileOut
    blocks: list[ScheduleBlockOut]


class BlockStatusIn(BaseModel):
    status: Literal["planned", "done", "skipped", "moved", "missed"]


@router.get("/onboarding/questions")
def get_onboarding_questions():
    return {"questions": onboarding_questions()}


@router.post("/onboarding", response_model=ScheduleOnboardingOut, status_code=201)
def create_from_onboarding(payload: ScheduleOnboardingIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    try:
        profile = build_onboarding_schedule(
            db,
            user_id=user.id,
            wake_time=payload.wake_time,
            sleep_time=payload.sleep_time,
            timezone=payload.timezone,
            school_days=payload.school_days,
            school_start=payload.school_start,
            school_end=payload.school_end,
            study_goal_minutes=payload.study_goal_minutes,
            session_minutes=payload.session_minutes,
            break_minutes=payload.break_minutes,
            subjects=[s.model_dump() for s in payload.subjects],
            fixed_blocks=[b.model_dump() for b in payload.fixed_blocks],
            notes=payload.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    blocks = get_weekly_schedule(db, user_id=user.id)
    push_event({"type": "schedule_updated", "profile_id": profile.id, "blocks": len(blocks)})
    return {"profile": profile, "blocks": blocks}


@router.get("/status")
def status(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return schedule_status(db, user_id=user.id)


@router.get("/profile", response_model=Optional[ScheduleProfileOut])
def profile(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return get_active_profile(db, user_id=user.id)


@router.get("/weekly", response_model=list[ScheduleBlockOut])
def weekly(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return get_weekly_schedule(db, user_id=user.id)


@router.get("", response_model=list[ScheduleBlockOut])
@router.get("/", response_model=list[ScheduleBlockOut])
@router.get("/today", response_model=list[ScheduleBlockOut])
def today(target_date: Optional[date] = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return get_day_schedule(db, user_id=user.id, target_date=target_date)


@router.patch("/blocks/{block_id}", response_model=ScheduleBlockOut)
def set_block_status(block_id: int, payload: BlockStatusIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    try:
        block = update_block_status(db, block_id, payload.status, user_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not block:
        raise HTTPException(status_code=404, detail="Schedule block not found")
    push_event({"type": "schedule_block_updated", "id": block.id, "status": block.status})
    return block


@router.post("/reschedule", response_model=list[ScheduleBlockOut])
def reschedule(target_date: Optional[date] = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Find skipped/missed blocks for today and reschedule them into free windows."""
    new_blocks = reschedule_missed_blocks(db, user_id=user.id, target_date=target_date)
    if new_blocks:
        push_event({
            "type": "schedule_rescheduled",
            "count": len(new_blocks),
            "blocks": [b.id for b in new_blocks],
        })
    return new_blocks


@router.post("/boost", response_model=list[ScheduleBlockOut])
def boost(
    target_date: Optional[date] = None,
    lookahead_days: int = 3,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Create extra study blocks for subjects with upcoming assignment deadlines."""
    boosted = boost_subject_priority(
        db, user_id=user.id, target_date=target_date, lookahead_days=lookahead_days
    )
    if boosted:
        push_event({
            "type": "schedule_boosted",
            "count": len(boosted),
            "subjects": list({b.subject for b in boosted if b.subject}),
        })
    return boosted


@router.get("/smart-suggestions")
def suggestions(target_date: Optional[date] = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Get AI-powered schedule adjustment suggestions."""
    return {"suggestions": smart_suggestions(db, user_id=user.id, target_date=target_date)}
