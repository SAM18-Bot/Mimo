"""
Empirical verification test suite for Challenger M1-2:
1. Exhaustive route authentication checks for /settings/*, /monitoring/*, /voice/*, /sync/*.
2. Unauthenticated (no header), malformed header, invalid JWT, expired JWT, revoked JWT, non-existent user token checks -> all return 401.
3. Authenticated requests with valid tokens succeed across all endpoints.
4. Multi-tenant data isolation and tenancy bound operations across /sync/*, /voice/*, /settings/*, /monitoring/*.
5. Edge case and error handling tests.
"""

from datetime import date, timedelta

import pytest

from db.models import Assignment, DailySummary, User

# ── Fixtures & Helpers ──────────────────────────────────────────────────

@pytest.fixture
def test_users(db_session):
    """Create two distinct users in the database."""
    from modules.auth.security import create_access_token, hash_password

    u1 = User(
        email="alice@mimo.test",
        password_hash=hash_password("password123"),
        role="student",
        display_name="Alice Student"
    )
    u2 = User(
        email="bob@mimo.test",
        password_hash=hash_password("password456"),
        role="student",
        display_name="Bob Student"
    )
    db_session.add_all([u1, u2])
    db_session.commit()
    db_session.refresh(u1)
    db_session.refresh(u2)

    token1 = create_access_token(user_id=u1.id, role="student")
    token2 = create_access_token(user_id=u2.id, role="student")

    return {
        "u1": u1,
        "u2": u2,
        "token1": token1,
        "token2": token2,
        "headers1": {"Authorization": f"Bearer {token1}"},
        "headers2": {"Authorization": f"Bearer {token2}"},
    }


# ── 1. Unauthenticated Request Verification (401) ───────────────────────

TARGET_ENDPOINTS = [
    # Settings endpoints
    ("GET", "/settings/data", None),
    ("POST", "/settings/save", {"key": "EOD_REPORT_HOUR", "value": "22"}),
    ("POST", "/settings/save-all", {"settings": {"EOD_REPORT_HOUR": "22"}}),
    ("POST", "/settings/restart", None),

    # Monitoring endpoints
    ("POST", "/monitoring/pause", None),
    ("POST", "/monitoring/resume", None),
    ("GET", "/monitoring/status", None),

    # Voice endpoints
    ("POST", "/voice/command", {"text": "show my tasks"}),
    ("POST", "/voice/speak", {"text": "hello world"}),
    ("GET", "/voice/status", None),
    ("GET", "/voice/intents", None),

    # Sync endpoints
    ("POST", "/sync/push", {
        "date": "2026-08-20",
        "mobileProductiveMin": 10,
        "mobileDistractingMin": 0,
        "mobileNeutralMin": 0,
        "assignments": []
    }),
    ("GET", "/sync/pull", None),
]


@pytest.mark.parametrize("method,endpoint,payload", TARGET_ENDPOINTS)
def test_endpoints_reject_unauthenticated_requests(client, method, endpoint, payload):
    """Verify all targeted endpoints strictly return 401 when no token is supplied."""
    if method == "GET":
        res = client.get(endpoint)
    elif method == "POST":
        res = client.post(endpoint, json=payload or {})
    else:
        pytest.fail(f"Unsupported HTTP method: {method}")

    assert res.status_code == 401, f"{method} {endpoint} returned {res.status_code}, expected 401"
    assert "Missing bearer token" in res.json().get("detail", "")


# ── 2. Malformed & Invalid Authorization Header Verification (401) ──────

MALFORMED_HEADERS = [
    {"Authorization": ""},
    {"Authorization": "Bearer"},
    {"Authorization": "Bearer   "},
    {"Authorization": "Basic dXNlcjpwYXNz"},
    {"Authorization": "Token 12345"},
    {"Authorization": "Bearer invalid.garbage.token"},
    {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.signature"},
]


@pytest.mark.parametrize("headers", MALFORMED_HEADERS)
def test_malformed_headers_return_401(client, headers):
    """Verify malformed auth headers are rejected with 401 on /settings/data, /monitoring/status, /voice/status, /sync/pull."""
    for endpoint in ["/settings/data", "/monitoring/status", "/voice/status", "/sync/pull"]:
        res = client.get(endpoint, headers=headers)
        assert res.status_code == 401, f"Expected 401 for header {headers} on {endpoint}, got {res.status_code}"


def test_expired_token_returns_401(client):
    """Verify expired JWT token returns 401."""
    from modules.auth.security import create_access_token
    # Generate token expired 1 hour ago
    expired_token = create_access_token(user_id=1, role="student", expires_minutes=-60)
    res = client.get("/sync/pull", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401
    assert "Invalid token" in res.json().get("detail", "")


def test_nonexistent_user_token_returns_401(client):
    """Verify token signed with valid secret but non-existent user_id returns 401."""
    from modules.auth.security import create_access_token
    ghost_token = create_access_token(user_id=999999, role="student")
    res = client.get("/monitoring/status", headers={"Authorization": f"Bearer {ghost_token}"})
    assert res.status_code == 401
    assert "Invalid token" in res.json().get("detail", "")


def test_revoked_token_returns_401(client, test_users):
    """Verify token in TokenBlocklist is rejected with 401 Token revoked."""
    test_users["token1"]
    headers = test_users["headers1"]

    # Verify token works first
    r1 = client.get("/voice/status", headers=headers)
    assert r1.status_code == 200

    # Revoke token via /auth/logout
    r_logout = client.post("/auth/logout", headers=headers)
    assert r_logout.status_code == 200

    # Subsequent request using the same token must be rejected with 401
    r2 = client.get("/voice/status", headers=headers)
    assert r2.status_code == 401
    assert "Token revoked" in r2.json().get("detail", "")


# ── 3. Valid Token Access Verification across All Routes ────────────────

def test_settings_routes_with_valid_token(client, test_users):
    """Verify /settings/* routes with valid auth token."""
    headers = test_users["headers1"]

    # /settings/data
    r_data = client.get("/settings/data", headers=headers)
    assert r_data.status_code == 200
    assert "sections" in r_data.json()

    # /settings/save
    r_save = client.post("/settings/save", json={"key": "EOD_REPORT_HOUR", "value": "21"}, headers=headers)
    assert r_save.status_code == 200
    assert r_save.json().get("ok") is True

    # /settings/save invalid key
    r_save_inv = client.post("/settings/save", json={"key": "NON_EXISTENT_KEY", "value": "xyz"}, headers=headers)
    assert r_save_inv.status_code == 400

    # /settings/save-all
    r_saveall = client.post("/settings/save-all", json={"settings": {"EOD_REPORT_HOUR": "22"}}, headers=headers)
    assert r_saveall.status_code == 200
    assert r_saveall.json().get("ok") is True

    # /settings/restart
    r_restart = client.post("/settings/restart", headers=headers)
    assert r_restart.status_code == 200
    assert r_restart.json().get("ok") is True


def test_monitoring_routes_with_valid_token(client, test_users):
    """Verify /monitoring/* routes with valid auth token."""
    headers = test_users["headers1"]

    # /monitoring/status
    r_status = client.get("/monitoring/status", headers=headers)
    assert r_status.status_code == 200
    assert "paused" in r_status.json()

    # /monitoring/pause
    r_pause = client.post("/monitoring/pause", headers=headers)
    assert r_pause.status_code == 200
    assert r_pause.json() == {"ok": True, "status": "paused"}

    # /monitoring/resume
    r_resume = client.post("/monitoring/resume", headers=headers)
    assert r_resume.status_code == 200
    assert r_resume.json() == {"ok": True, "status": "active"}


def test_voice_routes_with_valid_token(client, test_users):
    """Verify /voice/* routes with valid auth token."""
    headers = test_users["headers1"]

    # /voice/status
    r_status = client.get("/voice/status", headers=headers)
    assert r_status.status_code == 200
    assert r_status.json()["hotword"] == "hey coach"

    # /voice/intents
    r_intents = client.get("/voice/intents", headers=headers)
    assert r_intents.status_code == 200
    assert len(r_intents.json()["intents"]) >= 5

    # /voice/speak
    r_speak = client.post("/voice/speak", json={"text": "Good morning!"}, headers=headers)
    assert r_speak.status_code == 200
    assert r_speak.json()["ok"] is True

    # /voice/command
    r_cmd = client.post("/voice/command", json={"text": "show my tasks", "speak_response": False}, headers=headers)
    assert r_cmd.status_code == 200
    assert r_cmd.json()["ok"] is True


def test_sync_routes_with_valid_token(client, test_users, db_session):
    """Verify /sync/* push and pull with valid auth token."""
    u1 = test_users["u1"]
    headers = test_users["headers1"]

    # 1. Push sync
    push_payload = {
        "date": "2026-08-20",
        "mobileProductiveMin": 25,
        "mobileDistractingMin": 10,
        "mobileNeutralMin": 5,
        "assignments": []
    }
    r_push = client.post("/sync/push", json=push_payload, headers=headers)
    assert r_push.status_code == 200
    assert r_push.json() == {"status": "ok"}

    # Verify in DB
    summary = db_session.query(DailySummary).filter(
        DailySummary.user_id == u1.id,
        DailySummary.date == date(2026, 8, 20)
    ).first()
    assert summary is not None
    assert summary.productive_time_s == 25 * 60
    assert summary.distracted_time_s == 10 * 60
    assert summary.neutral_time_s == 5 * 60
    assert summary.desk_time_s == 40 * 60

    # 2. Pull sync
    r_pull = client.get("/sync/pull", headers=headers)
    assert r_pull.status_code == 200
    pull_data = r_pull.json()
    assert "mergedStats" in pull_data
    assert "assignments" in pull_data


# ── 4. Multi-Tenant Cross-User Isolation Verification ───────────────────

def test_sync_and_voice_multi_tenant_isolation(client, test_users, db_session):
    """Verify multi-tenant isolation across /sync/* and /voice/* endpoints."""
    u1 = test_users["u1"]
    u2 = test_users["u2"]
    h1 = test_users["headers1"]
    h2 = test_users["headers2"]

    # 1. User 1 creates an assignment via /assignments
    a1 = Assignment(
        user_id=u1.id,
        title="Alice Confidential Project",
        subject="Biology",
        due_date=date.today() + timedelta(days=2),
        priority="high",
        status="pending"
    )
    # User 2 creates an assignment
    a2 = Assignment(
        user_id=u2.id,
        title="Bob Top Secret Physics",
        subject="Physics",
        due_date=date.today() + timedelta(days=3),
        priority="high",
        status="pending"
    )
    db_session.add_all([a1, a2])
    db_session.commit()

    # User 1 pulls sync
    r1 = client.get("/sync/pull", headers=h1)
    assert r1.status_code == 200
    u1_tasks = [t["title"] for t in r1.json()["assignments"]]
    assert "Alice Confidential Project" in u1_tasks
    assert "Bob Top Secret Physics" not in u1_tasks

    # User 2 pulls sync
    r2 = client.get("/sync/pull", headers=h2)
    assert r2.status_code == 200
    u2_tasks = [t["title"] for t in r2.json()["assignments"]]
    assert "Bob Top Secret Physics" in u2_tasks
    assert "Alice Confidential Project" not in u2_tasks

    # 2. User 1 adds assignment via /voice/command
    r_voice = client.post("/voice/command", json={"text": "add history homework due next Friday", "speak_response": False}, headers=h1)
    assert r_voice.status_code == 200

    # Verify new assignment was bound to u1.id
    history_task = db_session.query(Assignment).filter(
        (Assignment.subject == "History") | (Assignment.title == "History")
    ).first()
    assert history_task is not None
    assert history_task.user_id == u1.id
    assert history_task.user_id != u2.id

    # 3. User 1 and User 2 push sync stats independently
    client.post("/sync/push", json={"date": "2026-08-20", "mobileProductiveMin": 50, "mobileDistractingMin": 0, "mobileNeutralMin": 0}, headers=h1)
    client.post("/sync/push", json={"date": "2026-08-20", "mobileProductiveMin": 12, "mobileDistractingMin": 0, "mobileNeutralMin": 0}, headers=h2)

    db_session.expire_all()
    s1 = db_session.query(DailySummary).filter(DailySummary.user_id == u1.id, DailySummary.date == date(2026, 8, 20)).first()
    s2 = db_session.query(DailySummary).filter(DailySummary.user_id == u2.id, DailySummary.date == date(2026, 8, 20)).first()

    assert s1.productive_time_s == 50 * 60
    assert s2.productive_time_s == 12 * 60


# ── 5. Edge Cases and Robust Error Handling ─────────────────────────────

def test_sync_push_edge_cases(client, test_users):
    """Verify push_sync handles unusual payloads cleanly."""
    headers = test_users["headers1"]

    # Zero values
    r_zero = client.post("/sync/push", json={
        "date": "2026-08-20",
        "mobileProductiveMin": 0,
        "mobileDistractingMin": 0,
        "mobileNeutralMin": 0,
        "assignments": []
    }, headers=headers)
    assert r_zero.status_code == 200

    # Future date
    r_future = client.post("/sync/push", json={
        "date": "2030-01-01",
        "mobileProductiveMin": 15,
        "mobileDistractingMin": 0,
        "mobileNeutralMin": 0,
    }, headers=headers)
    assert r_future.status_code == 200

    # Malformed JSON schema -> 422
    r_bad_schema = client.post("/sync/push", json={"invalid": "payload"}, headers=headers)
    assert r_bad_schema.status_code == 422


def test_voice_command_unrecognized_text(client, test_users):
    """Verify voice command handles gibberish or empty string gracefully without 500 crash."""
    headers = test_users["headers1"]

    r_gibberish = client.post("/voice/command", json={"text": "xyz abc 123 !@#$%", "speak_response": False}, headers=headers)
    assert r_gibberish.status_code == 200
    assert r_gibberish.json()["ok"] is True

    r_empty = client.post("/voice/command", json={"text": "", "speak_response": False}, headers=headers)
    assert r_empty.status_code == 200
    assert r_empty.json()["ok"] is True

