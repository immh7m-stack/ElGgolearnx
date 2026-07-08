from django.urls import path

from . import api_views

urlpatterns = [
    path("progress/skill/<int:skill_id>/", api_views.ToggleSkillAPI.as_view(), name="api-toggle-skill"),
    path("progress/project/", api_views.SubmitProjectAPI.as_view(), name="api-submit-project"),
    path("progress/dashboard/", api_views.DashboardAPI.as_view(), name="api-dashboard"),
    path("progress/<slug:field_slug>/stats/", api_views.FieldStatsAPI.as_view(), name="api-field-stats"),
]
