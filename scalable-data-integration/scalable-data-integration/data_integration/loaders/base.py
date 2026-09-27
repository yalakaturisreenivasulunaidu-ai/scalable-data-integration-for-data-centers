"""
Base interface for loaders (a.k.a. sinks) that write transformed
records to a destination system.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseLoader(ABC):
    def __init__(self, name: str, options: Dict[str, Any] | None = None):
        self.name = name
        self.options = options or {}

    def open(self) -> None:
        """Optional: set up connection/file handle before loading."""
        pass

    @abstractmethod
    def load(self, batch: List[Dict[str, Any]]) -> int:
        """Persist a batch of records. Return the count written."""
        raise NotImplementedError

    def close(self) -> None:
        pass

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
