import logging
import threading
from datetime import datetime
import config
from desktop.session import get_token

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
        self._paused = threading.Event()
        self._session_token = None
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

    def set_paused(self, paused: bool) -> None:
        if paused:
            self._paused.set()
        else:
            self._paused.clear()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3.0)
        log.info("Desktop tracker stopped.")

    def _loop(self):
        import httpx
        from desktop.main_desktop import SERVER_URL

        while not self._stop_event.is_set():
            try:
                token = get_token()
                if token != self._session_token:
                    self._stitcher.reset()
                    self._distracting_buffer_s = 0
                    self._session_token = token

                if token and self._paused.is_set():
                    for session in self._stitcher.flush():
                        self._save_session(session, token)
                    self._distracting_buffer_s = 0
                elif token:
                    app, title = get_active_window()
                    category = categorize_app(app, title)
                    closed = self._stitcher.on_window_change(app, title, category, datetime.now())
                    for session in closed:
                        self._save_session(session, token)

                    if category == "distracting":
                        self._distracting_buffer_s += config.SCREEN_POLL_INTERVAL
                        if (
                            self._distracting_buffer_s > 120
                            and self._is_study_block_active(token)
                            and token == get_token()
                            and not self._paused.is_set()
                            and get_active_window()[0] == app
                        ):
                            self._kill_process(app)
                            self._distracting_buffer_s = 0
                    else:
                        self._distracting_buffer_s = 0

                    if token == get_token() and not self._paused.is_set():
                        response = httpx.post(
                            f"{SERVER_URL}/screen/mock",
                            json={"app": app, "title": title[:80], "category": category},
                            headers={"Authorization": f"Bearer {token}"},
                            timeout=2,
                        )
                        response.raise_for_status()
            except httpx.HTTPError as exc:
                log.debug("Could not report live activity: %s", type(exc).__name__)
            except Exception:
                log.exception("Desktop tracker loop error")

            self._stop_event.wait(config.SCREEN_POLL_INTERVAL)

        if self._session_token == get_token():
            for session in self._stitcher.flush():
                self._save_session(session, self._session_token)

    def _save_session(self, session: Session, token: str | None) -> None:
        if session.duration_s < 2 or not token or token != get_token():
            return
        import httpx
        from desktop.main_desktop import SERVER_URL

        payload = {
            "app_name": session.app[:200],
            "window_title": session.title[:500],
            "category": session.category,
            "started_at": session.started_at.isoformat(),
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "duration_s": session.duration_s,
            "session_date": session.started_at.date().isoformat(),
        }
        try:
            response = httpx.post(
                f"{SERVER_URL}/screen/session", json=payload,
                headers={"Authorization": f"Bearer {token}"}, timeout=2,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            log.warning("Could not save a desktop session: %s", type(exc).__name__)

    def _is_study_block_active(self, token: str) -> bool:
        import httpx
        from desktop.main_desktop import SERVER_URL

        try:
            response = httpx.get(
                f"{SERVER_URL}/schedule/study-blocks/active",
                headers={"Authorization": f"Bearer {token}"}, timeout=2,
            )
            response.raise_for_status()
            return response.json().get("active") is True
        except (httpx.HTTPError, ValueError):
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
                subprocess.run(["killall", "-9", "--", app_name], capture_output=True)
        except Exception as e:
            log.error(f"Failed to kill process {app_name}: {e}")
