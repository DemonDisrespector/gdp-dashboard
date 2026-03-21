"""Async FHIR R4 client with automatic OAuth 2.0 token management."""
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx
from fastapi import Depends

from app.config import Settings, get_settings
from app.fhir.auth import get_access_token
from app.fhir.resources import RESOURCE_TYPES

logger = logging.getLogger(__name__)

# FHIR resource types supported by this client
SUPPORTED_RESOURCES: List[str] = RESOURCE_TYPES


class FHIRError(Exception):
    """Raised when the FHIR server returns a non-2xx response."""

    def __init__(self, status_code: int, body: str, resource_type: str = ""):
        self.status_code = status_code
        self.body = body
        self.resource_type = resource_type
        super().__init__(f"FHIR {status_code} for {resource_type}: {body[:200]}")


class FHIRClient:
    """
    Async FHIR R4 client.

    Handles:
    - OAuth 2.0 client-credentials auth (auto-refresh)
    - GET /fhir/r4/{ResourceType}/{id}
    - GET /fhir/r4/{ResourceType}?<search params>
    - Automatic pagination via Bundle.link[rel=next]
    """

    def __init__(self, settings: Settings):
        self._settings = settings
        self._http = httpx.AsyncClient(
            base_url=str(settings.modmed_base_url),
            timeout=settings.fhir_request_timeout,
            headers={
                "Accept": "application/fhir+json",
                "Content-Type": "application/fhir+json",
            },
        )

    async def _auth_headers(self) -> Dict[str, str]:
        token = await get_access_token(self._http)
        return {"Authorization": f"Bearer {token}"}

    async def get_resource(self, resource_type: str, resource_id: str) -> Dict[str, Any]:
        """Read a single FHIR resource by ID."""
        if resource_type not in SUPPORTED_RESOURCES:
            raise ValueError(f"Unsupported resource type: {resource_type}")
        url = f"/{resource_type}/{resource_id}"
        headers = await self._auth_headers()
        logger.debug("FHIR GET %s", url)
        resp = await self._http.get(url, headers=headers)
        if not resp.is_success:
            raise FHIRError(resp.status_code, resp.text, resource_type)
        return resp.json()

    async def search_resource(
        self,
        resource_type: str,
        params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Search FHIR resources; returns a Bundle with all pages merged."""
        if resource_type not in SUPPORTED_RESOURCES:
            raise ValueError(f"Unsupported resource type: {resource_type}")
        all_entries: List[Dict] = []
        search_params = dict(params or {})
        search_params.setdefault("_count", str(self._settings.fhir_page_size))

        async for bundle in self._paginate(resource_type, search_params):
            all_entries.extend(bundle.get("entry", []))

        return {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": len(all_entries),
            "entry": all_entries,
        }

    async def get_patient_everything(self, patient_id: str) -> Dict[str, Any]:
        """
        Use FHIR $everything operation to pull all resources for a patient.
        Falls back to individual resource type queries when not supported.
        """
        url = f"/Patient/{patient_id}/$everything"
        headers = await self._auth_headers()
        resp = await self._http.get(url, headers=headers)
        if resp.status_code == 404 or resp.status_code == 400:
            logger.warning("$everything not supported; falling back to per-type queries")
            return await self._fetch_all_resource_types(patient_id)
        if not resp.is_success:
            raise FHIRError(resp.status_code, resp.text, "Patient/$everything")
        return resp.json()

    async def _fetch_all_resource_types(self, patient_id: str) -> Dict[str, Any]:
        """Individual search for each supported resource type."""
        all_entries: List[Dict] = []
        patient = await self.get_resource("Patient", patient_id)
        all_entries.append({"resource": patient})

        patient_scoped = [
            r for r in SUPPORTED_RESOURCES if r != "Patient"
        ]
        for rtype in patient_scoped:
            try:
                bundle = await self.search_resource(rtype, {"patient": patient_id})
                all_entries.extend(bundle.get("entry", []))
            except FHIRError as exc:
                logger.warning("Could not fetch %s for patient %s: %s", rtype, patient_id, exc)

        return {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": len(all_entries),
            "entry": all_entries,
        }

    async def _paginate(
        self, resource_type: str, params: Dict[str, str]
    ) -> AsyncIterator[Dict[str, Any]]:
        """Yield successive Bundle pages following next links."""
        headers = await self._auth_headers()
        url = f"/{resource_type}"
        next_url: Optional[str] = None

        while True:
            if next_url:
                # next_url is absolute – use raw httpx request
                resp = await self._http.get(next_url, headers=headers)
            else:
                resp = await self._http.get(url, params=params, headers=headers)

            if not resp.is_success:
                raise FHIRError(resp.status_code, resp.text, resource_type)

            bundle = resp.json()
            yield bundle

            next_url = _extract_next_url(bundle)
            if not next_url:
                break

    async def close(self):
        await self._http.aclose()


def _extract_next_url(bundle: Dict[str, Any]) -> Optional[str]:
    for link in bundle.get("link", []):
        if link.get("relation") == "next":
            return link.get("url")
    return None


# ── FastAPI dependency ────────────────────────────────────────────────────────

_client_singleton: Optional[FHIRClient] = None


def get_fhir_client(settings: Settings = Depends(get_settings)) -> FHIRClient:
    global _client_singleton
    if _client_singleton is None:
        _client_singleton = FHIRClient(settings)
    return _client_singleton
