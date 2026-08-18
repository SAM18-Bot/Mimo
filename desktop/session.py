"""
desktop/session.py — shared auth-token holder for the desktop app.

The pywebview window's JS reports the logged-in user's JWT back into
Python (via the js_api bridge in window_manager.py) — either right after
a fresh login, or on startup if a session was already cached in the
webview's local storage. Background threads that aren't part of the
webview (system tray stats loop, screen tracker, roast engine, ...) read
it from here to attach it to their own HTTP calls to the cloud API.
"""

import threading

_lock  = threading.Lock()
_token = None


def set_token(token: str) -> None:
    global _token
    with _lock:
        _token = token or None


def get_token():
    with _lock:
        return _token


def is_logged_in() -> bool:
    return get_token() is not None


def auth_headers() -> dict:
    """{} if no session yet, else a ready-to-use Authorization header dict."""
    token = get_token()
    return {"Authorization": f"Bearer {token}"} if token else {}
