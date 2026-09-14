import logging
import threading
import time
from datetime import datetime
import config

from modules.screen_tracker.tracker import get_active_window
from modules.screen_tracker.categorizer import categorize_app
from modules.screen_tracker.session import SessionStitcher, Session
import platform

log = logging.getLogger(__name__)
_SYSTEM = platform.system()

class DesktopTracker:

    def __init__(self, event_bus=None):
        self._event_bus = event_bus
        self._stop_event = threading.Event()
        self._thread = None
        self._stitcher = SessionStitcher()
        self._distracting_buffer_s = 0

    def start(self):
        if self._stop_event.is_set():
            self._stop_event.clear()
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="desktop-tracker"
        )
        self._thread.start()
        log.info("Desktop tracker started.")

    def stop(self):
        self._stop_event.set()
        closed_sessions = self._stitcher.flush()
        for session in closed_sessions:
            self._save_session(session)
        if self._thread:
            self._thread.join(timeout=3.0)
        log.info("Desktop tracker stopped.")

    def _loop(self):
        while not self._stop_event.is_set():
            try:
                app, title = get_active_window()
                category = categorize_app(app, title)
                now = datetime.now()

                closed_sessions = self._stitcher.on_window_change(app, title, category, now)
                for session in closed_sessions:
                    self._save_session(session)

                if category == "distracting":
                    self._distracting_buffer_s += config.SCREEN_POLL_INTERVAL
                    if self._distracting_buffer_s > 120:
                        if self._is_study_block_active():
                            self._kill_process(app)
                            self._distracting_buffer_s = 0
                else:
                    self._distracting_buffer_s = 0

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
                log.error("Desktop tracker loop error: %s", e)

            # Replaces time.sleep to fix teardown segfaults
            self._stop_event.wait(config.SCREEN_POLL_INTERVAL)

    def _save_session(self, session: Session):
        if session.duration_s < 2:
            return
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
        except Exception as e:
            log.error("Failed to save screen session remotely: %s", e)

    def _is_study_block_active(self) -> bool:
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
        from modules.screen_tracker.categorizer import is_browser
        if is_browser(app_name):
            log.warning(f"Browser {app_name} is distracting, emitting roast skipped locally (handled by backend).")
            return

        log.warning(f"Blocking distracting app: {app_name}")
        try:
            if _SYSTEM == "Windows":
                import subprocess
                subprocess.run(["taskkill", "/F", "/IM", f"{app_name}.exe"], capture_output=True)
            elif _SYSTEM in ["Linux", "Darwin"]:
                import subprocess
                subprocess.run(["killall", "-9", app_name], capture_output=True)
        except Exception as e:
            log.error(f"Failed to kill process {app_name}: {e}")
