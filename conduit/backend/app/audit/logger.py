"""
HIPAA-compliant audit logger.

All entries are de-identified before persistence:
- Patient identifiers → HMAC-SHA256 token (keyed by ENCRYPTION_KEY env var)
- No PHI is written to the audit_logs table
- Minimum data: event type, actor, resource metadata, outcome
"""
import hashlib
import hmac
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.audit import AuditLog

logger = logging.getLogger(__name__)
settings = get_settings()


def _patient_token(patient_id: str) -> str:
    """
    Produce a one-way HMAC-SHA256 token for a patient identifier.
    The token is consistent per (patient_id, key) pair and can be used
    to correlate audit events without exposing the raw ID.
    """
    return hmac.new(
        settings.encryption_key.encode(),
        patient_id.encode(),
        hashlib.sha256,
    ).hexdigest()


class AuditLogger:
    """
    Write structured, de-identified audit events to PostgreSQL.

    Event types
    -----------
    fhir_fetch    FHIR resources were read from the source system
    transform     FHIR resources were transformed
    deliver       Transformed data was sent to the destination
    error         An error occurred in any stage
    access        A human or system accessed transfer data via the API
    """

    def __init__(self, db: AsyncSession, actor_id: str = "system", actor_type: str = "system"):
        self._db = db
        self._actor_id = actor_id
        self._actor_type = actor_type

    async def log(
        self,
        *,
        event_type: str,
        patient_id: str,
        source_system: str,
        outcome: str,  # success | failure | partial
        resource_types: Optional[List[str]] = None,
        resource_count: int = 0,
        transfer_id: Optional[uuid.UUID] = None,
        destination_name: Optional[str] = None,
        detail: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Create and persist a single de-identified audit log entry."""
        entry = AuditLog(
            occurred_at=datetime.now(timezone.utc),
            patient_token=_patient_token(patient_id),
            transfer_id=transfer_id,
            event_type=event_type,
            actor_type=self._actor_type,
            actor_id=self._actor_id,
            source_system=source_system,
            destination_name=destination_name,
            resource_types=resource_types or [],
            resource_count=resource_count,
            outcome=outcome,
            detail=detail,
            extra=extra or {},
        )
        self._db.add(entry)
        await self._db.flush()
        logger.info(
            "AUDIT event=%s outcome=%s patient_token=%s... transfer=%s",
            event_type,
            outcome,
            entry.patient_token[:8],
            transfer_id,
        )
        return entry

    # ── Convenience helpers ───────────────────────────────────────────────────

    async def log_fhir_fetch(
        self,
        patient_id: str,
        source_system: str,
        resource_types: List[str],
        resource_count: int,
        transfer_id: Optional[uuid.UUID] = None,
        success: bool = True,
        detail: Optional[str] = None,
    ) -> AuditLog:
        return await self.log(
            event_type="fhir_fetch",
            patient_id=patient_id,
            source_system=source_system,
            outcome="success" if success else "failure",
            resource_types=resource_types,
            resource_count=resource_count,
            transfer_id=transfer_id,
            detail=detail,
        )

    async def log_transform(
        self,
        patient_id: str,
        source_system: str,
        resource_types: List[str],
        resource_count: int,
        transfer_id: Optional[uuid.UUID] = None,
        success: bool = True,
        detail: Optional[str] = None,
    ) -> AuditLog:
        return await self.log(
            event_type="transform",
            patient_id=patient_id,
            source_system=source_system,
            outcome="success" if success else "failure",
            resource_types=resource_types,
            resource_count=resource_count,
            transfer_id=transfer_id,
            detail=detail,
        )

    async def log_deliver(
        self,
        patient_id: str,
        source_system: str,
        destination_name: str,
        resource_types: List[str],
        resource_count: int,
        transfer_id: Optional[uuid.UUID] = None,
        success: bool = True,
        detail: Optional[str] = None,
    ) -> AuditLog:
        return await self.log(
            event_type="deliver",
            patient_id=patient_id,
            source_system=source_system,
            destination_name=destination_name,
            outcome="success" if success else "failure",
            resource_types=resource_types,
            resource_count=resource_count,
            transfer_id=transfer_id,
            detail=detail,
        )

    async def log_error(
        self,
        patient_id: str,
        source_system: str,
        detail: str,
        transfer_id: Optional[uuid.UUID] = None,
        destination_name: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        return await self.log(
            event_type="error",
            patient_id=patient_id,
            source_system=source_system,
            destination_name=destination_name,
            outcome="failure",
            transfer_id=transfer_id,
            detail=detail,
            extra=extra,
        )
