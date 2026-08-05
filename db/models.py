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


class ScheduleProfile(Base):
    __tablename__ = "schedule_profiles"

    id                 = Column(Integer, primary_key=True, index=True)
    timezone           = Column(String(80), default="local")
    wake_time          = Column(String(5), nullable=False)
    sleep_time         = Column(String(5), nullable=False)
    school_start       = Column(String(5))
    school_end         = Column(String(5))
    study_goal_minutes = Column(Integer, default=120)
    session_minutes    = Column(Integer, default=50)
    break_minutes      = Column(Integer, default=10)
    active             = Column(Boolean, default=True)
    notes              = Column(Text)
    created_at         = Column(DateTime, default=func.now())
    updated_at         = Column(DateTime, default=func.now(), onupdate=func.now())

    blocks = relationship("ScheduleBlock", back_populates="profile", cascade="all, delete")


class ScheduleBlock(Base):
    __tablename__ = "schedule_blocks"

    id          = Column(Integer, primary_key=True, index=True)
    profile_id  = Column(Integer, ForeignKey("schedule_profiles.id"), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # Monday=0 ... Sunday=6
    block_date  = Column(Date)
    start_time  = Column(String(5), nullable=False)
    end_time    = Column(String(5), nullable=False)
    kind        = Column(String(30), nullable=False)  # school | study | fixed | break
    title       = Column(String(200), nullable=False)
    subject     = Column(String(100))
    flexibility = Column(String(20), default="movable")  # fixed | movable | flexible
    source      = Column(String(30), default="onboarding")
    priority    = Column(String(20), default="medium")
    status      = Column(String(20), default="planned")  # planned | done | skipped | moved
    created_at  = Column(DateTime, default=func.now())

    profile = relationship("ScheduleProfile", back_populates="blocks")


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


class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    email         = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role          = Column(String(20), nullable=False, default="student")  # student | parent
    display_name  = Column(String(120))
    created_at    = Column(DateTime, default=func.now())

    devices        = relationship("Device", back_populates="user", cascade="all, delete")
    parent_links   = relationship("ParentStudentLink", foreign_keys="ParentStudentLink.parent_id", cascade="all, delete")
    student_links  = relationship("ParentStudentLink", foreign_keys="ParentStudentLink.student_id", cascade="all, delete")


class Device(Base):
    __tablename__ = "devices"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    device_name  = Column(String(120), nullable=False)
    device_type  = Column(String(30), nullable=False)  # desktop | android | hardware | other
    platform     = Column(String(80))
    status       = Column(String(20), default="linked")
    linked_at    = Column(DateTime, default=func.now())
    last_seen_at = Column(DateTime)
    created_at   = Column(DateTime, default=func.now())

    user         = relationship("User", back_populates="devices")


class ParentInvite(Base):
    __tablename__ = "parent_invites"

    id          = Column(Integer, primary_key=True, index=True)
    student_id  = Column(Integer, ForeignKey("users.id"), nullable=False)
    code        = Column(String(12), unique=True, nullable=False, index=True)
    expires_at  = Column(DateTime, nullable=False)
    consumed_at = Column(DateTime)
    created_at  = Column(DateTime, default=func.now())


class ParentStudentLink(Base):
    __tablename__ = "parent_student_links"

    id         = Column(Integer, primary_key=True, index=True)
    parent_id  = Column(Integer, ForeignKey("users.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())
