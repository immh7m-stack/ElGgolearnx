from __future__ import annotations

import logging
from typing import Any

from .models.book_source import BookProvider, BookResult
from .providers.archive import ArchiveBookProvider
from .providers.doi import DoiBookProvider
from .providers.google_books import GoogleBooksProvider
from .providers.openlibrary import OpenLibraryProvider
from .providers.pdf import PdfBookProvider
from .providers.remote_html import RemoteHtmlProvider

logger = logging.getLogger(__name__)


class BookSourceResolver:
    def __init__(self) -> None:
        self.providers: list[BookProvider] = [
            PdfBookProvider(),
            ArchiveBookProvider(),
            GoogleBooksProvider(),
            OpenLibraryProvider(),
            DoiBookProvider(),
            RemoteHtmlProvider(),
        ]

    def normalize(self, item: dict[str, Any]) -> BookResult:
        for provider in self.providers:
            if provider.matches(item):
                return provider.normalize(item)
        return RemoteHtmlProvider().normalize(item)

    def search(self, query: str, limit: int = 10) -> list[BookResult]:
        from .book_search import search_remote_books

        items = search_remote_books(query, limit)
        return self.book_results(items)

    def book_results(self, items: list[dict[str, Any]]) -> list[BookResult]:
        normalized = [self.normalize(item) for item in items]
        unique = {
            (result.source_url or result.download_url or result.title): result
            for result in normalized
        }
        return sorted(unique.values(), key=lambda r: (r.can_read, r.can_download), reverse=True)
