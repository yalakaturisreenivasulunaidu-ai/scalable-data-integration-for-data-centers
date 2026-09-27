from typing import Any, Dict

from .api_connector import APIConnector
from .base import BaseConnector
from .database_connector import DatabaseConnector
from .file_connector import FileConnector

_REGISTRY = {
    "database": DatabaseConnector,
    "api": APIConnector,
    "file": FileConnector,
}


def create_connector(name: str, type_: str, options: Dict[str, Any] | None = None) -> BaseConnector:
    """Factory: build a connector instance from a config-declared type string."""
    if type_ not in _REGISTRY:
        raise ValueError(
            f"Unknown connector type '{type_}'. Available: {list(_REGISTRY)}"
        )
    return _REGISTRY[type_](name=name, options=options or {})


def register_connector(type_name: str, connector_cls) -> None:
    """Allow users to plug in custom connector types at runtime."""
    _REGISTRY[type_name] = connector_cls
