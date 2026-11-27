"""
Settings API endpoints — used by the settings.html page.

GET  /settings          → returns current settings (sensitive keys masked)
POST /settings          → save one or more settings
POST /settings/restart  → restart background services after settings change
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from server.api.routes_auth import local_controls_user
from server.config import WEB_DIR
from server.db.models import User

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
    path = WEB_DIR / "settings.html"
    if not path.is_file():
        raise HTTPException(404, "Settings page not found")
    return FileResponse(path)


# ── API ───────────────────────────────────────────────────────────────────

@router.get("/data")
def get_settings(user: User = Depends(local_controls_user)):
    """Return current settings grouped by section (sensitive values masked)."""
    from server.modules.settings_manager import get_settings_for_ui
    return get_settings_for_ui()


@router.post("/save")
def save_setting(payload: SettingUpdate, user: User = Depends(local_controls_user)):
    """Save a single setting to .env."""
    from server.modules.settings_manager import save_setting as _save
    ok = _save(payload.key, payload.value)
    if not ok:
        raise HTTPException(400, f"Unknown or invalid setting: {payload.key}")
    return {"ok": True, "key": payload.key}


@router.post("/save-all")
def save_all_settings(payload: BulkSettingsUpdate, user: User = Depends(local_controls_user)):
    """Save multiple settings at once."""
    from server.modules.settings_manager import save_many
    results = save_many(payload.settings)
    failed  = [k for k, v in results.items() if not v]
    return {
        "ok":     len(failed) == 0,
        "saved":  [k for k, v in results.items() if v],
        "failed": failed,
    }


@router.post("/restart")
def restart_services(user: User = Depends(local_controls_user)):
    """
    Restart monitoring services after settings change.
    Safe to call without full app restart for most changes.
    API key changes require a full restart.
    """
    try:
        import importlib

        from server import config
        from server.api.websocket import push_event
        from server.schedulers.background_tasks import start_all, stop_all
        importlib.reload(config)

        stop_all()
        start_all(
            speak_fn     = lambda t: print(f"[TTS] {t}"),
            broadcast_fn = push_event,
        )
        return {"ok": True, "message": "Services restarted with new settings."}
    except Exception as e:
        return {"ok": False, "error": str(e)}







