"""
A handful of common, config-driven transformers useful for
data-center telemetry / operational data.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .base import BaseTransformer


class FieldMapTransformer(BaseTransformer):
    """Rename fields according to options['mapping'] = {old: new}."""

    def transform(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        mapping = self.options.get("mapping", {})
        out = dict(record)
        for old_key, new_key in mapping.items():
            if old_key in out:
                out[new_key] = out.pop(old_key)
        return out


class TypeCastTransformer(BaseTransformer):
    """Cast fields to types, e.g. options['casts'] = {'value': 'float'}."""

    _CASTERS = {"float": float, "int": int, "str": str}

    def transform(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        casts = self.options.get("casts", {})
        out = dict(record)
        for field, type_name in casts.items():
            if field in out and out[field] is not None:
                caster = self._CASTERS.get(type_name)
                if caster:
                    try:
                        out[field] = caster(out[field])
                    except (ValueError, TypeError):
                        return None  # drop malformed record
        return out


class ValidationTransformer(BaseTransformer):
    """Drop records missing any of options['required_fields']."""

    def transform(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        required = self.options.get("required_fields", [])
        for field in required:
            if record.get(field) in (None, ""):
                return None
        return record


class EnrichmentTransformer(BaseTransformer):
    """Add static/derived metadata: ingestion timestamp, pipeline tag, etc."""

    def transform(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        out = dict(record)
        out["_ingested_at"] = datetime.now(timezone.utc).isoformat()
        out["_tag"] = self.options.get("tag", "default")
        return out
