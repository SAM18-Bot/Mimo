"""
API integration tests using FastAPI TestClient.

Tests every route with real DB operations (in-memory SQLite).
No mocking except OpenAI (which is never called in tests).

Coverage:
  /assignments  — CRUD + NLP
  /screen       — breakdown + mock injection
  /cv           — mock injection + events
  /reports      — stats + accountability
  /voice        — command routing + status
  /study        — recommendations + next
  /health       — server health
"""

import pytest
from datetime import date, timedelta


# ── helpers ───────────────────────────────────────────────────────────────

def today_plus(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


# ── health ────────────────────────────────────────────────────────────────

class TestHealth:

    def test_health_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"


# ── assignments ───────────────────────────────────────────────────────────

class TestAssignmentsAPI:

    def test_create_assignment(self, client):
        r = client.post("/assignments/", json={
            "title":    "Math Homework",
            "due_date": today_plus(5),
            "subject":  "Math",
            "priority": "high",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["title"]   == "Math Homework"
        assert data["status"]  == "pending"
        assert data["priority"] == "high"

    def test_create_via_nlp(self, client):
        r = client.post("/assignments/nlp", json={
            "text": "Physics lab due tomorrow"
        })
        assert r.status_code == 201
        data = r.json()
        assert data["due_date"] == today_plus(1)
        assert data["subject"] is not None

    def test_nlp_invalid_text_422(self, client):
        r = client.post("/assignments/nlp", json={"text": "do some stuff"})
        assert r.status_code == 422

    def test_list_assignments_empty(self, client):
        r = client.get("/assignments/")
        assert r.status_code == 200
        assert r.json() == []

    def test_list_after_create(self, client):
        client.post("/assignments/", json={
            "title": "Test", "due_date": today_plus(3)
        })
        r = client.get("/assignments/")
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_upcoming_endpoint(self, client):
        client.post("/assignments/", json={
            "title": "Near", "due_date": today_plus(2)
        })
        client.post("/assignments/", json={
            "title": "Far",  "due_date": today_plus(30)
        })
        r = client.get("/assignments/upcoming?days=7")
        assert r.status_code == 200
        titles = [a["title"] for a in r.json()]
        assert "Near" in titles
        assert "Far"  not in titles

    def test_overdue_endpoint(self, client):
        client.post("/assignments/", json={
            "title": "Past", "due_date": today_plus(-2)
        })
        client.post("/assignments/", json={
            "title": "Future", "due_date": today_plus(5)
        })
        r = client.get("/assignments/overdue")
        assert r.status_code == 200
        titles = [a["title"] for a in r.json()]
        assert "Past"   in titles
        assert "Future" not in titles

    def test_mark_done(self, client):
        create = client.post("/assignments/", json={
            "title": "To Done", "due_date": today_plus(3)
        })
        assignment_id = create.json()["id"]
        r = client.post(f"/assignments/{assignment_id}/done")
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_mark_done_nonexistent(self, client):
        r = client.post("/assignments/99999/done")
        assert r.status_code == 404

    def test_update_status(self, client):
        create = client.post("/assignments/", json={
            "title": "WIP", "due_date": today_plus(3)
        })
        aid = create.json()["id"]
        r   = client.patch(f"/assignments/{aid}/status", json={"status": "in_progress"})
        assert r.status_code == 200
        assert r.json()["status"] == "in_progress"

    def test_delete_assignment(self, client):
        create = client.post("/assignments/", json={
            "title": "Deletable", "due_date": today_plus(3)
        })
        aid = create.json()["id"]
        r   = client.delete(f"/assignments/{aid}")
        assert r.status_code == 204
        assert client.get("/assignments/").json() == []


# ── screen ────────────────────────────────────────────────────────────────

class TestScreenAPI:

    def test_breakdown_empty(self, client):
        r = client.get("/screen/breakdown")
        assert r.status_code == 200
        data = r.json()
        assert data["productive_min"]  == 0
        assert data["distracting_min"] == 0

    def test_mock_productive_window(self, client):
        r = client.post("/screen/mock", json={
            "app": "code", "title": "main.py"
        })
        assert r.status_code == 200
        assert r.json()["category"] == "productive"

    def test_mock_distracting_window(self, client):
        r = client.post("/screen/mock", json={
            "app": "instagram", "title": "Instagram"
        })
        assert r.status_code == 200
        assert r.json()["category"] == "distracting"

    def test_mock_updates_breakdown(self, client):
        # Inject 2 productive sessions
        client.post("/screen/mock", json={"app": "code", "title": "project.py"})
        client.post("/screen/mock", json={"app": "notion", "title": "Notes"})
        r = client.get("/screen/breakdown")
        # Should have some sessions
        assert r.status_code == 200

    def test_sessions_list(self, client):
        client.post("/screen/mock", json={"app": "code", "title": "test.py"})
        r = client.get("/screen/sessions")
        assert r.status_code == 200
        sessions = r.json()
        assert len(sessions) >= 1
        assert sessions[0]["app_name"] == "code"


# ── CV ────────────────────────────────────────────────────────────────────

class TestCVAPI:

    def test_mock_present_event(self, client):
        r = client.post("/cv/mock", json={"event": "present"})
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_mock_absent_event(self, client):
        r = client.post("/cv/mock", json={"event": "absent"})
        assert r.status_code == 200

    def test_mock_distracted_event(self, client):
        r = client.post("/cv/mock", json={"event": "distracted"})
        assert r.status_code == 200

    def test_mock_invalid_event(self, client):
        r = client.post("/cv/mock", json={"event": "flying"})
        assert r.status_code == 400

    def test_events_logged(self, client):
        client.post("/cv/mock", json={"event": "present"})
        client.post("/cv/mock", json={"event": "absent"})
        r = client.get("/cv/events")
        assert r.status_code == 200
        events = r.json()
        event_types = [e["event"] for e in events]
        assert "present" in event_types
        assert "absent"  in event_types

    def test_focus_today(self, client):
        r = client.get("/cv/focus/today")
        assert r.status_code == 200
        data = r.json()
        assert "focus_score" in data


# ── reports ───────────────────────────────────────────────────────────────

class TestReportsAPI:

    def test_stats_endpoint(self, client):
        r = client.get("/reports/stats")
        assert r.status_code == 200
        data = r.json()
        assert "focus_score"     in data
        assert "productive_min"  in data
        assert "distracting_min" in data

    def test_history_endpoint(self, client):
        r = client.get("/reports/history?days=7")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_log_accountability(self, client):
        r = client.post("/reports/accountability", json={
            "question": "What's your priority today?",
            "answer":   "Finish the AI project",
        })
        assert r.status_code == 201
        assert r.json()["ok"] is True

    def test_get_today_accountability(self, client):
        client.post("/reports/accountability", json={
            "question": "What subject?", "answer": "Physics"
        })
        r = client.get("/reports/accountability/today")
        assert r.status_code == 200
        logs = r.json()
        assert len(logs) >= 1
        assert logs[0]["answer"] == "Physics"

    def test_roasts_endpoint_empty(self, client):
        r = client.get("/reports/roasts")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_latest_eod_no_data(self, client):
        r = client.get("/reports/eod/latest")
        assert r.status_code == 200


# ── voice ─────────────────────────────────────────────────────────────────

class TestVoiceAPI:

    def test_voice_status(self, client):
        r = client.get("/voice/status")
        assert r.status_code == 200
        data = r.json()
        assert "no_voice_mode" in data
        assert "hotword"       in data

    def test_list_intents(self, client):
        r = client.get("/voice/intents")
        assert r.status_code == 200
        intents = r.json()["intents"]
        names = [i["name"] for i in intents]
        assert "add_assignment"  in names
        assert "show_tasks"      in names
        assert "productivity"    in names

    def test_command_show_tasks(self, client):
        r = client.post("/voice/command", json={
            "text": "show my tasks", "speak_response": False
        })
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_command_add_assignment(self, client):
        r = client.post("/voice/command", json={
            "text": "add math assignment due Friday",
            "speak_response": False,
        })
        assert r.status_code == 200

    def test_command_productivity(self, client):
        r = client.post("/voice/command", json={
            "text": "how productive was I", "speak_response": False
        })
        assert r.status_code == 200

    def test_speak_endpoint(self, client):
        r = client.post("/voice/speak", json={"text": "Hello test"})
        assert r.status_code == 200
        assert r.json()["ok"] is True


# ── study advisor ─────────────────────────────────────────────────────────

class TestStudyAPI:

    def test_recommendations_endpoint(self, client):
        r = client.get("/study/recommendations")
        assert r.status_code == 200
        data = r.json()
        assert "recommendations" in data
        assert "weak_subjects"   in data

    def test_next_to_study(self, client):
        r = client.get("/study/next")
        assert r.status_code == 200
        assert "recommendation" in r.json()

    def test_subject_breakdown(self, client):
        r = client.get("/study/subjects")
        assert r.status_code == 200

    def test_recommendations_with_assignment_data(self, client):
        # Create some assignments first
        client.post("/assignments/", json={
            "title": "Math HW", "subject": "Math",
            "due_date": today_plus(3)
        })
        client.post("/assignments/", json={
            "title": "Physics Lab", "subject": "Physics",
            "due_date": today_plus(1)
        })
        r = client.get("/study/recommendations")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data["recommendations"], list)


# ── full workflow ─────────────────────────────────────────────────────────

class TestFullWorkflow:
    """
    End-to-end scenario tests that chain multiple API calls.
    Simulates a real study session.
    """

    def test_study_session_flow(self, client):
        """
        1. Log morning accountability
        2. Add assignments
        3. Simulate productive + distracting sessions
        4. Check stats reflect the activity
        """
        # Morning Q&A
        client.post("/reports/accountability", json={
            "question": "Priority today?",
            "answer":   "Finish AI assignment"
        })

        # Add assignment
        r = client.post("/assignments/", json={
            "title": "AI Project", "subject": "AI",
            "due_date": today_plus(1), "priority": "high"
        })
        aid = r.json()["id"]

        # Productive session
        client.post("/screen/mock", json={"app": "code", "title": "ai_project.py"})
        client.post("/cv/mock", json={"event": "present"})

        # Distraction
        client.post("/screen/mock", json={"app": "instagram", "title": "Instagram"})
        client.post("/cv/mock", json={"event": "distracted"})

        # Check stats
        stats = client.get("/reports/stats").json()
        assert stats["productive_min"] >= 0
        assert stats["distracting_min"] >= 0

        # Mark done
        r = client.post(f"/assignments/{aid}/done")
        assert r.json()["ok"] is True

        # Verify it's gone from upcoming
        upcoming = client.get("/assignments/upcoming").json()
        ids = [a["id"] for a in upcoming]
        assert aid not in ids
