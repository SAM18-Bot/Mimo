"""
Monitoring control endpoints — pause and resume background monitoring.
Called by the system tray and the settings page.

POST /monitoring/pause   — stops screen tracker + CV pipeline
POST /monitoring/resume  — restarts them
GET  /monitoring/status  — returns current state
"""

from fastapi import APIRouter, Depends

from server.api.routes_auth import local_controls_user
from server.db.models import User

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

_paused: bool = False


@router.post("/pause")
def pause_monitoring(user: User = Depends(local_controls_user)):
    """Pause screen tracking and CV pipeline."""
    global _paused
    _paused = True

    try:
        from server.schedulers.background_tasks import presence_monitor, screen_tracker
        if screen_tracker and hasattr(screen_tracker, "stop"):
            screen_tracker.stop()
        if presence_monitor and hasattr(presence_monitor, "stop"):
            presence_monitor.stop()
    except Exception as e:
        return {"ok": False, "error": str(e)}

    from server.api.websocket import push_event
    push_event({"user_id": user.id, "type": "monitoring_paused"})
    return {"ok": True, "status": "paused"}


@router.post("/resume")
def resume_monitoring(user: User = Depends(local_controls_user)):
    """Resume screen tracking and CV pipeline."""
    global _paused
    _paused = False

    try:
        from server.api.websocket import push_event
        from server.schedulers.background_tasks import (
            presence_monitor,
            screen_tracker,
        )

        # Restart screen tracker
        if screen_tracker:
            try:
                screen_tracker.start()
            except Exception:
                pass

        # Restart presence monitor
        if presence_monitor:
            try:
                presence_monitor.start()
            except Exception:
                pass

        push_event({"user_id": user.id, "type": "monitoring_resumed"})

    except Exception as e:
        return {"ok": False, "error": str(e)}

    return {"ok": True, "status": "active"}


@router.get("/status")
def monitoring_status(user: User = Depends(local_controls_user)):
    """Returns current monitoring state."""
    import os

    from server.schedulers.background_tasks import (
        presence_monitor,
        screen_tracker,
        stream_client,
    )

    screen_running = (
        screen_tracker is not None
        and getattr(screen_tracker, "_running", False)
    )
    cv_running = (
        presence_monitor is not None
        and getattr(presence_monitor, "_running", False)
    )
    esp32_connected = (
        stream_client is not None
        and getattr(stream_client, "connected", False)
    )

    return {
        "paused":           _paused,
        "screen_tracking":  screen_running,
        "cv_monitoring":    cv_running,
        "esp32_connected":  esp32_connected,
        "no_hardware":      os.getenv("NO_HARDWARE", "1") == "1",
        "no_voice":         os.getenv("NO_VOICE", "1") == "1",
    }
