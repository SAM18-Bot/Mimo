from datetime import date, timedelta

from db.models import DailySummary, RoastLog, User
from modules.ai_layer.roast_engine import RoastEngine
from modules.assignments.manager import create_assignment
from modules.voice.intent_router import IntentRouter


def test_push_sync_stress_column_names_and_dates(client, auth_headers, db_session):
    """Stress test push_sync with various date formats and initial DailySummary states."""
    user = db_session.query(User).filter(User.id == 1).first()
    assert user is not None

    # Test 1: Standard push creating new summary
    payload1 = {
        "date": "2026-08-10",
        "mobileProductiveMin": 20,
        "mobileDistractingMin": 10,
        "mobileNeutralMin": 5,
        "assignments": []
    }
    resp1 = client.post("/sync/push", json=payload1, headers=auth_headers)
    assert resp1.status_code == 200, f"Expected 200, got {resp1.status_code}: {resp1.text}"

    summary1 = db_session.query(DailySummary).filter(
        DailySummary.user_id == user.id,
        DailySummary.date == date(2026, 8, 10)
    ).first()
    assert summary1 is not None
    assert summary1.productive_time_s == 20 * 60
    assert summary1.distracted_time_s == 10 * 60
    assert summary1.neutral_time_s == 5 * 60
    assert summary1.desk_time_s == 35 * 60

    # Test 2: Accumulating onto existing summary
    resp2 = client.post("/sync/push", json=payload1, headers=auth_headers)
    assert resp2.status_code == 200
    db_session.refresh(summary1)
    assert summary1.productive_time_s == 40 * 60
    assert summary1.distracted_time_s == 20 * 60
    assert summary1.neutral_time_s == 10 * 60
    assert summary1.desk_time_s == 70 * 60

    # Test 3: Invalid date string fallback to date.today()
    payload_invalid_date = {
        "date": "invalid-date-string",
        "mobileProductiveMin": 15,
        "mobileDistractingMin": 5,
        "mobileNeutralMin": 0,
        "assignments": []
    }
    resp3 = client.post("/sync/push", json=payload_invalid_date, headers=auth_headers)
    assert resp3.status_code == 200

    today_summary = db_session.query(DailySummary).filter(
        DailySummary.user_id == user.id,
        DailySummary.date == date.today()
    ).first()
    assert today_summary is not None
    assert today_summary.productive_time_s >= 15 * 60


def test_pull_sync_user_isolation(client, auth_headers, db_session):
    """Stress test pull_sync parameter and user isolation."""
    # Create user 2
    u2 = User(email="user2_sync@example.com", display_name="User Two")
    db_session.add(u2)
    db_session.commit()
    db_session.refresh(u2)

    # Create assignment for User 1
    create_assignment(db_session, title="User1 Sync Task", due_date=date.today() + timedelta(days=2), user_id=1)
    # Create assignment for User 2
    create_assignment(db_session, title="User2 Sync Task", due_date=date.today() + timedelta(days=2), user_id=u2.id)

    # Call pull_sync authenticated as User 1
    resp = client.get("/sync/pull", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    titles = [a["title"] for a in data["assignments"]]
    assert "User1 Sync Task" in titles
    assert "User2 Sync Task" not in titles


def test_roast_engine_creation_and_multiuser(client, auth_headers, db_session):
    """Stress test RoastEngine RoastLog creation and user_id passing across triggers."""
    u2 = User(email="user2_roast@example.com", display_name="User Two")
    db_session.add(u2)
    db_session.commit()
    db_session.refresh(u2)

    assert u2.id != 1

    engine = RoastEngine()
    engine._save_roast(trigger="test_user1", message="roast msg 1", user_id=1)
    engine._save_roast(trigger="test_user2", message="roast msg 2", user_id=u2.id)

    logs_u1 = db_session.query(RoastLog).filter(RoastLog.user_id == 1).all()
    logs_u2 = db_session.query(RoastLog).filter(RoastLog.user_id == u2.id).all()

    assert any(l.trigger == "test_user1" for l in logs_u1)
    assert any(l.trigger == "test_user2" for l in logs_u2)
    assert not any(l.trigger == "test_user2" for l in logs_u1)
    assert not any(l.trigger == "test_user1" for l in logs_u2)

    # Test trigger_roast with explicit user_id
    engine.trigger_roast(trigger="manual_roast", app="VSCode", minutes=15, user_id=u2.id)
    db_session.expire_all()
    logs_u2_after = db_session.query(RoastLog).filter(RoastLog.user_id == u2.id).all()
    assert any(l.trigger == "manual_roast" for l in logs_u2_after)


def test_intent_router_what_to_study_multiuser(client, auth_headers, db_session, monkeypatch):
    """Stress test IntentRouter _handle_what_to_study with specific user_id both normal and fallback paths."""
    u2 = User(email="user2_intent@example.com", display_name="User Two")
    db_session.add(u2)
    db_session.commit()
    db_session.refresh(u2)

    spoken_msgs = []
    def mock_speak(text):
        spoken_msgs.append(text)

    # Test normal path
    router1 = IntentRouter(speak_fn=mock_speak, user_id=1)
    router1._handle_what_to_study()
    assert len(spoken_msgs) > 0

    spoken_msgs.clear()
    router2 = IntentRouter(speak_fn=mock_speak, user_id=u2.id)
    router2._handle_what_to_study()
    assert len(spoken_msgs) > 0

    # Test exception fallback path by breaking StudyAdvisor
    from modules.ai_layer import study_advisor
    def faulty_init(self, db):
        raise RuntimeError("Advisor broken for stress test")
    
    monkeypatch.setattr(study_advisor.StudyAdvisor, "__init__", faulty_init)
    
    spoken_msgs.clear()
    router2._handle_what_to_study()
    assert len(spoken_msgs) > 0
