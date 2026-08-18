"""
Window manager — handles the pywebview browser window lifecycle.

Key behaviours:
  • Closing the window HIDES it (app keeps running in system tray)
  • Clicking "Open Mimo" in the tray SHOWS the hidden window again
  • The quit action from the tray DESTROYS the window and exits
  • Falls back to the default browser if pywebview is not installed

Call flow:
    1. wm = WindowManager(url="http://127.0.0.1:8000")
    2. wm.create()           ← call before webview.start()
    3. webview.start(...)    ← blocks on main thread; pass wm.on_webview_start as func
    4. wm.open()             ← can be called from any thread (tray) to show window
    5. wm.destroy()          ← hard-quit, called by tray Quit
"""

import logging
import threading
import webbrowser

log = logging.getLogger(__name__)

_URL = "http://127.0.0.1:8000"


class _JSBridge:
    """
    Exposed to the webview's JS as `window.pywebview.api`.

    dashboard.html calls `window.pywebview.api.report_token(token)` right
    after a successful login, and again on load if a session was already
    cached — that's how the Python side (system tray, background threads)
    finds out who's logged in and gets a token it can attach to its own
    API calls.
    """

    def report_token(self, token: str) -> bool:
        from desktop.session import set_token
        set_token(token)
        log.info("Session token received from dashboard.")
        return True


class WindowManager:
    def __init__(self, url: str = _URL):
        self._url     = url
        self._window  = None
        self._alive   = False   # True after webview.start() is running
        self._visible = False
        self._lock    = threading.Lock()

    # ── lifecycle ─────────────────────────────────────────────────────────

    def create(self) -> bool:
        """
        Create the webview window object.
        Must be called before webview.start().
        Returns True on success, False if pywebview not available.
        """
        try:
            import webview

            self._window = webview.create_window(
                title              = "Mimo — AI Accountability",
                url                = self._url,
                width              = 1280,
                height             = 820,
                min_size           = (900, 600),
                background_color   = "#07070f",
                text_select        = False,
                zoomable           = False,
                js_api             = _JSBridge(),
            )

            # Hide instead of close when user clicks the X
            self._window.events.closing += self._on_closing

            log.info("Webview window created.")
            return True

        except ImportError:
            log.warning("pywebview not installed — will use default browser.")
            self._handle_fallback()
            return False

        except Exception as e:
            log.error("Failed to create webview window: %s", e)
            self._handle_fallback()
            return False

    def _handle_fallback(self):
        webbrowser.open(self._url)
        try:
            from desktop.notifications import notify
            notify("Mimo running", "Mimo is running in your system tray", timeout=5)
        except Exception as e:
            log.debug("Fallback notification failed: %s", e)

    def on_webview_start(self):
        """
        Passed as `func` to webview.start().
        Called by pywebview once the event loop is ready.
        """
        with self._lock:
            self._alive   = True
            self._visible = True

    def open(self):
        """
        Show the window if hidden, or open in browser as fallback.
        Safe to call from any thread (e.g. system tray).
        """
        with self._lock:
            alive   = self._alive
            window  = self._window
            visible = self._visible

        if alive and window:
            try:
                if not visible:
                    # Schedule show() on the webview GUI thread
                    window.show()
                    with self._lock:
                        self._visible = True
                else:
                    # Already visible — just bring to front
                    try:
                        window.evaluate_js("window.focus()")
                    except Exception:
                        pass
                return
            except Exception as e:
                log.debug("window.show() failed: %s — opening browser", e)

        # Fallback: open in default browser
        webbrowser.open(self._url)

    def destroy(self):
        """
        Hard destroy — called by the tray Quit action.
        Destroys the window and ends the webview event loop.
        """
        try:
            if self._window:
                self._window.destroy()
        except Exception:
            pass
        finally:
            with self._lock:
                self._alive   = False
                self._visible = False

    # ── event handlers ────────────────────────────────────────────────────

    def _on_closing(self):
        """
        Called when the user clicks the window X button.
        Hide instead of close so the app lives in the tray.
        """
        try:
            self._window.hide()
            with self._lock:
                self._visible = False
            log.info("Window hidden (app still running in system tray).")
        except Exception as e:
            log.debug("Hide failed: %s", e)

        # In pywebview 5.x, returning False from a closing handler
        # cancels the close. We always cancel it (hide instead).
        return False

    @property
    def is_available(self) -> bool:
        """True if pywebview is installed and the window was created."""
        return self._window is not None
