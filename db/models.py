from sqlalchemy import (
    Column, Integer, String, DateTime, Date,
    Float, Boolean, Text, ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db.database import Base


class ScreenSession(Base):
    __tablename__ = "screen_sessions"

    id           = Column(Integer, primary_key=True, index=True)
    app_name     = Column(String(200), nullable=False)
    window_title = Column(String(500))
    category     = Column(String(20))          # productive | neutral | distracting
    started_at   = Column(DateTime, nullable=False)
    ended_at     = Column(DateTime)
    duration_s   = Column(Integer, default=0)
    session_date = Column(Date)


class CVEvent(Base):
    __tablename__ = "cv_events"

    id           = Column(Integer, primary_key=True, index=True)
    event_type   = Column(String(20))          # present | absent | distracted | returned
    timestamp    = Column(DateTime, nullable=False, default=func.now())
    session_date = Column(Date)


class Assignment(Base):
    __tablename__ = "assignments"

    id         = Column(Integer, primary_key=True, index=True)
    title      = Column(String(300), nullable=False)
    subject    = Column(String(100))
    due_date   = Column(Date, nullable=False)
    priority   = Column(String(20), default="medium")   # low | medium | high
    status     = Column(String(20), default="pending")  # pending | in_progress | done
    notes      = Column(Text)
    created_at = Column(DateTime, default=func.now())
    reminded_at = Column(DateTime)

    reminders  = relationship("Reminder", back_populates="assignment", cascade="all, delete")


class AccountabilityLog(Base):
    __tablename__ = "accountability_logs"

    id          = Column(Integer, primary_key=True, index=True)
    date        = Column(Date, nullable=False)
    question    = Column(Text)
    answer      = Column(Text)
    recorded_at = Column(DateTime, default=func.now())


class DailySummary(Base):
    __tablename__ = "daily_summaries"

    id                = Column(Integer, primary_key=True, index=True)
    date              = Column(Date, unique=True, nullable=False)
    productive_time_s = Column(Integer, default=0)
    distracted_time_s = Column(Integer, default=0)
    neutral_time_s    = Column(Integer, default=0)
    desk_time_s       = Column(Integer, default=0)
    absent_time_s     = Column(Integer, default=0)
    focus_score       = Column(Float, default=0.0)
    distraction_count = Column(Integer, default=0)
    assignments_due   = Column(Integer, default=0)
    assignments_done  = Column(Integer, default=0)
    ai_report_text    = Column(Text)
    peak_hour         = Column(Integer)           # 0–23
    created_at        = Column(DateTime, default=func.now())


class StudySession(Base):
    __tablename__ = "study_sessions"

    id         = Column(Integer, primary_key=True, index=True)
    subject    = Column(String(100))
    started_at = Column(DateTime, nullable=False)
    ended_at   = Column(DateTime)
    duration_s = Column(Integer)
    source     = Column(String(20), default="auto")  # manual | auto


class Reminder(Base):
    __tablename__ = "reminders"

    id            = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"))
    remind_at     = Column(DateTime, nullable=False)
    delivered     = Column(Boolean, default=False)
    message       = Column(Text)

    assignment    = relationship("Assignment", back_populates="reminders")


class RoastLog(Base):
    __tablename__ = "roast_logs"

    id           = Column(Integer, primary_key=True, index=True)
    trigger      = Column(String(100))   # instagram | absent | youtube | etc.
    message      = Column(Text)
    timestamp    = Column(DateTime, default=func.now())
    session_date = Column(Date)
