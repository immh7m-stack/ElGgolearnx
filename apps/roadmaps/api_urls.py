from django.urls import path

from . import api_views

urlpatterns = [
    path("fields/", api_views.FieldListAPI.as_view(), name="api-fields"),
    path("fields/<slug:slug>/", api_views.FieldDetailAPI.as_view(), name="api-field-detail"),
    path("fields/<slug:slug>/tracks/", api_views.TrackListAPI.as_view(), name="api-tracks"),
    path("fields/<slug:slug>/tracks/<str:level>/", api_views.TrackDetailAPI.as_view(), name="api-track-detail"),
]
