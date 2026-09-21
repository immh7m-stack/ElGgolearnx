from __future__ import annotations

import logging
import shutil
import uuid
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from apps.library.models import Book

logger = logging.getLogger(__name__)

CACHE_DIR = Path(settings.BOOK_CACHE_PATH)
# Do not create the cache directory at import time (avoids side-effects during
# test discovery or module import). Creation is handled by `ensure_cache_dir`.


def get_book_cache_path(book: Book) -> Path:
    return CACHE_DIR / f"book_cache_{book.pk}.pdf"


def ensure_cache_dir() -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR


def cache_exists(book: Book) -> bool:
    cache_path = get_book_cache_path(book)
    return cache_path.is_file()


def get_cached_book(book: Book) -> Path | None:
    if not settings.BOOK_CACHE_ENABLED:
        return None
    cache_path = get_book_cache_path(book)
    if cache_path.is_file():
        logger.info("CACHE HIT: %s", book.pk)
        return cache_path
    logger.info("CACHE MISS: %s", book.pk)
    return None


def create_book_cache(book: Book, source_path: Path | str) -> Path | None:
    if not settings.BOOK_CACHE_ENABLED:
        return None
    cache_file = get_book_cache_path(book)
    ensure_cache_dir()
    try:
        source = Path(source_path)
        if not source.is_file():
            logger.warning("CACHE CREATE FAILED: source file not found for book %s", book.pk)
            return None
        # Use a unique temporary filename to avoid races when multiple processes
        # attempt to create the cache for the same book concurrently.
        tmp_path = cache_file.with_suffix(f".tmp-{uuid.uuid4().hex}")
        shutil.copy2(source, tmp_path)
        tmp_path.replace(cache_file)
        book.mark_cached(cache_file.stat().st_size)
        logger.info("CACHE CREATED: %s", book.pk)
        return cache_file
    except Exception as exc:
        logger.exception("CACHE CREATE ERROR: %s for book %s", exc, book.pk)
        return None


def remove_book_cache(book: Book) -> bool:
    cache_path = get_book_cache_path(book)
    if cache_path.is_file():
        try:
            cache_path.unlink()
            book.mark_cache_removed()
            logger.info("CACHE REMOVED: %s", book.pk)
            return True
        except Exception as exc:
            logger.exception("CACHE REMOVE ERROR: %s for book %s", exc, book.pk)
            return False
    if book.is_cached:
        book.mark_cache_removed()
    return False


def is_cache_expired(book: Book) -> bool:
    if not book.is_cached or not book.cache_expires_at:
        return False
    expired = timezone.now() >= book.cache_expires_at
    if expired:
        logger.info("CACHE EXPIRED: %s", book.pk)
    return expired


def refresh_book_metadata(book: Book) -> None:
    book.last_accessed = timezone.now()
    if book.is_cached and book.cache_expires_at and timezone.now() >= book.cache_expires_at:
        book.cache_expires_at = timezone.now() + settings.BOOK_CACHE_TTL
    book.save(update_fields=["last_accessed", "cache_expires_at"])
