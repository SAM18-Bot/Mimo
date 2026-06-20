"""
Mimo system tray icon.

Shows live focus score and assignment count in the menu.
Provides quick actions: open dashboard, pause/resume, settings, quit.

Thread: runs in its own daemon thread (call tray.start() then tray.run()).
Webview: when the main window is closed, the tray keeps Mimo alive.
"""

import logging
import threading
import time
import webbrowser
from typing import Optional

log = logging.getLogger(__name__)

_BASE_URL = "http://127.0.0.1:8000"


class MimoTray:
    """
    System tray manager.

    Call run() to start (blocking — call from a daemon thread).
    Call update_stats(score, assignments) from outside to refresh the menu.
    Call open_dashboard() to show the webview window.
    """

    def __init__(self, open_window_fn=None):
        """
        open_window_fn: optional callable to (re)open the pywebview window.
        If None, falls back to opening in the default browser.
        """
        self._icon           = None
        self._open_window_fn = open_window_fn

        # Live stats shown in menu
        self._focus_score    = 0
        self._grade          = "—"
        self._assignments    = 0
        self._paused         = False
        self._lock           = threading.Lock()

    # ── public API ────────────────────────────────────────────────────────

    def run(self):
        """Start the system tray (blocking). Call from a daemon thread."""
        try:
            import pystray
            from desktop.icon_generator import generate_tray_icon

            self._pystray = pystray   # keep reference

            self._icon = pystray.Icon(
                name   = "Mimo",
                icon   = generate_tray_icon(state="active"),
                title  = "Mimo — AI Accountability",
                menu   = self._make_menu(),
            )

            # Start stats refresh in background
            stats_thread = threading.Thread(
                target=self._stats_loop, daemon=True, name="tray-stats"
            )
            stats_thread.start()

            log.info("System tray started.")
            self._icon.run()   # blocks until quit

        except ImportError:
            log.warning("pystray not installed — system tray disabled.")
        except Exception as e:
            log.error("System tray error: %s", e)

    def update_stats(self, focus_score: float, grade: str, assignments: int):
        with self._lock:
            self._focus_score = round(focus_score)
            self._grade       = grade
            self._assignments = assignments
        self._refresh_menu()

    def set_paused(self, paused: bool):
        with self._lock:
            self._paused = paused
        self._refresh_icon()
        self._refresh_menu()

    def set_alert(self, active: bool):
        """Briefly flash the icon red when a roast fires."""
        from desktop.icon_generator import generate_tray_icon
        if self._icon:
            state = "alert" if active else ("paused" if self._paused else "active")
            self._icon.icon = generate_tray_icon(state=state)

    # ── menu construction ─────────────────────────────────────────────────

    def _make_menu(self):
        p = self._pystray

        return p.Menu(
            # Default action — double-click on tray
            p.MenuItem(
                "Open Mimo",
                self._on_open,
                default=True,
            ),
            p.Menu.SEPARATOR,

            # Live stats (non-clickable)
            p.MenuItem(
                lambda item: f"Focus  {self._focus_score}/100  Grade {self._grade}",
                action=None,
                enabled=False,
            ),
            p.MenuItem(
                lambda item: f"Assignments  {self._assignments} pending",
                action=None,
                enabled=False,
            ),
            p.Menu.SEPARATOR,

            # Pause / resume toggle
            p.MenuItem(
                lambda item: "▶  Resume monitoring" if self._paused else "⏸  Pause monitoring",
                self._on_toggle_pause,
            ),

            # Settings
            p.MenuItem("⚙  Settings", self._on_settings),

            p.Menu.SEPARATOR,

            # Auto-start toggle with check mark
            p.MenuItem(
                "Start with system",
                self._on_toggle_autostart,
                checked=lambda item: self._is_autostart(),
            ),

            p.Menu.SEPARATOR,
            p.MenuItem("✕  Quit Mimo", self._on_quit),
        )

    def _refresh_menu(self):
        if self._icon:
            try:
                self._icon.update_menu()
            except Exception:
                pass

    def _refresh_icon(self):
        if self._icon:
            try:
                from desktop.icon_generator import generate_tray_icon
                state = "paused" if self._paused else "active"
                self._icon.icon = generate_tray_icon(state=state)
            except Exception:
                pass

    # ── menu callbacks ────────────────────────────────────────────────────

    def _on_open(self, icon=None, item=None):
        if self._open_window_fn:
            try:
                self._open_window_fn()
                return
            except Exception:
                pass
        # Fallback: open in browser
        webbrowser.open(_BASE_URL)

    def _on_settings(self, icon=None, item=None):
        webbrowser.open(f"{_BASE_URL}/settings")

    def _on_toggle_pause(self, icon=None, item=None):
        try:
            import httpx
            if self._paused:
                httpx.post(f"{_BASE_URL}/monitoring/resume", timeout=3)
            else:
                httpx.post(f"{_BASE_URL}/monitoring/pause", timeout=3)
            self.set_paused(not self._paused)
        except Exception as e:
            log.error("Pause toggle failed: %s", e)

    def _on_toggle_autostart(self, icon=None, item=None):
        try:
            from desktop.autostart import toggle
            new_state = toggle()
            log.info("Autostart %s", "enabled" if new_state else "disabled")
        except Exception as e:
            log.error("Autostart toggle failed: %s", e)

    def _on_quit(self, icon=None, item=None):
        log.info("Quit requested from tray.")
        if self._icon:
            self._icon.stop()
        import os
        os._exit(0)

    @staticmethod
    def _is_autostart() -> bool:
        try:
            from desktop.autostart import is_enabled
            return is_enabled()
        except Exception:
            return False

    # ── stats refresh loop ────────────────────────────────────────────────

    def _stats_loop(self):
        """Fetches live stats from the API every 60 seconds."""
        while True:
            try:
                import httpx
                r = httpx.get(f"{_BASE_URL}/reports/stats", timeout=3)
                if r.status_code == 200:
                    data  = r.json()
                    score = data.get("focus_score", 0)
                    grade = data.get("letter_grade", "—")

                    # Count upcoming assignments
                    r2    = httpx.get(f"{_BASE_URL}/assignments/upcoming?days=14", timeout=3)
                    count = len(r2.json()) if r2.status_code == 200 else 0

                    self.update_stats(score, grade, count)
            except Exception:
                pass   # server may not be ready yet
            time.sleep(60)
