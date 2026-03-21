"""OAuth 2.0 client-credentials token manager for FHIR sources (ModMed)."""
import asyncio
import logging
import time
from dataclasses import dataclass, field

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class TokenCache:
    access_token: str = ""
    expires_at: float = 0.0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def is_valid(self, buffer_secs: int = 60) -> bool:
        return bool(self.access_token) and time.monotonic() < (self.expires_at - buffer_secs)


_token_cache: TokenCache = TokenCache()


async def get_access_token(http_client: httpx.AsyncClient) -> str:
    """Return a valid bearer token, refreshing if expired."""
    async with _token_cache.lock:
        if _token_cache.is_valid():
            return _token_cache.access_token
        token = await _fetch_token(http_client)
        _token_cache.access_token = token["access_token"]
        _token_cache.expires_at = time.monotonic() + token.get("expires_in", 3600)
        logger.debug("OAuth token refreshed; expires in %ss", token.get("expires_in"))
        return _token_cache.access_token


async def _fetch_token(http_client: httpx.AsyncClient) -> dict:
    """Perform OAuth 2.0 client-credentials grant against ModMed."""
    if not settings.modmed_client_id or not settings.modmed_client_secret:
        raise RuntimeError(
            "MODMED_CLIENT_ID and MODMED_CLIENT_SECRET must be configured."
        )
    resp = await http_client.post(
        str(settings.modmed_token_url),
        data={
            "grant_type": "client_credentials",
            "client_id": settings.modmed_client_id,
            "client_secret": settings.modmed_client_secret,
            "scope": settings.modmed_scope,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()
