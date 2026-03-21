"""
FHIR write destination connector.

Posts resources as a FHIR transaction Bundle to a target FHIR server using
the same OAuth 2.0 client-credentials flow as the source client.

Config keys
-----------
base_url       : str  – target FHIR server base URL
token_url      : str  – OAuth token endpoint
client_id      : str
client_secret  : str
scope          : str  – (default "fhir.write")
timeout        : int  – (default 30)
"""
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

import httpx

from app.connectors.base import BaseConnector, ConnectorResult

logger = logging.getLogger(__name__)


class FHIRWriteConnector(BaseConnector):
    """Write transformed resources as a FHIR transaction Bundle."""

    def validate_config(self):
        required = {"base_url", "token_url", "client_id", "client_secret"}
        missing = required - self.config.keys()
        if missing:
            raise ValueError(f"FHIRWriteConnector missing config keys: {missing}")

    async def send(self, payload: List[Dict[str, Any]]) -> ConnectorResult:
        timeout = int(self.config.get("timeout", 30))
        async with httpx.AsyncClient(timeout=timeout) as client:
            token = await self._get_token(client)
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/fhir+json",
                "Content-Type": "application/fhir+json",
            }
            bundle = self._build_transaction_bundle(payload)
            try:
                resp = await client.post(
                    self.config["base_url"],
                    json=bundle,
                    headers=headers,
                )
                resp.raise_for_status()
                response_bundle = resp.json()
                sent_ids = self._extract_ids(response_bundle)
                logger.info("FHIRWrite sent %d resources, got %d IDs", len(payload), len(sent_ids))
                return ConnectorResult(
                    success=True,
                    records_sent=len(payload),
                    destination_ids=sent_ids,
                    raw_response=response_bundle,
                )
            except httpx.HTTPStatusError as exc:
                logger.error("FHIRWrite HTTP error: %s", exc)
                return ConnectorResult(
                    success=False,
                    records_failed=len(payload),
                    error_message=str(exc),
                )

    async def _get_token(self, client: httpx.AsyncClient) -> str:
        resp = await client.post(
            self.config["token_url"],
            data={
                "grant_type": "client_credentials",
                "client_id": self.config["client_id"],
                "client_secret": self.config["client_secret"],
                "scope": self.config.get("scope", "fhir.write"),
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    @staticmethod
    def _build_transaction_bundle(resources: List[Dict[str, Any]]) -> Dict[str, Any]:
        entries = []
        for res in resources:
            rtype = res.get("resourceType", "Resource")
            rid = res.get("fhirId") or res.get("id") or str(uuid.uuid4())
            entries.append({
                "fullUrl": f"urn:uuid:{rid}",
                "resource": res,
                "request": {
                    "method": "PUT",
                    "url": f"{rtype}/{rid}",
                },
            })
        return {
            "resourceType": "Bundle",
            "type": "transaction",
            "entry": entries,
        }

    @staticmethod
    def _extract_ids(response_bundle: Dict[str, Any]) -> List[str]:
        ids = []
        for entry in response_bundle.get("entry", []):
            loc = entry.get("response", {}).get("location", "")
            if loc:
                ids.append(loc)
        return ids
