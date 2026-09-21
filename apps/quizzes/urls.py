from django.urls import path, include

from . import views

app_name = "quizzes"

urlpatterns = [
    path("api/", include("apps.quizzes.api_urls")),
    path("exam/<str:video_id>/", views.exam_detail, name="exam_detail"),
]
