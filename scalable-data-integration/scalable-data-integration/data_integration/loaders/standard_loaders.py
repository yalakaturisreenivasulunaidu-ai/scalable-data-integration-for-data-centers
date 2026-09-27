"""
Loader implementations: local JSONL file sink (works everywhere, good
default/demo target) and a generic database sink (SQLAlchemy, optional).
"""

from __future__ import annotations

import json
import logging
import os
import threading
from typing import Any, Dict, List

from .base import BaseLoader

logger = logging.getLogger(__name__)

# A process/thread-safe-ish file lock so parallel workers can share one sink file.
_file_lock = threading.Lock()


class FileLoader(BaseLoader):
    """Appends records as JSON-lines to a local output file."""

    def open(self) -> None:
        self.path = self.options.get("path", "output/data.jsonl")
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)

    def load(self, batch: List[Dict[str, Any]]) -> int:
        with _file_lock:
            with open(self.path, "a", encoding="utf-8") as f:
                for record in batch:
                    f.write(json.dumps(record, default=str) + "\n")
        logger.info("[%s] Wrote %d records to %s", self.name, len(batch), self.path)
        return len(batch)


class DatabaseLoader(BaseLoader):
    """Writes batches to a database table via SQLAlchemy, if available."""

    def open(self) -> None:
        self._engine = None
        self._mock_mode = "connection_string" not in self.options
        if self._mock_mode:
            logger.info(
                "[%s] No connection_string provided - loads will be logged, not persisted.",
                self.name,
            )
            return
        try:
            from sqlalchemy import create_engine

            self._engine = create_engine(self.options["connection_string"])
        except ImportError:
            logger.warning(
                "[%s] SQLAlchemy not installed - falling back to log-only mode.",
                self.name,
            )
            self._mock_mode = True

    def load(self, batch: List[Dict[str, Any]]) -> int:
        table = self.options.get("table", "integrated_data")
        if self._mock_mode:
            logger.info(
                "[%s] (mock) Would upsert %d records into table '%s'.",
                self.name, len(batch), table,
            )
            return len(batch)

        import sqlalchemy as sa

        metadata = sa.MetaData()
        tbl = sa.Table(table, metadata, autoload_with=self._engine)
        with self._engine.begin() as conn:
            conn.execute(tbl.insert(), batch)
        return len(batch)

    def close(self) -> None:
        if self._engine is not None:
            self._engine.dispose()
