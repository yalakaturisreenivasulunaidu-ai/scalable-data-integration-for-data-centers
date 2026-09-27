from typing import Any, Dict

from .base import BaseTransformer
from .standard_transformers import (
    EnrichmentTransformer,
    FieldMapTransformer,
    TypeCastTransformer,
    ValidationTransformer,
)

_REGISTRY = {
    "field_map": FieldMapTransformer,
    "type_cast": TypeCastTransformer,
    "validate": ValidationTransformer,
    "enrich": EnrichmentTransformer,
}


def create_transformer(name: str, type_: str, options: Dict[str, Any] | None = None) -> BaseTransformer:
    if type_ not in _REGISTRY:
        raise ValueError(
            f"Unknown transformer type '{type_}'. Available: {list(_REGISTRY)}"
        )
    return _REGISTRY[type_](name=name, options=options or {})


def register_transformer(type_name: str, transformer_cls) -> None:
    _REGISTRY[type_name] = transformer_cls
