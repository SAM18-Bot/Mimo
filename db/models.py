from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db.database import Base


class ScreenSession(Base):
    __tablename__ = "screen_sessions"

    id           = Column(Integer, primary_key=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    app_name     = Column(String(200), nullable=False)
    window_title = Column(String(500))
    category     = Column(String(20))          # productive | neutral | distracting
    started_at   = Column(DateTime, nullable=False)
    ended_at     = Column(DateTime)
    duration_s   = Column(Integer, default=0)
    session_date = Column(Date, index=True)
    
    user = relationship("User", back_populates="screen_sessions")


class CVEvent(Base):
    __tablename__ = "cv_events"

    id           = Column(Integer, primary_key=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    event_type   = Column(String(20))          # present | absent | distracted | returned
    timestamp    = Column(DateTime, nullable=False, default=func.now())
    session_date = Column(Date, index=True)
    
    user = relationship("User", back_populates="cv_events")


class Assignment(Base):
    __tablename__ = "assignments"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title      = Column(String(300), nullable=False)
    subject    = Column(String(100))
    due_date   = Column(Date, nullable=False, index=True)
    due_time   = Column(String(20), nullable=True)
    priority   = Column(String(20), default="medium", server_default="medium")   # low | medium | high
    status     = Column(String(20), default="pending", server_default="pending", index=True)  # pending | in_progress | done
    notes      = Column(Text)
    created_at = Column(DateTime, default=func.now())
    reminded_at = Column(DateTime)

    user = relationship("User", back_populates="assignments")
    reminders  = relationship("Reminder", back_populates="assignment", cascade="all, delete")


class AccountabilityLog(Base):
    __tablename__ = "accountability_logs"

    id          = Column(Integer, primary_key=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date        = Column(Date, nullable=False)
    question    = Column(Text)
    answer      = Column(Text)
    recorded_at = Column(DateTime, default=func.now())
    
    user = relationship("User", back_populates="accountability_logs")


class DailySummary(Base):
    __tablename__ = "daily_summaries"

    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_daily_summaries_user_date"),)

    id                = Column(Integer, primary_key=True)
    user_id           = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date              = Column(Date, nullable=False, index=True)
    productive_time_s = Column(Integer, default=0, server_default="0")
    distracted_time_s = Column(Integer, default=0, server_default="0")
    neutral_time_s    = Column(Integer, default=0, server_default="0")
    desk_time_s       = Column(Integer, default=0, server_default="0")
    absent_time_s     = Column(Integer, default=0, server_default="0")
    focus_score       = Column(Float, default=0.0, server_default="0.0")
    distraction_count = Column(Integer, default=0, server_default="0")
    assignments_due   = Column(Integer, default=0, server_default="0")
    assignments_done  = Column(Integer, default=0, server_default="0")
    ai_report_text    = Column(Text)
    peak_hour         = Column(Integer)           # 0–23
    created_at        = Column(DateTime, default=func.now())
    
    user = relationship("User", back_populates="daily_summaries")


class StudySession(Base):
    __tablename__ = "study_sessions"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject    = Column(String(100))
    started_at = Column(DateTime, nullable=False)
    ended_at   = Column(DateTime)
    duration_s = Column(Integer)
    source     = Column(String(20), default="auto", server_default="auto")  # manual | auto
    
    user = relationship("User", back_populates="study_sessions")


class ScheduleProfile(Base):
    __tablename__ = "schedule_profiles"
    __table_args__ = (Index("ix_schedule_profiles_active", "active"),)

    id                 = Column(Integer, primary_key=True)
    user_id            = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    timezone           = Column(String(80), default="local", server_default="local")
    wake_time          = Column(String(5), nullable=False)
    sleep_time         = Column(String(5), nullable=False)
    school_start       = Column(String(5))
    school_end         = Column(String(5))
    study_goal_minutes = Column(Integer, default=120, server_default="120")
    session_minutes    = Column(Integer, default=50, server_default="50")
    break_minutes      = Column(Integer, default=10, server_default="10")
    active             = Column(Boolean, default=True, server_default="1")
    notes              = Column(Text)
    created_at         = Column(DateTime, default=func.now())
    updated_at         = Column(DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="schedule_profiles")
    blocks = relationship("ScheduleBlock", back_populates="profile", cascade="all, delete")


class ScheduleBlock(Base):
    __tablename__ = "schedule_blocks"
    __table_args__ = (Index("ix_schedule_blocks_profile_day", "profile_id", "day_of_week"),)

    id          = Column(Integer, primary_key=True)
    profile_id  = Column(Integer, ForeignKey("schedule_profiles.id"), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # Monday=0 ... Sunday=6
    block_date  = Column(Date)
    start_time  = Column(String(5), nullable=False)
    end_time    = Column(String(5), nullable=False)
    kind        = Column(String(30), nullable=False)  # school | study | fixed | break
    title       = Column(String(200), nullable=False)
    subject     = Column(String(100))
    flexibility = Column(String(20), default="movable", server_default="movable")  # fixed | movable | flexible
    source      = Column(String(30), default="onboarding", server_default="onboarding")
    priority    = Column(String(20), default="medium", server_default="medium")
    status      = Column(String(20), default="planned", server_default="planned")  # planned | done | skipped | moved
    created_at  = Column(DateTime, default=func.now())

    profile = relationship("ScheduleProfile", back_populates="blocks")


class Reminder(Base):
    __tablename__ = "reminders"

    id            = Column(Integer, primary_key=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id", ondelete="CASCADE"))
    remind_at     = Column(DateTime, nullable=False, index=True)
    delivered     = Column(Boolean, default=False, server_default="0", index=True)
    message       = Column(Text)

    assignment    = relationship("Assignment", back_populates="reminders")


class RoastLog(Base):
    __tablename__ = "roast_logs"

    id           = Column(Integer, primary_key=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    trigger      = Column(String(100))   # instagram | absent | youtube | etc.
    message      = Column(Text)
    timestamp    = Column(DateTime, default=func.now())
    session_date = Column(Date, index=True)
    
    user = relationship("User", back_populates="roast_logs")


class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True)
    email         = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True) # Now optional because of Google Auth
    role          = Column(String(20), nullable=False, default="student", server_default="student")  # student | parent
    display_name  = Column(String(120))
    ai_engine     = Column(String(20), nullable=False, default="openai", server_default="openai")  # openai | gemini
    _api_key_encrypted = Column("api_key", String(255))
    
    @property
    def api_key(self):
        from cryptography.fernet import Fernet, InvalidToken

        import config
        if not self._api_key_encrypted: return None
        if not config.SECRET_KEY or len(config.SECRET_KEY) < 43:
            raise ValueError("SECRET_KEY must be configured with a valid 32-byte Fernet key.")
        try:
            f = Fernet(config.SECRET_KEY.encode())
            return f.decrypt(self._api_key_encrypted.encode()).decode()
        except InvalidToken:
            return None
            
    @api_key.setter
    def api_key(self, value):
        from cryptography.fernet import Fernet

        import config
        if not value:
            self._api_key_encrypted = None
            return
        if not config.SECRET_KEY or len(config.SECRET_KEY) < 43:
            raise ValueError("SECRET_KEY must be configured with a valid 32-byte Fernet key to store personal API keys safely.")
        f = Fernet(config.SECRET_KEY.encode())
        self._api_key_encrypted = f.encrypt(value.encode()).decode()
    
    # Onboarding fields
    course        = Column(String(120))
    age           = Column(Integer)
    education_level = Column(String(50))
    onboarding_completed = Column(Boolean, nullable=False, default=False, server_default="0")
    
    # Provider
    auth_provider = Column(String(50), nullable=False, default="local", server_default="local") # local | google
    google_id     = Column(String(255), unique=True, index=True)
    
    created_at    = Column(DateTime, default=func.now())

    devices        = relationship("Device", back_populates="user", cascade="all, delete")
    parent_links   = relationship("ParentStudentLink", foreign_keys="ParentStudentLink.parent_id", cascade="all, delete")
    student_links  = relationship("ParentStudentLink", foreign_keys="ParentStudentLink.student_id", cascade="all, delete")
    
    # Added relationships for tracking models
    screen_sessions = relationship("ScreenSession", back_populates="user", cascade="all, delete")
    cv_events       = relationship("CVEvent", back_populates="user", cascade="all, delete")
    assignments     = relationship("Assignment", back_populates="user", cascade="all, delete")
    accountability_logs = relationship("AccountabilityLog", back_populates="user", cascade="all, delete")
    daily_summaries = relationship("DailySummary", back_populates="user", cascade="all, delete")
    study_sessions  = relationship("StudySession", back_populates="user", cascade="all, delete")
    schedule_profiles = relationship("ScheduleProfile", back_populates="user", cascade="all, delete")
    roast_logs      = relationship("RoastLog", back_populates="user", cascade="all, delete")


class Device(Base):
    __tablename__ = "devices"

    id           = Column(Integer, primary_key=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    device_name  = Column(String(120), nullable=False)
    device_type  = Column(String(30), nullable=False)  # desktop | android | hardware | other
    platform     = Column(String(80))
    status       = Column(String(20), default="linked", server_default="linked")
    linked_at    = Column(DateTime, default=func.now())
    last_seen_at = Column(DateTime)
    created_at   = Column(DateTime, default=func.now())

    user         = relationship("User", back_populates="devices")


class ParentInvite(Base):
    __tablename__ = "parent_invites"

    id          = Column(Integer, primary_key=True)
    student_id  = Column(Integer, ForeignKey("users.id"), nullable=False)
    code        = Column(String(12), unique=True, nullable=False, index=True)
    expires_at  = Column(DateTime, nullable=False)
    consumed_at = Column(DateTime)
    created_at  = Column(DateTime, default=func.now())


class ParentStudentLink(Base):
    __tablename__ = "parent_student_links"

    id         = Column(Integer, primary_key=True)
    parent_id  = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=func.now())


class TokenBlocklist(Base):
    __tablename__ = "token_blocklist"

    id         = Column(Integer, primary_key=True)
    token      = Column(String(500), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now())


class SyncReceipt(Base):
    __tablename__ = "sync_receipts"
    __table_args__ = (UniqueConstraint("user_id", "sync_id", name="uq_sync_receipts_user_sync"),)

    id           = Column(Integer, primary_key=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    sync_id      = Column(String(64), nullable=False)
    summary_date = Column(Date, nullable=False)
    created_at   = Column(DateTime, default=func.now())


class Todo(Base):
    __tablename__ = "todos"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title      = Column(String(300), nullable=False)
    due_date   = Column(Date, nullable=True)
    remind_at  = Column(DateTime, nullable=True)
    status     = Column(String(20), default="pending")  # pending | done
    created_at = Column(DateTime, default=func.now())
    delivered  = Column(Boolean, default=False)

    user = relationship("User", backref="todos")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    sender     = Column(String(20), nullable=False)  # user | ai
    text       = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())

    user = relationship("User", backref="chat_messages")
