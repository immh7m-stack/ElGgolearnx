from django.urls import path

from . import views

app_name = "progress"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("skill/<int:skill_id>/toggle/", views.toggle_skill, name="toggle_skill"),
    path("project/<int:project_id>/submit/", views.submit_project, name="submit_project"),
]
