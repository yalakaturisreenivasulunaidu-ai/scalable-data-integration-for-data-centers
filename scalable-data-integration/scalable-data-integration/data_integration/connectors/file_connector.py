"""
File connector - reads CSV/JSON-lines files from a local path or
mounted network share (common in data-center log/metric shipping).
Falls back to mock records if no path is given or the file is missing.
"""

from __future__ import annotations

import csv
import json
import logging
import os
from typing import Any, Dict, Iterator

from .base import BaseConnector

logger = logging.getLogger(__name__)


class FileConnector(BaseConnector):
    def __init__(self, name: str, options: Dict[str, Any] | None = None):
        super().__init__(name, options)
        self.path = self.options.get("path")
        self.format = self.options.get("format", "csv")  # "csv" | "jsonl"
        self._mock_mode = not (self.path and os.path.exists(self.path))

    def connect(self) -> None:
        if self._mock_mode:
            logger.info(
                "[%s] No valid file path provided - running in mock mode.", self.name
            )

    def extract(self) -> Iterator[Dict[str, Any]]:
        if self._mock_mode:
            yield from self._mock_records()
            return

        if self.format == "jsonl":
            with open(self.path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        yield json.loads(line)
        else:
            with open(self.path, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    yield dict(row)

    def _mock_records(self) -> Iterator[Dict[str, Any]]:
        for i in range(1, 11):
            yield {
                "id": f"log-{i:03d}",
                "source": self.name,
                "metric": "disk_io_ops",
                "value": round(100 + (i * 17.5) % 300, 2),
                "timestamp": f"2026-09-27T00:{i:02d}:00Z",
            }
