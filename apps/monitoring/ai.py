import base64
import cv2
import numpy as np

from .detector_adapter import FaceFocusDetectorAdapter


class FocusAnalyzer:
    def __init__(self):
        self.detector = FaceFocusDetectorAdapter()

    def analyze_base64(self, image_base64: str) -> dict:
        if image_base64.startswith("data:"):
            header, image_base64 = image_base64.split(",", 1)
        image_bytes = base64.b64decode(image_base64)
        np_arr = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if image is None:
            return {"score": 0.0, "state": "invalid_image", "is_focused": False}

        _, pose = self.detector.process_frame(image)
        if pose is None:
            return {"score": 0.0, "state": "no_face", "is_focused": False}

        state = "Focused"
        if pose.is_drowsy:
            state = "Drowsiness Detected"
        elif pose.iris_distracted:
            state = f"Distracted - {pose.iris_direction}"
        elif not pose.is_focused:
            state = f"Distracted - {pose.gaze_direction}"

        return {
            "score": round(pose.focus_score, 1),
            "state": state,
            "is_focused": pose.is_focused,
            "is_drowsy": pose.is_drowsy,
            "iris_distracted": pose.iris_distracted,
            "gaze_direction": pose.gaze_direction,
            "timestamp": None,
        }
