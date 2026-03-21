"""Audit log query endpoints."""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.audit import AuditLog

router = APIRouter(prefix="/audit")


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    occurred_at: str
    patient_token: str
    transfer_id: Optional[uuid.UUID]
    event_type: str
    actor_type: str
    actor_id: str
    source_system: str
    destination_name: Optional[str]
    resource_types: list
    resource_count: int
    outcome: str
    detail: Optional[str]

    model_config = {"from_attributes": True}


class AuditListResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int
    page: int
    page_size: int


@router.get("", response_model=AuditListResponse, summary="Query audit logs")
async def list_audit_logs(
    db: AsyncSession = Depends(get_db),
    event_type: Optional[str] = Query(None),
    outcome: Optional[str] = Query(None),
    transfer_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    offset = (page - 1) * page_size
    q = select(AuditLog).order_by(AuditLog.occurred_at.desc())
    count_q = select(func.count()).select_from(AuditLog)

    filters = []
    if event_type:
        filters.append(AuditLog.event_type == event_type)
    if outcome:
        filters.append(AuditLog.outcome == outcome)
    if transfer_id:
        filters.append(AuditLog.transfer_id == transfer_id)

    for f in filters:
        q = q.where(f)
        count_q = count_q.where(f)

    total = (await db.execute(count_q)).scalar_one()
    rows = (await db.execute(q.offset(offset).limit(page_size))).scalars().all()

    return AuditListResponse(
        items=[
            AuditLogResponse(
                id=r.id,
                occurred_at=r.occurred_at.isoformat(),
                patient_token=r.patient_token,
                transfer_id=r.transfer_id,
                event_type=r.event_type,
                actor_type=r.actor_type,
                actor_id=r.actor_id,
                source_system=r.source_system,
                destination_name=r.destination_name,
                resource_types=r.resource_types,
                resource_count=r.resource_count,
                outcome=r.outcome,
                detail=r.detail,
            )
            for r in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
