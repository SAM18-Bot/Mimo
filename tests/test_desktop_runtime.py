"""
Tests for desktop runtime logic — window manager, tray, single instance,
and the server-wait logic in main_desktop.

These tests avoid actually opening GUI windows. In a headless CI environment
pywebview/pystray fail to initialize real windows, which is expected — we
test that the code degrades gracefully (falls back to browser, etc.)
rather than crashing.
"""

import os
import threading
import time

import pytest

# ── WindowManager ──────────────────────────────────────────────────────────

class TestWindowManager:

    def test_create_returns_bool(self):
        from desktop.window_manager import WindowManager
        wm = WindowManager(url="http://127.0.0.1:8000")
        result = wm.create()
        assert isinstance(result, bool)

    def test_is_available_false_before_create(self):
        from desktop.window_manager import WindowManager
        wm = WindowManager(url="http://127.0.0.1:8000")
        assert wm.is_available is False

    def test_open_falls_back_to_browser_when_not_alive(self, monkeypatch):
        """If webview never started, open() should fall back to webbrowser.open."""
        from desktop import window_manager as wm_mod

        opened = {"called": False, "url": None}
        def fake_open(url):
            opened["called"] = True
            opened["url"] = url

        monkeypatch.setattr(wm_mod.webbrowser, "open", fake_open)

        wm = wm_mod.WindowManager(url="http://127.0.0.1:8000")
        # Don't call create() or on_webview_start() — _alive stays False
        wm.open()

        assert opened["called"] is True
        assert opened["url"] == "http://127.0.0.1:8000"

    def test_on_webview_start_sets_alive_and_visible(self):
        from desktop.window_manager import WindowManager
        wm = WindowManager()
        assert wm._alive is False
        wm.on_webview_start()
        assert wm._alive is True
        assert wm._visible is True

    def test_destroy_resets_state(self):
        from desktop.window_manager import WindowManager
        wm = WindowManager()
        wm.on_webview_start()
        wm.destroy()
        assert wm._alive is False
        assert wm._visible is False

    def test_destroy_safe_when_window_is_none(self):
        """destroy() should not raise even if create() was never called."""
        from desktop.window_manager import WindowManager
        wm = WindowManager()
        wm.destroy()   # should not raise

    def test_custom_url_is_stored(self):
        from desktop.window_manager import WindowManager
        wm = WindowManager(url="http://localhost:9999")
        assert wm._url == "http://localhost:9999"

    def test_default_url(self):
        from desktop.window_manager import _URL, WindowManager
        wm = WindowManager()
        assert wm._url == _URL

    def test_on_closing_hides_not_destroys(self):
        """The _on_closing handler should hide the window, not destroy it."""
        from desktop.window_manager import WindowManager

        wm = WindowManager()
        wm.on_webview_start()

        # Fake a window object with hide()
        hidden = {"called": False}
        class FakeWindow:
            def hide(self_inner):
                hidden["called"] = True

        wm._window = FakeWindow()
        result = wm._on_closing()

        assert hidden["called"] is True
        assert wm._visible is False
        assert result is False   # cancels the actual close


# ── MimoTray (menu logic, no real tray icon) ───────────────────────────────

class TestMimoTrayLogic:

    def test_init_default_state(self):
        from desktop.tray import MimoTray
        tray = MimoTray()
        assert tray._focus_score == 0
        assert tray._grade       == "—"
        assert tray._assignments == 0
        assert tray._paused      is False

    def test_update_stats_sets_values(self):
        from desktop.tray import MimoTray
        tray = MimoTray()
        tray.update_stats(focus_score=87.6, grade="A", assignments=3)
        assert tray._focus_score == 88   # rounded
        assert tray._grade       == "A"
        assert tray._assignments == 3

    def test_update_stats_rounds_correctly(self):
        from desktop.tray import MimoTray
        tray = MimoTray()
        tray.update_stats(focus_score=49.4, grade="C", assignments=0)
        assert tray._focus_score == 49

    def test_set_paused_true(self):
        from desktop.tray import MimoTray
        tray = MimoTray()
        tray.set_paused(True)
        assert tray._paused is True

    def test_set_paused_false(self):
        from desktop.tray import MimoTray
        tray = MimoTray()
        tray.set_paused(True)
        tray.set_paused(False)
        assert tray._paused is False

    def test_refresh_menu_safe_when_icon_none(self):
        """Calling _refresh_menu before run() should not raise."""
        from desktop.tray import MimoTray
        tray = MimoTray()
        tray._refresh_menu()   # icon is None — should be a no-op

    def test_refresh_icon_safe_when_icon_none(self):
        from desktop.tray import MimoTray
        tray = MimoTray()
        tray._refresh_icon()   # should not raise

    def test_on_open_uses_open_window_fn(self):
        from desktop.tray import MimoTray
        called = {"yes": False}
        def fake_open():
            called["yes"] = True

        tray = MimoTray(open_window_fn=fake_open)
        tray._on_open()
        assert called["yes"] is True

    def test_on_open_falls_back_to_browser(self, monkeypatch):
        from desktop import tray as tray_mod
        opened = {"called": False}
        monkeypatch.setattr(tray_mod.webbrowser, "open", lambda url: opened.__setitem__("called", True))

        tray = tray_mod.MimoTray(open_window_fn=None)
        tray._on_open()
        assert opened["called"] is True

    def test_is_autostart_returns_bool(self):
        from desktop.tray import MimoTray
        result = MimoTray._is_autostart()
        assert isinstance(result, bool)

    def test_lock_is_threading_lock(self):
        from desktop.tray import MimoTray
        tray = MimoTray()
        assert isinstance(tray._lock, type(threading.Lock()))


# ── Single instance ─────────────────────────────────────────────────────────

class TestSingleInstance:

    def test_acquire_and_release_unix(self):
        """On the first acquire we should get the lock; release should free it."""
        import platform
        if platform.system() == "Windows":
            pytest.skip("Unix-only test")

        from desktop.single_instance import acquire, release

        first = acquire()
        assert first is True

        release()   # clean up so other tests aren't affected

    def test_double_acquire_blocks_second(self):
        """
        A second acquire() from a DIFFERENT process while the first holds
        the lock should fail. POSIX fcntl locks are per-process, so this
        must use a real subprocess to test contention correctly — locking
        twice within the same process always succeeds (self-lock merge).
        """
        import platform
        import subprocess
        import sys
        import textwrap
        if platform.system() == "Windows":
            pytest.skip("Unix-only test (uses fcntl)")

        from desktop.single_instance import acquire, release

        # Hold the lock in THIS process
        first = acquire()
        assert first is True

        # Spawn a real second process that tries to acquire the same lock
        child_code = textwrap.dedent(f"""
            import sys
            sys.path.insert(0, {os.path.dirname(os.path.dirname(os.path.abspath(__file__)))!r})
            from desktop.single_instance import acquire
            result = acquire()
            print("LOCKED" if result else "BLOCKED")
        """)
        proc = subprocess.run(
            [sys.executable, "-c", child_code],
            capture_output=True, text=True, timeout=10,
        )

        release()   # clean up our own lock

        assert "BLOCKED" in proc.stdout, (
            f"Expected child process to be blocked. stdout={proc.stdout!r} stderr={proc.stderr!r}"
        )

    def test_is_already_running_inverse_of_acquire(self):
        import platform
        if platform.system() == "Windows":
            pytest.skip("Unix-only test")

        from desktop.single_instance import acquire, is_already_running, release

        acquire()
        result = is_already_running()
        assert isinstance(result, bool)
        release()


# ── main_desktop server-wait logic ──────────────────────────────────────────

class TestWaitForServer:

    def test_wait_for_server_succeeds_when_healthy(self, monkeypatch):
        import httpx

        from desktop import main_desktop as md

        class FakeResponse:
            status_code = 200

        def fake_get(url, timeout=2):
            return FakeResponse()

        monkeypatch.setattr(httpx, "get", fake_get)

        result = md._wait_for_server(timeout=2, splash=None)
        assert result is True

    def test_wait_for_server_times_out_when_unreachable(self, monkeypatch):
        import httpx

        from desktop import main_desktop as md

        def fake_get(url, timeout=2):
            raise ConnectionError("refused")

        monkeypatch.setattr(httpx, "get", fake_get)

        start  = time.time()
        result = md._wait_for_server(timeout=1, splash=None)
        elapsed = time.time() - start

        assert result is False
        assert elapsed < 3   # should not hang way past the timeout

    def test_wait_for_server_updates_splash_message(self, monkeypatch):
        import httpx

        from desktop import main_desktop as md

        def fake_get(url, timeout=2):
            raise ConnectionError("refused")
        monkeypatch.setattr(httpx, "get", fake_get)

        messages = []
        class FakeSplash:
            def update(self, msg):
                messages.append(msg)

        md._wait_for_server(timeout=1, splash=FakeSplash())
        assert len(messages) > 0
        assert all("Starting Mimo" in m for m in messages)

    def test_constants_are_sane(self):
        from desktop import main_desktop as md
        # We just want to ensure it has the constants we rely on
        assert md.SERVER_PORT == 8000
        assert md.SERVER_URL  == "https://mimo-e8u2.onrender.com"
        assert md.STARTUP_TIMEOUT > 0
