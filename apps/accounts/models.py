from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    bio = models.TextField(blank=True)
    github_url = models.URLField(max_length=200, blank=True)
    linkedin_url = models.URLField(max_length=200, blank=True)
    avatar_url = models.URLField(max_length=500, blank=True)
    preferred_lang = models.CharField(max_length=10, default="ar", choices=[("ar", "العربية"), ("en", "English")])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.get_username()


class LearnerStats(models.Model):
    LEVEL_CHOICES = [
        ("junior", "Junior"),
        ("mid", "Mid"),
        ("senior", "Senior"),
    ]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="learner_stats")
    total_skills_done = models.PositiveIntegerField(default=0)
    total_projects_done = models.PositiveIntegerField(default=0)
    current_level = models.CharField(max_length=20, choices=LEVEL_CHOICES, blank=True)
    current_field_slug = models.CharField(max_length=100, blank=True)
    streak_days = models.PositiveIntegerField(default=0)
    last_active = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Stats: {self.user.get_username()}"
