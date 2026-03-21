"""Abstract base class for all destination connectors."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ConnectorResult:
    success: bool
    records_sent: int = 0
    records_failed: int = 0
    destination_ids: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    raw_response: Optional[Any] = None


class BaseConnector(ABC):
    """
    Pluggable destination connector interface.

    Subclasses must implement `send` and may override `validate_config`.
    Configuration is provided as a plain dict so connectors remain
    decoupled from the ORM and can be instantiated from any context.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.validate_config()

    def validate_config(self):
        """Override to enforce required config keys."""

    @abstractmethod
    async def send(self, payload: List[Dict[str, Any]]) -> ConnectorResult:
        """
        Deliver the transformed payload to the destination.

        Parameters
        ----------
        payload:
            List of transformed resource dicts produced by the TransformEngine.

        Returns
        -------
        ConnectorResult with success flag and metadata.
        """

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def close(self):
        """Override for cleanup (e.g. close HTTP sessions, browser pages)."""
