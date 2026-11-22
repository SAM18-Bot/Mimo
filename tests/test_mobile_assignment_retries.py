from datetime import date, timedelta
from uuid import uuid4

from db.models import Assignment, Reminder, User
from modules.auth.security import create_access_token


def test_retried_assignment_preserves_completion_and_reminders(client, auth_headers, db_session):
    deadline = date.today() + timedelta(days=3)
    payload = {"request_id": str(uuid4()), "title": "Paper", "due_date": str(deadline), "due_time": "5pm"}
    first = client.post("/assignments", headers=auth_headers, json=payload)
    assert first.status_code == 201
    assignment_id = first.json()["id"]
    count = db_session.query(Reminder).filter_by(assignment_id=assignment_id).count()
    assert count > 0
    assert client.post(f"/assignments/{assignment_id}/done", headers=auth_headers).status_code == 200
    retry = client.post("/assignments/", headers=auth_headers, json=payload)
    assert retry.status_code == 201
    assert retry.json() == {**first.json(), "status": "done"}
    assert db_session.query(Reminder).filter_by(assignment_id=assignment_id).count() == count

    other = User(email="other-mobile-sync@example.com")
    db_session.add(other)
    db_session.commit()
    other_headers = {"Authorization": f"Bearer {create_access_token(other.id, 'student')}"}
    own = client.post("/assignments", headers=other_headers, json=payload)
    assert own.status_code == 201 and own.json()["id"] != assignment_id
    assert db_session.query(Assignment).count() == 2


def test_mobile_usage_preserves_app_and_device_in_breakdown(client, auth_headers):
    body = {"date": date.today().isoformat(), "mobileProductiveMin": 2, "mobileNeutralMin": 0,
            "mobileDistractingMin": 0, "sync_id": str(uuid4()), "app_name": "Docs"}
    assert client.post("/sync/push", headers=auth_headers, json=body).status_code == 200
    result = client.get("/screen/breakdown", headers=auth_headers).json()
    assert result["top_productive"] == [{"app": "Docs", "minutes": 2}]
    assert result["device_minutes"] == {"android": 2}
