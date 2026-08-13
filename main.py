"""
main.py — Entry point for the AI Accountability System.

Startup sequence:
  1. Init database (create tables)
  2. Mount static files (dashboard)
  3. Register all API routers (including new voice + study routes)
  4. Start WebSocket drain loop (asyncio)
  5. Start background threads (screen tracker, CV, voice)
  6. Start APScheduler (reminders, EOD report)

Run:
  uvicorn main:app --reload --host 0.0.0.0 --port 8000
  Then open http://localhost:8000 for the live dashboard.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

# ── logging ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level  = logging.INFO,
    format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

# ── DB init ───────────────────────────────────────────────────────────────
from db.database import init_db
init_db()

# ── WebSocket ──────────────────────────────────────────────────────────────
from api.websocket import manager, drain_event_bus, push_event


def _speak(text: str):
    try:
        from modules.voice.speaker import speak
        speak(text)
    except Exception:
        print(f"[TTS] {text}")


# ── lifespan ──────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("=" * 60)
    log.info("  AI Accountability System starting...")
    log.info("=" * 60)

    drain_task = asyncio.create_task(drain_event_bus())

    from schedulers.background_tasks import start_all
    start_all(speak_fn=_speak, broadcast_fn=push_event)

    from schedulers.daily_trigger import start_scheduler
    start_scheduler(speak_fn=_speak, broadcast_fn=push_event)

    log.info("Dashboard  → http://localhost:8000")
    log.info("Settings   → http://localhost:8000/settings")
    log.info("API docs   → http://localhost:8000/docs")
    log.info("File tree  → http://localhost:8000/static/file_tree.html")

    yield

    log.info("Shutting down...")
    drain_task.cancel()

    from schedulers.background_tasks import stop_all
    stop_all()

    from schedulers.daily_trigger import stop_scheduler
    stop_scheduler()

    log.info("Shutdown complete.")


# ── app ───────────────────────────────────────────────────────────────────
app = FastAPI(
    title       = "Mimo — AI Accountability System",
    description = "Behavior-aware AI productivity coach for students.",
    version     = "2.0.0",
    lifespan    = lifespan,
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# ── API routers ───────────────────────────────────────────────────────────
from api.routes_assignments import router as assignments_router
from api.routes_screen       import router as screen_router
from api.routes_reports      import router as reports_router
from api.routes_cv           import router as cv_router
from api.routes_voice        import router as voice_router         # NEW
from modules.ai_layer.study_advisor  import router as study_router      # NEW
from api.routes_settings             import router as settings_router    # NEW
from api.routes_monitoring           import router as monitoring_router  # NEW
from api.routes_schedule             import router as schedule_router     # NEW
from api.routes_auth                 import router as auth_router         # NEW
from api.routes_sync                 import router as sync_router         # NEW
from api.routes_onboarding           import router as onboarding_router   # NEW

app.include_router(assignments_router)
app.include_router(screen_router)
app.include_router(reports_router)
app.include_router(cv_router)
app.include_router(voice_router)
app.include_router(study_router)
app.include_router(settings_router)
app.include_router(monitoring_router)
app.include_router(schedule_router)
app.include_router(auth_router)
app.include_router(sync_router)
app.include_router(onboarding_router)

# ── WebSocket ─────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, token: str = None):
    if not token:
        await ws.close(code=1008, reason="Missing token")
        return

    from modules.auth.security import decode_access_token
    
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except Exception:
        await ws.close(code=1008, reason="Invalid token")
        return

    from db.database import get_db_ctx
    from db.models import TokenBlocklist
    with get_db_ctx() as db:
        if db.query(TokenBlocklist).filter(TokenBlocklist.token == token).first():
            await ws.close(code=1008, reason="Token revoked")
            return

    await manager.connect(ws)
    try:
        from modules.behavior_engine.aggregator import get_daily_stats
        from modules.assignments.manager import get_upcoming

        with get_db_ctx() as db:
            stats = get_daily_stats(db, user_id=user_id)
            tasks = get_upcoming(db, user_id=user_id, days=7)

        await manager.broadcast({"type": "stats_update", "stats": stats})
        await manager.broadcast({
            "type":  "tasks_list",
            "tasks": [
                {"id": a.id, "title": a.title, "due_date": str(a.due_date),
                 "priority": a.priority, "status": a.status, "subject": a.subject}
                for a in tasks
            ],
        })

        while True:
            await ws.receive_text()

    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception as e:
        log.error("WebSocket error: %s", e)
        manager.disconnect(ws)


# ── pages ─────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return FileResponse("static/dashboard.html")


@app.get("/schedule", response_class=HTMLResponse)
async def schedule_page():
    return FileResponse("static/schedule.html")


@app.get("/parents", response_class=HTMLResponse)
async def parent_portal():
    return FileResponse("static/parent_portal.html")


# ── health ────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    from schedulers.background_tasks import screen_tracker, stream_client, roast_engine
    import os
    return {
        "status":          "ok",
        "version":         "2.0.0",
        "screen_tracker":  screen_tracker is not None,
        "esp32_connected": stream_client.connected if stream_client else False,
        "roast_engine":    roast_engine is not None,
        "ws_clients":      manager.client_count,
        "no_hardware":     os.getenv("NO_HARDWARE", "1") == "1",
        "no_voice":        os.getenv("NO_VOICE", "1") == "1",
    }
