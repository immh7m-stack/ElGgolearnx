from django.contrib import admin

from .models import LearnerStats, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "preferred_lang", "github_url")


@admin.register(LearnerStats)
class LearnerStatsAdmin(admin.ModelAdmin):
    list_display = ("user", "total_skills_done", "total_projects_done", "current_level")
