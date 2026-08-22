from datetime import date

from db.models import Assignment, DailySummary, RoastLog, User
from modules.ai_layer.roast_engine import RoastEngine
from modules.voice.intent_router import IntentRouter


def test_roast_engine_save_roast(db_session, auth_headers):
    """Test RoastEngine._save_roast persists user_id into RoastLog without crashing."""
    user = db_session.query(User).filter(User.id == 1).first()
    assert user is not None

    engine = RoastEngine()
    engine._save_roast(trigger="test_trigger", message="test message", user_id=user.id)
    
    log_entry = db_session.query(RoastLog).filter(RoastLog.user_id == user.id).first()
    assert log_entry is not None
    assert log_entry.trigger == "test_trigger"
    assert log_entry.message == "test message"
    assert log_entry.user_id == user.id


def test_roast_engine_trigger_roast(db_session, auth_headers):
    """Test RoastEngine.trigger_roast accepts user_id and executes successfully."""
    user = db_session.query(User).filter(User.id == 1).first()
    assert user is not None

    engine = RoastEngine()
    engine.trigger_roast(trigger="distraction", app="Chrome", minutes=10, user_id=user.id)
    
    log_entry = db_session.query(RoastLog).filter(RoastLog.user_id == user.id).first()
    assert log_entry is not None
    assert log_entry.user_id == user.id


def test_intent_router_handle_what_to_study(db_session, auth_headers):
    """Test IntentRouter._handle_what_to_study passes user_id without TypeError."""
    user = db_session.query(User).filter(User.id == 1).first()
    assert user is not None

    router = IntentRouter(user_id=user.id)
    # Should not raise any TypeError when invoking _handle_what_to_study
    router._handle_what_to_study()


def test_push_sync_endpoint(client, auth_headers, db_session):
    """Test POST /sync/push updates DailySummary with correct column names and user_id."""
    payload = {
        "date": date.today().isoformat(),
        "mobileProductiveMin": 30,
        "mobileDistractingMin": 15,
        "mobileNeutralMin": 5,
        "assignments": []
    }
    response = client.post("/sync/push", json=payload, headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    summary = db_session.query(DailySummary).filter(
        DailySummary.user_id == 1,
        DailySummary.date == date.today()
    ).first()
    assert summary is not None
    assert summary.productive_time_s == 30 * 60
    assert summary.distracted_time_s == 15 * 60
    assert summary.neutral_time_s == 5 * 60
    assert summary.user_id == 1


def test_pull_sync_endpoint(client, auth_headers, db_session):
    """Test GET /sync/pull accepts authenticated user and returns user assignments."""
    # Create test assignment for user
    assignment = Assignment(
        user_id=1,
        title="Sync Test Assignment",
        subject="Math",
        due_date=date.today(),
        priority="high",
        status="pending"
    )
    db_session.add(assignment)
    db_session.commit()

    response = client.get("/sync/pull", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "assignments" in data
    assert any(a["title"] == "Sync Test Assignment" for a in data["assignments"])
