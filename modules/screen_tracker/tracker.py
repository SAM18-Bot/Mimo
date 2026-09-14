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

