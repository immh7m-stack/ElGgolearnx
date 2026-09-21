from __future__ import annotations

from typing import Any

from .base import BaseBookProvider
from ..models.book_source import BookResult, ViewerType


class PdfBookProvider(BaseBookProvider):
    name = "pdf"

    def matches(self, item: dict[str, Any]) -> bool:
        return bool(item.get("pdf_download") or item.get("pdf_url") or item.get("url")) and item.get("is_pdf") is True

    def normalize(self, item: dict[str, Any]) -> BookResult:
        pdf_url = item.get("pdf_download") or item.get("pdf_url") or item.get("url")
        source_url = item.get("url") or pdf_url or ""
        return BookResult(
            title=item.get("title", "Untitled"),
            author=item.get("author"),
            cover=item.get("thumbnail") or item.get("cover_url"),
            viewer_type=ViewerType.PDF,
            source=item.get("source", "Web"),
            source_url=source_url,
            pdf_url=pdf_url,
            preview_url=source_url,
            download_url=pdf_url,
            can_read=bool(pdf_url),
            can_download=bool(pdf_url),
            metadata=item.get("metadata", {}),
        )
