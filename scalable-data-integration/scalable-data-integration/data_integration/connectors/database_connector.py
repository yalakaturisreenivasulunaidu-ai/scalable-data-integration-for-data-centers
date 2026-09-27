"""
Generic database connector.

Uses SQLAlchemy if available and a connection string is provided in
options (key: "connection_string" and "query"). If SQLAlchemy/DB
libraries aren't installed, falls back to a mock in-memory dataset so
the pipeline remains runnable out of the box for demos/tests.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterator

from .base import BaseConnector

logger = logging.getLogger(__name__)


class DatabaseConnector(BaseConnector):
    def __init__(self, name: str, options: Dict[str, Any] | None = None):
        super().__init__(name, options)
        self._engine = None
        self._mock_mode = "connection_string" not in self.options

    def connect(self) -> None:
        if self._mock_mode:
            logger.info(
                "[%s] No connection_string provided - running in mock mode.",
                self.name,
            )
            return

        try:
            from sqlalchemy import create_engine

            self._engine = create_engine(self.options["connection_string"])
            logger.info("[%s] Connected to database.", self.name)
        except ImportError:
            logger.warning(
                "[%s] SQLAlchemy not installed - falling back to mock mode.",
                self.name,
            )
            self._mock_mode = True

    def extract(self) -> Iterator[Dict[str, Any]]:
        if self._mock_mode:
            yield from self._mock_records()
            return

        query = self.options.get("query", "SELECT 1")
        chunk_size = self.options.get("chunk_size", 1000)

        with self._engine.connect() as conn:
            result = conn.execution_options(stream_results=True).execute(query)
            while True:
                chunk = result.fetchmany(chunk_size)
                if not chunk:
                    break
                for row in chunk:
                    yield dict(row._mapping)

    def _mock_records(self) -> Iterator[Dict[str, Any]]:
        """Deterministic mock rows so the pipeline runs end-to-end without infra."""
        for i in range(1, 21):
            yield {
                "id": i,
                "source": self.name,
                "metric": "cpu_utilization",
                "value": round(30 + (i * 2.7) % 60, 2),
                "timestamp": f"2026-09-27T00:{i:02d}:00Z",
            }

    def close(self) -> None:
        if self._engine is not None:
            self._engine.dispose()
