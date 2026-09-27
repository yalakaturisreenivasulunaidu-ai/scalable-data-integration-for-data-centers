"""
Generic REST API connector with pagination and retry support.
Falls back to mock data if `requests` is unavailable or no URL is given,
so the base project runs without external dependencies or network access.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Iterator

from .base import BaseConnector

logger = logging.getLogger(__name__)


class APIConnector(BaseConnector):
    def __init__(self, name: str, options: Dict[str, Any] | None = None):
        super().__init__(name, options)
        self._mock_mode = "url" not in self.options

    def connect(self) -> None:
        if self._mock_mode:
            logger.info("[%s] No URL provided - running in mock mode.", self.name)
            return
        try:
            import requests  # noqa: F401
        except ImportError:
            logger.warning(
                "[%s] 'requests' not installed - falling back to mock mode.",
                self.name,
            )
            self._mock_mode = True

    def extract(self) -> Iterator[Dict[str, Any]]:
        if self._mock_mode:
            yield from self._mock_records()
            return

        import requests

        url = self.options["url"]
        headers = self.options.get("headers", {})
        page_param = self.options.get("page_param", "page")
        max_retries = self.options.get("max_retries", 3)
        page = 1

        while True:
            for attempt in range(1, max_retries + 1):
                try:
                    resp = requests.get(
                        url, headers=headers, params={page_param: page}, timeout=30
                    )
                    resp.raise_for_status()
                    break
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "[%s] Request failed (attempt %s/%s): %s",
                        self.name, attempt, max_retries, exc,
                    )
                    if attempt == max_retries:
                        return
                    time.sleep(2 ** attempt)

            payload = resp.json()
            records = payload.get("results", payload if isinstance(payload, list) else [])
            if not records:
                break
            for record in records:
                yield record
            if not payload.get("next"):
                break
            page += 1

    def _mock_records(self) -> Iterator[Dict[str, Any]]:
        for i in range(1, 16):
            yield {
                "id": f"rack-{i:03d}",
                "source": self.name,
                "metric": "temperature_c",
                "value": round(18 + (i * 1.3) % 8, 2),
                "timestamp": f"2026-09-27T00:{i:02d}:00Z",
            }
