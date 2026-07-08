from django.contrib import admin

from .models import UserProjectLog, UserSkillProgress


@admin.register(UserSkillProgress)
class UserSkillProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "skill", "is_done", "completed_at")
    list_filter = ("is_done",)


@admin.register(UserProjectLog)
class UserProjectLogAdmin(admin.ModelAdmin):
    list_display = ("user", "project", "status", "submitted_at")
    list_filter = ("status",)
