"""
Presence monitor — reads frames from frame_slot, uses Mediapipe FaceDetection
to determine:
  - present   : face visible
  - absent    : no face for ABSENCE_THRESHOLD seconds
  - distracted: face visible but looking away
  - returned  : came back after absence

Events are written to CVEvent table and forwarded to the roast engine.
"""

import logging
import threading
import time
from datetime import datetime, date
from typing import Optional, Callable

import cv2
import mediapipe as mp
import numpy as np

from db.database import get_db_ctx
from db.models import CVEvent
from modules.cv_pipeline.stream_client import frame_slot
try:
    from modules.cv_pipeline.focus_detector import GazeDetector as _GazeDetector
except ImportError:
    _GazeDetector = None
import config

log = logging.getLogger(__name__)


class PresenceMonitor:
    def __init__(
        self,
        on_event: Optional[Callable] = None,   # callback(event_type: str)
        broadcast_fn: Optional[Callable] = None,
        user_id: int = 1,
    ):
        self._on_event    = on_event
        self._broadcast   = broadcast_fn
        self._user_id     = user_id
        self._running     = False
        self._thread      = None

        # state machine
        self._state: str  = "unknown"   # present | absent | distracted
        self._last_seen   = time.time()
        self._away_since: Optional[float] = None

        # Mediapipe face detector (lightweight model 0)
        self._detector = mp.solutions.face_detection.FaceDetection(
            model_selection=0, min_detection_confidence=0.5
        )
        # Advanced gaze detector (uses FaceMesh + iris when available)
        self._gaze_detector = None
        if _GazeDetector is not None:
            try:
                self._gaze_detector = _GazeDetector(use_iris=True)
                log.info("GazeDetector: using head-pose + iris tracking.")
            except Exception as e:
                log.warning(f"GazeDetector init failed, using basic fallback: {e}")

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True, name="presence-monitor")
        self._thread.start()
        log.info("Presence monitor started.")

    def stop(self):
        self._running = False
        self._detector.close()
        log.info("Presence monitor stopped.")

    def _loop(self):
        while self._running:
            frame = frame_slot.get(timeout=2.0)
            if frame is None:
                # No frame → treat as absent if it's been a while
                self._handle_no_frame()
                continue

            face_detected, looking_away = self._analyze_frame(frame)
            self._update_state(face_detected, looking_away)

            time.sleep(0.1)  # don't spin too fast

    def _analyze_frame(self, frame: np.ndarray) -> tuple[bool, bool]:
        """Returns (face_detected, looking_away). Uses GazeDetector when available."""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # ── primary path: GazeDetector (head pose + iris) ─────────────
        if self._gaze_detector is not None:
            result = self._gaze_detector.detect(rgb)
            if result is not None:
                return True, not result.looking_at_screen
            # GazeDetector returned None → face not found
            return False, False

        # ── fallback: basic face detection with center-x heuristic ────
        result = self._detector.process(rgb)
        if not result.detections:
            return False, False

        det    = result.detections[0]
        bbox   = det.location_data.relative_bounding_box
        face_cx = bbox.xmin + bbox.width / 2
        looking_away = not (0.2 < face_cx < 0.8)
        return True, looking_away

    def _handle_no_frame(self):
        # Stream down — if it's been a while, log as absent
        if time.time() - self._last_seen > config.ABSENCE_THRESHOLD:
            self._transition("absent")

    def _update_state(self, face_detected: bool, looking_away: bool):
        now = time.time()

        if not face_detected:
            # Start absence timer
            if self._away_since is None:
                self._away_since = now
            elif now - self._away_since > config.ABSENCE_THRESHOLD:
                self._transition("absent")
        else:
            self._last_seen  = now
            self._away_since = None

            if looking_away:
                if self._state != "distracted":
                    self._transition("distracted")
            else:
                if self._state != "present":
                    new_state = "returned" if self._state == "absent" else "present"
                    self._transition(new_state)
                    if new_state == "returned":
                        # After logging "returned", set state to "present"
                        self._state = "present"

    def _transition(self, new_state: str):
        if new_state == self._state:
            return

        old_state   = self._state
        self._state = new_state
        ts          = datetime.now()

        log.debug(f"CV state: {old_state} → {new_state}")

        # Write to DB
        self._log_event(new_state, ts)

        # Callback
        if self._on_event:
            self._on_event(new_state)

        # WebSocket broadcast
        if self._broadcast:
            self._broadcast({
                "type":    "cv_event",
                "event":   new_state,
                "ts":      ts.isoformat(),
                "user_id": self._user_id,
            })

    def _log_event(self, event_type: str, ts: datetime):
        try:
            with get_db_ctx() as db:
                db.add(CVEvent(
                    user_id      = self._user_id,
                    event_type   = event_type,
                    timestamp    = ts,
                    session_date = ts.date(),
                ))
        except Exception as e:
            log.error(f"CVEvent save error: {e}")
