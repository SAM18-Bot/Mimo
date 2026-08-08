from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import User, ScheduleProfile, ScheduleBlock
from datetime import date

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])

class OnboardingRequest(BaseModel):
    user_id: int
    course: str
    age: int
    education_level: str
    ai_engine: str
    api_key: Optional[str] = None
    wake_time: str = "07:00"
    sleep_time: str = "23:00"
    study_goal_minutes: int = 120

@router.post("/complete")
def complete_onboarding(data: OnboardingRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.course = data.course
    user.age = data.age
    user.education_level = data.education_level
    user.ai_engine = data.ai_engine
    if data.api_key:
        user.api_key = data.api_key
    user.onboarding_completed = True

    # Generate a default schedule profile based on the onboarding data
    profile = ScheduleProfile(
        wake_time=data.wake_time,
        sleep_time=data.sleep_time,
        study_goal_minutes=data.study_goal_minutes,
        active=True
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    # Generate an AI schedule block (mocked here, but would call AI to generate blocks)
    # We will add a simple default block
    block = ScheduleBlock(
        profile_id=profile.id,
        day_of_week=0, # Monday
        start_time="18:00",
        end_time="20:00",
        kind="study",
        title=f"Study {data.course}",
        subject=data.course
    )
    db.add(block)
    db.commit()

    return {"status": "success", "message": "Onboarding completed successfully."}
