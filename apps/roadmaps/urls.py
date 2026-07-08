from django.urls import path

from . import views

app_name = "roadmaps"

urlpatterns = [
    path("", views.fields_list, name="fields"),
    path("<slug:slug>/<str:level>/", views.track_detail, name="track"),
    path("<slug:slug>/<str:level>/module/<int:order>/", views.module_detail, name="module"),
    path("<slug:slug>/<str:level>/watch/", views.watch_playlist, name="watch"),
]
