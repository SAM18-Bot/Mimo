"""
Grabs frames from the ESP32-CAM MJPEG stream.
Runs in a background thread, puts latest frame into a shared slot.
Other modules (presence.py) read from the slot — they always get the latest frame.
"""

import logging
import threading
import time

import cv2
import numpy as np

import config

log = logging.getLogger(__name__)


class FrameSlot:
    """Thread-safe single-frame buffer. Readers always get the latest."""
    def __init__(self):
        self._frame: np.ndarray | None = None
        self._lock  = threading.Lock()
        self._event = threading.Event()

    def put(self, frame: np.ndarray):
        with self._lock:
            self._frame = frame
        self._event.set()

    def get(self, timeout: float = 2.0) -> np.ndarray | None:
        self._event.wait(timeout)
        self._event.clear()
        with self._lock:
            return self._frame.copy() if self._frame is not None else None

    @property
    def has_frame(self) -> bool:
        return self._frame is not None


# Global slot — imported by presence.py
frame_slot = FrameSlot()


class StreamClient:
    def __init__(self, url: str | None = None):
        self._url     = url or config.ESP32_STREAM_URL
        self._running = False
        self._thread  = None
        self._cap     = None
        self.connected = False

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True, name="esp32-stream")
        self._thread.start()
        log.info(f"ESP32 stream client started → {self._url}")

    def stop(self):
        self._running = False
        if self._cap:
            self._cap.release()
        log.info("ESP32 stream client stopped.")

    def _loop(self):
        retry_delay = 3.0

        while self._running:
            try:
                log.info(f"Connecting to ESP32-CAM at {self._url} ...")
                self._cap = cv2.VideoCapture(self._url)

                if not self._cap.isOpened():
                    raise ConnectionError(f"Cannot open stream: {self._url}")

                self.connected = True
                log.info("ESP32-CAM connected.")
                retry_delay = 3.0

                while self._running:
                    ret, frame = self._cap.read()
                    if not ret or frame is None:
                        log.warning("Frame read failed — reconnecting...")
                        break
                    # We read frames continuously so the MJPEG buffer doesn't lag.
                    # The FrameSlot always just holds the most recent one.
                    frame_slot.put(frame)

            except Exception as e:
                log.warning(f"Stream error: {e}. Retrying in {retry_delay}s...")
                self.connected = False
            finally:
                if self._cap:
                    self._cap.release()
                    self._cap = None

            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 1.5, 30.0)   # exponential backoff up to 30s
