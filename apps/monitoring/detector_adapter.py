from __future__ import annotations

from typing import Any, Optional, Tuple

from apps.monitoring.engine.detector import FaceFocusDetector


class FaceFocusDetectorAdapter:
    def __init__(self):
        self.detector = FaceFocusDetector(max_num_faces=1)

    def process_frame(self, frame: Any) -> Tuple[Optional[object], Optional[object]]:
        return self.detector.process_frame(frame)
