from django.contrib import admin

from .models import StudySession, StudyTimer, Task, UserProjectLog, UserSkillProgress


@admin.register(UserSkillProgress)
class UserSkillProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "skill", "is_done", "completed_at")
    list_filter = ("is_done",)


@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):
    list_display = ("user", "label", "duration_minutes", "date", "created_at")
    list_filter = ("date",)
    search_fields = ("label", "user__username", "user__email")


@admin.register(StudyTimer)
class StudyTimerAdmin(admin.ModelAdmin):
    list_display = ("user", "label", "duration_minutes", "status", "start_at", "end_at")
    list_filter = ("status", "start_at", "end_at")
    search_fields = ("label", "user__username", "user__email")


@admin.register(UserProjectLog)
class UserProjectLogAdmin(admin.ModelAdmin):
    list_display = ("user", "project", "status", "submitted_at")
    list_filter = ("status",)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "is_completed", "target_date", "category", "created_at")
    list_filter = ("is_completed", "target_date", "category")
    search_fields = ("title", "description", "user__username", "user__email")
    date_hierarchy = "target_date"
