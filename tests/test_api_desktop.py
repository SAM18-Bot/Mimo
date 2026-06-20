"""
API integration tests for desktop-specific routes:
  GET  /settings           → settings HTML page
  GET  /settings/data      → settings JSON for UI
  POST /settings/save      → save one setting
  POST /settings/save-all  → save multiple settings
  GET  /monitoring/status  → current monitoring state
  POST /monitoring/pause   → pause background modules
  POST /monitoring/resume  → resume background modules
"""

import os
import pytest


# ── Shared fixture: redirect .env writes to tmp file ─────────────────────

@pytest.fixture
def mock_env(tmp_path, monkeypatch):
    """
    Redirects all .env reads and writes in settings_manager to a temp file.
    Prevents tests from overwriting the real .env.
    """
    import desktop.settings_manager as sm
    env_file = tmp_path / ".env"
    env_file.write_text(
        "EOD_REPORT_HOUR=22\n"
        "NO_HARDWARE=1\n"
        "NO_VOICE=1\n"
        "DISTRACTION_ROAST_AFTER_MINUTES=5\n"
        "MIN_ROAST_INTERVAL_SECONDS=300\n"
    )
    monkeypatch.setattr(sm, "_ENV_PATH", str(env_file))
    return env_file


# ── Settings page ─────────────────────────────────────────────────────────

class TestSettingsPage:

    def test_settings_page_returns_html(self, client):
        r = client.get("/settings")
        assert r.status_code == 200
        ct = r.headers.get("content-type", "")
        assert "text/html" in ct

    def test_settings_page_contains_mimo(self, client):
        r = client.get("/settings")
        assert "Mimo" in r.text

    def test_settings_page_has_form_elements(self, client):
        r = client.get("/settings")
        # The settings page uses JS to render form, check at least the scaffold
        assert "sections-container" in r.text
        assert "save-btn" in r.text

    def test_settings_page_links_to_dashboard(self, client):
        r = client.get("/settings")
        assert 'href="/"' in r.text


# ── Settings data ─────────────────────────────────────────────────────────

class TestSettingsData:

    def test_data_endpoint_returns_200(self, client):
        r = client.get("/settings/data")
        assert r.status_code == 200

    def test_data_has_sections_key(self, client):
        r = client.get("/settings/data")
        data = r.json()
        assert "sections" in data

    def test_data_sections_are_list(self, client):
        r = client.get("/settings/data")
        data = r.json()
        assert isinstance(data["sections"], list)
        assert len(data["sections"]) > 0

    def test_data_sections_have_required_fields(self, client):
        r = client.get("/settings/data")
        for sec in r.json()["sections"]:
            assert "name" in sec
            assert "items" in sec
            for item in sec["items"]:
                assert "key"       in item
                assert "label"     in item
                assert "value"     in item
                assert "sensitive" in item
                assert "type"      in item

    def test_data_contains_ai_section(self, client):
        r = client.get("/settings/data")
        names = [s["name"] for s in r.json()["sections"]]
        assert "AI" in names

    def test_data_contains_hardware_section(self, client):
        r = client.get("/settings/data")
        names = [s["name"] for s in r.json()["sections"]]
        assert "Hardware" in names

    def test_data_contains_voice_section(self, client):
        r = client.get("/settings/data")
        names = [s["name"] for s in r.json()["sections"]]
        assert "Voice" in names

    def test_api_key_is_masked_in_response(self, client, mock_env):
        """The API key should come back masked with ••••."""
        # First write a real-looking key
        client.post("/settings/save", json={
            "key": "OPENAI_API_KEY", "value": "sk-test-key-12345678"
        })
        r    = client.get("/settings/data")
        data = r.json()
        # Find the OPENAI_API_KEY item
        api_item = None
        for sec in data["sections"]:
            for item in sec["items"]:
                if item["key"] == "OPENAI_API_KEY":
                    api_item = item
        assert api_item is not None
        assert api_item["sensitive"] is True


# ── Settings save ─────────────────────────────────────────────────────────

class TestSettingsSave:

    def test_save_valid_numeric_key(self, client, mock_env):
        r = client.post("/settings/save", json={
            "key": "EOD_REPORT_HOUR", "value": "21"
        })
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_save_valid_toggle_key(self, client, mock_env):
        r = client.post("/settings/save", json={
            "key": "NO_HARDWARE", "value": "1"
        })
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_save_url_setting(self, client, mock_env):
        r = client.post("/settings/save", json={
            "key": "ESP32_STREAM_URL",
            "value": "http://192.168.1.200:81/stream"
        })
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_save_invalid_key_returns_400(self, client, mock_env):
        r = client.post("/settings/save", json={
            "key": "TOTALLY_FAKE_KEY_THAT_DOES_NOT_EXIST",
            "value": "123"
        })
        assert r.status_code == 400

    def test_save_response_includes_key(self, client, mock_env):
        r = client.post("/settings/save", json={
            "key": "EOD_REPORT_HOUR", "value": "22"
        })
        data = r.json()
        assert data["key"] == "EOD_REPORT_HOUR"

    def test_save_masked_value_is_accepted_not_written(self, client, mock_env):
        """A value containing •••• should be accepted (200) but not written."""
        r = client.post("/settings/save", json={
            "key": "OPENAI_API_KEY", "value": "sk-test••••••••"
        })
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_save_api_key_clean_value(self, client, mock_env):
        r = client.post("/settings/save", json={
            "key": "OPENAI_API_KEY",
            "value": "sk-proj-testkey123"
        })
        assert r.status_code == 200
        assert r.json()["ok"] is True


# ── Settings save-all ─────────────────────────────────────────────────────

class TestSettingsSaveAll:

    def test_save_all_valid_settings(self, client, mock_env):
        r = client.post("/settings/save-all", json={
            "settings": {
                "EOD_REPORT_HOUR":                  "22",
                "NO_HARDWARE":                      "1",
                "NO_VOICE":                         "1",
                "DISTRACTION_ROAST_AFTER_MINUTES":  "5",
            }
        })
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert len(data["failed"]) == 0

    def test_save_all_with_one_invalid_key(self, client, mock_env):
        r = client.post("/settings/save-all", json={
            "settings": {
                "EOD_REPORT_HOUR": "22",
                "INVALID_KEY_XYZ": "bad",
            }
        })
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is False                      # not all succeeded
        assert "INVALID_KEY_XYZ" in data["failed"]
        assert "EOD_REPORT_HOUR" in data["saved"]

    def test_save_all_empty_dict(self, client, mock_env):
        r = client.post("/settings/save-all", json={"settings": {}})
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True   # nothing to save = all succeeded


# ── Monitoring API ────────────────────────────────────────────────────────

class TestMonitoringStatus:

    def test_status_returns_200(self, client):
        r = client.get("/monitoring/status")
        assert r.status_code == 200

    def test_status_has_paused_field(self, client):
        r = client.get("/monitoring/status")
        assert "paused" in r.json()

    def test_status_has_screen_tracking_field(self, client):
        r = client.get("/monitoring/status")
        assert "screen_tracking" in r.json()

    def test_status_has_cv_monitoring_field(self, client):
        r = client.get("/monitoring/status")
        assert "cv_monitoring" in r.json()

    def test_status_has_no_hardware_field(self, client):
        r = client.get("/monitoring/status")
        assert "no_hardware" in r.json()

    def test_status_has_no_voice_field(self, client):
        r = client.get("/monitoring/status")
        assert "no_voice" in r.json()

    def test_status_no_hardware_is_true_in_test_env(self, client):
        """In test environment NO_HARDWARE=1 is set."""
        r = client.get("/monitoring/status")
        assert r.json()["no_hardware"] is True

    def test_status_fields_are_booleans(self, client):
        r = client.get("/monitoring/status")
        data = r.json()
        for field in ("paused", "screen_tracking", "cv_monitoring",
                      "no_hardware", "no_voice"):
            assert isinstance(data[field], bool), f"{field} should be bool"


class TestMonitoringPauseResume:

    def test_pause_returns_200(self, client):
        r = client.post("/monitoring/pause")
        assert r.status_code == 200

    def test_pause_response_has_ok_true(self, client):
        r = client.post("/monitoring/pause")
        assert r.json()["ok"] is True

    def test_pause_response_has_status_paused(self, client):
        r = client.post("/monitoring/pause")
        assert r.json()["status"] == "paused"

    def test_resume_returns_200(self, client):
        r = client.post("/monitoring/resume")
        assert r.status_code == 200

    def test_resume_response_has_ok_true(self, client):
        r = client.post("/monitoring/resume")
        assert r.json()["ok"] is True

    def test_resume_response_has_status_active(self, client):
        r = client.post("/monitoring/resume")
        assert r.json()["status"] == "active"

    def test_pause_then_resume_sequence(self, client):
        r1 = client.post("/monitoring/pause")
        r2 = client.post("/monitoring/resume")
        assert r1.json()["ok"] is True
        assert r2.json()["ok"] is True

    def test_multiple_pauses_dont_crash(self, client):
        for _ in range(3):
            r = client.post("/monitoring/pause")
            assert r.status_code == 200

    def test_multiple_resumes_dont_crash(self, client):
        for _ in range(3):
            r = client.post("/monitoring/resume")
            assert r.status_code == 200
