
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from api.routes_auth import current_user
from db.database import get_db
from db.models import ScheduleBlock, ScheduleProfile, User

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])

class OnboardingRequest(BaseModel):
    course: str = Field(..., min_length=1, max_length=120)
    age: int = Field(..., ge=5, le=120)
    education_level: Literal["high_school", "undergraduate", "graduate", "other"]
    ai_engine: Literal["gemini", "openai"]
    api_key: str | None = None
    wake_time: str = Field(default="07:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    sleep_time: str = Field(default="23:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    study_goal_minutes: int = Field(default=120, ge=15, le=1440)

    @field_validator("course")
    @classmethod
    def strip_course(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("course cannot be blank")
        return value

@router.post("/complete")
def complete_onboarding(data: OnboardingRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.onboarding_completed:
        return {"status": "success", "message": "Onboarding already completed.", "onboarding_completed": True}

    try:
        user.course = data.course
        user.age = data.age
        user.education_level = data.education_level
        user.ai_engine = data.ai_engine
        if data.api_key:
            user.api_key = data.api_key.strip()
        user.onboarding_completed = True

        db.query(ScheduleProfile).filter(ScheduleProfile.user_id == user.id).update(
            {ScheduleProfile.active: False}, synchronize_session=False
        )
        profile = ScheduleProfile(
            user_id=user.id,
            wake_time=data.wake_time,
            sleep_time=data.sleep_time,
            study_goal_minutes=data.study_goal_minutes,
            active=True,
        )
        db.add(profile)
        db.flush()
        db.add(ScheduleBlock(
            profile_id=profile.id,
            day_of_week=0,
            start_time="18:00",
            end_time="20:00",
            kind="study",
            title=f"Study {data.course}",
            subject=data.course,
        ))
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise

    return {"status": "success", "message": "Onboarding completed successfully.", "onboarding_completed": True}
