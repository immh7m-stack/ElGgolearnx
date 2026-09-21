from django.urls import path

from . import api_views

urlpatterns = [
    path("progress/skill/<int:skill_id>/", api_views.ToggleSkillAPI.as_view(), name="api-toggle-skill"),
    path("progress/project/", api_views.SubmitProjectAPI.as_view(), name="api-submit-project"),
    path("progress/study-session/", api_views.StudySessionAPI.as_view(), name="api-study-session"),
    path("progress/study-timer/", api_views.StudyTimerAPI.as_view(), name="api-study-timer"),
    path("progress/study-timer/finish/", api_views.StudyTimerFinishAPI.as_view(), name="api-study-timer-finish"),
    path("progress/study-timer/cancel/", api_views.StudyTimerCancelAPI.as_view(), name="api-study-timer-cancel"),
    path("progress/dashboard/", api_views.DashboardAPI.as_view(), name="api-dashboard"),
    path("progress/focus-analysis/", api_views.FocusAnalysisAPI.as_view(), name="api-focus-analysis"),
    path("progress/focus-sessions/", api_views.FocusSessionAPI.as_view(), name="api-focus-sessions"),
    path("progress/<slug:field_slug>/stats/", api_views.FieldStatsAPI.as_view(), name="api-field-stats"),
    path("plan/tasks/", api_views.TaskListAPI.as_view(), name="api-tasks-list"),
    path("plan/tasks/<int:task_id>/", api_views.TaskDetailAPI.as_view(), name="api-task-detail"),
    path("plan/tasks/<int:task_id>/toggle/", api_views.TaskToggleAPI.as_view(), name="api-task-toggle"),
    path("plan/tasks/stats/", api_views.TaskStatsAPI.as_view(), name="api-tasks-stats"),
]
