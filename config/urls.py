from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("", TemplateView.as_view(template_name="splash/splash.html"), name="splash"),
    path("accounts/", include("apps.accounts.urls")),
    path("fields/", include("apps.roadmaps.urls")),
    path("library/", include("apps.library.urls")),
    path("dashboard/", include("apps.progress.urls")),
    path("plan/", include("apps.planner.urls")),
    path("api/", include("apps.roadmaps.api_urls")),
    path("api/", include("apps.progress.api_urls")),
    path("api/", include("apps.chatbot.api_urls")),
    path("api/", include("apps.accounts.api_urls")),
    path("api/", include("apps.quizzes.api_urls")),
    path("quizzes/", include("apps.quizzes.urls")),
    path("monitoring/", include("apps.monitoring.urls")),
    path("home/", TemplateView.as_view(template_name="pages/home.html"), name="home"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
