import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
# Load .env first; optional api.env only fills vars not already set (avoid wiping keys).
load_dotenv(BASE_DIR / ".env", override=True)
load_dotenv(BASE_DIR / "api.env", override=False)

SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-in-production")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
_raw_allowed_hosts = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")
if _raw_allowed_hosts.strip() == "*":
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = [h.strip() for h in _raw_allowed_hosts.split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "rest_framework",
    "corsheaders",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "apps.accounts.apps.AccountsConfig",
    "apps.roadmaps",
    "apps.progress",
    "apps.chatbot",
    "apps.community",
    "apps.library",
    "apps.planner",
    "apps.monitoring",
    "apps.quizzes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ar"
TIME_ZONE = "Africa/Cairo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

BOOK_CACHE_ENABLED = (os.getenv("BOOK_CACHE_ENABLED", "True")).lower() == "true"
BOOK_CACHE_TTL = timedelta(hours=int(os.getenv("BOOK_CACHE_TTL_HOURS", "24")))
BOOK_CACHE_PATH = BASE_DIR / "media" / "cache" / "books"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "elgolearnx-cache",
        "TIMEOUT": 300,
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SITE_ID = 1
SITE_DOMAIN = (os.getenv("SITE_DOMAIN") or "127.0.0.1:8001").strip()
SITE_NAME = (os.getenv("SITE_NAME") or "Local Development").strip()

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

GOOGLE_CLIENT_ID = (os.getenv("GOOGLE_CLIENT_ID") or "").strip()
GOOGLE_CLIENT_SECRET = (os.getenv("GOOGLE_CLIENT_SECRET") or "").strip()

# Use Django's default test runner

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": GOOGLE_CLIENT_ID,
            "secret": GOOGLE_CLIENT_SECRET,
            "key": "",
        },
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    }
}

SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_STORE_TOKENS = True
SOCIALACCOUNT_ADAPTER = "apps.accounts.adapter.SocialAccountAdapter"

ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "optional"
ACCOUNT_FORMS = {
    "login": "apps.accounts.forms.CustomLoginForm",
    "signup": "apps.accounts.forms.CustomSignupForm",
}
LOGIN_REDIRECT_URL = "/library/search/"
LOGOUT_REDIRECT_URL = "/"
LOGIN_URL = "/accounts/login/"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
}

GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY") or "").strip()
# انظر https://ai.google.dev/gemini-api/docs/models — النماذج القديمة قد تعيد 404
GEMINI_MODEL = (os.getenv("GEMINI_MODEL") or "gemini-2.5-flash").strip()
GOOGLE_BOOKS_API_KEY = (os.getenv("GOOGLE_BOOKS_API_KEY") or "").strip()
YOUTUBE_API_KEY = (os.getenv("YOUTUBE_API_KEY") or "").strip()
ELGOLEARN_SYNC_SECRET = (os.getenv("ELGOLEARN_SYNC_SECRET") or "dev-sync-secret").strip()
ROADMAPS_DATA_DIR = BASE_DIR / "data" / "roadmaps"
