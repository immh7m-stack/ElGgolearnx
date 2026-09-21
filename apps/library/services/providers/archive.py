from __future__ import annotations

from typing import Any

from .base import BaseBookProvider
from ..models.book_source import BookResult, ViewerType


class ArchiveBookProvider(BaseBookProvider):
    name = "archive"

    def matches(self, item: dict[str, Any]) -> bool:
        url = item.get("url", "") or ""
        return "archive.org" in url and item.get("is_pdf") is True

    def normalize(self, item: dict[str, Any]) -> BookResult:
        pdf_url = item.get("pdf_url") or item.get("url", "")
        return BookResult(
            title=item.get("title", "Untitled"),
            author=item.get("author"),
            cover=item.get("thumbnail") or item.get("cover_url"),
            viewer_type=ViewerType.ARCHIVE,
            source=item.get("source", "Archive"),
            source_url=item.get("url", ""),
            pdf_url=pdf_url,
            preview_url=item.get("url", ""),
            download_url=pdf_url,
            can_read=bool(pdf_url),
            can_download=bool(pdf_url),
            metadata=item.get("metadata", {}),
        )
