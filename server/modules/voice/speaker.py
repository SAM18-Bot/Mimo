"""
TTS speaker using pyttsx3 (fully offline, no API needed).
Runs in its own thread so it never blocks the main loop.
"""

import logging
import queue
import threading

log = logging.getLogger(__name__)

_tts_queue: queue.Queue = queue.Queue()
_tts_thread: threading.Thread = None
_engine = None


def _worker():
    """Dedicated thread that processes TTS requests one by one."""
    global _engine
    try:
        import pyttsx3
        _engine = pyttsx3.init()
        _engine.setProperty("rate",   160)    # words per minute (default ~200, slightly slower = clearer)
        _engine.setProperty("volume", 0.95)

        # Try to set a decent voice (index 0 = default system voice)
        voices = _engine.getProperty("voices")
        if voices:
            # Prefer a female voice if available (index 1 on most systems)
            _engine.setProperty("voice", voices[min(1, len(voices)-1)].id)

        log.info("TTS engine initialized.")

        while True:
            text = _tts_queue.get()
            if text is None:   # sentinel to stop
                break
            try:
                _engine.say(text)
                _engine.runAndWait()
            except Exception as e:
                log.error(f"TTS error: {e}")
            finally:
                _tts_queue.task_done()

    except ImportError:
        log.warning("pyttsx3 not installed — TTS disabled. Run: pip install pyttsx3")
    except Exception as e:
        log.error(f"TTS worker crashed: {e}")


def start():
    global _tts_thread
    _tts_thread = threading.Thread(target=_worker, daemon=True, name="tts-worker")
    _tts_thread.start()


def speak(text: str):
    """Queue text for speaking. Non-blocking."""
    if text:
        log.info(f"TTS: {text}")
        _tts_queue.put(text)


def stop():
    _tts_queue.put(None)   # sentinel
    if _tts_thread:
        _tts_thread.join(timeout=3)
