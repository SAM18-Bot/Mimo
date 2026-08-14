"""
routes_voice.py — REST interface for the voice command system.

Why this exists:
  Microphone-based voice input requires hardware. These endpoints let you
  test every voice command via /docs or curl without a microphone.
  The intent_router is the same code — only the input method changes.

Endpoints:
  POST /voice/command   → text in, action out (mirrors "hey coach" + command)
  POST /voice/speak     → directly inject a TTS message
  GET  /voice/status    → is voice system running, hotword, etc.
  GET  /voice/intents   → list of all supported intent patterns
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from api.routes_auth import current_user
from db.models import User

router = APIRouter(prefix="/voice", tags=["voice"])


# ── schemas ───────────────────────────────────────────────────────────────

class CommandRequest(BaseModel):
    text: str           # e.g. "add math assignment due Friday"
    speak_response: bool = True   # whether to also fire TTS

class SpeakRequest(BaseModel):
    text: str


# ── endpoints ─────────────────────────────────────────────────────────────

@router.post("/command")
def send_command(payload: CommandRequest, user: User = Depends(current_user)):
    """
    Route a text command through the intent router — same path as real voice.
    Perfect for testing every intent from /docs without a microphone.

    Examples:
      {"text": "add math assignment due Friday"}
      {"text": "show my tasks"}
      {"text": "how productive was I today"}
      {"text": "mark physics done"}
      {"text": "what should I study"}
      {"text": "give me my report"}
    """
    from api.websocket import push_event

    def _speak(msg: str):
        # Print to server console AND broadcast to dashboard
        print(f"\n🔊 [VOICE RESPONSE] {msg}\n")
        push_event({"type": "voice_response", "message": msg, "user_id": user.id})

    try:
        from modules.voice.intent_router import IntentRouter
        router_inst = IntentRouter(
            speak_fn     = _speak if payload.speak_response else None,
            broadcast_fn = push_event,
            user_id      = user.id,
        )
        router_inst.route(payload.text)
        return {"ok": True, "routed_text": payload.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/speak")
def speak_text(payload: SpeakRequest, user: User = Depends(current_user)):
    """Directly fire a TTS message. Tests the speaker module independently."""
    try:
        from modules.voice.speaker import speak
        speak(payload.text)
        return {"ok": True, "spoken": payload.text}
    except Exception as e:
        # TTS not installed — broadcast to dashboard instead
        from api.websocket import push_event
        push_event({"type": "voice_response", "message": payload.text, "user_id": user.id})
        return {"ok": True, "spoken": payload.text, "tts_warning": str(e)}


@router.get("/status")
def voice_status(user: User = Depends(current_user)):
    """Returns the current state of the voice subsystem."""
    from schedulers.background_tasks import voice_listener
    import os

    no_voice  = os.getenv("NO_VOICE", "1") == "1"

    listener_running = False
    if voice_listener and hasattr(voice_listener, "_running"):
        listener_running = voice_listener._running

    return {
        "no_voice_mode":    no_voice,
        "listener_running": listener_running,
        "hotword":          "hey coach",
        "tts_available":    _check_tts(),
        "stt_available":    _check_stt(),
        "note": (
            "NO_VOICE=1 in .env. Set NO_VOICE=0 and install pyttsx3 + pyaudio to enable."
            if no_voice else
            "Voice system active. Say 'hey coach' to activate."
        ),
    }


@router.get("/intents")
def list_intents(user: User = Depends(current_user)):
    """Lists all supported voice command patterns with examples."""
    return {
        "intents": [
            {
                "name":     "add_assignment",
                "triggers": ["add assignment", "new assignment", "homework", "due"],
                "examples": [
                    "add math assignment due Friday",
                    "physics homework due tomorrow",
                    "AI project due next Monday",
                ],
            },
            {
                "name":     "show_tasks",
                "triggers": ["show tasks", "my tasks", "what do I have", "today's tasks"],
                "examples": [
                    "show my tasks",
                    "what do I have today",
                    "show today's assignments",
                ],
            },
            {
                "name":     "mark_done",
                "triggers": ["done with", "finished", "completed", "submitted"],
                "examples": [
                    "done with math",
                    "I finished the physics lab",
                    "submitted AI project",
                ],
            },
            {
                "name":     "productivity",
                "triggers": ["how productive", "focus score", "my score", "how was my day"],
                "examples": [
                    "how productive was I today",
                    "what's my focus score",
                    "how was my day",
                ],
            },
            {
                "name":     "what_to_study",
                "triggers": ["what should I study", "recommend", "what to study"],
                "examples": [
                    "what should I study now",
                    "recommend something to study",
                ],
            },
            {
                "name":     "eod_report",
                "triggers": ["my report", "daily report", "end of day", "summary"],
                "examples": [
                    "give me my end of day report",
                    "daily summary",
                    "how did I do today",
                ],
            },
        ]
    }


# ── helpers ───────────────────────────────────────────────────────────────

def _check_tts() -> bool:
    try:
        import pyttsx3  # noqa: F401
        return True
    except ImportError:
        return False


def _check_stt() -> bool:
    try:
        import speech_recognition  # noqa: F401
        return True
    except ImportError:
        return False
