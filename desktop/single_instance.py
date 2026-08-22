"""
Single instance guard — ensures only one copy of Mimo runs at a time.

On Windows: uses a named mutex (most reliable)
On Mac/Linux: uses a PID lock file in ~/.mimo/

Usage:
    from desktop.single_instance import acquire, release, is_already_running

    if not acquire():
        print("Mimo is already running.")
        sys.exit(0)

    # ... run app ...

    release()
"""

import logging
import os
import platform

log = logging.getLogger(__name__)

_SYSTEM   = platform.system()
_APP_NAME = "MimoAccountabilityApp"
_LOCK_DIR = os.path.expanduser("~/.mimo")
_PID_FILE = os.path.join(_LOCK_DIR, "mimo.pid")

# Platform handles
_mutex    = None   # Windows mutex handle
_pid_fd   = None   # Unix file descriptor (locked)


# ── public API ────────────────────────────────────────────────────────────

def acquire() -> bool:
    """
    Try to acquire the single-instance lock.
    Returns True if we are the first instance.
    Returns False if another instance is already running.
    """
    if _SYSTEM == "Windows":
        return _acquire_windows()
    else:
        return _acquire_unix()


def release():
    """Release the single-instance lock (called at shutdown)."""
    if _SYSTEM == "Windows":
        _release_windows()
    else:
        _release_unix()


def is_already_running() -> bool:
    """Check without acquiring — True if another instance is running."""
    return not acquire()


# ── Windows ───────────────────────────────────────────────────────────────

def _acquire_windows() -> bool:
    global _mutex
    try:
        import ctypes
        _mutex = ctypes.windll.kernel32.CreateMutexW(None, False, _APP_NAME)
        err    = ctypes.windll.kernel32.GetLastError()
        if err == 183:   # ERROR_ALREADY_EXISTS
            log.info("Another Mimo instance is already running (mutex exists).")
            return False
        log.debug("Single-instance mutex acquired.")
        return True
    except Exception as e:
        log.warning("Windows mutex check failed: %s — proceeding anyway.", e)
        return True   # Fail open


def _release_windows():
    global _mutex
    if _mutex:
        try:
            import ctypes
            ctypes.windll.kernel32.CloseHandle(_mutex)
            _mutex = None
        except Exception:
            pass


# ── Unix (macOS + Linux) ──────────────────────────────────────────────────

def _acquire_unix() -> bool:
    global _pid_fd
    os.makedirs(_LOCK_DIR, exist_ok=True)

    try:
        import fcntl
        _pid_fd = open(_PID_FILE, "w")
        fcntl.lockf(_pid_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _pid_fd.write(str(os.getpid()))
        _pid_fd.flush()
        log.debug("Single-instance lock acquired: %s", _PID_FILE)
        return True

    except OSError:
        # Lock is held by another process
        log.info("Another Mimo instance is already running (lock file).")
        if _pid_fd:
            _pid_fd.close()
            _pid_fd = None
        return False

    except ImportError:
        # fcntl not available (shouldn't happen on Unix, but be safe)
        return _acquire_unix_fallback()


def _acquire_unix_fallback() -> bool:
    """Fallback: PID file without file lock."""
    import psutil

    if os.path.exists(_PID_FILE):
        try:
            pid = int(open(_PID_FILE).read().strip())
            if psutil.pid_exists(pid):
                # Check it's actually Mimo (not a recycled PID)
                try:
                    proc = psutil.Process(pid)
                    if "python" in proc.name().lower() or "mimo" in proc.name().lower():
                        log.info("Another Mimo instance running at PID %d.", pid)
                        return False
                except psutil.NoSuchProcess:
                    pass
        except (ValueError, OSError):
            pass   # Stale file

    # Write our PID
    with open(_PID_FILE, "w") as f:
        f.write(str(os.getpid()))
    return True


def _release_unix():
    global _pid_fd
    try:
        if _pid_fd:
            import fcntl
            fcntl.lockf(_pid_fd, fcntl.LOCK_UN)
            _pid_fd.close()
            _pid_fd = None
        if os.path.exists(_PID_FILE):
            os.remove(_PID_FILE)
    except Exception as e:
        log.debug("Lock release error (non-critical): %s", e)
