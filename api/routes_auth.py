from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy.orm import Session

from db.database import get_db, init_db, engine, Base
from db.models import Device, User
from modules.auth.manager import (
    consume_parent_invite,
    create_parent_invite,
    login_user,
    google_login_user,
    mark_device_seen,
    parent_can_access_student,
    register_device,
    register_user,
    weekly_student_summary,
)
from modules.auth.security import decode_access_token

router = APIRouter(tags=["auth"])



class UserOut(BaseModel):
    id: int
    email: str
    role: str
    display_name: Optional[str]
    onboarding_completed: bool = False

    model_config = ConfigDict(from_attributes=True)


class AuthOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: Literal["student", "parent"] = "student"
    display_name: Optional[str] = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str

class GoogleLoginIn(BaseModel):
    token: str


class DeviceRegisterIn(BaseModel):
    device_name: str = Field(..., min_length=1, max_length=120)
    device_type: Literal["desktop", "android", "hardware", "other"]
    platform: Optional[str] = None


class DeviceOut(BaseModel):
    id: int
    device_name: str
    device_type: str
    platform: Optional[str]
    status: str
    linked_at: Optional[datetime]
    last_seen_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class InviteOut(BaseModel):
    code: str
    expires_at: datetime


class InviteConsumeIn(BaseModel):
    code: str = Field(..., min_length=6, max_length=12)


class LinkOut(BaseModel):
    parent_id: int
    student_id: int


def current_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()

    from db.models import TokenBlocklist
    if db.query(TokenBlocklist).filter(TokenBlocklist.token == token).first():
        raise HTTPException(status_code=401, detail="Token revoked")

    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


@router.post("/auth/register", response_model=AuthOut, status_code=201)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    try:
        user, token = register_user(db, **payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"access_token": token, "user": user}


@router.post("/auth/logout", status_code=200)
def logout(
    authorization: Optional[str] = Header(default=None),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    token = authorization.split(" ", 1)[1].strip()
    payload = decode_access_token(token)
    expires_at = datetime.utcfromtimestamp(payload["exp"])
        
    from db.models import TokenBlocklist
    block = TokenBlocklist(token=token, expires_at=expires_at)
    db.add(block)
    db.commit()
    return {"status": "logged_out"}



from fastapi import Request
import time

_login_attempts = {}

@router.post("/auth/login", response_model=AuthOut)
def login(payload: LoginIn, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    
    # Rate limit: max 5 attempts per minute per IP
    attempts = _login_attempts.get(client_ip, [])
    attempts = [t for t in attempts if now - t < 60]
    if len(attempts) >= 5:
        raise HTTPException(status_code=429, detail="Too many login attempts. Please try again later.")
    
    _login_attempts[client_ip] = attempts + [now]

    try:
        user, token = login_user(db, email=payload.email, password=payload.password)
        # Clear attempts on success
        _login_attempts.pop(client_ip, None)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return {"access_token": token, "user": user}

@router.post("/auth/google", response_model=AuthOut)
def google_login(payload: GoogleLoginIn, db: Session = Depends(get_db)):
    try:
        user, token = google_login_user(db, token=payload.token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return {"access_token": token, "user": user}


@router.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@router.post("/devices/register", response_model=DeviceOut, status_code=201)
def add_device(
    payload: DeviceRegisterIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    try:
        return register_device(db, user=user, **payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/devices", response_model=list[DeviceOut])
def list_devices(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.query(Device).filter(Device.user_id == user.id).order_by(Device.created_at.desc()).all()


@router.post("/devices/{device_id}/heartbeat", response_model=DeviceOut)
def heartbeat(device_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    device = mark_device_seen(db, user=user, device_id=device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.post("/parent/invites", response_model=InviteOut, status_code=201)
def create_invite(user: User = Depends(current_user), db: Session = Depends(get_db)):
    try:
        return create_parent_invite(db, student=user)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/parent/link", response_model=LinkOut)
def link_parent(
    payload: InviteConsumeIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    try:
        link = consume_parent_invite(db, parent=user, code=payload.code)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {"parent_id": link.parent_id, "student_id": link.student_id}


@router.get("/parent/children", response_model=list[UserOut])
def children(user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.role != "parent":
        raise HTTPException(status_code=403, detail="Parent role required")
    from db.models import ParentStudentLink
    rows = (
        db.query(User)
        .join(ParentStudentLink, User.id == ParentStudentLink.student_id)
        .filter(ParentStudentLink.parent_id == user.id)
        .all()
    )
    return rows


@router.get("/parent/summary/{student_id}")
def parent_summary(student_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.role == "student" and user.id == student_id:
        return weekly_student_summary(db, student_id=student_id)
    if not parent_can_access_student(db, parent=user, student_id=student_id):
        raise HTTPException(status_code=403, detail="No access to this student")
    return weekly_student_summary(db, student_id=student_id)
