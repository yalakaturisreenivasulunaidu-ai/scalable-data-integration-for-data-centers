"""
Configuration loading and validation for the data integration pipeline.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List

import yaml


@dataclass
class SourceConfig:
    name: str
    type: str  # "database", "api", "file"
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TransformConfig:
    name: str
    type: str
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SinkConfig:
    name: str
    type: str  # "database", "file", "warehouse"
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineConfig:
    name: str
    sources: List[SourceConfig]
    transforms: List[TransformConfig]
    sinks: List[SinkConfig]
    max_workers: int = 4
    batch_size: int = 500
    retry_attempts: int = 3
    retry_backoff_seconds: float = 2.0


def load_config(path: str) -> PipelineConfig:
    """Load and parse a YAML pipeline configuration file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    pipeline = raw.get("pipeline", {})

    sources = [SourceConfig(**s) for s in raw.get("sources", [])]
    transforms = [TransformConfig(**t) for t in raw.get("transforms", [])]
    sinks = [SinkConfig(**s) for s in raw.get("sinks", [])]

    return PipelineConfig(
        name=pipeline.get("name", "unnamed-pipeline"),
        sources=sources,
        transforms=transforms,
        sinks=sinks,
        max_workers=pipeline.get("max_workers", 4),
        batch_size=pipeline.get("batch_size", 500),
        retry_attempts=pipeline.get("retry_attempts", 3),
        retry_backoff_seconds=pipeline.get("retry_backoff_seconds", 2.0),
    )
