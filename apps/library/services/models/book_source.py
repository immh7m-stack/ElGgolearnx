from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, Any


class ViewerType(str, Enum):
    PDF = "pdf"
    ARCHIVE = "archive"
    GOOGLE_BOOKS = "google_books"
    OPENLIBRARY = "openlibrary"
    DOI = "doi"
    EXTERNAL = "external"
    HTML = "html"


@dataclass
class BookResult:
    title: str
    author: str | None = None
    viewer_type: ViewerType = ViewerType.HTML
    source: str = "Web"
    source_url: str | None = None
    pdf_url: str | None = None
    preview_url: str | None = None
    download_url: str | None = None
    can_read: bool = False
    can_download: bool = False
    cover: str | None = None
    description: str = ""
    book_id: int | None = None
    is_free: bool = True
    language: str = ""
    category: str = ""
    pages: int | None = None
    is_cached: bool = False
    cached_at: str | None = None
    cache_size: int = 0
    cache_expires_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def url(self) -> str | None:
        return self.source_url

    @property
    def cover_url(self) -> str:
        return self.cover or ""

    @property
    def is_pdf(self) -> bool:
        return bool(self.pdf_url)

    def to_dict(self) -> dict[str, Any]:
        return {
            "book_id": self.book_id,
            "title": self.title,
            "author": self.author or "",
            "description": self.description,
            "viewer_type": self.viewer_type.value,
            "source": self.source,
            "source_url": self.source_url or "",
            "url": self.source_url or "",
            "pdf_url": self.pdf_url or "",
            "preview_url": self.preview_url or "",
            "download_url": self.download_url or "",
            "can_read": self.can_read,
            "can_download": self.can_download,
            "cover": self.cover or "",
            "cover_url": self.cover or "",
            "is_pdf": self.is_pdf,
            "is_free": self.is_free,
            "language": self.language,
            "category": self.category,
            "pages": self.pages,
            "is_cached": self.is_cached,
            "cached_at": self.cached_at,
            "cache_size": self.cache_size,
            "cache_expires_at": self.cache_expires_at,
            "metadata": self.metadata,
        }


class BookProvider(Protocol):
    name: str

    def matches(self, raw_result: dict[str, Any]) -> bool:
        ...

    def normalize(self, raw_result: dict[str, Any]) -> BookResult:
        ...
