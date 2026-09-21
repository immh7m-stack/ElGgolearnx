from __future__ import annotations

from typing import Any

from .base import BaseBookProvider
from ..models.book_source import BookResult, ViewerType


class DoiBookProvider(BaseBookProvider):
    name = "doi"

    def matches(self, item: dict[str, Any]) -> bool:
        url = item.get("url", "") or ""
        return "doi.org" in url or url.lower().startswith("doi:")

    def normalize(self, item: dict[str, Any]) -> BookResult:
        source_url = item.get("url", "")
        return BookResult(
            title=item.get("title", "Untitled"),
            author=item.get("author"),
            cover=item.get("thumbnail") or item.get("cover_url"),
            viewer_type=ViewerType.DOI,
            source=item.get("source", "DOI"),
            source_url=source_url,
            pdf_url=None,
            preview_url=source_url,
            download_url=None,
            can_read=True,
            can_download=False,
            metadata=item.get("metadata", {}),
        )
