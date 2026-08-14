"""
Adversarial Stress Test Suite for Milestone M2: Multi-Tenancy & Data Leak Fixes.
Author: Challenger M2_1
"""

import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

from db.models import User, Assignment, ScheduleProfile, ScheduleBlock
from modules.schedule.manager import (
    build_onboarding_schedule,
    get_weekly_schedule,
    update_block_status,
    boost_subject_priority,
    smart_suggestions,
)
from modules.auth.security import create_access_token
from api.websocket import ConnectionManager, manager
from modules.ai_layer.roast_engine import RoastEngine
from modules.assignments.reminder import ReminderLoop
from modules.cv_pipeline.presence import PresenceMonitor
from schedulers.daily_trigger import _push_live_stats


# ============================================================================
# 1. Update Block Status Security Tests
# ============================================================================

def test_update_block_status_cannot_modify_other_user_block(db_session):
    """Verify User B cannot modify User A's schedule block directly."""
    user_a = User(email="usera_block@test.com", password_hash="hash")
    user_b = User(email="userb_block@test.com", password_hash="hash")
    db_session.add_all([user_a, user_b])
    db_session.commit()

    build_onboarding_schedule(
        db_session, user_id=user_a.id, wake_time="07:00", sleep_time="23:00", study_goal_minutes=120
    )
    blocks_a = get_weekly_schedule(db_session, user_id=user_a.id)
    assert len(blocks_a) > 0
    block_a = blocks_a[0]
    original_status = block_a.status

    # User B attempts to change User A's block status
    res = update_block_status(db_session, block_id=block_a.id, status="done", user_id=user_b.id)
    assert res is None, "update_block_status must return None when User B tries to update User A's block"

    db_session.refresh(block_a)
    assert block_a.status == original_status, "Block A status must remain unchanged in DB"


def test_update_block_status_owner_can_modify(db_session):
    """Verify User A CAN modify their own schedule block."""
    user_a = User(email="usera_owner@test.com", password_hash="hash")
    db_session.add(user_a)
    db_session.commit()

    build_onboarding_schedule(
        db_session, user_id=user_a.id, wake_time="07:00", sleep_time="23:00", study_goal_minutes=120
    )
    blocks_a = get_weekly_schedule(db_session, user_id=user_a.id)
    block_a = blocks_a[0]

    res = update_block_status(db_session, block_id=block_a.id, status="done", user_id=user_a.id)
    assert res is not None
    assert res.status == "done"
    db_session.refresh(block_a)
    assert block_a.status == "done"


def test_update_block_status_invalid_status_raises(db_session):
    """Verify invalid status string raises ValueError."""
    user_a = User(email="usera_invalid@test.com", password_hash="hash")
    db_session.add(user_a)
    db_session.commit()

    build_onboarding_schedule(
        db_session, user_id=user_a.id, wake_time="07:00", sleep_time="23:00", study_goal_minutes=120
    )
    blocks_a = get_weekly_schedule(db_session, user_id=user_a.id)
    block_a = blocks_a[0]

    with pytest.raises(ValueError):
        update_block_status(db_session, block_id=block_a.id, status="HACKED_STATUS", user_id=user_a.id)


def test_update_block_status_api_cross_tenant_404(client, db_engine):
    """Verify PATCH /schedule/blocks/{id} returns 404 when User B targets User A's block."""
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=db_engine)
    session = Session()

    user_a = User(email="api_usera@test.com", password_hash="hash", role="student")
    user_b = User(email="api_userb@test.com", password_hash="hash", role="student")
    session.add_all([user_a, user_b])
    session.commit()

    profile_a = build_onboarding_schedule(
        session, user_id=user_a.id, wake_time="07:00", sleep_time="23:00", study_goal_minutes=60
    )
    blocks_a = get_weekly_schedule(session, user_id=user_a.id)
    block_a_id = blocks_a[0].id

    token_b = create_access_token(user_id=user_b.id, role="student")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User B calls API endpoint on User A's block ID
    response = client.patch(
        f"/schedule/blocks/{block_a_id}",
        json={"status": "done"},
        headers=headers_b,
    )
    assert response.status_code == 404, f"Expected 404 Not Found, got {response.status_code}: {response.text}"

    # Verify status in DB was unchanged
    session = Session()
    b = session.get(ScheduleBlock, block_a_id)
    assert b.status != "done"


# ============================================================================
# 2. Cross-Tenant Assignment Data Leakage Tests
# ============================================================================

def test_boost_subject_priority_no_cross_tenant_leak(db_session):
    """Verify boost_subject_priority does not leak User B's assignments to User A."""
    user_a = User(email="boost_usera@test.com", password_hash="hash")
    user_b = User(email="boost_userb@test.com", password_hash="hash")
    db_session.add_all([user_a, user_b])
    db_session.commit()

    build_onboarding_schedule(
        db_session, user_id=user_a.id, wake_time="07:00", sleep_time="23:00", study_goal_minutes=60
    )
    build_onboarding_schedule(
        db_session, user_id=user_b.id, wake_time="07:00", sleep_time="23:00", study_goal_minutes=60
    )

    # Urgent assignment for User B ONLY
    assignment_b = Assignment(
        user_id=user_b.id,
        title="User B Secret Nuclear Physics Essay",
        subject="Nuclear Physics",
        due_date=date.today() + timedelta(days=1),
        status="pending",
    )
    db_session.add(assignment_b)
    db_session.commit()

    # User A calls boost_subject_priority
    boosted_a = boost_subject_priority(db_session, user_id=user_a.id)
    assert len(boosted_a) == 0, "User A should get NO boosted blocks because User A has no assignments"
    assert not any("Nuclear Physics" in b.title for b in boosted_a)

    # User B calls boost_subject_priority
    boosted_b = boost_subject_priority(db_session, user_id=user_b.id)
    assert len(boosted_b) > 0, "User B SHOULD get boosted blocks for their own assignment"
    assert any("Nuclear Physics" in b.title for b in boosted_b)


def test_smart_suggestions_no_cross_tenant_leak(db_session):
    """Verify smart_suggestions does not expose User B's assignment titles or IDs to User A."""
    user_a = User(email="sugg_usera@test.com", password_hash="hash")
    user_b = User(email="sugg_userb@test.com", password_hash="hash")
    db_session.add_all([user_a, user_b])
    db_session.commit()

    build_onboarding_schedule(
        db_session, user_id=user_a.id, wake_time="07:00", sleep_time="23:00", study_goal_minutes=60
    )
    build_onboarding_schedule(
        db_session, user_id=user_b.id, wake_time="07:00", sleep_time="23:00", study_goal_minutes=60
    )

    assignment_b = Assignment(
        user_id=user_b.id,
        title="CONFIDENTIAL_USER_B_TASK",
        subject="TopSecretSubject",
        due_date=date.today() + timedelta(days=1),
        status="todo",
    )
    db_session.add(assignment_b)
    db_session.commit()

    # User A gets suggestions
    suggs_a = smart_suggestions(db_session, user_id=user_a.id)
    for s in suggs_a:
        assert s.get("assignment_id") != assignment_b.id, "User B assignment_id leaked to User A!"
        if "message" in s:
            assert "CONFIDENTIAL_USER_B_TASK" not in s["message"]
            assert "TopSecretSubject" not in s["message"]


def test_smart_suggestions_api_no_cross_tenant_leak(client, db_engine):
    """Verify GET /schedule/smart-suggestions API route isolates suggestions per user."""
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=db_engine)
    session = Session()

    user_a = User(email="sugg_api_a@test.com", password_hash="hash", role="student")
    user_b = User(email="sugg_api_b@test.com", password_hash="hash", role="student")
    session.add_all([user_a, user_b])
    session.commit()

    build_onboarding_schedule(
        session, user_id=user_a.id, wake_time="07:00", sleep_time="23:00", study_goal_minutes=60
    )
    build_onboarding_schedule(
        session, user_id=user_b.id, wake_time="07:00", sleep_time="23:00", study_goal_minutes=60
    )

    assignment_b = Assignment(
        user_id=user_b.id,
        title="USER_B_API_EXCLUSIVE_TASK",
        subject="ExclusiveSubjectB",
        due_date=date.today() + timedelta(days=1),
        status="todo",
    )
    session.add(assignment_b)
    session.commit()

    token_a = create_access_token(user_id=user_a.id, role="student")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    res_a = client.get("/schedule/smart-suggestions", headers=headers_a)
    assert res_a.status_code == 200
    suggestions = res_a.json().get("suggestions", [])
    for s in suggestions:
        assert s.get("assignment_id") != assignment_b.id
        msg = s.get("message", "")
        assert "USER_B_API_EXCLUSIVE_TASK" not in msg
        assert "ExclusiveSubjectB" not in msg


def test_roast_engine_get_context_user_isolation(db_session):
    """Verify RoastEngine._get_context filters assignments strictly by user_id."""
    u1 = User(email="roast_ctx_u1@test.com", password_hash="hash")
    u2 = User(email="roast_ctx_u2@test.com", password_hash="hash")
    db_session.add_all([u1, u2])
    db_session.commit()

    a1 = Assignment(user_id=u1.id, title="User 1 History Homework", due_date=date.today() + timedelta(days=1), status="todo")
    a2 = Assignment(user_id=u2.id, title="User 2 Secret Calculus Exam", due_date=date.today() + timedelta(days=1), status="todo")
    db_session.add_all([a1, a2])
    db_session.commit()

    engine = RoastEngine()
    ctx1 = engine._get_context(user_id=u1.id)
    assert "User 1 History Homework" in ctx1["pending_assignments"]
    assert "User 2 Secret Calculus Exam" not in ctx1["pending_assignments"]

    ctx2 = engine._get_context(user_id=u2.id)
    assert "User 2 Secret Calculus Exam" in ctx2["pending_assignments"]
    assert "User 1 History Homework" not in ctx2["pending_assignments"]


# ============================================================================
# 3. WebSocket Message Routing & Isolation Tests
# ============================================================================

@pytest.mark.anyio
async def test_websocket_unicast_isolation():
    """Verify unicast and targeted broadcast only deliver to the target user's WebSocket."""
    cm = ConnectionManager()
    ws_user_a = AsyncMock()
    ws_user_b = AsyncMock()

    await cm.connect(ws_user_a, user_id=10)
    await cm.connect(ws_user_b, user_id=20)

    # 1. Direct unicast to User A (10)
    await cm.unicast(10, {"type": "private_a", "data": "secret_a"})
    ws_user_a.send_text.assert_called_once()
    ws_user_b.send_text.assert_not_called()

    ws_user_a.send_text.reset_mock()
    ws_user_b.send_text.reset_mock()

    # 2. Targeted broadcast with user_id in dict
    await cm.broadcast({"type": "roast", "user_id": 20, "message": "Get back to work User B"})
    ws_user_b.send_text.assert_called_once()
    ws_user_a.send_text.assert_not_called()

    ws_user_a.send_text.reset_mock()
    ws_user_b.send_text.reset_mock()

    # 3. Targeted broadcast with user_id argument
    await cm.broadcast({"type": "stats_update", "data": 123}, user_id=10)
    ws_user_a.send_text.assert_called_once()
    ws_user_b.send_text.assert_not_called()


def test_roast_engine_broadcast_includes_user_id():
    """Verify RoastEngine includes user_id in WebSocket broadcast payloads."""
    broadcast_mock = MagicMock()
    engine = RoastEngine(broadcast_fn=broadcast_mock)

    # Trigger roast for user_id=42
    engine._fire_roast(trigger="distraction", app="YouTube", minutes=15, user_id=42)

    broadcast_mock.assert_called_once()
    payload = broadcast_mock.call_args[0][0]
    assert isinstance(payload, dict)
    assert payload.get("user_id") == 42, f"Payload must contain user_id=42, got {payload}"
    assert payload.get("type") == "roast"


def test_reminder_loop_broadcast_includes_user_id():
    """Verify ReminderLoop includes user_id in broadcast payloads."""
    broadcast_mock = MagicMock()
    loop = ReminderLoop(broadcast_fn=broadcast_mock)

    loop._deliver("Test Reminder Message", assignment_id=99, user_id=77)

    broadcast_mock.assert_called_once()
    payload = broadcast_mock.call_args[0][0]
    assert isinstance(payload, dict)
    assert payload.get("user_id") == 77, f"Payload must contain user_id=77, got {payload}"
    assert payload.get("type") == "reminder"


def test_presence_monitor_broadcast_includes_user_id():
    """Verify PresenceMonitor includes user_id in broadcast payloads."""
    broadcast_mock = MagicMock()
    pm = PresenceMonitor(broadcast_fn=broadcast_mock, user_id=88)

    pm._transition("distracted")

    broadcast_mock.assert_called_once()
    payload = broadcast_mock.call_args[0][0]
    assert isinstance(payload, dict)
    assert payload.get("user_id") == 88, f"Payload must contain user_id=88, got {payload}"
    assert payload.get("type") == "cv_event"


def test_daily_trigger_stats_push_includes_user_id(db_session):
    """Verify _push_live_stats attaches user_id to every broadcasted stats_update."""
    broadcast_mock = MagicMock()

    u1 = User(email="stats_u1@test.com", password_hash="hash")
    u2 = User(email="stats_u2@test.com", password_hash="hash")
    db_session.add_all([u1, u2])
    db_session.commit()

    _push_live_stats(broadcast_fn=broadcast_mock)

    assert broadcast_mock.call_count >= 2
    emitted_user_ids = {call[0][0].get("user_id") for call in broadcast_mock.call_args_list}
    assert u1.id in emitted_user_ids
    assert u2.id in emitted_user_ids


def test_websocket_connect_user_isolation(client, db_engine):
    """Verify WebSocket endpoint /ws receives initial messages scoped ONLY to connected user."""
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=db_engine)
    session = Session()

    u1 = User(email="ws_u1@test.com", password_hash="hash", role="student")
    u2 = User(email="ws_u2@test.com", password_hash="hash", role="student")
    session.add_all([u1, u2])
    session.commit()

    a1 = Assignment(user_id=u1.id, title="U1 Task Unique", due_date=date.today() + timedelta(days=2), status="todo")
    a2 = Assignment(user_id=u2.id, title="U2 Task Unique", due_date=date.today() + timedelta(days=2), status="todo")
    session.add_all([a1, a2])
    session.commit()

    token1 = create_access_token(user_id=u1.id, role="student")

    with client.websocket_connect(f"/ws?token={token1}") as ws1:
        # First received message: stats_update for user 1
        msg1 = ws1.receive_json()
        assert msg1["type"] == "stats_update"

        # Second received message: tasks_list for user 1
        msg2 = ws1.receive_json()
        assert msg2["type"] == "tasks_list"
        task_titles = [t["title"] for t in msg2["tasks"]]
        assert "U1 Task Unique" in task_titles
        assert "U2 Task Unique" not in task_titles, "User 2's task leaked to User 1's WebSocket connection!"
