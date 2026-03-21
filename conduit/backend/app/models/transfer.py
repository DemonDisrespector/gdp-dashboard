"""Transfer ORM model."""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class TransferStatus(str, enum.Enum):
    pending = "pending"
    fetching = "fetching"
    transforming = "transforming"
    delivering = "delivering"
    completed = "completed"
    failed = "failed"
    retrying = "retrying"


class Transfer(Base):
    __tablename__ = "transfers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Source patient reference (hashed at rest – not raw MRN)
    patient_token: Mapped[str] = mapped_column(String(64), index=True)

    # FHIR source details
    source_system: Mapped[str] = mapped_column(String(128), default="modmed")
    source_patient_id: Mapped[str] = mapped_column(String(256))

    # Destination
    destination_type: Mapped[str] = mapped_column(
        String(32)
    )  # api | fhir_write | browser
    destination_name: Mapped[str] = mapped_column(String(256))
    destination_config: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Lifecycle
    status: Mapped[TransferStatus] = mapped_column(
        Enum(TransferStatus), default=TransferStatus.pending, index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(default=0)

    # Payload metadata (no PHI stored directly)
    resource_types: Mapped[list] = mapped_column(JSONB, default=list)
    resource_count: Mapped[int] = mapped_column(default=0)

    # Relationships
    audit_logs: Mapped[list["AuditLog"]] = relationship(  # noqa: F821
        back_populates="transfer", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_transfers_status_created", "status", "created_at"),
        Index("ix_transfers_patient_token_created", "patient_token", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Transfer {self.id} status={self.status}>"
