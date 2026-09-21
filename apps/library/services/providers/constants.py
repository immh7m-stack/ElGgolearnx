from __future__ import annotations

from django.conf import settings

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}
REMOTE_TIMEOUT_SECONDS = 15
GOOGLE_BOOKS_BASE_URL = "https://www.googleapis.com/books/v1/volumes"
GOOGLE_BOOKS_API_KEY = (getattr(settings, "GOOGLE_BOOKS_API_KEY", "") or "").strip()
