"""
Cross-platform auto-start on system boot.

Windows  → HKEY_CURRENT_USER/SOFTWARE/Microsoft/Windows/CurrentVersion/Run
macOS    → ~/Library/LaunchAgents/com.mimo.app.plist
Linux    → ~/.config/autostart/mimo.desktop

Usage:
    from desktop.autostart import enable, disable, is_enabled
    enable()      # register Mimo to start on boot
    disable()     # remove from startup
    is_enabled()  # True/False
"""

import logging
import os
import platform
import shlex
import sys
from xml.sax.saxutils import escape

log = logging.getLogger(__name__)

_APP_NAME = "Mimo"
_SYSTEM   = platform.system()


def enable() -> bool:
    """Register Mimo to start on system boot. Returns True on success."""
    try:
        if _SYSTEM == "Windows":
            return _enable_windows()
        elif _SYSTEM == "Darwin":
            return _enable_macos()
        elif _SYSTEM == "Linux":
            return _enable_linux()
        else:
            log.warning("Autostart not supported on %s", _SYSTEM)
            return False
    except Exception as e:
        log.error("Failed to enable autostart: %s", e)
        return False


def disable() -> bool:
    """Remove Mimo from system startup. Returns True on success."""
    try:
        if _SYSTEM == "Windows":
            return _disable_windows()
        elif _SYSTEM == "Darwin":
            return _disable_macos()
        elif _SYSTEM == "Linux":
            return _disable_linux()
        else:
            return False
    except Exception as e:
        log.error("Failed to disable autostart: %s", e)
        return False


def is_enabled() -> bool:
    """Check if Mimo is registered in system startup."""
    try:
        if _SYSTEM == "Windows":
            return _check_windows()
        elif _SYSTEM == "Darwin":
            return _check_macos()
        elif _SYSTEM == "Linux":
            return _check_linux()
        return False
    except Exception:
        return False


def toggle() -> bool:
    """Toggle autostart. Returns new state (True = enabled)."""
    if is_enabled():
        disable()
        return False
    else:
        enable()
        return True


def get_executable_path() -> str:
    """
    Returns the path to use for autostart registration.
    - If running as a PyInstaller bundle: path to the .exe/.app
    - If running as a Python script: 'python /path/to/desktop/main_desktop.py'
    """
    if getattr(sys, "frozen", False):
        # PyInstaller bundle
        return sys.executable
    else:
        python  = sys.executable
        script  = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "main_desktop.py")
        )
        return f'"{python}" "{script}"'


# ── Windows ───────────────────────────────────────────────────────────────

def _enable_windows() -> bool:
    import winreg
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
        0, winreg.KEY_SET_VALUE,
    )
    winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, get_executable_path())
    winreg.CloseKey(key)
    log.info("Autostart enabled (Windows Registry)")
    return True


def _disable_windows() -> bool:
    import winreg
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE,
        )
        winreg.DeleteValue(key, _APP_NAME)
        winreg.CloseKey(key)
    except FileNotFoundError:
        pass  # Already disabled
    log.info("Autostart disabled (Windows Registry)")
    return True


def _check_windows() -> bool:
    import winreg
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_READ,
        )
        winreg.QueryValueEx(key, _APP_NAME)
        winreg.CloseKey(key)
        return True
    except (FileNotFoundError, OSError):
        return False


# ── macOS ─────────────────────────────────────────────────────────────────

_PLIST_PATH = os.path.expanduser("~/Library/LaunchAgents/com.mimo.app.plist")

def _plist_content() -> str:
    exe = get_executable_path()
    # Split into key/string pairs for the plist
    parts = shlex.split(exe)
    args  = "\n".join(f"        <string>{escape(p)}</string>" for p in parts)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.mimo.app</string>
    <key>ProgramArguments</key>
    <array>
{args}
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>{os.path.expanduser("~/Library/Logs/mimo.log")}</string>
    <key>StandardErrorPath</key>
    <string>{os.path.expanduser("~/Library/Logs/mimo_err.log")}</string>
</dict>
</plist>
"""

def _enable_macos() -> bool:
    os.makedirs(os.path.dirname(_PLIST_PATH), exist_ok=True)
    with open(_PLIST_PATH, "w") as f:
        f.write(_plist_content())
    os.system(f"launchctl load -w '{_PLIST_PATH}' 2>/dev/null")
    log.info("Autostart enabled (macOS LaunchAgent: %s)", _PLIST_PATH)
    return True


def _disable_macos() -> bool:
    if os.path.exists(_PLIST_PATH):
        os.system(f"launchctl unload '{_PLIST_PATH}' 2>/dev/null")
        os.remove(_PLIST_PATH)
    log.info("Autostart disabled (macOS LaunchAgent removed)")
    return True


def _check_macos() -> bool:
    return os.path.exists(_PLIST_PATH)


# ── Linux ─────────────────────────────────────────────────────────────────

_AUTOSTART_DIR  = os.path.expanduser("~/.config/autostart")
_DESKTOP_PATH   = os.path.join(_AUTOSTART_DIR, "mimo.desktop")

def _desktop_content() -> str:
    exe = get_executable_path()
    icon = os.path.join(os.path.dirname(__file__), "assets", "mimo_active_64.png")
    return f"""[Desktop Entry]
Type=Application
Name=Mimo
Comment=AI Student Accountability System
Exec={exe}
Icon={icon}
Terminal=false
StartupNotify=false
X-GNOME-Autostart-enabled=true
"""

def _enable_linux() -> bool:
    os.makedirs(_AUTOSTART_DIR, exist_ok=True)
    with open(_DESKTOP_PATH, "w") as f:
        f.write(_desktop_content())
    os.chmod(_DESKTOP_PATH, 0o755)
    log.info("Autostart enabled (Linux autostart: %s)", _DESKTOP_PATH)
    return True


def _disable_linux() -> bool:
    if os.path.exists(_DESKTOP_PATH):
        os.remove(_DESKTOP_PATH)
    log.info("Autostart disabled (Linux autostart entry removed)")
    return True


def _check_linux() -> bool:
    return os.path.exists(_DESKTOP_PATH)
