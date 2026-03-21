"""Audit log ORM model – stores de-identified transfer events."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class AuditLog(Base):
    """
    HIPAA §164.312(b) – Audit Controls.

    PHI is never stored in this table. Patient identifiers are replaced with
    a one-way HMAC-SHA256 token derived from the patient ID and a server-side
    secret. Resource payloads are NOT persisted; only metadata is kept.
    """

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # De-identified patient reference
    patient_token: Mapped[str] = mapped_column(String(64), index=True)

    # Transfer linkage (nullable – some audit events are not transfer-scoped)
    transfer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transfers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    transfer: Mapped["Transfer"] = relationship(  # noqa: F821
        back_populates="audit_logs"
    )

    # Event taxonomy
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    # e.g. fhir_fetch | transform | deliver | error | access

    # Actor
    actor_type: Mapped[str] = mapped_column(String(32))  # system | user
    actor_id: Mapped[str] = mapped_column(String(256))

    # Non-PHI metadata
    source_system: Mapped[str] = mapped_column(String(128))
    destination_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    resource_types: Mapped[list] = mapped_column(JSONB, default=list)
    resource_count: Mapped[int] = mapped_column(default=0)
    outcome: Mapped[str] = mapped_column(String(16))  # success | failure | partial
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict)

    __table_args__ = (
        Index("ix_audit_logs_event_occurred", "event_type", "occurred_at"),
        Index("ix_audit_logs_outcome_occurred", "outcome", "occurred_at"),
        {"schema": None},  # Override via alembic env if audit schema differs
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.id} event={self.event_type} outcome={self.outcome}>"
