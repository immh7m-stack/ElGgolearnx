from django.conf import settings
from django.db import models

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
