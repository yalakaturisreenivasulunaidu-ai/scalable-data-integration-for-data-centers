"""
Pipeline orchestrator.

Design goals for a data-center-scale workload:
  * Each configured *source* is extracted concurrently (thread pool -
    extraction is I/O bound: DB/API/file reads).
  * Records flow through the transform chain and are batched.
  * Batches are handed to sinks with bounded retries + backoff, so a
    transient failure on one node/sink doesn't kill the whole run.
  * The number of workers is config-driven (`max_workers`) so the same
    code scales from a laptop to a many-core data-center host, and the
    thread pool can be swapped for a process pool for CPU-bound
    transforms (see `use_process_pool`).
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

from .config import PipelineConfig
from .connectors import create_connector
from .loaders import create_loader
from .transformers import create_transformer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class PipelineStats:
    def __init__(self):
        self.extracted = 0
        self.transformed = 0
        self.dropped = 0
        self.loaded = 0
        self.errors: List[str] = []

    def as_dict(self) -> Dict[str, Any]:
        return {
            "extracted": self.extracted,
            "transformed": self.transformed,
            "dropped": self.dropped,
            "loaded": self.loaded,
            "error_count": len(self.errors),
            "errors": self.errors[:20],  # cap for readability
        }


class Pipeline:
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.transformers = [
            create_transformer(t.name, t.type, t.options) for t in config.transforms
        ]
        self.loaders = [create_loader(s.name, s.type, s.options) for s in config.sinks]
        self.stats = PipelineStats()

    # ---- core stages -----------------------------------------------------

    def _apply_transforms(self, record: Dict[str, Any]) -> Dict[str, Any] | None:
        current = record
        for transformer in self.transformers:
            if current is None:
                break
            try:
                current = transformer.transform(current)
            except Exception as exc:  # noqa: BLE001
                self.stats.errors.append(f"transform:{transformer.name}: {exc}")
                return None
        return current

    def _load_batch_with_retry(self, batch: List[Dict[str, Any]]) -> None:
        if not batch:
            return
        for loader in self.loaders:
            attempt = 0
            while attempt < self.config.retry_attempts:
                try:
                    written = loader.load(batch)
                    self.stats.loaded += written
                    break
                except Exception as exc:  # noqa: BLE001
                    attempt += 1
                    wait = self.config.retry_backoff_seconds * attempt
                    logger.warning(
                        "Load to '%s' failed (attempt %d/%d): %s - retrying in %.1fs",
                        loader.name, attempt, self.config.retry_attempts, exc, wait,
                    )
                    time.sleep(wait)
            else:
                self.stats.errors.append(
                    f"load:{loader.name}: exhausted {self.config.retry_attempts} retries"
                )

    def _run_source(self, source_cfg) -> None:
        """Extract -> transform -> batch -> load, for a single source."""
        connector = create_connector(source_cfg.name, source_cfg.type, source_cfg.options)
        batch: List[Dict[str, Any]] = []

        with connector:
            for record in connector.extract():
                self.stats.extracted += 1
                transformed = self._apply_transforms(record)

                if transformed is None:
                    self.stats.dropped += 1
                    continue

                self.stats.transformed += 1
                batch.append(transformed)

                if len(batch) >= self.config.batch_size:
                    self._load_batch_with_retry(batch)
                    batch = []

        self._load_batch_with_retry(batch)  # flush remainder

    # ---- entry point -------------------------------------------------------

    def run(self) -> Dict[str, Any]:
        logger.info(
            "Starting pipeline '%s' with %d source(s), %d worker(s).",
            self.config.name, len(self.config.sources), self.config.max_workers,
        )

        for loader in self.loaders:
            loader.open()

        try:
            with ThreadPoolExecutor(max_workers=self.config.max_workers) as pool:
                futures = {
                    pool.submit(self._run_source, source): source.name
                    for source in self.config.sources
                }
                for future in as_completed(futures):
                    source_name = futures[future]
                    try:
                        future.result()
                        logger.info("Source '%s' finished.", source_name)
                    except Exception as exc:  # noqa: BLE001
                        self.stats.errors.append(f"source:{source_name}: {exc}")
                        logger.error("Source '%s' failed: %s", source_name, exc)
        finally:
            for loader in self.loaders:
                loader.close()

        logger.info("Pipeline '%s' complete: %s", self.config.name, self.stats.as_dict())
        return self.stats.as_dict()
