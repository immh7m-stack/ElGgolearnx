from django.conf import settings
from django.db import models


class MonitoringSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="monitoring_sessions")
    session_id = models.CharField(max_length=120)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    avg_focus_score = models.FloatField(default=0.0)
    total_distractions = models.PositiveIntegerField(default=0)
    telemetry_points_count = models.PositiveIntegerField(default=0)
    status_key = models.CharField(max_length=20, default="good")
    status = models.CharField(max_length=50, default="pending")

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.user} — monitoring session {self.session_id}"


class MonitoringTelemetryPoint(models.Model):
    session = models.ForeignKey(MonitoringSession, on_delete=models.CASCADE, related_name="telemetry_points")
    timestamp = models.DateTimeField()
    score = models.FloatField(default=0.0)
    state = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"session {self.session_id} — {self.score}%"
