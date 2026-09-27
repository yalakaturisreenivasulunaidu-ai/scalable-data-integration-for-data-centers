from typing import Any, Dict

from .base import BaseLoader
from .standard_loaders import DatabaseLoader, FileLoader

_REGISTRY = {
    "file": FileLoader,
    "database": DatabaseLoader,
    "warehouse": DatabaseLoader,  # alias - point at a warehouse via connection_string
}


def create_loader(name: str, type_: str, options: Dict[str, Any] | None = None) -> BaseLoader:
    if type_ not in _REGISTRY:
        raise ValueError(f"Unknown loader type '{type_}'. Available: {list(_REGISTRY)}")
    return _REGISTRY[type_](name=name, options=options or {})


def register_loader(type_name: str, loader_cls) -> None:
    _REGISTRY[type_name] = loader_cls
