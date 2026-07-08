from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.urls import path
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class RegisterAPI(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip()
        password = request.data.get("password", "")
        if not email or not password:
            return Response({"error": "email and password required"}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(email=email).exists():
            return Response({"error": "email already registered"}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.create_user(username=email, email=email, password=password)
        login(request, user)
        return Response({"id": user.id, "email": user.email}, status=status.HTTP_201_CREATED)


class LoginAPI(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip()
        password = request.data.get("password", "")
        user = authenticate(request, username=email, password=password)
        if user is None:
            return Response({"error": "invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        login(request, user)
        return Response({"id": user.id, "email": user.email})


class LogoutAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"ok": True})


class MeAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = request.user.profile
        return Response({
            "id": request.user.id,
            "email": request.user.email,
            "bio": profile.bio,
            "github_url": profile.github_url,
            "preferred_lang": profile.preferred_lang,
        })


urlpatterns = [
    path("auth/register/", RegisterAPI.as_view(), name="api-register"),
    path("auth/login/", LoginAPI.as_view(), name="api-login"),
    path("auth/logout/", LogoutAPI.as_view(), name="api-logout"),
    path("auth/me/", MeAPI.as_view(), name="api-me"),
]
