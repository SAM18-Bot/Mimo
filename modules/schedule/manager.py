from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from db.models import Assignment, ScheduleBlock, ScheduleProfile


DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
VALID_PRIORITIES = {"low", "medium", "high"}
VALID_STATUSES = {"planned", "done", "skipped", "moved", "missed"}


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
    if wake_min == sleep_min:
        raise ValueError("wake_time and sleep_time cannot be the same")
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


def reschedule_missed_blocks(
    db: Session,
    *,
    target_date: Optional[date] = None,
) -> list[ScheduleBlock]:
    """Find skipped/missed study blocks for today and reschedule them into free windows."""
    target = target_date or date.today()
    profile = get_active_profile(db)
    if not profile:
        return []

    day_of_week = target.weekday()
    day_blocks = (
        db.query(ScheduleBlock)
        .filter(ScheduleBlock.profile_id == profile.id)
        .filter(ScheduleBlock.day_of_week == day_of_week)
        .order_by(ScheduleBlock.start_time)
        .all()
    )

    missed = [b for b in day_blocks if b.kind == "study" and b.status in ("skipped", "missed")]
    if not missed:
        return []

    # Build busy intervals from non-missed blocks
    busy: list[tuple[int, int]] = []
    for b in day_blocks:
        if b.status not in ("skipped", "missed"):
            busy.append((_parse_time(b.start_time), _parse_time(b.end_time)))

    # Determine schedule bounds
    wake_min = _parse_time(profile.wake_time)
    sleep_min = _parse_time(profile.sleep_time)
    if wake_min < sleep_min:
        segments = [(wake_min, sleep_min)]
    else:
        segments = [(wake_min, 24 * 60), (0, sleep_min)]

    # Find free windows across all segments
    free: list[tuple[int, int]] = []
    for seg_start, seg_end in segments:
        free.extend(_free_windows(seg_start, seg_end, busy))

    rescheduled: list[ScheduleBlock] = []
    for block in missed:
        duration = _parse_time(block.end_time) - _parse_time(block.start_time)
        if duration <= 0:
            duration = profile.session_minutes or 50

        placed = False
        for i, (ws, we) in enumerate(free):
            if we - ws >= duration:
                new_block = ScheduleBlock(
                    profile_id=profile.id,
                    day_of_week=day_of_week,
                    block_date=target,
                    start_time=_format_time(ws),
                    end_time=_format_time(ws + duration),
                    kind="study",
                    title=block.title,
                    subject=block.subject,
                    flexibility="movable",
                    source="rescheduled",
                    priority=block.priority,
                    status="planned",
                )
                db.add(new_block)
                rescheduled.append(new_block)

                # Shrink the free window
                new_start = ws + duration + (profile.break_minutes or 0)
                if new_start < we:
                    free[i] = (new_start, we)
                else:
                    free[i] = (we, we)  # exhausted

                placed = True
                break

        if not placed:
            break  # No more free windows

    if rescheduled:
        db.commit()
        for b in rescheduled:
            db.refresh(b)

    return rescheduled


def boost_subject_priority(
    db: Session,
    *,
    target_date: Optional[date] = None,
    lookahead_days: int = 3,
) -> list[ScheduleBlock]:
    """Create extra study blocks for subjects with assignments due within lookahead_days."""
    target = target_date or date.today()
    profile = get_active_profile(db)
    if not profile:
        return []

    deadline = target + timedelta(days=lookahead_days)
    urgent_assignments = (
        db.query(Assignment)
        .filter(Assignment.due_date >= target)
        .filter(Assignment.due_date <= deadline)
        .filter(Assignment.status != "done")
        .all()
    )

    if not urgent_assignments:
        return []

    # Collect unique subjects needing boost
    urgent_subjects: dict[str, int] = {}  # subject -> urgency (days until due)
    for a in urgent_assignments:
        subj = (a.subject or "General").strip()
        days_left = (a.due_date - target).days
        if subj not in urgent_subjects or days_left < urgent_subjects[subj]:
            urgent_subjects[subj] = days_left

    day_of_week = target.weekday()
    day_blocks = (
        db.query(ScheduleBlock)
        .filter(ScheduleBlock.profile_id == profile.id)
        .filter(ScheduleBlock.day_of_week == day_of_week)
        .order_by(ScheduleBlock.start_time)
        .all()
    )

    # Build busy intervals
    busy: list[tuple[int, int]] = []
    for b in day_blocks:
        busy.append((_parse_time(b.start_time), _parse_time(b.end_time)))

    wake_min = _parse_time(profile.wake_time)
    sleep_min = _parse_time(profile.sleep_time)
    if wake_min < sleep_min:
        segments = [(wake_min, sleep_min)]
    else:
        segments = [(wake_min, 24 * 60), (0, sleep_min)]

    free: list[tuple[int, int]] = []
    for seg_start, seg_end in segments:
        free.extend(_free_windows(seg_start, seg_end, busy))

    session_min = profile.session_minutes or 50
    boosted: list[ScheduleBlock] = []

    # Sort by urgency (most urgent first)
    for subj, days_left in sorted(urgent_subjects.items(), key=lambda x: x[1]):
        placed = False
        for i, (ws, we) in enumerate(free):
            if we - ws >= session_min:
                new_block = ScheduleBlock(
                    profile_id=profile.id,
                    day_of_week=day_of_week,
                    block_date=target,
                    start_time=_format_time(ws),
                    end_time=_format_time(ws + session_min),
                    kind="study",
                    title=f"Deadline boost: {subj}",
                    subject=subj,
                    flexibility="movable",
                    source="deadline_boost",
                    priority="high",
                    status="planned",
                )
                db.add(new_block)
                boosted.append(new_block)

                new_start = ws + session_min + (profile.break_minutes or 0)
                if new_start < we:
                    free[i] = (new_start, we)
                else:
                    free[i] = (we, we)

                placed = True
                break

        if not placed:
            break

    if boosted:
        db.commit()
        for b in boosted:
            db.refresh(b)

    return boosted


def smart_suggestions(
    db: Session,
    *,
    target_date: Optional[date] = None,
) -> list[dict]:
    """Generate AI-style schedule adjustment suggestions based on current state."""
    target = target_date or date.today()
    profile = get_active_profile(db)
    suggestions: list[dict] = []

    if not profile:
        suggestions.append({
            "type": "setup",
            "priority": "high",
            "message": "No schedule configured. Complete onboarding to get personalized study blocks.",
        })
        return suggestions

    day_of_week = target.weekday()
    day_blocks = (
        db.query(ScheduleBlock)
        .filter(ScheduleBlock.profile_id == profile.id)
        .filter(ScheduleBlock.day_of_week == day_of_week)
        .order_by(ScheduleBlock.start_time)
        .all()
    )

    study_blocks = [b for b in day_blocks if b.kind == "study"]
    missed = [b for b in study_blocks if b.status in ("skipped", "missed")]
    done = [b for b in study_blocks if b.status == "done"]

    # Suggestion: reschedule missed blocks
    if missed:
        subjects = list({b.subject or "General" for b in missed})
        suggestions.append({
            "type": "reschedule",
            "priority": "high",
            "message": f"You have {len(missed)} skipped/missed block(s) for {', '.join(subjects)}. Use POST /schedule/reschedule to find new time slots.",
            "missed_count": len(missed),
            "subjects": subjects,
        })

    # Suggestion: upcoming assignment deadlines
    deadline = target + timedelta(days=3)
    urgent = (
        db.query(Assignment)
        .filter(Assignment.due_date >= target)
        .filter(Assignment.due_date <= deadline)
        .filter(Assignment.status != "done")
        .all()
    )
    if urgent:
        for a in urgent:
            days_left = (a.due_date - target).days
            label = "today" if days_left == 0 else f"in {days_left} day(s)"
            suggestions.append({
                "type": "deadline_boost",
                "priority": "high" if days_left <= 1 else "medium",
                "message": f"\"{a.title}\" is due {label}. Consider boosting study time for {a.subject or 'this subject'}.",
                "assignment_id": a.id,
                "days_left": days_left,
            })

    # Suggestion: completion rate
    if study_blocks and not missed:
        completion = len(done) / len(study_blocks) * 100
        if completion >= 80:
            suggestions.append({
                "type": "praise",
                "priority": "low",
                "message": f"Great work! You've completed {len(done)}/{len(study_blocks)} study blocks today ({completion:.0f}%).",
            })
        elif completion >= 50:
            remaining = len(study_blocks) - len(done)
            suggestions.append({
                "type": "encouragement",
                "priority": "medium",
                "message": f"{remaining} study block(s) remaining today. Keep pushing!",
            })

    if not suggestions:
        suggestions.append({
            "type": "on_track",
            "priority": "low",
            "message": "Your schedule looks good for today. Stay focused!",
        })

    return suggestions


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
        wake_min = _parse_time(profile.wake_time)
        sleep_min = _parse_time(profile.sleep_time)

        # Support overnight schedules (e.g., wake 10:00, sleep 02:00)
        if wake_min < sleep_min:
            segments = [(wake_min, sleep_min)]
        else:
            segments = [(wake_min, 24 * 60), (0, sleep_min)]

        free_wins: list[tuple[int, int]] = []
        for seg_start, seg_end in segments:
            free_wins.extend(_free_windows(seg_start, seg_end, busy))

        session_index = 0
        for start, end in free_wins:
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
