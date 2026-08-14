"""
Monitoring control endpoints — pause and resume background monitoring.
Called by the system tray and the settings page.

POST /monitoring/pause   — stops screen tracker + CV pipeline
POST /monitoring/resume  — restarts them
GET  /monitoring/status  — returns current state
"""

from fastapi import APIRouter, Depends
from api.routes_auth import current_user
from db.models import User

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

_paused: bool = False


@router.post("/pause")
def pause_monitoring(user: User = Depends(current_user)):
    """Pause screen tracking and CV pipeline."""
    global _paused
    _paused = True

    try:
        from schedulers.background_tasks import screen_tracker, presence_monitor
        if screen_tracker and hasattr(screen_tracker, "stop"):
            screen_tracker.stop()
        if presence_monitor and hasattr(presence_monitor, "stop"):
            presence_monitor.stop()
    except Exception as e:
        return {"ok": False, "error": str(e)}

    from api.websocket import push_event
    push_event({"type": "monitoring_paused"})
    return {"ok": True, "status": "paused"}


@router.post("/resume")
def resume_monitoring(user: User = Depends(current_user)):
    """Resume screen tracking and CV pipeline."""
    global _paused
    _paused = False

    try:
        from schedulers.background_tasks import screen_tracker, presence_monitor, roast_engine
        from api.websocket import push_event

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

        push_event({"type": "monitoring_resumed"})

    except Exception as e:
        return {"ok": False, "error": str(e)}

    return {"ok": True, "status": "active"}


@router.get("/status")
def monitoring_status(user: User = Depends(current_user)):
    """Returns current monitoring state."""
    from schedulers.background_tasks import screen_tracker, presence_monitor, stream_client
    import os

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
