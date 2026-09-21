from __future__ import annotations

from typing import Any

from .base import BaseBookProvider
from ..models.book_source import BookResult, ViewerType


class GoogleBooksProvider(BaseBookProvider):
    name = "google_books"

    def matches(self, item: dict[str, Any]) -> bool:
        url = item.get("url", "") or ""
        host = url.split("//")[-1].lower()
        return "books.google.com" in host or "play.google.com" in host or item.get("source") == "Google Books"

    def normalize(self, item: dict[str, Any]) -> BookResult:
        web_reader_link = item.get("web_reader_link") or item.get("url", "")
        pdf_download = item.get("pdf_download") or item.get("pdf_url", "")
        source_url = web_reader_link or item.get("info_link") or item.get("url", "")
        has_pdf = bool(pdf_download and pdf_download.lower().endswith(".pdf"))

        viewer_type = ViewerType.GOOGLE_BOOKS
        if not web_reader_link and has_pdf:
            viewer_type = ViewerType.PDF
            source_url = pdf_download

        preview_url = web_reader_link or source_url
        return BookResult(
            title=item.get("title", "Untitled"),
            author=item.get("author"),
            cover=item.get("thumbnail") or item.get("cover_url"),
            viewer_type=viewer_type,
            source=item.get("source", "Google Books"),
            source_url=source_url,
            pdf_url=pdf_download or None,
            preview_url=preview_url,
            download_url=pdf_download or None,
            can_read=bool(source_url),
            can_download=bool(pdf_download),
            metadata=item.get("metadata", {}),
        )
