"""Transfer management endpoints."""
import uuid
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.transfer import Transfer, TransferStatus
from app.services.transfer_service import TransferService

router = APIRouter(prefix="/transfers")


# ── Schemas ───────────────────────────────────────────────────────────────────

class TransferRequest(BaseModel):
    source_patient_id: str = Field(..., description="FHIR Patient resource ID at source")
    source_system: str = Field(default="modmed")
    destination_type: str = Field(..., pattern="^(api|fhir_write|browser)$")
    destination_name: str
    destination_config: dict = Field(default_factory=dict)
    resource_types: List[str] = Field(
        default=[
            "Patient", "Coverage", "Condition", "Procedure",
            "ServiceRequest", "Practitioner", "DocumentReference",
            "AllergyIntolerance", "MedicationRequest",
        ]
    )


class TransferResponse(BaseModel):
    id: uuid.UUID
    status: TransferStatus
    source_system: str
    destination_type: str
    destination_name: str
    resource_types: list
    resource_count: int
    retry_count: int
    error_message: Optional[str]
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class TransferListResponse(BaseModel):
    items: List[TransferResponse]
    total: int
    page: int
    page_size: int


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=TransferResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Initiate a new patient referral transfer",
)
async def create_transfer(
    body: TransferRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    service = TransferService(db)
    transfer = await service.create_transfer(body.model_dump())
    background_tasks.add_task(service.execute_transfer, transfer.id)
    return _to_response(transfer)


@router.get("", response_model=TransferListResponse, summary="List transfers")
async def list_transfers(
    db: AsyncSession = Depends(get_db),
    status_filter: Optional[TransferStatus] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    offset = (page - 1) * page_size
    q = select(Transfer).order_by(Transfer.created_at.desc())
    count_q = select(func.count()).select_from(Transfer)
    if status_filter:
        q = q.where(Transfer.status == status_filter)
        count_q = count_q.where(Transfer.status == status_filter)
    total = (await db.execute(count_q)).scalar_one()
    rows = (await db.execute(q.offset(offset).limit(page_size))).scalars().all()
    return TransferListResponse(
        items=[_to_response(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{transfer_id}", response_model=TransferResponse, summary="Get transfer detail")
async def get_transfer(transfer_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    transfer = await db.get(Transfer, transfer_id)
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    return _to_response(transfer)


@router.post("/{transfer_id}/retry", response_model=TransferResponse, summary="Retry a failed transfer")
async def retry_transfer(
    transfer_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    transfer = await db.get(Transfer, transfer_id)
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    if transfer.status not in (TransferStatus.failed,):
        raise HTTPException(status_code=409, detail=f"Cannot retry transfer in status '{transfer.status}'")
    service = TransferService(db)
    transfer = await service.reset_for_retry(transfer)
    background_tasks.add_task(service.execute_transfer, transfer.id)
    return _to_response(transfer)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_response(t: Transfer) -> TransferResponse:
    return TransferResponse(
        id=t.id,
        status=t.status,
        source_system=t.source_system,
        destination_type=t.destination_type,
        destination_name=t.destination_name,
        resource_types=t.resource_types,
        resource_count=t.resource_count,
        retry_count=t.retry_count,
        error_message=t.error_message,
        created_at=t.created_at.isoformat(),
        updated_at=t.updated_at.isoformat(),
    )
