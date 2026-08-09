"""
desktop/main_desktop.py — Mimo Desktop Application Entry Point

Startup sequence:
  1. Single-instance check (prevent two copies running)
  2. Configure logging (console + optional file)
  3. Show splash screen (tkinter, no extra install)
  4. Start FastAPI server (background thread)
  5. Wait for server health check
  6. Create pywebview window
  7. Start system tray (background thread)
  8. Show startup notification
  9. Start pywebview event loop on main thread (blocks)
 10. On all windows closed → app continues in tray
 11. Tray Quit → clean shutdown

Run directly:
    python desktop/main_desktop.py

Or from project root:
    python run_desktop.py
"""

import atexit
import logging
import os
import platform
import sys
import tempfile
import threading
import time

# ── project root on sys.path ──────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ── suppress console window on Windows when packaged ─────────────────────
if sys.platform == "win32" and getattr(sys, "frozen", False):
    import ctypes
    ctypes.windll.user32.ShowWindow(
        ctypes.windll.kernel32.GetConsoleWindow(), 0
    )

# ── logging ───────────────────────────────────────────────────────────────
def _get_log_dir() -> str:
    """Return a writable directory for desktop logs."""
    candidates = []

    override = os.environ.get("MIMO_LOG_DIR")
    if override:
        candidates.append(override)

    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            candidates.append(os.path.join(local_app_data, "Mimo", "logs"))

    candidates.extend([
        os.path.join(os.path.expanduser("~"), ".mimo"),
        os.path.join(ROOT, "logs"),
        os.path.join(tempfile.gettempdir(), "mimo"),
    ])

    for path in candidates:
        try:
            os.makedirs(path, exist_ok=True)
            return path
        except OSError:
            continue

    return ROOT


_LOG_DIR = _get_log_dir()

_handlers: list = [logging.StreamHandler(sys.stdout)]

# Log to file when running as a packaged app (no visible console)
if getattr(sys, "frozen", False):
    _log_file = os.path.join(_LOG_DIR, "mimo.log")
    _handlers.append(logging.FileHandler(_log_file, encoding="utf-8"))

logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers = _handlers,
)
log = logging.getLogger("mimo.desktop")


# ── constants ─────────────────────────────────────────────────────────────
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8000
SERVER_URL  = f"http://{SERVER_HOST}:{SERVER_PORT}"
STARTUP_TIMEOUT = 40   # seconds to wait for FastAPI to be ready


# ══════════════════════════════════════════════════════════════════════════
# Step 1 — Single instance
# ══════════════════════════════════════════════════════════════════════════

def _check_single_instance() -> bool:
    """Returns True if we are the only running instance."""
    try:
        from desktop.single_instance import acquire
        if not acquire():
            _show_already_running_dialog()
            return False
        atexit.register(_release_lock)
        return True
    except Exception as e:
        log.warning("Single-instance check failed (non-critical): %s", e)
        return True   # Fail open — better to allow duplicates than crash


def _release_lock():
    try:
        from desktop.single_instance import release
        release()
    except Exception:
        pass


def _show_already_running_dialog():
    """Tell the user Mimo is already running, then exit."""
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo(
            "Mimo already running",
            "Mimo is already running.\n\nCheck the system tray icon.",
        )
        root.destroy()
    except Exception:
        print("Mimo is already running. Check the system tray.", file=sys.stderr)


# ══════════════════════════════════════════════════════════════════════════
# Step 2 — Server
# ══════════════════════════════════════════════════════════════════════════

def _start_server():
    """Start the FastAPI/uvicorn server in a daemon thread."""
    def _run():
        try:
            import uvicorn
            uvicorn.run(
                "main:app",
                host      = SERVER_HOST,
                port      = SERVER_PORT,
                log_level = "warning",    # quieter in desktop mode
                log_config= None,         # prevents 'Unable to configure formatter' crash in PyInstaller
                reload    = False,
                workers   = 1,
            )
        except Exception as e:
            log.error("FastAPI server crashed: %s", e)

    thread = threading.Thread(target=_run, daemon=True, name="fastapi-server")
    thread.start()
    log.info("FastAPI server thread started.")
    return thread


def _wait_for_server(timeout: int = STARTUP_TIMEOUT, splash=None) -> bool:
    """
    Poll the /health endpoint until the server is ready.
    Updates the splash screen message during the wait.
    """
    import httpx

    start    = time.time()
    attempts = 0

    while time.time() - start < timeout:
        try:
            r = httpx.get(f"{SERVER_URL}/health", timeout=2)
            if r.status_code == 200:
                log.info("Server ready after %.1fs", time.time() - start)
                return True
        except Exception:
            pass

        attempts += 1
        if splash:
            dots = "." * (attempts % 4)
            splash.update(f"Starting Mimo{dots}")
        time.sleep(0.5)

    log.error("Server did not become ready within %ds", timeout)
    return False


# ══════════════════════════════════════════════════════════════════════════
# Step 3 — Tray
# ══════════════════════════════════════════════════════════════════════════

def _start_tray(window_manager) -> "MimoTray":
    """Start the system tray in a daemon thread."""
    from desktop.tray import MimoTray

    tray   = MimoTray(open_window_fn=window_manager.open)
    thread = threading.Thread(target=tray.run, daemon=True, name="system-tray")
    thread.start()
    return tray


# ══════════════════════════════════════════════════════════════════════════
# Step 4 — Shutdown
# ══════════════════════════════════════════════════════════════════════════

def _shutdown(window_manager=None):
    """Clean shutdown of all services."""
    log.info("Shutting down Mimo…")

    try:
        from schedulers.background_tasks import stop_all
        stop_all()
    except Exception:
        pass

    try:
        from schedulers.daily_trigger import stop_scheduler
        stop_scheduler()
    except Exception:
        pass

    if window_manager:
        try:
            window_manager.destroy()
        except Exception:
            pass

    log.info("Mimo shut down cleanly.")


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════

def main():
    log.info("=" * 56)
    log.info("  Mimo Desktop — %s %s", platform.system(), platform.release())
    log.info("=" * 56)

    # ── single instance ───────────────────────────────────────────────────
    if not _check_single_instance():
        sys.exit(0)

    # ── splash screen ─────────────────────────────────────────────────────
    from desktop.splash import SplashScreen
    splash = SplashScreen()
    splash.show()
    splash.update("Starting Mimo…")

    # ── start FastAPI server ──────────────────────────────────────────────
    _start_server()

    # ── wait for server ───────────────────────────────────────────────────
    if not _wait_for_server(splash=splash):
        splash.close()
        _show_error_dialog(
            "Mimo failed to start",
            f"The Mimo server did not start within {STARTUP_TIMEOUT} seconds.\n\n"
            "Check that port 8000 is free and try again.",
        )
        sys.exit(1)

    splash.update("Server ready — opening dashboard…")
    log.info("Server is ready. Initialising desktop components.")

    # ── window manager ────────────────────────────────────────────────────
    from desktop.window_manager import WindowManager
    wm             = WindowManager(url=SERVER_URL)
    webview_ok     = wm.create()
    atexit.register(_shutdown, wm)

    # ── system tray ───────────────────────────────────────────────────────
    tray = _start_tray(wm)

    # ── startup notification ──────────────────────────────────────────────
    try:
        from desktop.notifications import notify_startup
        notify_startup()
    except Exception:
        pass

    # ── close splash ──────────────────────────────────────────────────────
    time.sleep(0.3)
    splash.close()

    # ── webview event loop (main thread) ─────────────────────────────────
    if webview_ok:
        try:
            import webview
            log.info("Starting pywebview event loop.")
            webview.start(
                func       = wm.on_webview_start,
                debug      = False,
                private_mode = False,
            )
            # webview.start() returns when all windows are destroyed
            # At this point the app lives in the tray only
            log.info("pywebview event loop ended — app running in system tray.")

        except Exception as e:
            log.warning("pywebview error: %s — falling back to browser.", e)
            _open_browser_fallback()

    else:
        # pywebview not available — open in default browser instead
        _open_browser_fallback()

    # ── keep main thread alive while tray is running ──────────────────────
    # (tray thread is daemon, so we must keep main alive)
    log.info("App running in system tray. Press Ctrl+C to quit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Keyboard interrupt — shutting down.")
        _shutdown(wm)
        sys.exit(0)


def _open_browser_fallback():
    """Open the dashboard in the default browser when pywebview isn't available."""
    import webbrowser
    log.info("Opening dashboard in browser: %s", SERVER_URL)
    webbrowser.open(SERVER_URL)


def _show_error_dialog(title: str, message: str):
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, message)
        root.destroy()
    except Exception:
        print(f"\nERROR: {title}\n{message}", file=sys.stderr)


# ── entry ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
