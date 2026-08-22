from datetime import date

import pytest


def _minutes(value: str) -> int:
    hour, minute = map(int, value.split(":"))
    return hour * 60 + minute


def test_build_onboarding_schedule_creates_profile_and_blocks(db_session):
    from modules.schedule.manager import build_onboarding_schedule, get_weekly_schedule

    profile = build_onboarding_schedule(
        db_session,
        user_id=1,
        wake_time="06:30",
        sleep_time="22:30",
        school_days=[0, 1, 2, 3, 4],
        school_start="08:00",
        school_end="15:00",
        study_goal_minutes=120,
        session_minutes=50,
        break_minutes=10,
        subjects=[
            {"name": "Math", "priority": "high"},
            {"name": "Physics", "priority": "medium"},
        ],
    )

    blocks = get_weekly_schedule(db_session, 1)
    assert profile.active is True
    assert any(b.kind == "school" for b in blocks)
    assert any(b.kind == "study" and b.subject == "Math" for b in blocks)
    assert any(b.kind == "study" and b.subject == "Physics" for b in blocks)


def test_generated_study_blocks_do_not_overlap_fixed_blocks(db_session):
    from modules.schedule.manager import build_onboarding_schedule, get_weekly_schedule

    build_onboarding_schedule(
        db_session,
        user_id=1,
        wake_time="06:00",
        sleep_time="22:00",
        school_days=[0],
        school_start="08:00",
        school_end="15:00",
        study_goal_minutes=100,
        session_minutes=50,
        fixed_blocks=[
            {"day_of_week": 0, "title": "Football", "start_time": "17:00", "end_time": "18:00"},
        ],
        subjects=[{"name": "Chemistry", "priority": "high"}],
    )

    monday = [b for b in get_weekly_schedule(db_session, 1) if b.day_of_week == 0]
    busy = [(b.kind, _minutes(b.start_time), _minutes(b.end_time)) for b in monday if b.kind != "study"]
    study = [(b.start_time, b.end_time) for b in monday if b.kind == "study"]

    for start_text, end_text in study:
        start = _minutes(start_text)
        end = _minutes(end_text)
        for _, busy_start, busy_end in busy:
            assert end <= busy_start or start >= busy_end


def test_rebuilding_schedule_deactivates_previous_profile(db_session):
    from db.models import ScheduleProfile
    from modules.schedule.manager import build_onboarding_schedule, schedule_status

    build_onboarding_schedule(
        db_session,
        user_id=1,
        wake_time="06:30",
        sleep_time="22:00",
        study_goal_minutes=60,
        subjects=[{"name": "Math", "priority": "medium"}],
    )
    second = build_onboarding_schedule(
        db_session,
        user_id=1,
        wake_time="07:00",
        sleep_time="22:30",
        study_goal_minutes=60,
        subjects=[{"name": "Biology", "priority": "medium"}],
    )

    profiles = db_session.query(ScheduleProfile).all()
    assert len(profiles) == 2
    assert sum(1 for p in profiles if p.active) == 1
    assert schedule_status(db_session, 1)["profile_id"] == second.id


def test_overnight_schedule_generates_blocks(db_session):
    """Overnight schedule (wake 22:00, sleep 02:00) should now work, not raise."""
    from modules.schedule.manager import build_onboarding_schedule, get_weekly_schedule

    profile = build_onboarding_schedule(
        db_session,
        user_id=1,
        wake_time="22:00",
        sleep_time="02:00",
        study_goal_minutes=60,
        session_minutes=30,
        break_minutes=5,
        school_days=[],
        subjects=[{"name": "Math", "priority": "high"}],
    )

    blocks = get_weekly_schedule(db_session, 1)
    study_blocks = [b for b in blocks if b.kind == "study"]
    assert len(study_blocks) > 0
    assert profile.active is True

    # Verify blocks span across midnight (some after 22:00, some before 02:00)
    for b in study_blocks:
        start_min = int(b.start_time.split(":")[0]) * 60 + int(b.start_time.split(":")[1])
        # Must be either >= 22:00 (1320) or < 02:00 (120)
        assert start_min >= 1320 or start_min < 120


def test_same_wake_sleep_raises_value_error(db_session):
    from modules.schedule.manager import build_onboarding_schedule

    with pytest.raises(ValueError, match="cannot be the same"):
        build_onboarding_schedule(
            db_session,
            user_id=1,
            wake_time="08:00",
            sleep_time="08:00",
            study_goal_minutes=60,
        )


def test_update_block_status(db_session):
    from modules.schedule.manager import (
        build_onboarding_schedule,
        get_weekly_schedule,
        update_block_status,
    )

    build_onboarding_schedule(
        db_session,
        user_id=1,
        wake_time="06:30",
        sleep_time="22:00",
        study_goal_minutes=60,
        subjects=[{"name": "Math", "priority": "medium"}],
    )
    block = next(b for b in get_weekly_schedule(db_session, 1) if b.kind == "study")
    updated = update_block_status(db_session, block.id, "done")

    assert updated.status == "done"


def test_onboarding_questions_api(client, auth_headers):
    r = client.get("/schedule/onboarding/questions", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data["questions"]) >= 5
    assert any(q["key"] == "subjects" for q in data["questions"])


def test_schedule_page_returns_html(client):
    r = client.get("/static/schedule.html")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert "Build Your Week" in r.text
    assert "buildSchedule" in r.text


def test_onboarding_api_creates_weekly_schedule(client, auth_headers):
    r = client.post(
        "/schedule/onboarding",
        json={
            "wake_time": "06:30",
            "sleep_time": "22:30",
            "school_days": [0, 1, 2, 3, 4],
            "school_start": "08:00",
            "school_end": "15:00",
            "study_goal_minutes": 100,
            "session_minutes": 50,
            "subjects": [
                {"name": "Math", "priority": "high"},
                {"name": "English", "priority": "low"},
            ],
        },
        headers=auth_headers,
    )

    assert r.status_code == 201
    body = r.json()
    assert body["profile"]["wake_time"] == "06:30"
    assert any(b["kind"] == "study" for b in body["blocks"])


def test_schedule_status_and_weekly_api(client, auth_headers):
    client.post(
        "/schedule/onboarding",
        json={
            "wake_time": "06:30",
            "sleep_time": "22:30",
            "study_goal_minutes": 60,
            "subjects": [{"name": "Physics", "priority": "medium"}],
        },
        headers=auth_headers,
    )

    status = client.get("/schedule/status", headers=auth_headers).json()
    weekly = client.get("/schedule/weekly", headers=auth_headers).json()

    assert status["configured"] is True
    assert status["blocks"] == len(weekly)
    assert all("start_time" in block for block in weekly)


def test_today_api_filters_by_target_date(client, auth_headers):
    client.post(
        "/schedule/onboarding",
        json={
            "wake_time": "06:30",
            "sleep_time": "22:30",
            "study_goal_minutes": 60,
            "subjects": [{"name": "Computer Science", "priority": "high"}],
        },
        headers=auth_headers,
    )

    r = client.get("/schedule/today", params={"target_date": "2026-08-05"}, headers=auth_headers)
    assert r.status_code == 200
    blocks = r.json()
    assert blocks
    assert all(block["day_of_week"] == date(2026, 8, 5).weekday() for block in blocks)


def test_patch_block_status_api(client, auth_headers):
    created = client.post(
        "/schedule/onboarding",
        json={
            "wake_time": "06:30",
            "sleep_time": "22:30",
            "study_goal_minutes": 60,
            "subjects": [{"name": "Math", "priority": "medium"}],
        },
        headers=auth_headers,
    ).json()
    block_id = next(b["id"] for b in created["blocks"] if b["kind"] == "study")

    r = client.patch(f"/schedule/blocks/{block_id}", json={"status": "skipped"}, headers=auth_headers)

    assert r.status_code == 200
    assert r.json()["status"] == "skipped"


# ═══════════════════════════════════════════════════════
# RESCHEDULING TESTS
# ═══════════════════════════════════════════════════════


def test_reschedule_missed_blocks_creates_new_blocks(db_session):
    from modules.schedule.manager import (
        build_onboarding_schedule,
        get_weekly_schedule,
        reschedule_missed_blocks,
        update_block_status,
    )

    build_onboarding_schedule(
        db_session,
        user_id=1,
        wake_time="06:00",
        sleep_time="22:00",
        study_goal_minutes=120,
        session_minutes=50,
        break_minutes=10,
        school_days=[],
        subjects=[{"name": "Math", "priority": "high"}],
    )

    blocks = get_weekly_schedule(db_session, 1)
    study_blocks = [b for b in blocks if b.kind == "study"]
    assert len(study_blocks) > 0

    # Mark the first study block for today's weekday as skipped
    today_dow = date.today().weekday()
    today_study = [b for b in study_blocks if b.day_of_week == today_dow]
    if not today_study:
        return  # No blocks on today's weekday, skip test

    update_block_status(db_session, today_study[0].id, "skipped")

    rescheduled = reschedule_missed_blocks(db_session, 1)
    assert len(rescheduled) >= 1
    assert rescheduled[0].source == "rescheduled"
    assert rescheduled[0].subject == today_study[0].subject
    assert rescheduled[0].status == "planned"


def test_reschedule_returns_empty_when_no_missed(db_session):
    from modules.schedule.manager import (
        build_onboarding_schedule,
        reschedule_missed_blocks,
    )

    build_onboarding_schedule(
        db_session,
        user_id=1,
        wake_time="06:00",
        sleep_time="22:00",
        study_goal_minutes=60,
        school_days=[],
        subjects=[{"name": "Physics", "priority": "medium"}],
    )

    rescheduled = reschedule_missed_blocks(db_session, 1)
    assert rescheduled == []


def test_reschedule_returns_empty_when_no_profile(db_session):
    from modules.schedule.manager import reschedule_missed_blocks

    assert reschedule_missed_blocks(db_session, 1) == []


# ═══════════════════════════════════════════════════════
# PRIORITY BOOST TESTS
# ═══════════════════════════════════════════════════════


def test_boost_creates_blocks_for_urgent_assignments(db_session):
    from db.models import Assignment
    from modules.schedule.manager import (
        boost_subject_priority,
        build_onboarding_schedule,
    )

    build_onboarding_schedule(
        db_session,
        user_id=1,
        wake_time="06:00",
        sleep_time="22:00",
        study_goal_minutes=60,
        session_minutes=50,
        school_days=[],
        subjects=[{"name": "Math", "priority": "medium"}],
    )

    # Create an urgent assignment due tomorrow
    tomorrow = date.today() + __import__("datetime").timedelta(days=1)
    assignment = Assignment(
        user_id=1,
        title="Math Homework",
        subject="Math",
        due_date=tomorrow,
        priority="high",
        status="pending",
    )
    db_session.add(assignment)
    db_session.commit()

    boosted = boost_subject_priority(db_session, 1)
    assert len(boosted) >= 1
    assert boosted[0].source == "deadline_boost"
    assert boosted[0].subject == "Math"
    assert boosted[0].priority == "high"


def test_boost_returns_empty_when_no_urgent_assignments(db_session):
    from modules.schedule.manager import (
        boost_subject_priority,
        build_onboarding_schedule,
    )

    build_onboarding_schedule(
        db_session,
        user_id=1,
        wake_time="06:00",
        sleep_time="22:00",
        study_goal_minutes=60,
        school_days=[],
        subjects=[{"name": "History", "priority": "low"}],
    )

    boosted = boost_subject_priority(db_session, 1)
    assert boosted == []


def test_boost_ignores_done_assignments(db_session):
    from db.models import Assignment
    from modules.schedule.manager import (
        boost_subject_priority,
        build_onboarding_schedule,
    )

    build_onboarding_schedule(
        db_session,
        user_id=1,
        wake_time="06:00",
        sleep_time="22:00",
        study_goal_minutes=60,
        school_days=[],
        subjects=[{"name": "English", "priority": "medium"}],
    )

    tomorrow = date.today() + __import__("datetime").timedelta(days=1)
    assignment = Assignment(
        user_id=1,
        title="English Essay",
        subject="English",
        due_date=tomorrow,
        priority="high",
        status="done",
    )
    db_session.add(assignment)
    db_session.commit()

    boosted = boost_subject_priority(db_session, 1)
    assert boosted == []


def test_boost_returns_empty_when_no_profile(db_session):
    from modules.schedule.manager import boost_subject_priority

    assert boost_subject_priority(db_session, 1) == []


# ═══════════════════════════════════════════════════════
# SMART SUGGESTIONS TESTS
# ═══════════════════════════════════════════════════════


def test_smart_suggestions_no_profile(db_session):
    from modules.schedule.manager import smart_suggestions

    result = smart_suggestions(db_session, 1)
    assert len(result) == 1
    assert result[0]["type"] == "setup"
    assert result[0]["priority"] == "high"


def test_smart_suggestions_with_missed_blocks(db_session):
    from modules.schedule.manager import (
        build_onboarding_schedule,
        smart_suggestions,
        update_block_status,
    )

    build_onboarding_schedule(
        db_session,
        user_id=1,
        wake_time="06:00",
        sleep_time="22:00",
        study_goal_minutes=60,
        school_days=[],
        subjects=[{"name": "Biology", "priority": "medium"}],
    )

    from modules.schedule.manager import get_day_schedule

    today_blocks = get_day_schedule(db_session, 1)
    study_blocks = [b for b in today_blocks if b.kind == "study"]
    if not study_blocks:
        return

    update_block_status(db_session, study_blocks[0].id, "skipped")

    result = smart_suggestions(db_session, 1)
    reschedule_suggestions = [s for s in result if s["type"] == "reschedule"]
    assert len(reschedule_suggestions) >= 1
    assert reschedule_suggestions[0]["missed_count"] >= 1


def test_smart_suggestions_on_track(db_session):
    from modules.schedule.manager import build_onboarding_schedule, smart_suggestions

    build_onboarding_schedule(
        db_session,
        user_id=1,
        wake_time="06:00",
        sleep_time="22:00",
        study_goal_minutes=60,
        school_days=[],
        subjects=[{"name": "Art", "priority": "low"}],
    )

    result = smart_suggestions(db_session, 1)
    # Should at least have an on_track or encouragement suggestion
    assert len(result) >= 1


# ═══════════════════════════════════════════════════════
# API ENDPOINT TESTS
# ═══════════════════════════════════════════════════════


def test_reschedule_api_endpoint(client, auth_headers):
    # Create a schedule first
    client.post(
        "/schedule/onboarding",
        json={
            "wake_time": "06:00",
            "sleep_time": "22:00",
            "study_goal_minutes": 60,
            "subjects": [{"name": "Math", "priority": "high"}],
        },
        headers=auth_headers,
    )

    r = client.post("/schedule/reschedule", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_boost_api_endpoint(client, auth_headers):
    client.post(
        "/schedule/onboarding",
        json={
            "wake_time": "06:00",
            "sleep_time": "22:00",
            "study_goal_minutes": 60,
            "subjects": [{"name": "Physics", "priority": "medium"}],
        },
        headers=auth_headers,
    )

    r = client.post("/schedule/boost", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_smart_suggestions_api_endpoint(client, auth_headers):
    r = client.get("/schedule/smart-suggestions", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "suggestions" in data
    assert isinstance(data["suggestions"], list)
    assert len(data["suggestions"]) >= 1


def test_missed_status_accepted_in_block_update(client, auth_headers):
    created = client.post(
        "/schedule/onboarding",
        json={
            "wake_time": "06:30",
            "sleep_time": "22:30",
            "study_goal_minutes": 60,
            "subjects": [{"name": "Chemistry", "priority": "medium"}],
        },
        headers=auth_headers,
    ).json()
    block_id = next(b["id"] for b in created["blocks"] if b["kind"] == "study")

    r = client.patch(f"/schedule/blocks/{block_id}", json={"status": "missed"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "missed"


def test_boost_subject_priority_user_isolation(db_session):
    from datetime import date, timedelta

    from db.models import Assignment, User
    from modules.schedule.manager import (
        boost_subject_priority,
        build_onboarding_schedule,
    )

    u1 = User(email="u1_boost@test.com", password_hash="pw")
    u2 = User(email="u2_boost@test.com", password_hash="pw")
    db_session.add_all([u1, u2])
    db_session.commit()

    build_onboarding_schedule(
        db_session, user_id=u1.id, wake_time="06:00", sleep_time="22:00", study_goal_minutes=60
    )
    build_onboarding_schedule(
        db_session, user_id=u2.id, wake_time="06:00", sleep_time="22:00", study_goal_minutes=60
    )

    # Urgent assignment for u2 only
    a_u2 = Assignment(
        user_id=u2.id,
        title="U2 Math Exam",
        subject="Math",
        due_date=date.today() + timedelta(days=1),
        status="todo",
    )
    db_session.add(a_u2)
    db_session.commit()

    # u1 boosting priority should NOT pick up u2's assignment
    boosted_u1 = boost_subject_priority(db_session, user_id=u1.id)
    assert not any("Math" in b.title for b in boosted_u1)

    # u2 boosting priority SHOULD pick up u2's assignment
    boosted_u2 = boost_subject_priority(db_session, user_id=u2.id)
    assert any("Math" in b.title for b in boosted_u2)


def test_smart_suggestions_user_isolation(db_session):
    from datetime import date, timedelta

    from db.models import Assignment, User
    from modules.schedule.manager import build_onboarding_schedule, smart_suggestions

    u1 = User(email="u1_sugg@test.com", password_hash="pw")
    u2 = User(email="u2_sugg@test.com", password_hash="pw")
    db_session.add_all([u1, u2])
    db_session.commit()

    build_onboarding_schedule(
        db_session, user_id=u1.id, wake_time="06:00", sleep_time="22:00", study_goal_minutes=60
    )

    a_u2 = Assignment(
        user_id=u2.id,
        title="U2 Bio Lab",
        subject="Biology",
        due_date=date.today() + timedelta(days=1),
        status="todo",
    )
    db_session.add(a_u2)
    db_session.commit()

    suggs_u1 = smart_suggestions(db_session, user_id=u1.id)
    assert not any(s.get("assignment_id") == a_u2.id for s in suggs_u1)


def test_update_block_status_ownership(db_session):
    from db.models import User
    from modules.schedule.manager import (
        build_onboarding_schedule,
        get_weekly_schedule,
        update_block_status,
    )

    u1 = User(email="u1_block@test.com", password_hash="pw")
    u2 = User(email="u2_block@test.com", password_hash="pw")
    db_session.add_all([u1, u2])
    db_session.commit()

    build_onboarding_schedule(
        db_session, user_id=u1.id, wake_time="06:00", sleep_time="22:00", study_goal_minutes=60
    )
    blocks_u1 = get_weekly_schedule(db_session, user_id=u1.id)
    b1_id = blocks_u1[0].id

    # User 2 attempting to update User 1's block should fail (return None)
    res = update_block_status(db_session, block_id=b1_id, status="done", user_id=u2.id)
    assert res is None

    # User 1 updating User 1's block should succeed
    res_ok = update_block_status(db_session, block_id=b1_id, status="done", user_id=u1.id)
    assert res_ok is not None
    assert res_ok.status == "done"

