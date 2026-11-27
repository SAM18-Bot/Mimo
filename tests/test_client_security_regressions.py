from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from starlette.websockets import WebSocketDisconnect

from server.db.models import ScheduleBlock, ScheduleProfile, User
from server.modules.auth.security import create_access_token


def test_cloud_accounts_cannot_use_server_controls(client, auth_headers):
    for path in ("/settings/data", "/monitoring/status"):
        assert client.get(path, headers=auth_headers).status_code == 403
    assert client.post("/settings/restart", headers=auth_headers).status_code == 403


def test_mobile_sync_is_idempotent_and_visible_in_reports(client, auth_headers):
    today = date.today().isoformat()
    payload = {
        "date": today,
        "mobileProductiveMin": 3,
        "mobileDistractingMin": 2,
        "mobileNeutralMin": 1,
        "sync_id": "mimo-test-batch",
    }
    first = client.post("/sync/push", json=payload, headers=auth_headers)
    assert first.status_code == 200 and not first.json()["duplicate"]
    repeated = client.post("/sync/push", json=payload, headers=auth_headers)
    assert repeated.status_code == 200 and repeated.json()["duplicate"]
    for path, key in (("/sync/pull", "mergedStats"), ("/reports/stats", None)):
        response = client.get(path, headers=auth_headers)
        assert response.status_code == 200
        stats = response.json()[key] if key else response.json()
        assert (stats["productive_min"], stats["distracting_min"], stats["neutral_min"]) == (3, 2, 1)
    assert client.post("/sync/push", json=payload | {"date": "invalid"}, headers=auth_headers).status_code == 422
    assert client.post("/sync/push", json=payload | {"mobileProductiveMin": -1}, headers=auth_headers).status_code == 422


def test_invalid_desktop_session_is_a_validation_error(client, auth_headers):
    payload = {
        "app_name": "Editor", "window_title": "Project", "category": "productive",
        "started_at": "invalid", "session_date": date.today().isoformat(), "duration_s": 60,
    }
    assert client.post("/screen/session", json=payload, headers=auth_headers).status_code == 422


def test_assignment_and_live_stats_are_private_to_the_account(client, auth_headers, db_session):
    other = User(email="other-security-test@example.com")
    db_session.add(other)
    db_session.commit()
    other_headers = {"Authorization": f"Bearer {create_access_token(other.id, 'student')}"}
    first_token = auth_headers["Authorization"].split()[1]
    with client.websocket_connect("/ws", subprotocols=["mimo.auth", first_token]) as first:
        assert first.accepted_subprotocol == "mimo.auth"
        assert first.receive_json()["type"] == "stats_update"
        assert first.receive_json()["type"] == "tasks_list"
        assignment = client.post("/assignments", headers=auth_headers, json={
            "title": "Private assignment",
            "due_date": (date.today() + timedelta(days=1)).isoformat(),
        })
        assert assignment.status_code == 201
        assert first.receive_json()["type"] == "assignment_added"

    with client.websocket_connect("/ws", headers=other_headers) as second:
        assert second.receive_json()["stats"]["upcoming_list"] == []
        assert second.receive_json()["tasks"] == []
        assert client.post("/auth/logout", headers=other_headers).status_code == 200
        with pytest.raises(WebSocketDisconnect) as disconnected:
            second.receive_json()
        assert disconnected.value.code == 1008


def test_google_sign_in_requires_configuration_and_never_auto_links(
    client, auth_headers, monkeypatch,
):
    from server import config
    from server.modules.auth import manager

    monkeypatch.setattr(config, "GOOGLE_CLIENT_ID", "")
    assert client.post("/auth/google", json={"token": "unused"}).status_code == 401

    account = client.get("/auth/me", headers=auth_headers).json()
    monkeypatch.setattr(config, "GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setattr(manager.id_token, "verify_oauth2_token", lambda *_: {
        "email": account["email"], "email_verified": True, "sub": "new-google-subject",
    })
    assert client.post("/auth/google", json={"token": "unused"}).status_code == 401


def test_logout_does_not_revoke_a_separate_session(client, auth_headers):
    user_id = client.get("/auth/me", headers=auth_headers).json()["id"]
    separate = {"Authorization": f"Bearer {create_access_token(user_id, 'student')}"}
    assert client.post("/auth/logout", headers=auth_headers).status_code == 200
    assert client.get("/auth/me", headers=separate).status_code == 200


def test_desktop_enforcement_only_uses_the_active_planned_schedule(client, auth_headers, db_session):
    user_id = client.get("/auth/me", headers=auth_headers).json()["id"]
    timezone = "Asia/Kolkata"
    now = datetime.now(ZoneInfo(timezone))
    inactive = ScheduleProfile(user_id=user_id, active=False, wake_time="07:00", sleep_time="23:00")
    active = ScheduleProfile(user_id=user_id, active=True, wake_time="07:00", sleep_time="23:00", timezone=timezone)
    db_session.add_all([inactive, active])
    db_session.flush()
    for profile, status in ((inactive, "planned"), (active, "done")):
        db_session.add(ScheduleBlock(
            profile_id=profile.id, day_of_week=now.weekday(), title="Study",
            kind="study", start_time="00:00", end_time="23:59", status=status,
        ))
    db_session.commit()
    assert not client.get("/schedule/study-blocks/active", headers=auth_headers).json()["active"]
