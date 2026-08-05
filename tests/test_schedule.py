from datetime import date

import pytest


def _minutes(value: str) -> int:
    hour, minute = map(int, value.split(":"))
    return hour * 60 + minute


def test_build_onboarding_schedule_creates_profile_and_blocks(db_session):
    from modules.schedule.manager import build_onboarding_schedule, get_weekly_schedule

    profile = build_onboarding_schedule(
        db_session,
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

    blocks = get_weekly_schedule(db_session)
    assert profile.active is True
    assert any(b.kind == "school" for b in blocks)
    assert any(b.kind == "study" and b.subject == "Math" for b in blocks)
    assert any(b.kind == "study" and b.subject == "Physics" for b in blocks)


def test_generated_study_blocks_do_not_overlap_fixed_blocks(db_session):
    from modules.schedule.manager import build_onboarding_schedule, get_weekly_schedule

    build_onboarding_schedule(
        db_session,
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

    monday = [b for b in get_weekly_schedule(db_session) if b.day_of_week == 0]
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
        wake_time="06:30",
        sleep_time="22:00",
        study_goal_minutes=60,
        subjects=[{"name": "Math", "priority": "medium"}],
    )
    second = build_onboarding_schedule(
        db_session,
        wake_time="07:00",
        sleep_time="22:30",
        study_goal_minutes=60,
        subjects=[{"name": "Biology", "priority": "medium"}],
    )

    profiles = db_session.query(ScheduleProfile).all()
    assert len(profiles) == 2
    assert sum(1 for p in profiles if p.active) == 1
    assert schedule_status(db_session)["profile_id"] == second.id


def test_invalid_times_raise_value_error(db_session):
    from modules.schedule.manager import build_onboarding_schedule

    with pytest.raises(ValueError):
        build_onboarding_schedule(
            db_session,
            wake_time="23:00",
            sleep_time="06:00",
            study_goal_minutes=60,
        )


def test_update_block_status(db_session):
    from modules.schedule.manager import build_onboarding_schedule, get_weekly_schedule, update_block_status

    build_onboarding_schedule(
        db_session,
        wake_time="06:30",
        sleep_time="22:00",
        study_goal_minutes=60,
        subjects=[{"name": "Math", "priority": "medium"}],
    )
    block = next(b for b in get_weekly_schedule(db_session) if b.kind == "study")
    updated = update_block_status(db_session, block.id, "done")

    assert updated.status == "done"


def test_onboarding_questions_api(client):
    r = client.get("/schedule/onboarding/questions")
    assert r.status_code == 200
    data = r.json()
    assert len(data["questions"]) >= 5
    assert any(q["key"] == "subjects" for q in data["questions"])


def test_schedule_page_returns_html(client):
    r = client.get("/schedule")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert "Build Your Week" in r.text
    assert "buildSchedule" in r.text


def test_onboarding_api_creates_weekly_schedule(client):
    r = client.post("/schedule/onboarding", json={
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
    })

    assert r.status_code == 201
    body = r.json()
    assert body["profile"]["wake_time"] == "06:30"
    assert any(b["kind"] == "study" for b in body["blocks"])


def test_schedule_status_and_weekly_api(client):
    client.post("/schedule/onboarding", json={
        "wake_time": "06:30",
        "sleep_time": "22:30",
        "study_goal_minutes": 60,
        "subjects": [{"name": "Physics", "priority": "medium"}],
    })

    status = client.get("/schedule/status").json()
    weekly = client.get("/schedule/weekly").json()

    assert status["configured"] is True
    assert status["blocks"] == len(weekly)
    assert all("start_time" in block for block in weekly)


def test_today_api_filters_by_target_date(client):
    client.post("/schedule/onboarding", json={
        "wake_time": "06:30",
        "sleep_time": "22:30",
        "study_goal_minutes": 60,
        "subjects": [{"name": "Computer Science", "priority": "high"}],
    })

    r = client.get("/schedule/today", params={"target_date": "2026-08-05"})
    assert r.status_code == 200
    blocks = r.json()
    assert blocks
    assert all(block["day_of_week"] == date(2026, 8, 5).weekday() for block in blocks)


def test_patch_block_status_api(client):
    created = client.post("/schedule/onboarding", json={
        "wake_time": "06:30",
        "sleep_time": "22:30",
        "study_goal_minutes": 60,
        "subjects": [{"name": "Math", "priority": "medium"}],
    }).json()
    block_id = next(b["id"] for b in created["blocks"] if b["kind"] == "study")

    r = client.patch(f"/schedule/blocks/{block_id}", json={"status": "skipped"})

    assert r.status_code == 200
    assert r.json()["status"] == "skipped"
