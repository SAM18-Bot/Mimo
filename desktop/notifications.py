"""
Native OS notifications for Mimo.

Uses `plyer` which works on Windows (toast), macOS, and Linux (libnotify).
Falls back silently if the platform doesn't support it.

Usage:
    from desktop.notifications import notify, notify_roast, notify_reminder
    notify("Assignment due tomorrow!", "Math homework needs to be submitted.")
"""

import logging
import os
import sys

log = logging.getLogger(__name__)

_APP_NAME = "Mimo"
_ICON_PATH = os.path.join(os.path.dirname(__file__), "assets", "mimo_active_64.png")

def _notification_icon() -> str | None:
    """Return an icon path accepted by the current notification backend."""
    if sys.platform == "win32":
        return None
    if os.path.exists(_ICON_PATH):
        return _ICON_PATH
    return None


def _notifications_disabled() -> bool:
    disabled = os.environ.get("MIMO_DISABLE_NOTIFICATIONS", "").lower()
    return disabled in {"1", "true", "yes"} or "PYTEST_CURRENT_TEST" in os.environ


def notify(title: str, message: str, timeout: int = 5) -> bool:
    """
    Show a native OS notification.

    Returns True if notification was delivered, False if not supported.
    """
    if _notifications_disabled():
        return False

    try:
        from plyer import notification
        kwargs = dict(
            title       = f"{_APP_NAME} — {title}",
            message     = message,
            app_name    = _APP_NAME,
            timeout     = timeout,
        )
        icon = _notification_icon()
        if icon:
            kwargs["app_icon"] = icon

        notification.notify(**kwargs)
        log.debug("Notification sent: %s", title)
        return True

    except Exception as e:
        # Silently fail — notifications are a nice-to-have, not critical
        log.debug("Notification failed (non-critical): %s", e)
        return False


# ── Convenience wrappers ──────────────────────────────────────────────────

def notify_roast(message: str) -> bool:
    """Show a roast as a native notification."""
    return notify("🔥 Caught you", message, timeout=6)


def notify_reminder(assignment_title: str, message: str) -> bool:
    """Show an assignment reminder notification."""
    return notify(f"⚡ {assignment_title}", message, timeout=8)


def notify_eod(focus_score: float, grade: str) -> bool:
    """End-of-day summary notification."""
    return notify(
        "📊 Daily Report Ready",
        f"Today's focus score: {focus_score}/100 — Grade {grade}. Open dashboard to see your analysis.",
        timeout=10,
    )


def notify_startup() -> bool:
    """Show notification when Mimo starts."""
    return notify("Mimo started", "Monitoring is active. Say 'hey Mimo' or open the dashboard.", timeout=4)
