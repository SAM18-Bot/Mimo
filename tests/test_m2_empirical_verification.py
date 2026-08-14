"""
Empirical Verification Test Suite for Milestone M2.
Tests ConnectionManager unicast, user socket mapping under multi-user concurrent connections,
fault tolerance, and multi-tenant schedule data leak isolation.
"""

import asyncio
import random
from unittest.mock import AsyncMock, MagicMock
import pytest
from datetime import date, timedelta

from api.websocket import ConnectionManager, drain_event_bus, event_bus
from db.models import User, Assignment, ScheduleProfile, ScheduleBlock
from modules.schedule.manager import (
    build_onboarding_schedule,
    boost_subject_priority,
    smart_suggestions,
    update_block_status,
)


@pytest.mark.anyio
async def test_empirical_multi_user_concurrent_unicast():
    """
    Stress test ConnectionManager under multi-user concurrent connections.
    - 50 distinct users, 4 sockets each (200 total active sockets).
    - 1,000 concurrent unicast messages sent across users in parallel.
    - Asserts 100% strict isolation (zero cross-tenant leaks).
    """
    cm = ConnectionManager()
    num_users = 50
    sockets_per_user = 4
    total_messages = 1000

    # User -> list of AsyncMock sockets
    user_sockets_map = {}
    socket_to_user_map = {}

    for uid in range(1, num_users + 1):
        user_sockets_map[uid] = []
        for s_idx in range(sockets_per_user):
            ws = AsyncMock()
            ws.send_text = AsyncMock()
            user_sockets_map[uid].append(ws)
            socket_to_user_map[ws] = uid
            await cm.connect(ws, user_id=uid)

    assert cm.client_count == num_users * sockets_per_user

    # Verify socket mapping structures
    for uid in range(1, num_users + 1):
        assert len(cm._user_sockets[uid]) == sockets_per_user
        for ws in user_sockets_map[uid]:
            assert cm._socket_users[ws] == uid

    # Track message delivery counts per socket
    received_by_socket = {ws: [] for ws in socket_to_user_map.keys()}

    async def send_random_unicast(msg_id: int):
        target_uid = random.randint(1, num_users)
        payload = {"type": "test_msg", "msg_id": msg_id, "user_id": target_uid}
        await cm.unicast(target_uid, payload)

    # Fire 1000 concurrent unicast calls
    await asyncio.gather(*(send_random_unicast(i) for i in range(total_messages)))

    # Audit all sockets for strict target isolation
    for uid, sockets in user_sockets_map.items():
        for ws in sockets:
            for call in ws.send_text.call_args_list:
                args, _ = call
                import json
                msg_dict = json.loads(args[0])
                assert msg_dict["user_id"] == uid, f"LEAK DETECTED! Socket for user {uid} received message intended for user {msg_dict['user_id']}"

    # Verify teardown / disconnect cleanup
    for uid in range(1, num_users + 1):
        for ws in list(user_sockets_map[uid]):
            cm.disconnect(ws)

    assert cm.client_count == 0
    assert len(cm._active) == 0
    assert len(cm._user_sockets) == 0
    assert len(cm._socket_users) == 0


@pytest.mark.anyio
async def test_empirical_dead_socket_concurrent_fault_tolerance():
    """
    Stress test fault tolerance when sockets fail during concurrent unicast/broadcast.
    """
    cm = ConnectionManager()
    num_users = 20
    good_sockets = {}
    bad_sockets = {}

    for uid in range(1, num_users + 1):
        ws_good = AsyncMock()
        ws_good.send_text = AsyncMock()
        ws_bad = AsyncMock()
        ws_bad.send_text = AsyncMock(side_effect=RuntimeError("Connection reset"))

        await cm.connect(ws_good, user_id=uid)
        await cm.connect(ws_bad, user_id=uid)

        good_sockets[uid] = ws_good
        bad_sockets[uid] = ws_bad

    assert cm.client_count == num_users * 2

    # Send unicast to each user (should encounter exception on bad socket and prune it safely)
    for uid in range(1, num_users + 1):
        await cm.unicast(uid, {"type": "ping", "user_id": uid})

    # Assert client count reduced to half (good sockets remaining)
    assert cm.client_count == num_users
    for uid in range(1, num_users + 1):
        assert bad_sockets[uid] not in cm._active
        assert bad_sockets[uid] not in cm._socket_users
        assert good_sockets[uid] in cm._user_sockets[uid]


def test_empirical_schedule_manager_multi_tenant_isolation(db_session):
    """
    Empirically verify Schedule Manager multi-tenant data leak defenses:
    1. boost_subject_priority ignores other user's assignments.
    2. smart_suggestions ignores other user's assignments.
    3. update_block_status prevents cross-tenant modification.
    """
    db = db_session
    u1 = User(email="user1_m2@example.com", password_hash="pw")
    u2 = User(email="user2_m2@example.com", password_hash="pw")
    db.add_all([u1, u2])
    db.commit()

    p1 = build_onboarding_schedule(
        db, user_id=u1.id, wake_time="07:00", sleep_time="23:00",
        subjects=[{"name": "Math", "priority": "high"}]
    )
    p2 = build_onboarding_schedule(
        db, user_id=u2.id, wake_time="08:00", sleep_time="22:00",
        subjects=[{"name": "Secret History", "priority": "high"}]
    )

    # Add urgent assignment for User 2
    today = date.today()
    a2 = Assignment(
        user_id=u2.id,
        title="User 2 Secret Assignment",
        subject="Secret History",
        due_date=today + timedelta(days=1),
        status="pending",
    )
    db.add(a2)
    db.commit()

    # User 1 runs boost_subject_priority
    boosted_u1 = boost_subject_priority(db, user_id=u1.id, target_date=today)
    # User 1 should NOT get boost for User 2's "Secret History"
    for b in boosted_u1:
        assert b.subject != "Secret History"
        assert "Secret" not in b.title

    # User 1 gets smart suggestions
    sug_u1 = smart_suggestions(db, user_id=u1.id, target_date=today)
    sug_str = str(sug_u1)
    assert "Secret History" not in sug_str
    assert "User 2 Secret Assignment" not in sug_str

    # Attempt cross-tenant update_block_status
    u2_blocks = db.query(ScheduleBlock).filter(ScheduleBlock.profile_id == p2.id).all()
    target_block = u2_blocks[0]
    orig_status = target_block.status

    # User 1 attempts to update User 2's block status
    res = update_block_status(db, block_id=target_block.id, status="done", user_id=u1.id)
    assert res is None, "Cross-tenant block status update must be rejected!"
    db.refresh(target_block)
    assert target_block.status == orig_status, "Target block status must remain unchanged!"
