"""
Settings API endpoints — used by the settings.html page.

GET  /settings          → returns current settings (sensitive keys masked)
POST /settings          → save one or more settings
POST /settings/restart  → restart background services after settings change
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Optional
from api.routes_auth import current_user
from db.models import User
import os

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingUpdate(BaseModel):
    key:   str
    value: str


class BulkSettingsUpdate(BaseModel):
    settings: dict


# ── page ──────────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
def settings_page():
    """Serve the settings HTML page."""
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "static", "settings.html",
    )
    if not os.path.exists(path):
        raise HTTPException(404, "Settings page not found")
    return FileResponse(path)


# ── API ───────────────────────────────────────────────────────────────────

@router.get("/data")
def get_settings(user: User = Depends(current_user)):
    """Return current settings grouped by section (sensitive values masked)."""
    from desktop.settings_manager import get_settings_for_ui
    return get_settings_for_ui()


@router.post("/save")
def save_setting(payload: SettingUpdate, user: User = Depends(current_user)):
    """Save a single setting to .env."""
    from desktop.settings_manager import save_setting as _save
    ok = _save(payload.key, payload.value)
    if not ok:
        raise HTTPException(400, f"Unknown or invalid setting: {payload.key}")
    return {"ok": True, "key": payload.key}


@router.post("/save-all")
def save_all_settings(payload: BulkSettingsUpdate, user: User = Depends(current_user)):
    """Save multiple settings at once."""
    from desktop.settings_manager import save_many
    results = save_many(payload.settings)
    failed  = [k for k, v in results.items() if not v]
    return {
        "ok":     len(failed) == 0,
        "saved":  [k for k, v in results.items() if v],
        "failed": failed,
    }


@router.post("/restart")
def restart_services(user: User = Depends(current_user)):
    """
    Restart monitoring services after settings change.
    Safe to call without full app restart for most changes.
    API key changes require a full restart.
    """
    try:
        from schedulers.background_tasks import stop_all, start_all
        from api.websocket import push_event
        import config
        import importlib
        importlib.reload(config)

        stop_all()
        start_all(
            speak_fn     = lambda t: print(f"[TTS] {t}"),
            broadcast_fn = push_event,
        )
        return {"ok": True, "message": "Services restarted with new settings."}
    except Exception as e:
        return {"ok": False, "error": str(e)}



