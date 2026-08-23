"""
Screen tracker — polls the active window every SCREEN_POLL_INTERVAL seconds.
Uses SessionStitcher (from session.py) to stitch adjacent windows into sessions.
Cross-platform: Windows (win32gui), Linux (xdotool), macOS (osascript).
"""

import logging
import platform
import threading
import time
from datetime import datetime

import psutil

import config
from modules.screen_tracker.categorizer import categorize_app
from modules.screen_tracker.session import Session, SessionStitcher

log = logging.getLogger(__name__)

_SYSTEM = platform.system()

# ── platform-specific imports ──────────────────────────────────────────────
_WIN32 = False
_LINUX = False

if _SYSTEM == "Windows":
    try:
        import win32gui
        import win32process
        _WIN32 = True
    except ImportError:
        log.warning("pywin32 not installed. Install with: pip install pywin32")

if _SYSTEM == "Linux":
    try:
        import subprocess as _sp
        _LINUX = True
    except Exception:
        pass


# ── active window reader ───────────────────────────────────────────────────

def get_active_window() -> tuple[str, str]:
    """Return (app_name_lower, window_title) for the currently focused window."""
    try:
        if _SYSTEM == "Windows" and _WIN32:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            title = win32gui.GetWindowText(hwnd)
            proc  = psutil.Process(pid)
            app   = proc.name().replace(".exe", "").lower()
            return app, title

        elif _SYSTEM == "Linux" and _LINUX:
            r = _sp.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True, text=True, timeout=1,
            )
            title = r.stdout.strip()
            r2 = _sp.run(
                ["xdotool", "getactivewindow", "getwindowpid"],
                capture_output=True, text=True, timeout=1,
            )
            pid_str = r2.stdout.strip()
            if pid_str.isdigit():
                proc = psutil.Process(int(pid_str))
                app  = proc.name().lower()
            else:
                app  = title.split()[0].lower() if title else "unknown"
            return app, title

        elif _SYSTEM == "Darwin":
            import subprocess
            script = (
                'tell application "System Events" to '
                'get name of first process whose frontmost is true'
            )
            r   = subprocess.run(["osascript", "-e", script],
                                 capture_output=True, text=True, timeout=2)
            app = r.stdout.strip().lower()
            return app, app

    except Exception as e:
        log.debug("get_active_window error: %s", e)

    return "unknown", ""


# ── screen tracker ─────────────────────────────────────────────────────────

class ScreenTracker:

    def __init__(self, event_bus=None):
        """
        event_bus: object with put_nowait(dict) — receives window-change events.
                   Can be an EventDispatcher (background_tasks) or a queue.Queue.
        """
        self._event_bus = event_bus
        self._running   = False
        self._thread    = None
        self._stitcher  = SessionStitcher()
        self._distracting_buffer_s = 0

    # ── lifecycle ─────────────────────────────────────────────────────────

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(
            target=self._loop, daemon=True, name="screen-tracker"
        )
        self._thread.start()
        log.info("Screen tracker started.")

    def stop(self):
        self._running = False
        # Flush any in-progress session
        closed_sessions = self._stitcher.flush()
        for session in closed_sessions:
            self._save_session(session)
        if self._thread:
            self._thread.join(timeout=5)
        log.info("Screen tracker stopped.")

    # ── main loop ─────────────────────────────────────────────────────────

    def _loop(self):
        while self._running:
            try:
                app, title = get_active_window()
                category   = categorize_app(app, title)
                now        = datetime.now()

                closed_sessions = self._stitcher.on_window_change(app, title, category, now)
                for session in closed_sessions:
                    self._save_session(session)

                # Check if we should block the app
                if category == "distracting":
                    self._distracting_buffer_s += config.SCREEN_POLL_INTERVAL
                    if self._distracting_buffer_s > 120:  # 2 minutes
                        # Are we in a study block?
                        if self._is_study_block_active():
                            self._kill_process(app)
                            self._distracting_buffer_s = 0
                else:
                    self._distracting_buffer_s = 0

                # Post to /screen/mock so backend knows live window for roasts/dashboard
                try:
                    import httpx

                    from desktop.main_desktop import SERVER_URL
                    from desktop.session import get_token
                    token = get_token()
                    if token:
                        headers = {"Authorization": f"Bearer {token}"}
                        httpx.post(f"{SERVER_URL}/screen/mock", json={
                            "app": app,
                            "title": title[:80],
                            "category": category
                        }, headers=headers, timeout=2)
                except Exception:
                    pass

            except Exception as e:
                log.error("Screen tracker loop error: %s", e)

            time.sleep(config.SCREEN_POLL_INTERVAL)

    # ── DB persistence ────────────────────────────────────────────────────

    def _save_session(self, session: Session):
        if session.duration_s < 2:
            return   # skip noise
        try:
            import httpx

            from desktop.main_desktop import SERVER_URL
            from desktop.session import get_token
            token = get_token()
            if not token:
                log.debug("No token, skipping session save.")
                return
            headers = {"Authorization": f"Bearer {token}"}
            payload = {
                "app_name": session.app,
                "window_title": session.title,
                "category": session.category,
                "started_at": session.started_at.isoformat(),
                "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                "duration_s": session.duration_s,
                "session_date": (session.started_at or datetime.now()).date().isoformat()
            }
            r = httpx.post(f"{SERVER_URL}/screen/session", json=payload, headers=headers)
            if r.status_code == 200:
                log.debug("Saved session remotely: [%s] %s %ds", session.category, session.app, session.duration_s)
            else:
                log.error("Failed to save session, status: %s", r.status_code)
        except Exception as e:
            log.error("Failed to save screen session remotely: %s", e)

    def _is_study_block_active(self) -> bool:
        """Check via HTTP if we are currently inside a 'study' schedule block."""
        try:
            import httpx

            from desktop.main_desktop import SERVER_URL
            from desktop.session import get_token
            token = get_token()
            if not token:
                return False
            headers = {"Authorization": f"Bearer {token}"}
            r = httpx.get(f"{SERVER_URL}/schedule/study-blocks/active", headers=headers)
            if r.status_code == 200:
                return r.json().get("active", False)
        except Exception as e:
            log.error("Failed to check study block remotely: %s", e)
        return False

    def _kill_process(self, app_name: str):
        """Force kill the distracting app, unless it's a browser."""
        from modules.screen_tracker.categorizer import is_browser
        if is_browser(app_name):
            log.warning(f"Browser {app_name} is distracting, but preventing force kill to save tabs. Emitting roast instead.")
            try:
                from desktop.session import get_token
                token = get_token()
                if token:
                    # Trigger a manual roast on the backend via /voice/roast (we could add an endpoint if needed)
                    # For now, just logging it since /screen/mock already triggers RoastEngine!
                    log.warning(f"Browser {app_name} is distracting, emitting roast skipped locally (handled by backend).")
            except Exception as e:
                log.error(f"Failed to handle browser distraction: {e}")
            return

        log.warning(f"Blocking distracting app: {app_name}")
        try:
            if _SYSTEM == "Windows":
                import subprocess
                subprocess.run(["taskkill", "/F", "/IM", f"{app_name}.exe"], capture_output=True)
            elif _SYSTEM == "Linux" or _SYSTEM == "Darwin":
                import subprocess
                subprocess.run(["killall", "-9", app_name], capture_output=True)
        except Exception as e:
            log.error(f"Failed to kill process {app_name}: {e}")
