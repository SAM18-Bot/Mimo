"""
Background task orchestrator.
Starts all long-running threads and wires them together.
Hardware modules (CV pipeline, voice listener) fail gracefully if not available.
"""

import logging
import os

log = logging.getLogger(__name__)

# Singletons accessed by routes for live status
screen_tracker   = None
stream_client    = None
presence_monitor = None
voice_listener   = None
roast_engine     = None

NO_HARDWARE = os.getenv("NO_HARDWARE", "1").strip() == "1"  # default: skip hardware
NO_VOICE    = os.getenv("NO_VOICE",    "1").strip() == "1"  # default: skip voice
NO_TRACKER  = True # Decoupled client  # default: run tracker


class EventDispatcher:
    """
    Drop-in queue replacement that dispatches screen events to both
    the WebSocket bus AND the roast engine without circular imports.
    """
    def __init__(self, broadcast_fn, on_window_change_fn):
        self._broadcast        = broadcast_fn
        self._on_window_change = on_window_change_fn

    def put_nowait(self, data: dict):
        if self._broadcast:
            self._broadcast(data)
        if data.get("type") == "window_change" and self._on_window_change:
            self._on_window_change(
                data.get("app", ""),
                data.get("title", ""),
                data.get("category", "neutral"),
            )


def start_all(speak_fn=None, broadcast_fn=None):
    global screen_tracker, stream_client, presence_monitor, voice_listener, roast_engine

    # ── TTS ───────────────────────────────────────────────────────────────
    if not NO_VOICE:
        try:
            from modules.voice.speaker import start as start_tts
            start_tts()
            log.info("TTS speaker started.")
        except Exception as e:
            log.warning(f"TTS failed to start (will use print): {e}")
            speak_fn = lambda t: print(f"[TTS] {t}")
    else:
        log.info("NO_VOICE=1 — TTS disabled. Roasts will print to console.")
        speak_fn = lambda t: print(f"\n🔊 [VOICE] {t}\n")

    # ── Roast engine ──────────────────────────────────────────────────────
    from modules.ai_layer.roast_engine import RoastEngine

    # Wire native OS notifications when running as desktop app
    _notify_fn = None
    try:
        from desktop.notifications import notify_roast
        _notify_fn = notify_roast
        log.info("Native OS notifications enabled.")
    except ImportError:
        pass  # server-only mode — fine

    roast_engine = RoastEngine(
        speak_fn     = speak_fn,
        broadcast_fn = broadcast_fn,
        notify_fn    = _notify_fn,
    )
    log.info("Roast engine ready.")

    # ── Screen tracker (skip if NO_TRACKER) ───────────────────────────────
    if NO_TRACKER:
        log.info("NO_TRACKER=1 — Screen tracking disabled. Use POST /screen/mock to inject events.")
    else:
        dispatcher = EventDispatcher(
            broadcast_fn        = broadcast_fn,
            on_window_change_fn = roast_engine.on_window_change,
        )
        from modules.screen_tracker.tracker import ScreenTracker
        screen_tracker = ScreenTracker(event_bus=dispatcher)
        try:
            screen_tracker.start()
            log.info("Screen tracker started.")
        except Exception as e:
            log.warning(f"Screen tracker failed to start: {e}")
            log.warning("Use POST /screen/mock to inject window events manually.")

    # ── CV pipeline (skip if NO_HARDWARE) ────────────────────────────────
    if NO_HARDWARE:
        log.info("NO_HARDWARE=1 — Camera/CV disabled. Use POST /cv/mock to inject events.")
    else:
        from modules.cv_pipeline.stream_client import StreamClient
        stream_client = StreamClient()
        try:
            stream_client.start()
        except Exception as e:
            log.warning(f"Stream client failed: {e}")

        def on_cv_event(event_type: str):
            roast_engine.on_cv_event(event_type)

        from modules.cv_pipeline.presence import PresenceMonitor
        presence_monitor = PresenceMonitor(
            on_event     = on_cv_event,
            broadcast_fn = broadcast_fn,
        )
        try:
            presence_monitor.start()
            log.info("Presence monitor started.")
        except Exception as e:
            log.warning(f"Presence monitor failed: {e}")

    # ── Voice listener (skip if NO_VOICE) ─────────────────────────────────
    if NO_VOICE:
        log.info("NO_VOICE=1 — Voice listener disabled. Use /docs to test commands.")
    else:
        from modules.voice.intent_router import IntentRouter
        intent_router = IntentRouter(speak_fn=speak_fn, broadcast_fn=broadcast_fn)
        from modules.voice.listener import VoiceListener
        voice_listener = VoiceListener(on_command=intent_router.route)
        try:
            voice_listener.start()
            log.info("Voice listener started.")
        except Exception as e:
            log.warning(f"Voice listener failed: {e}")

    log.info("Background tasks ready.")

    from schedulers.todo_reminder import start_todo_reminders
    start_todo_reminders()

    return {
        "screen_tracker":   screen_tracker,
        "stream_client":    stream_client,
        "presence_monitor": presence_monitor,
        "voice_listener":   voice_listener,
        "roast_engine":     roast_engine,
    }


def stop_all():
    for name, obj in [
        ("voice_listener",   voice_listener),
        ("screen_tracker",   screen_tracker),
        ("presence_monitor", presence_monitor),
        ("stream_client",    stream_client),
    ]:
        if obj and hasattr(obj, "stop"):
            try:
                obj.stop()
                log.info(f"{name} stopped.")
            except Exception as e:
                log.warning(f"{name} stop error: {e}")

    if not NO_VOICE:
        try:
            from modules.voice.speaker import stop as stop_tts
            stop_tts()
        except Exception:
            pass

    from schedulers.todo_reminder import stop_todo_reminders
    stop_todo_reminders()
