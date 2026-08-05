from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from db.models import DailySummary, Device, ParentInvite, ParentStudentLink, User
from modules.auth.security import create_access_token, hash_password, verify_password


VALID_ROLES = {"student", "parent"}
VALID_DEVICE_TYPES = {"desktop", "android", "hardware", "other"}


def register_user(
    db: Session,
    *,
    email: str,
    password: str,
    role: str = "student",
    display_name: Optional[str] = None,
) -> tuple[User, str]:
    email = _normalize_email(email)
    role = role.lower()
    if role not in VALID_ROLES:
        raise ValueError("role must be student or parent")
    if len(password) < 8:
        raise ValueError("password must be at least 8 characters")
    if db.query(User).filter(User.email == email).first():
        raise ValueError("email already registered")

    user = User(
        email=email,
        password_hash=hash_password(password),
        role=role,
        display_name=display_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, create_access_token(user.id, user.role)


def login_user(db: Session, *, email: str, password: str) -> tuple[User, str]:
    user = db.query(User).filter(User.email == _normalize_email(email)).first()
    if not user or not verify_password(password, user.password_hash):
        raise ValueError("invalid email or password")
    return user, create_access_token(user.id, user.role)


def register_device(
    db: Session,
    *,
    user: User,
    device_name: str,
    device_type: str,
    platform: Optional[str] = None,
) -> Device:
    device_type = device_type.lower()
    if device_type not in VALID_DEVICE_TYPES:
        raise ValueError("device_type must be desktop, android, hardware, or other")
    if not device_name.strip():
        raise ValueError("device_name cannot be blank")

    device = Device(
        user_id=user.id,
        device_name=device_name.strip(),
        device_type=device_type,
        platform=platform,
        last_seen_at=datetime.utcnow(),
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


def mark_device_seen(db: Session, *, user: User, device_id: int) -> Optional[Device]:
    device = db.get(Device, device_id)
    if not device or device.user_id != user.id:
        return None
    device.last_seen_at = datetime.utcnow()
    db.commit()
    db.refresh(device)
    return device


def create_parent_invite(db: Session, *, student: User, expires_hours: int = 72) -> ParentInvite:
    if student.role != "student":
        raise ValueError("only student accounts can create parent invites")
    code = _new_invite_code(db)
    invite = ParentInvite(
        student_id=student.id,
        code=code,
        expires_at=datetime.utcnow() + timedelta(hours=expires_hours),
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return invite


def consume_parent_invite(db: Session, *, parent: User, code: str) -> ParentStudentLink:
    if parent.role != "parent":
        raise ValueError("only parent accounts can consume parent invites")

    invite = (
        db.query(ParentInvite)
        .filter(ParentInvite.code == code.strip().upper())
        .first()
    )
    if not invite or invite.consumed_at or invite.expires_at <= datetime.utcnow():
        raise ValueError("invalid or expired invite code")

    existing = (
        db.query(ParentStudentLink)
        .filter(ParentStudentLink.parent_id == parent.id)
        .filter(ParentStudentLink.student_id == invite.student_id)
        .first()
    )
    if existing:
        invite.consumed_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    link = ParentStudentLink(parent_id=parent.id, student_id=invite.student_id)
    invite.consumed_at = datetime.utcnow()
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def parent_can_access_student(db: Session, *, parent: User, student_id: int) -> bool:
    if parent.role != "parent":
        return False
    return (
        db.query(ParentStudentLink)
        .filter(ParentStudentLink.parent_id == parent.id)
        .filter(ParentStudentLink.student_id == student_id)
        .first()
        is not None
    )


def weekly_student_summary(db: Session, *, student_id: int, days: int = 7) -> dict:
    # Current data tables are not user-scoped yet, so this returns global local summary
    # behind strict parent/student access control. User-scoping can be added once
    # screen sessions and assignments carry user_id.
    rows = db.query(DailySummary).order_by(DailySummary.date.desc()).limit(days).all()
    scores = [r.focus_score or 0 for r in rows]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    return {
        "student_id": student_id,
        "days": days,
        "avg_focus_score": avg_score,
        "summaries": [
            {
                "date": str(r.date),
                "focus_score": r.focus_score,
                "productive_min": (r.productive_time_s or 0) // 60,
                "distracting_min": (r.distracted_time_s or 0) // 60,
                "assignments_done": r.assignments_done,
                "assignments_due": r.assignments_due,
            }
            for r in rows
        ],
    }


def _normalize_email(email: str) -> str:
    email = (email or "").strip().lower()
    if "@" not in email:
        raise ValueError("valid email required")
    return email


def _new_invite_code(db: Session) -> str:
    for _ in range(20):
        code = f"{secrets.randbelow(1_000_000):06d}"
        if not db.query(ParentInvite).filter(ParentInvite.code == code).first():
            return code
    raise RuntimeError("could not generate unique invite code")
