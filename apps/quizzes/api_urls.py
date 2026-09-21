from django.urls import path
from apps.quizzes.views import FetchOrGenerateQuizView, SubmitQuizView

app_name = "quizzes_api"

urlpatterns = [
    path("fetch-or-generate/", FetchOrGenerateQuizView.as_view(), name="fetch_or_generate"),
    path("submit/", SubmitQuizView.as_view(), name="submit"),
]
