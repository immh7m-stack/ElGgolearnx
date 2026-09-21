from __future__ import annotations

from typing import Any

from .base import BaseBookProvider
from ..models.book_source import BookResult, ViewerType


class RemoteHtmlProvider(BaseBookProvider):
    name = "html"

    def matches(self, item: dict[str, Any]) -> bool:
        return True

    def normalize(self, item: dict[str, Any]) -> BookResult:
        source_url = item.get("url", "") or ""
        pdf_url = item.get("pdf_url") or None
        can_read = bool(source_url)
        can_download = bool(pdf_url)
        return BookResult(
            title=item.get("title", "Untitled"),
            author=item.get("author"),
            cover=item.get("thumbnail") or item.get("cover_url"),
            viewer_type=ViewerType.HTML,
            source=item.get("source", "Web"),
            source_url=source_url,
            pdf_url=pdf_url,
            preview_url=source_url,
            download_url=pdf_url,
            can_read=can_read,
            can_download=can_download,
            metadata=item.get("metadata", {}),
        )
