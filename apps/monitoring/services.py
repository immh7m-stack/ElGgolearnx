from datetime import datetime
from typing import Any, Dict, List, Optional

from .models import MonitoringTelemetryPoint, MonitoringSession


class MonitoringService:
    @staticmethod
    def build_summary(data: Dict[str, Any]) -> Dict[str, Any]:
        telemetry = data.get("telemetry", [])
        scores = [item.get("score", 0.0) for item in telemetry if isinstance(item, dict)]
        avg_focus_score = round(sum(scores) / len(scores), 1) if scores else 0.0
        total_distractions = sum(1 for item in telemetry if "Distracted" in str(item.get("state", "")) or "Drowsiness" in str(item.get("state", "")))
        return {
            "avg_focus_score": avg_focus_score,
            "total_distractions": total_distractions,
            "telemetry_points_count": len(telemetry),
        }

    @staticmethod
    def save_session(user, session_id: str, data: Dict[str, Any]) -> MonitoringSession:
        summary = MonitoringService.build_summary(data)
        session, _ = MonitoringSession.objects.update_or_create(
            user=user,
            session_id=session_id,
            defaults={
                "avg_focus_score": summary["avg_focus_score"],
                "total_distractions": summary["total_distractions"],
                "telemetry_points_count": summary["telemetry_points_count"],
                "status_key": data.get("status_key", "good"),
                "status": data.get("status", "active"),
            },
        )

        if telemetry := data.get("telemetry"):
            MonitoringTelemetryPoint.objects.filter(session=session).delete()
            points = []
            for item in telemetry:
                timestamp = item.get("timestamp")
                if isinstance(timestamp, str):
                    try:
                        timestamp = datetime.fromisoformat(timestamp)
                    except ValueError:
                        timestamp = datetime.now()
                points.append(MonitoringTelemetryPoint(
                    session=session,
                    timestamp=timestamp,
                    score=item.get("score", 0.0),
                    state=item.get("state", ""),
                ))
            MonitoringTelemetryPoint.objects.bulk_create(points)

        return session
