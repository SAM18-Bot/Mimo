"""
focus_detector.py — Gaze / head-pose estimation using Mediapipe FaceMesh.

Extracted from presence.py so it can be tested and tuned independently.

Algorithm:
  1. Run FaceMesh (468 landmarks) on each frame
  2. Solve PnP (2D→3D) with 6 canonical face points → get rotation vector
  3. Convert rotation to Euler angles (yaw / pitch / roll)
  4. If |yaw| > YAW_THRESHOLD or |pitch| > PITCH_THRESHOLD → looking away
  5. Secondary check: iris horizontal position relative to eye corners

Returns GazeResult with: looking_at_screen, confidence, direction label.

Falls back gracefully if FaceMesh landmarks are unavailable (low-res frame, partial face).
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np

log = logging.getLogger(__name__)

# ── gaze thresholds ───────────────────────────────────────────────────────
YAW_THRESHOLD   = 25.0   # degrees left/right before "looking away"
PITCH_THRESHOLD = 20.0   # degrees up/down before "looking away"

# Mediapipe FaceMesh landmark indices used for 6-point head pose
# Chosen for visibility stability across head orientations
_POSE_POINTS_IDX = [1, 152, 33, 263, 61, 291]   # nose, chin, L-eye, R-eye, L-mouth, R-mouth

# Approximate 3D positions of the same landmarks in a canonical face (mm)
_MODEL_3D = np.array([
    [0.0,    0.0,    0.0],    # nose tip
    [0.0,  -330.0, -65.0],    # chin
    [-225.0, 170.0, -135.0],  # left eye corner
    [225.0,  170.0, -135.0],  # right eye corner
    [-150.0, -150.0, -125.0], # left mouth corner
    [150.0,  -150.0, -125.0], # right mouth corner
], dtype=np.float64)

# Iris landmark indices (FaceMesh with iris enabled)
_L_IRIS_CENTER = 468
_R_IRIS_CENTER = 473
_L_EYE_LEFT    = 33
_L_EYE_RIGHT   = 133
_R_EYE_LEFT    = 362
_R_EYE_RIGHT   = 263


@dataclass
class GazeResult:
    looking_at_screen: bool
    confidence:        float          # 0.0–1.0
    direction:         str            # "center" | "left" | "right" | "up" | "down" | "away"
    yaw_deg:           float = 0.0
    pitch_deg:         float = 0.0
    method:            str   = "pose" # "pose" | "iris" | "fallback"

    @property
    def label(self) -> str:
        if self.looking_at_screen:
            return "focused"
        return f"looking {self.direction}"


class GazeDetector:
    """
    Per-frame gaze estimator. Create once, call detect() on each frame.
    Thread-safe (no mutable state between calls).
    """

    def __init__(self, use_iris: bool = True):
        """
        use_iris: also use iris tracking for secondary confirmation.
        Disable if running on CPU-only hardware (iris adds ~5ms).
        """
        self._use_iris = use_iris
        self._face_mesh = None
        self._init_mesh()

    def _init_mesh(self):
        try:
            import mediapipe as mp
            self._face_mesh = mp.solutions.face_mesh.FaceMesh(
                max_num_faces       = 1,
                refine_landmarks    = self._use_iris,  # enables iris landmarks (468+)
                min_detection_confidence = 0.5,
                min_tracking_confidence  = 0.5,
            )
            log.debug("GazeDetector: FaceMesh initialised (iris=%s)", self._use_iris)
        except ImportError:
            log.warning("mediapipe not installed — GazeDetector disabled")

    def detect(self, frame_rgb: np.ndarray) -> Optional[GazeResult]:
        """
        Analyse one RGB frame. Returns GazeResult or None if no face found.
        frame_rgb must be np.ndarray shape (H, W, 3) dtype uint8.
        """
        if self._face_mesh is None:
            return None

        h, w = frame_rgb.shape[:2]
        result = self._face_mesh.process(frame_rgb)

        if not result.multi_face_landmarks:
            return None

        lm = result.multi_face_landmarks[0].landmark
        pts = [(int(l.x * w), int(l.y * h)) for l in lm]

        # ── primary: head-pose PnP ────────────────────────────────────────
        pose_result = self._head_pose(pts, w, h)

        # ── secondary: iris check ─────────────────────────────────────────
        if self._use_iris and len(lm) > _R_IRIS_CENTER:
            iris_result = self._iris_check(pts)
        else:
            iris_result = None

        # ── fuse results ──────────────────────────────────────────────────
        return self._fuse(pose_result, iris_result)

    # ── head pose via PnP ─────────────────────────────────────────────────

    def _head_pose(
        self, pts: list, img_w: int, img_h: int
    ) -> Optional[GazeResult]:
        try:
            image_pts = np.array(
                [pts[i] for i in _POSE_POINTS_IDX], dtype=np.float64
            )
            focal   = img_w  # rough focal length approximation
            cx, cy  = img_w / 2.0, img_h / 2.0
            cam_mat = np.array(
                [[focal, 0, cx], [0, focal, cy], [0, 0, 1]], dtype=np.float64
            )
            dist    = np.zeros((4, 1))

            ok, rvec, tvec = cv_solvePnP(
                _MODEL_3D, image_pts, cam_mat, dist
            )
            if not ok:
                return None

            rmat, _ = cv_Rodrigues(rvec)
            angles  = _rotation_to_euler(rmat)  # yaw, pitch, roll in degrees

            yaw, pitch = angles[0], angles[1]
            looking    = abs(yaw) < YAW_THRESHOLD and abs(pitch) < PITCH_THRESHOLD

            direction = _angle_to_direction(yaw, pitch)
            conf      = _confidence_from_angles(yaw, pitch)

            return GazeResult(
                looking_at_screen = looking,
                confidence        = conf,
                direction         = direction,
                yaw_deg           = round(yaw, 1),
                pitch_deg         = round(pitch, 1),
                method            = "pose",
            )
        except Exception as e:
            log.debug("Head pose estimation failed: %s", e)
            return None

    # ── iris position check ────────────────────────────────────────────────

    def _iris_check(self, pts: list) -> Optional[GazeResult]:
        """
        Estimate gaze direction from iris position within eye socket.
        If iris is centered within the eye → looking forward.
        """
        try:
            def _ratio(iris_x, left_x, right_x) -> float:
                span = right_x - left_x
                if span < 1:
                    return 0.5
                return (iris_x - left_x) / span  # 0=far left, 1=far right, 0.5=center

            l_ratio = _ratio(
                pts[_L_IRIS_CENTER][0],
                pts[_L_EYE_LEFT][0],
                pts[_L_EYE_RIGHT][0],
            )
            r_ratio = _ratio(
                pts[_R_IRIS_CENTER][0],
                pts[_R_EYE_LEFT][0],
                pts[_R_EYE_RIGHT][0],
            )
            avg = (l_ratio + r_ratio) / 2.0
            # 0.35–0.65 is considered "center"
            looking = 0.30 <= avg <= 0.70
            direction = "center" if looking else ("left" if avg < 0.30 else "right")
            conf = 1.0 - abs(avg - 0.5) * 2.0  # 1.0 at center, 0.0 at extremes

            return GazeResult(
                looking_at_screen = looking,
                confidence        = round(conf, 2),
                direction         = direction,
                method            = "iris",
            )
        except Exception as e:
            log.debug("Iris check failed: %s", e)
            return None

    # ── fusion ─────────────────────────────────────────────────────────────

    def _fuse(
        self,
        pose: Optional[GazeResult],
        iris: Optional[GazeResult],
    ) -> GazeResult:
        if pose is None and iris is None:
            return GazeResult(
                looking_at_screen=True, confidence=0.3,
                direction="unknown", method="fallback"
            )
        if pose is None:
            return iris
        if iris is None:
            return pose

        # Both available: weighted average of confidence, majority vote on looking
        votes_looking = sum([
            pose.looking_at_screen,
            iris.looking_at_screen,
        ])
        looking = votes_looking >= 1   # at least one says looking
        conf    = (pose.confidence * 0.6 + iris.confidence * 0.4)

        return GazeResult(
            looking_at_screen = looking,
            confidence        = round(conf, 2),
            direction         = pose.direction,   # pose gives better direction
            yaw_deg           = pose.yaw_deg,
            pitch_deg         = pose.pitch_deg,
            method            = "pose+iris",
        )

    def close(self):
        if self._face_mesh:
            self._face_mesh.close()


# ── math helpers ─────────────────────────────────────────────────────────

def _rotation_to_euler(R: np.ndarray) -> Tuple[float, float, float]:
    """Convert 3×3 rotation matrix to (yaw, pitch, roll) degrees."""
    sy = math.sqrt(R[0, 0] ** 2 + R[1, 0] ** 2)
    singular = sy < 1e-6

    if not singular:
        pitch = math.degrees(math.atan2( R[2, 1], R[2, 2]))
        yaw   = math.degrees(math.atan2(-R[2, 0], sy))
        roll  = math.degrees(math.atan2( R[1, 0], R[0, 0]))
    else:
        pitch = math.degrees(math.atan2(-R[1, 2], R[1, 1]))
        yaw   = math.degrees(math.atan2(-R[2, 0], sy))
        roll  = 0.0

    return yaw, pitch, roll


def _angle_to_direction(yaw: float, pitch: float) -> str:
    if abs(yaw) <= YAW_THRESHOLD and abs(pitch) <= PITCH_THRESHOLD:
        return "center"
    if abs(yaw) > abs(pitch):
        return "left" if yaw < 0 else "right"
    return "up" if pitch < 0 else "down"


def _confidence_from_angles(yaw: float, pitch: float) -> float:
    yaw_conf   = max(0.0, 1.0 - abs(yaw)   / (YAW_THRESHOLD   * 2))
    pitch_conf = max(0.0, 1.0 - abs(pitch) / (PITCH_THRESHOLD * 2))
    return round((yaw_conf + pitch_conf) / 2.0, 2)


# ── lazy OpenCV imports (avoids hard dependency at module level) ──────────

def cv_solvePnP(obj_pts, img_pts, cam, dist):
    import cv2
    return cv2.solvePnP(obj_pts, img_pts, cam, dist)


def cv_Rodrigues(rvec):
    import cv2
    return cv2.Rodrigues(rvec)
