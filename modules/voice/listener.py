"""
Voice listener — hotword-triggered speech recognition.
Hotword: "hey coach" (configurable)
After hotword detected → listens for a command → passes to intent_router.

Uses SpeechRecognition with Google STT (free, requires internet).
Swap recognize_google → recognize_whisper() for fully offline later.
"""

import logging
import threading
import time
from collections.abc import Callable

log = logging.getLogger(__name__)

HOTWORD = "hey coach"


class VoiceListener:
    def __init__(self, on_command: Callable | None = None):
        """on_command(text: str) called when a command is recognized."""
        self._on_command = on_command
        self._running    = False
        self._thread     = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True, name="voice-listener")
        self._thread.start()
        log.info(f"Voice listener started. Hotword: '{HOTWORD}'")

    def stop(self):
        self._running = False
        log.info("Voice listener stopped.")

    def _loop(self):
        try:
            import speech_recognition as sr
        except ImportError:
            log.warning("SpeechRecognition not installed — voice disabled.")
            return

        r = sr.Recognizer()
        r.energy_threshold       = 300
        r.dynamic_energy_threshold = True
        r.pause_threshold        = 0.8

        with sr.Microphone() as source:
            log.info("Calibrating microphone noise level...")
            r.adjust_for_ambient_noise(source, duration=1)
            log.info("Listening for hotword...")

            while self._running:
                try:
                    audio = r.listen(source, timeout=5, phrase_time_limit=4)
                    text  = r.recognize_google(audio).lower()
                    log.debug(f"Heard: {text!r}")

                    if HOTWORD in text:
                        log.info("Hotword detected — listening for command...")
                        from modules.voice.speaker import speak
                        speak("Yes?")

                        # Listen for the actual command
                        audio2 = r.listen(source, timeout=5, phrase_time_limit=8)
                        command = r.recognize_google(audio2).lower()
                        log.info(f"Command: {command!r}")

                        if self._on_command:
                            self._on_command(command)

                except sr.WaitTimeoutError:
                    continue   # nothing heard, keep listening
                except sr.UnknownValueError:
                    continue   # couldn't understand audio
                except sr.RequestError as e:
                    log.warning(f"STT API error: {e} — retrying in 5s")
                    time.sleep(5)
                except Exception as e:
                    log.error(f"Voice listener error: {e}")
                    time.sleep(2)
