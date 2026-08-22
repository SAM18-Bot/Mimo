from datetime import date, timedelta
from unittest.mock import patch

import pytest

from db.models import Assignment, DailySummary, RoastLog, User
from modules.ai_layer.roast_engine import RoastEngine
from modules.voice.intent_router import IntentRouter


# Helper function to create test user in the active DB session
def _create_test_user(session, email="test_m1_adv@example.com", user_id=None):
    user = session.query(User).filter(User.email == email).first()
    if not user:
        kwargs = {"email": email, "display_name": "M1 Test User"}
        if user_id is not None:
            kwargs["id"] = user_id
        user = User(**kwargs)
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


# ============================================================================
# 1. _save_roast() & RoastEngine Adversarial Tests
# ============================================================================

def test_save_roast_valid_user_id(client, db_session):
    """Verify _save_roast persists roast with valid user_id."""
    user = _create_test_user(db_session, "roast_valid@example.com")
    engine = RoastEngine()
    engine._save_roast(trigger="test_trigger", message="roast msg", user_id=user.id)

    log_entry = db_session.query(RoastLog).filter(
        RoastLog.user_id == user.id,
        RoastLog.trigger == "test_trigger"
    ).first()
    assert log_entry is not None
    assert log_entry.message == "roast msg"
    assert log_entry.user_id == user.id


def test_save_roast_missing_user_id_defaults(client, db_session):
    """Verify default parameter user_id=1 in _save_roast."""
    _create_test_user(db_session, "user1@example.com", user_id=1)
    engine = RoastEngine()
    engine._save_roast(trigger="default_trigger", message="default msg")

    log_entry = db_session.query(RoastLog).filter(
        RoastLog.trigger == "default_trigger"
    ).first()
    assert log_entry is not None
    assert log_entry.user_id == 1


def test_save_roast_none_user_id_db_constraint(client, db_session):
    """Verify _save_roast handles user_id=None without crashing python caller."""
    engine = RoastEngine()
    # RoastLog user_id is non-nullable. Passing user_id=None triggers IntegrityError in DB context.
    # _save_roast should catch Exception and log, not raise.
    try:
        engine._save_roast(trigger="none_trigger", message="none msg", user_id=None)
    except Exception as e:
        pytest.fail(f"_save_roast raised an unhandled exception for user_id=None: {e}")


def test_save_roast_invalid_user_id(client, db_session):
    """Verify _save_roast with non-existent user_id handles DB execution safely."""
    engine = RoastEngine()
    invalid_uid = 9999999
    try:
        engine._save_roast(trigger="invalid_uid_trigger", message="invalid uid msg", user_id=invalid_uid)
    except Exception as e:
        pytest.fail(f"_save_roast raised an unhandled exception for invalid user_id: {e}")


def test_roast_engine_fire_roast_user_id_propagation(client, db_session):
    """Verify user_id propagates through _fire_roast, _get_context, and _save_roast."""
    user = _create_test_user(db_session, "fire_roast_user@example.com")
    
    # Add a pending assignment for this specific user
    assignment = Assignment(
        user_id=user.id,
        title="Fire Roast Specific Assignment",
        due_date=date.today() + timedelta(days=1),
        status="pending"
    )
    db_session.add(assignment)
    db_session.commit()

    captured_roasts = []
    def mock_broadcast(data):
        captured_roasts.append(data)

    engine = RoastEngine(broadcast_fn=mock_broadcast)
    
    with patch("modules.ai_layer.roast_engine.generate_roast", return_value="Custom mock roast text"):
        engine.trigger_roast(trigger="distraction", app="YouTube", minutes=15, user_id=user.id)

    # Check DB log for this user
    log_entry = db_session.query(RoastLog).filter(
        RoastLog.user_id == user.id,
        RoastLog.trigger == "distraction"
    ).first()
    assert log_entry is not None
    assert log_entry.message == "Custom mock roast text"
    assert log_entry.user_id == user.id


# ============================================================================
# 2. _handle_what_to_study() Adversarial Tests
# ============================================================================

def test_handle_what_to_study_normal(client, db_session):
    """Verify _handle_what_to_study calls advisor and executes without exception."""
    user = _create_test_user(db_session, "study_normal@example.com")
    spoken = []
    broadcasted = []

    router = IntentRouter(
        speak_fn=lambda m: spoken.append(m),
        broadcast_fn=lambda b: broadcasted.append(b),
        user_id=user.id
    )

    router._handle_what_to_study()
    assert len(broadcasted) == 1
    assert broadcasted[0]["type"] == "study_advice"
    assert "message" in broadcasted[0]


def test_handle_what_to_study_advisor_exception_fallback(client, db_session):
    """Verify fallback path in _handle_what_to_study when StudyAdvisor raises Exception."""
    user = _create_test_user(db_session, "study_fallback@example.com")

    # Add assignment for fallback
    a = Assignment(
        user_id=user.id,
        title="Fallback Urgent Task",
        due_date=date.today() + timedelta(days=2),
        status="pending"
    )
    db_session.add(a)
    db_session.commit()

    spoken = []
    broadcasted = []
    router = IntentRouter(
        speak_fn=lambda m: spoken.append(m),
        broadcast_fn=lambda b: broadcasted.append(b),
        user_id=user.id
    )

    # Force StudyAdvisor.get_next_to_study to raise RuntimeError
    with patch("modules.ai_layer.study_advisor.StudyAdvisor.get_next_to_study", side_effect=RuntimeError("Advisor error")):
        router._handle_what_to_study()

    assert len(spoken) == 1
    assert "Fallback Urgent Task" in spoken[0]
    assert len(broadcasted) == 1
    assert "Fallback Urgent Task" in broadcasted[0]["message"]


def test_handle_what_to_study_multi_tenant_isolation(client, db_session):
    """Verify fallback path in _handle_what_to_study does not leak another user's assignments."""
    user_a = _create_test_user(db_session, "tenant_a_study@example.com")
    user_b = _create_test_user(db_session, "tenant_b_study@example.com")

    # User A has urgent assignment
    a_task = Assignment(
        user_id=user_a.id,
        title="User A Super Secret Math Homework",
        due_date=date.today() + timedelta(days=1),
        status="pending"
    )
    db_session.add(a_task)
    db_session.commit()

    # User B has no assignments
    spoken_b = []
    router_b = IntentRouter(
        speak_fn=lambda m: spoken_b.append(m),
        user_id=user_b.id
    )

    with patch("modules.ai_layer.study_advisor.StudyAdvisor.get_next_to_study", side_effect=Exception("Trigger fallback")):
        router_b._handle_what_to_study()

    assert len(spoken_b) == 1
    assert "User A Super Secret Math Homework" not in spoken_b[0]
    assert "No assignments due soon" in spoken_b[0]


# ============================================================================
# 3. push_sync() and pull_sync() Route Data Integrity Tests
# ============================================================================

def test_sync_endpoints_authentication_enforcement(client):
    """Verify /sync/push and /sync/pull reject unauthenticated requests with 401."""
    res_push = client.post("/sync/push", json={"date": date.today().isoformat(), "mobileProductiveMin": 10, "mobileDistractingMin": 0, "mobileNeutralMin": 0})
    assert res_push.status_code == 401

    res_pull = client.get("/sync/pull")
    assert res_pull.status_code == 401


def test_push_sync_data_integrity_and_accumulation(client, auth_headers, db_session):
    """Verify push_sync correctly creates and updates DailySummary with column mapping."""
    user = db_session.query(User).filter(User.id == 1).first()
    assert user is not None

    test_date_str = "2026-08-15"
    payload1 = {
        "date": test_date_str,
        "mobileProductiveMin": 20,
        "mobileDistractingMin": 10,
        "mobileNeutralMin": 5,
        "assignments": []
    }
    r1 = client.post("/sync/push", json=payload1, headers=auth_headers)
    assert r1.status_code == 200

    summary = db_session.query(DailySummary).filter(
        DailySummary.user_id == user.id,
        DailySummary.date == date.fromisoformat(test_date_str)
    ).first()
    assert summary is not None
    assert summary.productive_time_s == 20 * 60
    assert summary.distracted_time_s == 10 * 60
    assert summary.neutral_time_s == 5 * 60
    assert summary.desk_time_s == 35 * 60

    # Second push on same day should accumulate stats
    payload2 = {
        "date": test_date_str,
        "mobileProductiveMin": 10,
        "mobileDistractingMin": 5,
        "mobileNeutralMin": 5,
        "assignments": []
    }
    r2 = client.post("/sync/push", json=payload2, headers=auth_headers)
    assert r2.status_code == 200

    db_session.refresh(summary)
    assert summary.productive_time_s == 30 * 60
    assert summary.distracted_time_s == 15 * 60
    assert summary.neutral_time_s == 10 * 60
    assert summary.desk_time_s == 55 * 60


def test_push_sync_invalid_date_fallback(client, auth_headers, db_session):
    """Verify push_sync handles invalid date format by falling back to date.today()."""
    payload = {
        "date": "invalid-date-format-str",
        "mobileProductiveMin": 15,
        "mobileDistractingMin": 0,
        "mobileNeutralMin": 0,
        "assignments": []
    }
    res = client.post("/sync/push", json=payload, headers=auth_headers)
    assert res.status_code == 200

    summary = db_session.query(DailySummary).filter(
        DailySummary.user_id == 1,
        DailySummary.date == date.today()
    ).first()
    assert summary is not None


def test_pull_sync_multi_tenant_isolation(client, auth_headers, db_session):
    """Verify pull_sync only returns assignments for the authenticated user."""
    user1 = db_session.query(User).filter(User.id == 1).first()
    user2 = _create_test_user(db_session, "other_pull_user@example.com")

    # Add assignment for User 1
    a1 = Assignment(
        user_id=user1.id,
        title="User 1 Task for Pull",
        due_date=date.today(),
        status="pending"
    )
    # Add assignment for User 2
    a2 = Assignment(
        user_id=user2.id,
        title="User 2 Secret Task for Pull",
        due_date=date.today(),
        status="pending"
    )
    db_session.add_all([a1, a2])
    db_session.commit()

    res = client.get("/sync/pull", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()

    titles = [a["title"] for a in data.get("assignments", [])]
    assert "User 1 Task for Pull" in titles
    assert "User 2 Secret Task for Pull" not in titles
