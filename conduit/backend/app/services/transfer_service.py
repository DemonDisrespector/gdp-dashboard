"""
Transfer orchestration service.

Coordinates the full lifecycle of a patient referral transfer:
1. Create Transfer record
2. Fetch FHIR resources from source (ModMed)
3. Transform to destination format
4. Deliver via the appropriate connector
5. Audit-log every stage
"""
import hashlib
import hmac
import logging
import uuid
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.logger import AuditLogger
from app.config import get_settings
from app.connectors import get_connector
from app.fhir.client import FHIRClient
from app.models.transfer import Transfer, TransferStatus
from app.transform.engine import TransformEngine

logger = logging.getLogger(__name__)
settings = get_settings()


def _patient_token(patient_id: str) -> str:
    return hmac.new(
        settings.encryption_key.encode(),
        patient_id.encode(),
        hashlib.sha256,
    ).hexdigest()


class TransferService:
    def __init__(self, db: AsyncSession):
        self._db = db

    # ── Transfer lifecycle ────────────────────────────────────────────────────

    async def create_transfer(self, data: Dict[str, Any]) -> Transfer:
        transfer = Transfer(
            patient_token=_patient_token(data["source_patient_id"]),
            source_system=data.get("source_system", "modmed"),
            source_patient_id=data["source_patient_id"],
            destination_type=data["destination_type"],
            destination_name=data["destination_name"],
            destination_config=data.get("destination_config", {}),
            resource_types=data.get("resource_types", []),
            status=TransferStatus.pending,
        )
        self._db.add(transfer)
        await self._db.flush()
        logger.info("Created transfer %s for patient_token=%s…", transfer.id, transfer.patient_token[:8])
        return transfer

    async def reset_for_retry(self, transfer: Transfer) -> Transfer:
        transfer.status = TransferStatus.pending
        transfer.error_message = None
        transfer.retry_count += 1
        await self._db.flush()
        return transfer

    async def execute_transfer(self, transfer_id: uuid.UUID) -> None:
        """
        Full transfer pipeline – runs in a background task.
        Opens its own session to be independent of the request lifecycle.
        """
        from app.db import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            transfer = await db.get(Transfer, transfer_id)
            if not transfer:
                logger.error("Transfer %s not found", transfer_id)
                return
            audit = AuditLogger(db)
            try:
                await self._run_pipeline(transfer, db, audit)
                await db.commit()
            except Exception as exc:
                logger.exception("Transfer %s failed: %s", transfer_id, exc)
                transfer.status = TransferStatus.failed
                transfer.error_message = str(exc)[:1000]
                await audit.log_error(
                    patient_id=transfer.source_patient_id,
                    source_system=transfer.source_system,
                    destination_name=transfer.destination_name,
                    transfer_id=transfer.id,
                    detail=str(exc),
                )
                await db.commit()

    async def _run_pipeline(
        self,
        transfer: Transfer,
        db: AsyncSession,
        audit: AuditLogger,
    ) -> None:
        patient_id = transfer.source_patient_id
        resource_types = transfer.resource_types

        # ── 1. Fetch ──────────────────────────────────────────────────────────
        transfer.status = TransferStatus.fetching
        await db.flush()

        fhir_client = FHIRClient(settings)
        try:
            bundle = await fhir_client.get_patient_everything(patient_id)
            resource_count = len(bundle.get("entry", []))
            await audit.log_fhir_fetch(
                patient_id=patient_id,
                source_system=transfer.source_system,
                resource_types=resource_types,
                resource_count=resource_count,
                transfer_id=transfer.id,
                success=True,
            )
            logger.info("Fetched %d resources for transfer %s", resource_count, transfer.id)
        except Exception as exc:
            await audit.log_fhir_fetch(
                patient_id=patient_id,
                source_system=transfer.source_system,
                resource_types=resource_types,
                resource_count=0,
                transfer_id=transfer.id,
                success=False,
                detail=str(exc),
            )
            raise
        finally:
            await fhir_client.close()

        # ── 2. Transform ──────────────────────────────────────────────────────
        transfer.status = TransferStatus.transforming
        await db.flush()

        try:
            engine = TransformEngine(destination=transfer.destination_name)
            transformed = engine.transform_bundle(bundle)
            await audit.log_transform(
                patient_id=patient_id,
                source_system=transfer.source_system,
                resource_types=resource_types,
                resource_count=len(transformed),
                transfer_id=transfer.id,
                success=True,
            )
        except Exception as exc:
            await audit.log_transform(
                patient_id=patient_id,
                source_system=transfer.source_system,
                resource_types=resource_types,
                resource_count=0,
                transfer_id=transfer.id,
                success=False,
                detail=str(exc),
            )
            raise

        # ── 3. Deliver ────────────────────────────────────────────────────────
        transfer.status = TransferStatus.delivering
        await db.flush()

        connector = get_connector(
            transfer.destination_type,
            transfer.destination_config,
        )
        async with connector:
            result = await connector.send(transformed)

        await audit.log_deliver(
            patient_id=patient_id,
            source_system=transfer.source_system,
            destination_name=transfer.destination_name,
            resource_types=resource_types,
            resource_count=result.records_sent,
            transfer_id=transfer.id,
            success=result.success,
            detail=result.error_message,
        )

        if not result.success:
            raise RuntimeError(f"Delivery failed: {result.error_message}")

        # ── 4. Complete ───────────────────────────────────────────────────────
        transfer.status = TransferStatus.completed
        transfer.resource_count = result.records_sent
        logger.info("Transfer %s completed – %d records delivered", transfer.id, result.records_sent)
