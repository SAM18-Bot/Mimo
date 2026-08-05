def _register(client, email, role="student"):
    r = client.post("/auth/register", json={
        "email": email,
        "password": "strongpass123",
        "role": role,
        "display_name": email.split("@")[0],
    })
    assert r.status_code == 201
    return r.json()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_register_login_and_me(client):
    created = _register(client, "student@example.com")
    login = client.post("/auth/login", json={
        "email": "student@example.com",
        "password": "strongpass123",
    })

    assert login.status_code == 200
    me = client.get("/auth/me", headers=_auth(created["access_token"]))
    assert me.status_code == 200
    assert me.json()["email"] == "student@example.com"


def test_duplicate_registration_rejected(client):
    _register(client, "dup@example.com")
    r = client.post("/auth/register", json={
        "email": "dup@example.com",
        "password": "strongpass123",
        "role": "student",
    })
    assert r.status_code == 422


def test_device_registration_and_heartbeat(client):
    user = _register(client, "device@example.com")
    headers = _auth(user["access_token"])

    created = client.post("/devices/register", json={
        "device_name": "SAM Android",
        "device_type": "android",
        "platform": "Android 14",
    }, headers=headers)
    assert created.status_code == 201
    device_id = created.json()["id"]

    listed = client.get("/devices", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["device_name"] == "SAM Android"

    hb = client.post(f"/devices/{device_id}/heartbeat", headers=headers)
    assert hb.status_code == 200
    assert hb.json()["last_seen_at"] is not None


def test_device_access_is_owner_only(client):
    owner = _register(client, "owner@example.com")
    other = _register(client, "other@example.com")
    created = client.post("/devices/register", json={
        "device_name": "Desktop",
        "device_type": "desktop",
    }, headers=_auth(owner["access_token"]))
    device_id = created.json()["id"]

    r = client.post(f"/devices/{device_id}/heartbeat", headers=_auth(other["access_token"]))
    assert r.status_code == 404


def test_student_creates_parent_invite_and_parent_links(client):
    student = _register(client, "child@example.com", "student")
    parent = _register(client, "parent@example.com", "parent")

    invite = client.post("/parent/invites", headers=_auth(student["access_token"]))
    assert invite.status_code == 201
    assert len(invite.json()["code"]) == 6

    linked = client.post("/parent/link", json={
        "code": invite.json()["code"],
    }, headers=_auth(parent["access_token"]))
    assert linked.status_code == 200
    assert linked.json()["student_id"] == student["user"]["id"]

    children = client.get("/parent/children", headers=_auth(parent["access_token"]))
    assert children.status_code == 200
    assert children.json()[0]["email"] == "child@example.com"


def test_parent_summary_requires_link(client):
    student = _register(client, "private-child@example.com", "student")
    parent = _register(client, "blocked-parent@example.com", "parent")

    r = client.get(
        f"/parent/summary/{student['user']['id']}",
        headers=_auth(parent["access_token"]),
    )
    assert r.status_code == 403


def test_parent_summary_allowed_after_link(client):
    student = _register(client, "linked-child@example.com", "student")
    parent = _register(client, "linked-parent@example.com", "parent")
    invite = client.post("/parent/invites", headers=_auth(student["access_token"])).json()
    client.post("/parent/link", json={"code": invite["code"]}, headers=_auth(parent["access_token"]))

    r = client.get(
        f"/parent/summary/{student['user']['id']}",
        headers=_auth(parent["access_token"]),
    )
    assert r.status_code == 200
    assert r.json()["student_id"] == student["user"]["id"]
