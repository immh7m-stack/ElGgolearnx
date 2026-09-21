from __future__ import annotations

from typing import Any

from .base import BaseBookProvider
from ..models.book_source import BookResult, ViewerType


class OpenLibraryProvider(BaseBookProvider):
    name = "openlibrary"

    def matches(self, item: dict[str, Any]) -> bool:
        url = item.get("url", "") or ""
        return "openlibrary.org" in url

    def normalize(self, item: dict[str, Any]) -> BookResult:
        pdf_url = item.get("pdf_url") or (item.get("url", "") if item.get("is_pdf") else None)
        source_url = item.get("url", "")
        return BookResult(
            title=item.get("title", "Untitled"),
            author=item.get("author"),
            cover=item.get("thumbnail") or item.get("cover_url"),
            viewer_type=ViewerType.PDF if pdf_url else ViewerType.OPENLIBRARY,
            source=item.get("source", "Open Library"),
            source_url=source_url,
            pdf_url=pdf_url,
            preview_url=source_url,
            download_url=pdf_url,
            can_read=bool(source_url),
            can_download=bool(pdf_url),
            metadata=item.get("metadata", {}),
        )
