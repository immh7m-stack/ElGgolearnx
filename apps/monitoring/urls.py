from django.urls import path

from . import views

app_name = "monitoring"

urlpatterns = [
    path("dashboard/", views.monitoring_dashboard, name="dashboard"),
    path("analyze/", views.analyze_focus, name="analyze_focus"),
]
