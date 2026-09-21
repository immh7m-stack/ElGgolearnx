from datetime import date

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.roadmaps.models import Project, Skill


class UserSkillProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="skill_progress")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="user_progress")
    is_done = models.BooleanField(default=False)
    score = models.PositiveSmallIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("user", "skill")]

    def __str__(self):
        return f"{self.user} — {self.skill}"


class StudySession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="study_sessions")
    label = models.CharField(max_length=200, blank=True)
    duration_minutes = models.PositiveIntegerField(default=25)
    date = models.DateField(default=date.today)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} — {self.duration_minutes}m ({self.date})"


class StudyTimer(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("finished", "Finished"),
        ("cancelled", "Cancelled"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="study_timers")
    label = models.CharField(max_length=200, blank=True)
    duration_minutes = models.PositiveIntegerField(default=25)
    start_at = models.DateTimeField(auto_now_add=True)
    end_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    finished_at = models.DateTimeField(null=True, blank=True)
    session_created = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} — timer {self.duration_minutes}m ({self.status})"

    def remaining_seconds(self):
        return max(0, int((self.end_at - timezone.now()).total_seconds()))

    def finalize(self):
        if self.status != "active":
            return
        if timezone.now() < self.end_at:
            return
        self.status = "finished"
        self.finished_at = timezone.now()
        if not self.session_created:
            StudySession.objects.create(
                user=self.user,
                label=self.label,
                duration_minutes=self.duration_minutes,
                date=self.finished_at.date(),
            )
            self.session_created = True
        self.save()

    def cancel(self):
        if self.status != "active":
            return
        self.status = "cancelled"
        self.save()


class FocusSession(models.Model):
    STATUS_CHOICES = [
        ("excellent", "Excellent"),
        ("good", "Good"),
        ("warning", "Warning"),
        ("critical", "Critical"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="focus_sessions")
    session_id = models.PositiveIntegerField(default=0)
    avg_focus_score = models.FloatField(default=0.0)
    total_distractions = models.PositiveIntegerField(default=0)
    duration_seconds = models.PositiveIntegerField(default=0)
    telemetry_points_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="good")
    status_key = models.CharField(max_length=20, default="good")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} — {self.avg_focus_score}%"


class FocusTelemetryPoint(models.Model):
    session = models.ForeignKey(FocusSession, on_delete=models.CASCADE, related_name="telemetry_points")
    score = models.FloatField(default=0.0)
    state = models.CharField(max_length=200, blank=True)
    timestamp = models.DateTimeField()

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"{self.session_id} — {self.score}"


class UserProjectLog(models.Model):
    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("verified", "Verified"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_logs")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="submissions")
    github_url = models.URLField(max_length=500)
    live_url = models.URLField(max_length=500, blank=True)
    reflection = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="submitted")
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} — {self.project}"


class Task(models.Model):
    """مهام يومية من ElGoPlan — متصلة بقاعدة البيانات."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    target_date = models.DateField(null=True, blank=True, help_text="تاريخ استحقاق المهمة")
    mood = models.PositiveSmallIntegerField(default=2, choices=[(0, '😞'), (1, '😐'), (2, '🙂'), (3, '😊'), (4, '🌟')])
    category = models.CharField(max_length=100, blank=True, default="عام")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Tasks"

    def __str__(self):
        return f"{self.user} — {self.title}"

    def mark_completed(self):
        self.is_completed = True
        self.completed_at = timezone.now()
        self.save()
