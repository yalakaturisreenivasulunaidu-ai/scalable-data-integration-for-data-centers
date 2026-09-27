"""
Base interface for transformation steps applied to extracted records.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseTransformer(ABC):
    def __init__(self, name: str, options: Dict[str, Any] | None = None):
        self.name = name
        self.options = options or {}

    @abstractmethod
    def transform(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Transform a single record. Return None to drop the record
        from the pipeline (e.g. it failed validation).
        """
        raise NotImplementedError
