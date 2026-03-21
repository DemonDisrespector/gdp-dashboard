"""
REST API destination connector.

Config keys
-----------
url          : str   – destination endpoint URL
method       : str   – HTTP method (default POST)
headers      : dict  – extra headers (e.g. {"Authorization": "Bearer ..."})
batch_size   : int   – records per request (default 50)
timeout      : int   – seconds (default 30)
verify_ssl   : bool  – (default True)
"""
import logging
from typing import Any, Dict, List

import httpx

from app.connectors.base import BaseConnector, ConnectorResult

logger = logging.getLogger(__name__)


class APIConnector(BaseConnector):
    """POST (or PUT/PATCH) transformed records to a REST endpoint."""

    def validate_config(self):
        if "url" not in self.config:
            raise ValueError("APIConnector requires config key 'url'")

    async def send(self, payload: List[Dict[str, Any]]) -> ConnectorResult:
        url: str = self.config["url"]
        method: str = self.config.get("method", "POST").upper()
        headers: dict = {"Content-Type": "application/json", **self.config.get("headers", {})}
        batch_size: int = int(self.config.get("batch_size", 50))
        timeout: int = int(self.config.get("timeout", 30))
        verify_ssl: bool = self.config.get("verify_ssl", True)

        records_sent = 0
        records_failed = 0
        destination_ids: List[str] = []

        async with httpx.AsyncClient(verify=verify_ssl, timeout=timeout) as client:
            for i in range(0, len(payload), batch_size):
                batch = payload[i : i + batch_size]
                try:
                    resp = await client.request(method, url, json=batch, headers=headers)
                    resp.raise_for_status()
                    records_sent += len(batch)
                    body = resp.json() if resp.content else {}
                    if isinstance(body, list):
                        destination_ids.extend(str(r.get("id", "")) for r in body if isinstance(r, dict))
                    elif isinstance(body, dict) and "id" in body:
                        destination_ids.append(str(body["id"]))
                    logger.info("API connector sent batch of %d to %s → %d", len(batch), url, resp.status_code)
                except httpx.HTTPStatusError as exc:
                    records_failed += len(batch)
                    logger.error("API connector HTTP error: %s", exc)
                    return ConnectorResult(
                        success=False,
                        records_sent=records_sent,
                        records_failed=records_failed,
                        error_message=str(exc),
                    )
                except httpx.RequestError as exc:
                    records_failed += len(batch)
                    logger.error("API connector request error: %s", exc)
                    return ConnectorResult(
                        success=False,
                        records_sent=records_sent,
                        records_failed=records_failed,
                        error_message=str(exc),
                    )

        return ConnectorResult(
            success=True,
            records_sent=records_sent,
            records_failed=records_failed,
            destination_ids=destination_ids,
        )
