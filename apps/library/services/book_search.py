from __future__ import annotations

from typing import Any

from .book_source_resolver import BookSourceResolver


resolver = BookSourceResolver()


def search_books(query: str, limit: int = 10, **kwargs) -> list[dict[str, Any]]:
    return [result.to_dict() for result in resolver.search(query, limit=limit, **kwargs)]
