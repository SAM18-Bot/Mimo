"""
Unit tests for desktop utility modules.
All tests run without a display — no GUI required.

Coverage:
  desktop/icon_generator.py    — PIL image generation
  desktop/settings_manager.py  — .env read/write
  desktop/notifications.py     — import + graceful fail
  desktop/autostart.py         — path generation (no OS calls)
"""

import os

import pytest

# ── icon generator ────────────────────────────────────────────────────────

class TestIconGenerator:

    def test_active_icon_correct_size(self):
        from desktop.icon_generator import generate_tray_icon
        img = generate_tray_icon(size=64, state="active")
        assert img.size == (64, 64)
        assert img.mode == "RGBA"

    def test_paused_icon_correct_size(self):
        from desktop.icon_generator import generate_tray_icon
        img = generate_tray_icon(size=64, state="paused")
        assert img.size == (64, 64)
        assert img.mode == "RGBA"

    def test_alert_icon_correct_size(self):
        from desktop.icon_generator import generate_tray_icon
        img = generate_tray_icon(size=64, state="alert")
        assert img.size == (64, 64)
        assert img.mode == "RGBA"

    def test_32px_icon(self):
        from desktop.icon_generator import generate_tray_icon
        img = generate_tray_icon(size=32, state="active")
        assert img.size == (32, 32)

    def test_16px_icon(self):
        from desktop.icon_generator import generate_tray_icon
        img = generate_tray_icon(size=16, state="active")
        assert img.size == (16, 16)

    def test_different_states_produce_different_pixels(self):
        from desktop.icon_generator import generate_tray_icon
        active_bytes = generate_tray_icon(state="active").tobytes()
        paused_bytes = generate_tray_icon(state="paused").tobytes()
        assert active_bytes != paused_bytes

    def test_alert_differs_from_active(self):
        from desktop.icon_generator import generate_tray_icon
        active = generate_tray_icon(state="active").tobytes()
        alert  = generate_tray_icon(state="alert").tobytes()
        assert active != alert

    def test_unknown_state_falls_back_gracefully(self):
        from desktop.icon_generator import generate_tray_icon
        # Unknown state should not raise — falls back to default
        img = generate_tray_icon(state="unknown_state_xyz")
        assert img.size == (64, 64)

    def test_save_creates_file(self, tmp_path, monkeypatch):
        from desktop import icon_generator
        monkeypatch.setattr(icon_generator, "ASSETS_DIR", str(tmp_path))
        path = icon_generator.save_icon("active", 32)
        assert os.path.exists(path)
        assert path.endswith(".png")

    def test_save_filename_includes_state_and_size(self, tmp_path, monkeypatch):
        from desktop import icon_generator
        monkeypatch.setattr(icon_generator, "ASSETS_DIR", str(tmp_path))
        path = icon_generator.save_icon("paused", 64)
        basename = os.path.basename(path)
        assert "paused" in basename
        assert "64" in basename

    def test_save_skips_if_file_exists(self, tmp_path, monkeypatch):
        from desktop import icon_generator
        monkeypatch.setattr(icon_generator, "ASSETS_DIR", str(tmp_path))
        # First call creates file
        path = icon_generator.save_icon("active", 32)
        mtime1 = os.path.getmtime(path)
        import time; time.sleep(0.01)
        # Second call should skip (file exists)
        icon_generator.save_icon("active", 32)
        mtime2 = os.path.getmtime(path)
        assert mtime1 == mtime2   # file not modified

    def test_get_all_icons_returns_three_states(self):
        from desktop.icon_generator import get_all_icons
        icons = get_all_icons()
        assert set(icons.keys()) == {"active", "paused", "alert"}

    def test_get_all_icons_are_pil_images(self):
        from PIL import Image

        from desktop.icon_generator import get_all_icons
        icons = get_all_icons()
        for state, img in icons.items():
            assert isinstance(img, Image.Image), f"{state} is not a PIL Image"

    def test_icon_has_non_zero_pixels(self):
        from desktop.icon_generator import generate_tray_icon
        img    = generate_tray_icon(state="active")
        # Convert to RGBA mode to get per-pixel tuples, then check non-transparent
        rgba  = img.convert("RGBA")
        bands = rgba.split()
        alpha = list(bands[3].tobytes()) if False else list(bands[3].tobytes())
        non_transparent = [a for a in alpha if a > 0]
        assert len(non_transparent) > 0


# ── settings manager ──────────────────────────────────────────────────────

class TestSettingsManager:

    @pytest.fixture
    def env_path(self, tmp_path, monkeypatch):
        """Redirects all .env reads/writes to a temp file."""
        import desktop.settings_manager as sm
        env_file = tmp_path / ".env"
        env_file.write_text(
            "EOD_REPORT_HOUR=22\n"
            "NO_HARDWARE=1\n"
            "NO_VOICE=1\n"
            "OPENAI_API_KEY=sk-test-1234567890\n"
        )
        monkeypatch.setattr(sm, "_ENV_PATH", str(env_file))
        return env_file

    def test_load_returns_all_default_keys(self, env_path):
        from desktop.settings_manager import DEFAULTS, load_settings
        settings = load_settings(mask_sensitive=False)
        for key in DEFAULTS:
            assert key in settings, f"Missing key: {key}"

    def test_load_reads_from_env_file(self, env_path):
        from desktop.settings_manager import load_settings
        settings = load_settings(mask_sensitive=False)
        assert settings["EOD_REPORT_HOUR"] == "22"
        assert settings["NO_HARDWARE"] == "1"

    def test_sensitive_key_masked_by_default(self, env_path):
        from desktop.settings_manager import load_settings
        settings = load_settings(mask_sensitive=True)
        assert "••••" in settings["OPENAI_API_KEY"]

    def test_sensitive_key_not_masked_when_disabled(self, env_path):
        from desktop.settings_manager import load_settings
        settings = load_settings(mask_sensitive=False)
        assert settings["OPENAI_API_KEY"] == "sk-test-1234567890"

    def test_save_valid_key(self, env_path):
        from desktop.settings_manager import save_setting
        result = save_setting("EOD_REPORT_HOUR", "21")
        assert result is True
        # Verify it was written
        content = open(str(env_path)).read()
        assert "EOD_REPORT_HOUR" in content

    def test_save_invalid_key_returns_false(self, env_path):
        from desktop.settings_manager import save_setting
        result = save_setting("DEFINITELY_NOT_A_REAL_KEY_XYZ", "123")
        assert result is False

    def test_save_masked_value_is_skipped(self, env_path):
        from desktop.settings_manager import load_settings, save_setting
        # Save a masked value
        result = save_setting("OPENAI_API_KEY", "sk-••••••••")
        assert result is True
        # Real value should be unchanged
        settings = load_settings(mask_sensitive=False)
        assert "••••" not in settings["OPENAI_API_KEY"]
        assert settings["OPENAI_API_KEY"] == "sk-test-1234567890"

    def test_save_all_keys(self, env_path):
        from desktop.settings_manager import save_many
        results = save_many({
            "EOD_REPORT_HOUR": "20",
            "NO_HARDWARE": "0",
        })
        assert results["EOD_REPORT_HOUR"] is True
        assert results["NO_HARDWARE"] is True

    def test_save_all_with_invalid_key(self, env_path):
        from desktop.settings_manager import save_many
        results = save_many({
            "EOD_REPORT_HOUR": "22",
            "INVALID_KEY_999": "bad",
        })
        assert results["EOD_REPORT_HOUR"] is True
        assert results["INVALID_KEY_999"] is False

    def test_get_settings_for_ui_has_sections(self, env_path):
        from desktop.settings_manager import SECTIONS, get_settings_for_ui
        data = get_settings_for_ui()
        assert "sections" in data
        section_names = [s["name"] for s in data["sections"]]
        for name in SECTIONS:
            assert name in section_names

    def test_get_settings_for_ui_items_have_required_fields(self, env_path):
        from desktop.settings_manager import get_settings_for_ui
        data = get_settings_for_ui()
        for sec in data["sections"]:
            for item in sec["items"]:
                assert "key"       in item
                assert "label"     in item
                assert "value"     in item
                assert "sensitive" in item
                assert "type"      in item

    def test_input_type_password_for_api_key(self):
        from desktop.settings_manager import _infer_input_type
        assert _infer_input_type("OPENAI_API_KEY") == "password"

    def test_input_type_toggle_for_bool_flags(self):
        from desktop.settings_manager import _infer_input_type
        assert _infer_input_type("NO_HARDWARE")       == "toggle"
        assert _infer_input_type("NO_VOICE")          == "toggle"
        assert _infer_input_type("LIVE_ROAST_USE_AI") == "toggle"

    def test_input_type_number_for_numeric_settings(self):
        from desktop.settings_manager import _infer_input_type
        assert _infer_input_type("EOD_REPORT_HOUR")                   == "number"
        assert _infer_input_type("DISTRACTION_ROAST_AFTER_MINUTES")   == "number"
        assert _infer_input_type("MIN_ROAST_INTERVAL_SECONDS")        == "number"

    def test_input_type_text_for_urls(self):
        from desktop.settings_manager import _infer_input_type
        assert _infer_input_type("ESP32_STREAM_URL") == "text"
        assert _infer_input_type("DATABASE_URL")     == "text"

    def test_every_default_key_has_a_label(self):
        from desktop.settings_manager import DEFAULTS, LABELS
        for key in DEFAULTS:
            assert key in LABELS, f"Missing label for: {key}"

    def test_get_setting_returns_value(self, env_path):
        from desktop.settings_manager import get_setting
        val = get_setting("EOD_REPORT_HOUR")
        assert val == "22"

    def test_get_setting_returns_default_for_missing(self, tmp_path, monkeypatch):
        import desktop.settings_manager as sm
        empty_env = tmp_path / ".env"
        empty_env.write_text("")
        monkeypatch.setattr(sm, "_ENV_PATH", str(empty_env))
        val = sm.get_setting("EOD_REPORT_HOUR")
        assert val == "22"   # default


# ── notifications ─────────────────────────────────────────────────────────

class TestNotifications:

    def test_module_imports_cleanly(self):
        """Should import without needing a display."""
        from desktop import notifications
        assert callable(notifications.notify)
        assert callable(notifications.notify_roast)
        assert callable(notifications.notify_reminder)
        assert callable(notifications.notify_eod)
        assert callable(notifications.notify_startup)

    def test_notify_returns_bool_not_exception(self):
        """In headless env, plyer fails silently and returns False."""
        from desktop.notifications import notify
        result = notify("Test title", "Test message", timeout=1)
        assert isinstance(result, bool)

    def test_notify_roast_does_not_raise(self):
        from desktop.notifications import notify_roast
        # Should not raise even in headless environment
        result = notify_roast("You've been on Instagram for 10 minutes.")
        assert isinstance(result, bool)

    def test_notify_eod_does_not_raise(self):
        from desktop.notifications import notify_eod
        result = notify_eod(75.5, "B")
        assert isinstance(result, bool)

    def test_notify_reminder_does_not_raise(self):
        from desktop.notifications import notify_reminder
        result = notify_reminder("Math HW", "Due tomorrow!")
        assert isinstance(result, bool)

    def test_notify_startup_does_not_raise(self):
        from desktop.notifications import notify_startup
        result = notify_startup()
        assert isinstance(result, bool)


# ── autostart ─────────────────────────────────────────────────────────────

class TestAutostart:

    def test_get_executable_path_returns_string(self):
        from desktop.autostart import get_executable_path
        path = get_executable_path()
        assert isinstance(path, str)
        assert len(path) > 0

    def test_get_executable_path_references_python_or_exe(self):
        from desktop.autostart import get_executable_path
        path = get_executable_path().lower()
        # Either running as Python script or as frozen bundle
        assert "python" in path or "mimo" in path or ".exe" in path

    def test_is_enabled_returns_bool(self):
        from desktop.autostart import is_enabled
        result = is_enabled()
        assert isinstance(result, bool)

    def test_toggle_returns_bool(self, monkeypatch):
        """Toggle should return the new state (True/False)."""
        from desktop import autostart
        # Monkeypatch to avoid actually writing to the OS
        monkeypatch.setattr(autostart, "enable",     lambda: True)
        monkeypatch.setattr(autostart, "disable",    lambda: True)
        monkeypatch.setattr(autostart, "is_enabled", lambda: False)

        result = autostart.toggle()
        assert isinstance(result, bool)

    def test_linux_desktop_content_is_valid(self, monkeypatch):
        """The .desktop file content should be properly formatted."""
        import platform
        if platform.system() != "Linux":
            pytest.skip("Linux only")
        from desktop.autostart import _desktop_content
        content = _desktop_content()
        assert "[Desktop Entry]" in content
        assert "Name=Mimo" in content
        assert "Exec=" in content
        assert "Terminal=false" in content

    def test_macos_plist_content_is_xml(self, monkeypatch):
        """The LaunchAgent plist should be valid XML."""
        import platform
        if platform.system() != "Darwin":
            pytest.skip("macOS only")
        from desktop.autostart import _plist_content
        content = _plist_content()
        assert "<?xml" in content
        assert "com.mimo.app" in content
        assert "<true/>" in content   # RunAtLoad
