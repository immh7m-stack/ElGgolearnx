from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..models.book_source import BookProvider, BookResult


class BaseBookProvider(ABC, BookProvider):
    name = "base"

    @abstractmethod
    def matches(self, item: dict[str, Any]) -> bool:
        raise NotImplementedError

    @abstractmethod
    def normalize(self, item: dict[str, Any]) -> BookResult:
        raise NotImplementedError

    def search(self, query: str, limit: int = 10) -> list[BookResult]:
        raise NotImplementedError
