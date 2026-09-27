"""
Base interface that every data source connector must implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator


class BaseConnector(ABC):
    """
    A Connector is responsible for extracting records from a single
    data source. Implementations should be *iterable/streaming* where
    possible so large data-center datasets don't need to fit in memory.
    """

    def __init__(self, name: str, options: Dict[str, Any] | None = None):
        self.name = name
        self.options = options or {}

    @abstractmethod
    def connect(self) -> None:
        """Establish any connection/session needed before extraction."""
        raise NotImplementedError

    @abstractmethod
    def extract(self) -> Iterator[Dict[str, Any]]:
        """Yield records one at a time (or in small chunks)."""
        raise NotImplementedError

    def close(self) -> None:
        """Release any resources. Override if needed."""
        pass

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
