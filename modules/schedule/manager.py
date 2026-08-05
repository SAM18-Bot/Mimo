from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from db.models import ScheduleBlock, ScheduleProfile


DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
VALID_PRIORITIES = {"low", "medium", "high"}
VALID_STATUSES = {"planned", "done", "skipped", "moved"}


@dataclass(frozen=True)
class SubjectPreference:
    name: str
    priority: str = "medium"
    target_minutes: Optional[int] = None


@dataclass(frozen=True)
class FixedBlock:
    day_of_week: int
    title: str
    start_time: str
    end_time: str
    kind: str = "fixed"


def onboarding_questions() -> list[dict]:
    return [
        {
            "key": "wake_sleep",
            "question": "What time do you usually wake up and sleep?",
            "required": True,
        },
        {
            "key": "school_hours",
            "question": "Which days and hours are blocked by school or coaching?",
            "required": False,
        },
        {
            "key": "subjects",
            "question": "Which subjects need regular study blocks, and which are high priority?",
            "required": True,
        },
        {
            "key": "fixed_blocks",
            "question": "What fixed commitments should Mimo never overwrite?",
            "required": False,
        },
        {
            "key": "study_goal",
            "question": "How many focused study minutes should Mimo schedule per day?",
            "required": True,
        },
    ]


def build_onboarding_schedule(
    db: Session,
    *,
    wake_time: str,
    sleep_time: str,
    timezone: str = "local",
    school_days: Optional[list[int]] = None,
    school_start: Optional[str] = None,
    school_end: Optional[str] = None,
    study_goal_minutes: int = 120,
    session_minutes: int = 50,
    break_minutes: int = 10,
    subjects: Optional[Iterable[SubjectPreference | dict]] = None,
    fixed_blocks: Optional[Iterable[FixedBlock | dict]] = None,
    notes: Optional[str] = None,
) -> ScheduleProfile:
    wake_min = _parse_time(wake_time)
    sleep_min = _parse_time(sleep_time)
    if wake_min >= sleep_min:
        raise ValueError("sleep_time must be later than wake_time on the same day")
    if study_goal_minutes <= 0:
        raise ValueError("study_goal_minutes must be positive")
    if session_minutes <= 0:
        raise ValueError("session_minutes must be positive")
    if break_minutes < 0:
        raise ValueError("break_minutes cannot be negative")

    school_days = school_days if school_days is not None else [0, 1, 2, 3, 4]
    _validate_days(school_days)
    if (school_start and not school_end) or (school_end and not school_start):
        raise ValueError("school_start and school_end must be provided together")
    if school_start and school_end and _parse_time(school_start) >= _parse_time(school_end):
        raise ValueError("school_end must be later than school_start")

    subject_list = _normalize_subjects(subjects)
    fixed_list = _normalize_fixed_blocks(fixed_blocks)

    db.query(ScheduleProfile).update({ScheduleProfile.active: False})
    profile = ScheduleProfile(
        timezone=timezone or "local",
        wake_time=wake_time,
        sleep_time=sleep_time,
        school_start=school_start,
        school_end=school_end,
        study_goal_minutes=study_goal_minutes,
        session_minutes=session_minutes,
        break_minutes=break_minutes,
        active=True,
        notes=notes,
    )
    db.add(profile)
    db.flush()

    for block in _generate_blocks(
        profile=profile,
        subjects=subject_list,
        fixed_blocks=fixed_list,
        school_days=school_days,
    ):
        db.add(block)

    db.commit()
    db.refresh(profile)
    return profile


def get_active_profile(db: Session) -> Optional[ScheduleProfile]:
    return (
        db.query(ScheduleProfile)
        .filter(ScheduleProfile.active == True)  # noqa: E712
        .order_by(ScheduleProfile.created_at.desc(), ScheduleProfile.id.desc())
        .first()
    )


def get_weekly_schedule(db: Session) -> list[ScheduleBlock]:
    profile = get_active_profile(db)
    if not profile:
        return []
    return (
        db.query(ScheduleBlock)
        .filter(ScheduleBlock.profile_id == profile.id)
        .order_by(ScheduleBlock.day_of_week, ScheduleBlock.start_time)
        .all()
    )


def get_day_schedule(db: Session, target_date: Optional[date] = None) -> list[ScheduleBlock]:
    target = target_date or date.today()
    profile = get_active_profile(db)
    if not profile:
        return []
    return (
        db.query(ScheduleBlock)
        .filter(ScheduleBlock.profile_id == profile.id)
        .filter(ScheduleBlock.day_of_week == target.weekday())
        .order_by(ScheduleBlock.start_time)
        .all()
    )


def update_block_status(db: Session, block_id: int, status: str) -> Optional[ScheduleBlock]:
    if status not in VALID_STATUSES:
        raise ValueError(f"status must be one of: {', '.join(sorted(VALID_STATUSES))}")
    block = db.get(ScheduleBlock, block_id)
    if not block:
        return None
    block.status = status
    db.commit()
    db.refresh(block)
    return block


def schedule_status(db: Session) -> dict:
    profile = get_active_profile(db)
    if not profile:
        return {"configured": False, "profile_id": None, "blocks": 0}
    count = db.query(ScheduleBlock).filter(ScheduleBlock.profile_id == profile.id).count()
    return {"configured": True, "profile_id": profile.id, "blocks": count}


def _generate_blocks(
    *,
    profile: ScheduleProfile,
    subjects: list[SubjectPreference],
    fixed_blocks: list[FixedBlock],
    school_days: list[int],
) -> list[ScheduleBlock]:
    blocks: list[ScheduleBlock] = []
    subject_cycle = _expand_subjects(subjects)

    for day in range(7):
        busy: list[tuple[int, int]] = []

        if profile.school_start and profile.school_end and day in school_days:
            start = _parse_time(profile.school_start)
            end = _parse_time(profile.school_end)
            busy.append((start, end))
            blocks.append(_make_block(
                profile.id, day, start, end,
                kind="school",
                title="School / coaching",
                flexibility="fixed",
                priority="high",
            ))

        for fixed in fixed_blocks:
            if fixed.day_of_week != day:
                continue
            start = _parse_time(fixed.start_time)
            end = _parse_time(fixed.end_time)
            busy.append((start, end))
            blocks.append(_make_block(
                profile.id, day, start, end,
                kind=fixed.kind,
                title=fixed.title,
                flexibility="fixed",
                priority="high",
            ))

        remaining = profile.study_goal_minutes or 120
        free_windows = _free_windows(
            _parse_time(profile.wake_time),
            _parse_time(profile.sleep_time),
            busy,
        )

        session_index = 0
        for start, end in free_windows:
            cursor = start
            while remaining > 0 and cursor + min(remaining, profile.session_minutes or 50) <= end:
                duration = min(remaining, profile.session_minutes or 50)
                subject = subject_cycle[session_index % len(subject_cycle)]
                block_end = cursor + duration
                blocks.append(_make_block(
                    profile.id, day, cursor, block_end,
                    kind="study",
                    title=f"Study: {subject.name}",
                    subject=subject.name,
                    flexibility="movable",
                    priority=subject.priority,
                ))
                remaining -= duration
                session_index += 1
                cursor = block_end + (profile.break_minutes or 0)

            if remaining <= 0:
                break

    return sorted(blocks, key=lambda b: (b.day_of_week, b.start_time, b.kind != "school"))


def _make_block(
    profile_id: int,
    day: int,
    start: int,
    end: int,
    *,
    kind: str,
    title: str,
    subject: Optional[str] = None,
    flexibility: str = "movable",
    priority: str = "medium",
) -> ScheduleBlock:
    return ScheduleBlock(
        profile_id=profile_id,
        day_of_week=day,
        start_time=_format_time(start),
        end_time=_format_time(end),
        kind=kind,
        title=title,
        subject=subject,
        flexibility=flexibility,
        source="onboarding",
        priority=priority if priority in VALID_PRIORITIES else "medium",
        status="planned",
    )


def _normalize_subjects(subjects: Optional[Iterable[SubjectPreference | dict]]) -> list[SubjectPreference]:
    if not subjects:
        return [SubjectPreference(name="General study", priority="medium")]

    normalized = []
    for item in subjects:
        if isinstance(item, SubjectPreference):
            subject = item
        else:
            subject = SubjectPreference(
                name=str(item.get("name", "")).strip(),
                priority=str(item.get("priority", "medium")).lower(),
                target_minutes=item.get("target_minutes"),
            )
        if not subject.name:
            raise ValueError("subject name cannot be blank")
        if subject.priority not in VALID_PRIORITIES:
            raise ValueError("subject priority must be low, medium, or high")
        normalized.append(subject)
    return normalized


def _normalize_fixed_blocks(fixed_blocks: Optional[Iterable[FixedBlock | dict]]) -> list[FixedBlock]:
    if not fixed_blocks:
        return []
    normalized = []
    for item in fixed_blocks:
        if isinstance(item, FixedBlock):
            block = item
        else:
            block = FixedBlock(
                day_of_week=int(item.get("day_of_week")),
                title=str(item.get("title", "")).strip(),
                start_time=str(item.get("start_time")),
                end_time=str(item.get("end_time")),
                kind=str(item.get("kind", "fixed")).strip() or "fixed",
            )
        _validate_days([block.day_of_week])
        if not block.title:
            raise ValueError("fixed block title cannot be blank")
        if _parse_time(block.start_time) >= _parse_time(block.end_time):
            raise ValueError("fixed block end_time must be later than start_time")
        normalized.append(block)
    return normalized


def _expand_subjects(subjects: list[SubjectPreference]) -> list[SubjectPreference]:
    weights = {"high": 3, "medium": 2, "low": 1}
    ordered = sorted(subjects, key=lambda s: weights[s.priority], reverse=True)
    expanded = []
    for round_index in range(max(weights[s.priority] for s in ordered)):
        for subject in ordered:
            if weights[subject.priority] > round_index:
                expanded.append(subject)
    return expanded or [SubjectPreference("General study")]


def _free_windows(day_start: int, day_end: int, busy: list[tuple[int, int]]) -> list[tuple[int, int]]:
    windows = []
    cursor = day_start
    for start, end in sorted(_merge_intervals(busy)):
        if start > cursor:
            windows.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < day_end:
        windows.append((cursor, day_end))
    return windows


def _merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return merged


def _validate_days(days: list[int]) -> None:
    if any(day < 0 or day > 6 for day in days):
        raise ValueError("day_of_week values must be between 0 and 6")


def _parse_time(value: str) -> int:
    try:
        hour_text, minute_text = value.split(":", 1)
        hour = int(hour_text)
        minute = int(minute_text)
    except (AttributeError, TypeError, ValueError):
        raise ValueError("time values must use HH:MM format") from None

    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError("time values must use HH:MM format")
    return hour * 60 + minute


def _format_time(total_minutes: int) -> str:
    hour = total_minutes // 60
    minute = total_minutes % 60
    return f"{hour:02d}:{minute:02d}"
