from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Field, Track
from .serializers import FieldDetailSerializer, FieldListSerializer, TrackDetailSerializer, TrackListSerializer


class FieldListAPI(generics.ListAPIView):
    queryset = Field.objects.filter(is_active=True).prefetch_related("tracks")
    serializer_class = FieldListSerializer


class FieldDetailAPI(generics.RetrieveAPIView):
    queryset = Field.objects.filter(is_active=True).prefetch_related("tracks")
    serializer_class = FieldDetailSerializer
    lookup_field = "slug"


class TrackListAPI(generics.ListAPIView):
    serializer_class = TrackListSerializer

    def get_queryset(self):
        return Track.objects.filter(
            field__slug=self.kwargs["slug"], field__is_active=True
        ).select_related("field")


class TrackDetailAPI(generics.RetrieveAPIView):
    serializer_class = TrackDetailSerializer
    lookup_field = "career_level"
    lookup_url_kwarg = "level"

    def get_queryset(self):
        return Track.objects.filter(
            field__slug=self.kwargs["slug"], field__is_active=True
        ).prefetch_related("playlists", "modules__skills", "projects")
