"""Destination connector registry."""
from app.connectors.base import BaseConnector, ConnectorResult
from app.connectors.api import APIConnector
from app.connectors.fhir_write import FHIRWriteConnector

_REGISTRY = {
    "api": APIConnector,
    "fhir_write": FHIRWriteConnector,
}

try:
    from app.connectors.browser import BrowserConnector
    _REGISTRY["browser"] = BrowserConnector
except ImportError:
    pass  # playwright not installed


def get_connector(destination_type: str, config: dict) -> BaseConnector:
    """Instantiate the appropriate connector by destination type."""
    cls = _REGISTRY.get(destination_type)
    if cls is None:
        raise ValueError(f"Unknown destination type: '{destination_type}'. Available: {list(_REGISTRY)}")
    return cls(config)


__all__ = ["BaseConnector", "ConnectorResult", "get_connector"]
