import json
import re
from pathlib import Path
from datetime import date, datetime, timedelta, timezone

import httpx
from alembic import command
from alembic.config import Config
from google import genai
from google.genai import Client as GeminiClient, types
from sqlalchemy import create_engine, text

from server import config
from server.db.models import DailySummary, Reminder, ScheduleProfile, User
from server.modules.ai_layer.client import _chat as gemini_chat
from server.modules.auth.security import create_access_token


def other_account(db):
    user = User(email="second-student@example.org")
    db.add(user)
    db.commit()
    return {"Authorization": f"Bearer {create_access_token(user.id, 'student')}"}


def test_deadline_reminders_and_command_history(client, auth_headers, db_session):
    db_session.add(ScheduleProfile(user_id=1, timezone="Asia/Kolkata", wake_time="07:00", sleep_time="23:00"))
    db_session.commit()
    parsed = client.post("/assignments/nlp", headers=auth_headers, json={"text": "History report due 20 June at 5pm"})
    assert parsed.status_code == 201
    assignment = parsed.json()
    assert assignment["title"].lower() == "history report"
    assert assignment["due_time"] == "17:00"
    deadline = date.today() + timedelta(days=3)
    payload = {"title": "Biology paper", "due_date": deadline.isoformat(), "due_time": "5pm"}
    assert client.post("/assignments", headers=auth_headers, json={**payload, "due_time": "24:10"}).status_code == 422
    saved = client.post("/assignments", headers=auth_headers, json=payload).json()
    reminder = db_session.query(Reminder).filter_by(assignment_id=saved["id"]).order_by(Reminder.remind_at.desc()).first()
    assert reminder.remind_at == datetime(deadline.year, deadline.month, deadline.day, 11, 30)
    assert "17:00" in reminder.message

    cmd = {"text": "mark biology paper done", "speak_response": False}
    chat = client.post("/voice/command", headers=auth_headers, json=cmd).json()
    assert "Marked 'Biology paper' as done" in chat["ai_response"]
    history = client.get("/voice/history", headers=auth_headers).json()["messages"]
    assert [(line["sender"], line["text"]) for line in history] == [("user", cmd["text"]), ("ai", chat["ai_response"])]
    assert client.get("/voice/history", headers=other_account(db_session)).json()["messages"] == []


def test_todo_timezone_updates_and_ownership(client, auth_headers, db_session):
    second = other_account(db_session)
    response = client.post("/todos", headers=auth_headers, json={"title": "Reading", "remind_at": "2027-04-05T18:30:00+05:30"})
    assert response.status_code == 201
    todo = response.json()
    assert datetime.fromisoformat(todo["remind_at"]) == datetime(2027, 4, 5, 13, tzinfo=timezone.utc)
    route = f"/todos/{todo['id']}"
    assert client.get("/todos", headers=second).json() == []
    assert client.patch(route, headers=second, json={"status": "done"}).status_code == 404
    assert client.delete(route, headers=second).status_code == 404
    updated = client.patch(route, headers=auth_headers, json={"remind_at": None, "status": "done"}).json()
    assert updated["remind_at"] is None and updated["status"] == "done"
    assert client.delete(route, headers=auth_headers).status_code == 204


def test_check_in_and_latest_historical_report(client, auth_headers, db_session):
    second = other_account(db_session)
    answer = {"question": "How did studying go?", "answer": "Finished my essay."}
    assert client.post("/reports/accountability", headers=auth_headers, json=answer).status_code == 201
    assert client.get("/reports/accountability/today", headers=auth_headers).json() == [answer]
    assert client.get("/reports/accountability/today", headers=second).json() == []
    report = {"summary": "You finished the essay."}
    yesterday = date.today() - timedelta(days=1)
    db_session.add_all([DailySummary(user_id=1, date=yesterday, ai_report_text=str(report)),
                        DailySummary(user_id=1, date=date.today())])
    db_session.commit()
    latest = client.get("/reports/eod/latest", headers=auth_headers).json()
    assert latest["report"] == report and latest["date"] == yesterday.isoformat()
    assert "report" not in client.get("/reports/eod/latest", headers=second).json()


def test_gemini_sdk_request_and_response(monkeypatch):
    received = []

    def send(request):
        received.append((request.url.path, json.loads(request.content)))
        return httpx.Response(200, request=request, json={
            "candidates": [{"content": {"role": "model", "parts": [{"text": "SDK reply"}]}}]
        })
    with httpx.Client(transport=httpx.MockTransport(send)) as http:
        monkeypatch.setattr(genai, "Client", lambda **kwargs: GeminiClient(
            **kwargs, http_options=types.HttpOptions(httpx_client=http)))
        assert gemini_chat("system instructions", "a question", json_mode=True, api_key="unit-test-only") == "SDK reply"
    path, body = received[0]
    assert path.endswith("/models/gemini-3.1-flash-lite:generateContent")
    assert body["contents"][0]["parts"][0]["text"] == "a question"
    assert body["generationConfig"]["responseMimeType"] == "application/json"


def test_migrate_legacy_keys_and_deadlines(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'legacy.db'}"
    monkeypatch.setattr(config, "DATABASE_URL", url)
    cfg = Config()
    cfg.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "server/db/migrations"))
    command.upgrade(cfg, "005")
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO users (id,email,ai_engine,api_key) VALUES (1,'first@example.org','openai','old-ciphertext'),(2,'second@example.org','gemini','gemini-ciphertext')"))
        conn.execute(text("INSERT INTO assignments (user_id,title,due_date,due_time) VALUES (1,'Essay','2027-01-02','5pm')"))
    command.upgrade(cfg, "head")
    command.upgrade(cfg, "head")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT ai_engine,api_key FROM users ORDER BY id")).all() == [
            ("legacy", "old-ciphertext"), ("gemini", "gemini-ciphertext")]
        assert conn.scalar(text("SELECT due_time FROM assignments")) == "17:00"
        assert conn.scalar(text("SELECT version_num FROM alembic_version")) == "007"
    engine.dispose()
    user = User(ai_engine="legacy", _api_key_encrypted="old-ciphertext")
    assert user.api_key is None


def test_personal_gemini_key_rotation(client, auth_headers, db_session, monkeypatch):
    from cryptography.fernet import Fernet
    monkeypatch.setattr(config, "SECRET_KEY", Fernet.generate_key().decode())
    second = other_account(db_session)
    path = "/auth/me/gemini-key"
    assert client.put(path, headers=auth_headers, json={"api_key": "test-key"}).status_code == 204
    user = db_session.get(User, 1)
    assert user.api_key == "test-key" and user._api_key_encrypted != "test-key"
    assert client.put(path, headers=second, json={"api_key": None}).status_code == 204
    db_session.refresh(user)
    assert user.api_key == "test-key"
    assert client.put(path, headers=auth_headers, json={"api_key": ""}).status_code == 204
    db_session.refresh(user)
    assert user.api_key is None


def test_android_client_routes_match_backend(client):
    def normalized(path):
        return re.sub(r"\{[^}]+\}", "{}", "/" + path.split("?")[0].strip("/"))

    routes = {(method.upper(), normalized(path))
              for path, methods in client.get("/openapi.json").json()["paths"].items()
              for method in methods}
    network = Path(__file__).resolve().parents[1] / "android/app/src/main/java/com/mimo/app/network"
    calls = {(method, normalized(path))
             for source in network.glob("*.kt")
             for method, path in re.findall(r'@(GET|POST|PUT|PATCH|DELETE)\("([^"]+)"\)', source.read_text())}
    assert calls
    assert calls <= routes, calls - routes
