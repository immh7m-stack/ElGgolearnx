"""
detector.py — ElGolearn Attention Engine v5 (Occlusion Protection & Calibrated Drowsiness)
Pipeline:
    MediaPipe FaceLandmarker → Landmarks (478 pts incl. iris)
    ├── Head Pose   : solvePnP → arcsin/arctan2 → EMA → gaze direction
    ├── EAR + Occlusion Protection : Both eyes valid & closed (< 0.18) > 30 frames → is_drowsy
    ├── Iris Gaze   : iris offset relative to eye corners → eye gaze distraction
    └── Focus Score : Progressive Lerp (factor = 0.015) with smooth recovery
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional, Tuple

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    FaceLandmarker,
    FaceLandmarkerOptions,
    FaceLandmarkerResult,
    RunningMode,
)

# ─── 3D Model Points (Head Pose) ─────────────────────────────────────────────
_MODEL_POINTS_3D = np.array([
    (  0.0,    0.0,    0.0),    # 1   — Nose tip
    (  0.0, -330.0,  -65.0),    # 152 — Chin
    (-225.0,  170.0, -135.0),   # 33  — Left eye outer
    ( 225.0,  170.0, -135.0),   # 263 — Right eye outer
    (-150.0, -150.0, -125.0),   # 61  — Left mouth corner
    ( 150.0, -150.0, -125.0),   # 291 — Right mouth corner
], dtype=np.float64)

_HEAD_INDICES = [1, 152, 33, 263, 61, 291]
_DIST_COEFFS  = np.zeros((4, 1), dtype=np.float64)

# ─── Eye Landmark Indices ───────────────────────────────────────────────────
_LEFT_EYE_IDX  = [362, 385, 387, 263, 373, 380]
_RIGHT_EYE_IDX = [33,  160, 158, 133, 153, 144]

# ─── Iris Landmark Indices ──────────────────────────────────────────────────
_LEFT_IRIS_CENTER  = 468
_RIGHT_IRIS_CENTER = 473
_LEFT_EYE_OUTER    = 33
_LEFT_EYE_INNER    = 133
_RIGHT_EYE_INNER   = 362
_RIGHT_EYE_OUTER   = 263

# ─── Calibration Constants ───────────────────────────────────────────────────
EMA_ALPHA           = 0.25
EMA_EAR_ALPHA       = 0.65

YAW_THRESHOLD_DEG   = 20.0
PITCH_THRESHOLD_DEG = 15.0

EAR_THRESHOLD       = 0.18    # Both eyes EAR < 0.18 = closed
DROWSY_FRAME_LIMIT  = 10      # Continuous 10 frames (~0.8 - 1.0 sec)

IRIS_OFFSET_LOW     = 0.35
IRIS_OFFSET_HIGH    = 0.65
IRIS_LANDMARKS_COUNT = 478

_SCORE_LERP_FOCUSED = 0.015
_SCORE_LERP_AWAY    = 0.015
_SCORE_LERP_DROWSY  = 0.04
_SCORE_IDLE_DECAY   = 0.30


@dataclass
class PoseData:
    """Structured telemetry metadata produced per frame."""
    yaw:             float
    pitch:           float
    roll:            float
    is_focused:      bool
    gaze_direction:  str
    focus_score:     float
    nose_tip_2d:     Tuple[int, int]
    nose_end_2d:     Tuple[int, int]
    ear:             float
    is_drowsy:       bool
    iris_distracted: bool
    iris_direction:  str


class FaceFocusDetector:
    """
    ElGolearn Focus Detector with Hand Occlusion Protection & Calibrated Drowsiness.
    """

    MODEL_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "face_landmarker.task"
    )

    def __init__(self, max_num_faces: int = 1) -> None:
        if not os.path.isfile(self.MODEL_PATH):
            raise FileNotFoundError(
                f"❌ Model file missing: {self.MODEL_PATH}"
            )

        options = FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=self.MODEL_PATH),
            running_mode=RunningMode.IMAGE,
            num_faces=max_num_faces,
            min_face_detection_confidence=0.3,
            min_face_presence_confidence=0.3,
            min_tracking_confidence=0.3,
        )
        self.landmarker = FaceLandmarker.create_from_options(options)

        # Internal EMA state
        self._ema_yaw:    float = 0.0
        self._ema_pitch:  float = 0.0
        self._ema_roll:   float = 0.0
        self._ema_nose_x: float = 0.0
        self._ema_nose_y: float = 0.0
        self._initialized: bool = False

        # Internal EAR state
        self._ema_ear_l:       float = 0.30
        self._ema_ear_r:       float = 0.30
        self._ear_initialized: bool  = False
        self._drowsy_counter:  int   = 0

        # Focus Score
        self._focus_score: float = 50.0

    def process_frame(
        self, frame: np.ndarray
    ) -> Tuple[Any, Optional[PoseData]]:
        h, w = frame.shape[:2]
        rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self.landmarker.detect(mp_img)

        if not result.face_landmarks:
            # Face not detected / heavily occluded -> reset counter & decay score slowly
            self._focus_score    = max(0.0, self._focus_score - _SCORE_IDLE_DECAY)
            self._drowsy_counter = 0
            return result, None

        lm = result.face_landmarks[0]

        # 1. Head Pose
        pose = self._estimate_head_pose(lm, w, h)

        # 2. Check for occlusion & compute EAR
        eye_occluded, ear_l_raw, ear_r_raw = self._compute_validated_ear(lm, w, h)

        if eye_occluded:
            # Hand on face or eye region occluded / landmark anomaly detected
            # Do NOT trigger drowsiness false alarms; reset counter!
            self._drowsy_counter = 0
            is_drowsy = False
            ear_avg   = 0.0
        else:
            ear_l, ear_r = self._smooth_ear_both(ear_l_raw, ear_r_raw)
            ear_avg      = (ear_l + ear_r) / 2.0
            is_drowsy    = self._update_drowsy_counter(ear_l, ear_r)

        # 3. Iris Gaze Direction
        iris_distracted, iris_direction = self._compute_iris_gaze(lm, w)

        # 4. Final Focus Evaluation
        if pose.is_focused and iris_distracted:
            final_gaze    = iris_direction
            final_focused = False
        else:
            final_gaze    = pose.gaze_direction
            final_focused = pose.is_focused

        pose.gaze_direction  = final_gaze
        pose.is_focused      = final_focused
        pose.ear             = round(ear_avg, 3)
        pose.is_drowsy       = is_drowsy
        pose.iris_distracted = iris_distracted
        pose.iris_direction  = iris_direction

        # 5. Focus Score Lerp Update (Smooth recovery when eyes reopen)
        self._update_focus_score(final_focused, is_drowsy)
        pose.focus_score = round(self._focus_score, 1)

        return result, pose

    def _compute_validated_ear(
        self, landmarks, w: int, h: int
    ) -> Tuple[bool, float, float]:
        """
        Occlusion & Validity Check:
        Verifies that eye landmarks are present, reasonably shaped, and not distorted
        by hand-on-face or partial blocking.
        Returns: (is_occluded: bool, ear_left: float, ear_right: float)
        """
        try:
            if len(landmarks) < max(_LEFT_EYE_IDX + _RIGHT_EYE_IDX):
                return True, 0.0, 0.0

            ear_l = self._compute_ear_single(landmarks, _LEFT_EYE_IDX, w, h)
            ear_r = self._compute_ear_single(landmarks, _RIGHT_EYE_IDX, w, h)

            pts_l = [(landmarks[i].x * w, landmarks[i].y * h) for i in _LEFT_EYE_IDX]
            pts_r = [(landmarks[i].x * w, landmarks[i].y * h) for i in _RIGHT_EYE_IDX]

            w_l = self._euclidean(pts_l[0], pts_l[3])
            w_r = self._euclidean(pts_r[0], pts_r[3])

            # Anomaly check: Eye width too small (< 5px) or EAR abnormally high (> 0.6) suggests bad detection/occlusion
            if w_l < 5.0 or w_r < 5.0 or ear_l > 0.60 or ear_r > 0.60:
                return True, 0.0, 0.0

            return False, ear_l, ear_r

        except Exception:
            return True, 0.0, 0.0

    # ── Head Pose Estimation ────────────────────────────────────────────────
    def _estimate_head_pose(self, landmarks, img_w: int, img_h: int) -> PoseData:
        pts2d = np.array(
            [(landmarks[i].x * img_w, landmarks[i].y * img_h)
             for i in _HEAD_INDICES],
            dtype=np.float64,
        )

        fl  = float(img_w)
        cx, cy = img_w / 2.0, img_h / 2.0
        cam_mat = np.array(
            [[fl, 0.0, cx],
             [0.0, fl,  cy],
             [0.0, 0.0, 1.0]],
            dtype=np.float64,
        )

        _, rvec, tvec = cv2.solvePnP(
            _MODEL_POINTS_3D, pts2d, cam_mat, _DIST_COEFFS,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )

        rmat, _ = cv2.Rodrigues(rvec)
        pitch_raw = np.degrees(np.arcsin(np.clip(-rmat[2, 0], -1.0, 1.0)))
        yaw_raw   = np.degrees(np.arctan2(rmat[1, 0], rmat[0, 0]))
        roll_raw  = np.degrees(np.arctan2(rmat[2, 1], rmat[2, 2]))

        if not self._initialized:
            self._ema_yaw, self._ema_pitch, self._ema_roll = (
                yaw_raw, pitch_raw, roll_raw
            )
            self._initialized = True
        else:
            self._ema_yaw   = EMA_ALPHA * yaw_raw   + (1 - EMA_ALPHA) * self._ema_yaw
            self._ema_pitch = EMA_ALPHA * pitch_raw + (1 - EMA_ALPHA) * self._ema_pitch
            self._ema_roll  = EMA_ALPHA * roll_raw  + (1 - EMA_ALPHA) * self._ema_roll

        if self._ema_roll > 90.0:
            self._ema_roll -= 180.0
        elif self._ema_roll < -90.0:
            self._ema_roll += 180.0

        nose_tip = (int(pts2d[0][0]), int(pts2d[0][1]))
        nose_proj, _ = cv2.projectPoints(
            np.array([(0.0, 0.0, 400.0)], dtype=np.float64),
            rvec, tvec, cam_mat, _DIST_COEFFS,
        )
        nx, ny = float(nose_proj[0][0][0]), float(nose_proj[0][0][1])
        self._ema_nose_x = EMA_ALPHA * nx + (1 - EMA_ALPHA) * self._ema_nose_x
        self._ema_nose_y = EMA_ALPHA * ny + (1 - EMA_ALPHA) * self._ema_nose_y

        is_focused, gaze = self._evaluate_focus(self._ema_yaw, self._ema_pitch)

        return PoseData(
            yaw=round(self._ema_yaw, 1),
            pitch=round(self._ema_pitch, 1),
            roll=round(self._ema_roll, 1),
            is_focused=is_focused,
            gaze_direction=gaze,
            focus_score=self._focus_score,
            nose_tip_2d=nose_tip,
            nose_end_2d=(int(self._ema_nose_x), int(self._ema_nose_y)),
            ear=0.0,
            is_drowsy=False,
            iris_distracted=False,
            iris_direction="",
        )

    # ── EAR Math & Smoothing ────────────────────────────────────────────────
    @staticmethod
    def _euclidean(p1, p2) -> float:
        return float(np.linalg.norm(np.array(p1) - np.array(p2)))

    def _compute_ear_single(
        self, landmarks, indices: list, w: int, h: int
    ) -> float:
        pts = [(landmarks[i].x * w, landmarks[i].y * h) for i in indices]
        p1, p2, p3, p4, p5, p6 = pts
        v1 = self._euclidean(p2, p6)
        v2 = self._euclidean(p3, p5)
        hd = self._euclidean(p1, p4)
        return (v1 + v2) / (2.0 * hd) if hd > 1e-6 else 0.0

    def _smooth_ear_both(
        self, ear_l: float, ear_r: float
    ) -> Tuple[float, float]:
        if not self._ear_initialized:
            self._ema_ear_l = ear_l
            self._ema_ear_r = ear_r
            self._ear_initialized = True
        else:
            self._ema_ear_l = EMA_EAR_ALPHA * ear_l + (1 - EMA_EAR_ALPHA) * self._ema_ear_l
            self._ema_ear_r = EMA_EAR_ALPHA * ear_r + (1 - EMA_EAR_ALPHA) * self._ema_ear_r
        return self._ema_ear_l, self._ema_ear_r

    def _update_drowsy_counter(self, ear_l: float, ear_r: float) -> bool:
        """
        Drowsiness state machine:
        Requires BOTH eyes < EAR_THRESHOLD (0.18) continuously for > 30 frames.
        Re-opening eyes immediately resets counter and initiates smooth Lerp recovery.
        """
        both_closed = (ear_l < EAR_THRESHOLD) and (ear_r < EAR_THRESHOLD)

        if both_closed:
            self._drowsy_counter += 1
        else:
            self._drowsy_counter = 0

        return self._drowsy_counter > DROWSY_FRAME_LIMIT

    # ── Iris Gaze Tracking ──────────────────────────────────────────────────
    def _compute_iris_gaze(
        self, landmarks, img_w: int
    ) -> Tuple[bool, str]:
        try:
            if len(landmarks) < IRIS_LANDMARKS_COUNT:
                return False, ""

            iris_lx   = landmarks[_LEFT_IRIS_CENTER].x  * img_w
            l_outer_x = landmarks[_LEFT_EYE_OUTER].x    * img_w
            l_inner_x = landmarks[_LEFT_EYE_INNER].x    * img_w
            l_min_x   = min(l_outer_x, l_inner_x)
            l_width   = abs(l_inner_x - l_outer_x)
            offset_l  = (iris_lx - l_min_x) / l_width if l_width > 1e-6 else 0.5

            iris_rx   = landmarks[_RIGHT_IRIS_CENTER].x * img_w
            r_inner_x = landmarks[_RIGHT_EYE_INNER].x  * img_w
            r_outer_x = landmarks[_RIGHT_EYE_OUTER].x  * img_w
            r_min_x   = min(r_inner_x, r_outer_x)
            r_width   = abs(r_outer_x - r_inner_x)
            offset_r  = (iris_rx - r_min_x) / r_width if r_width > 1e-6 else 0.5

            avg_offset = (offset_l + offset_r) / 2.0

            if avg_offset < IRIS_OFFSET_LOW:
                return True, "Eye Gaze: Left"
            if avg_offset > IRIS_OFFSET_HIGH:
                return True, "Eye Gaze: Right"

            return False, ""

        except (IndexError, ZeroDivisionError):
            return False, ""

    # ── Focus Score Lerp Update ─────────────────────────────────────────────
    def _update_focus_score(self, is_focused: bool, is_drowsy: bool) -> None:
        """
        Progressive Ease-In/Ease-Out Lerp curve (factor = 0.015).
        Smooth recovery when eyes reopen.
        """
        if is_drowsy:
            target = 0.0
            factor = _SCORE_LERP_DROWSY
        elif is_focused:
            target = 100.0
            factor = _SCORE_LERP_FOCUSED
        else:
            target = 0.0
            factor = _SCORE_LERP_AWAY

        self._focus_score += (target - self._focus_score) * factor
        self._focus_score  = max(0.0, min(100.0, self._focus_score))

    @staticmethod
    def _evaluate_focus(yaw: float, pitch: float) -> Tuple[bool, str]:
        if abs(yaw) > YAW_THRESHOLD_DEG:
            return False, ("Looking Left" if yaw < 0 else "Looking Right")
        if pitch > PITCH_THRESHOLD_DEG:
            return False, "Looking Up"
        if pitch < -PITCH_THRESHOLD_DEG:
            return False, "Looking Down / Phone"
        return True, "Facing Screen"

    def close(self) -> None:
        self.landmarker.close()
