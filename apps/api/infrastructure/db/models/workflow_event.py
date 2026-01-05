"""
WorkflowEvent Model - Durable event log for SSE replay.

Maps to 'workflow_events' table from 002_contract_alignment.py.
Implements Contract §9.2 (Event Log Contract).
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db.models.base import Base

if TYPE_CHECKING:
    from infrastructure.db.models.workflow import Workflow


class WorkflowEvent(Base):
    """
    Durable event log entry for workflow state transitions.

    Per Contract §9.2:
    - sequence MUST be monotonic and gap-free per workflow
    - (workflow_id, sequence) MUST be unique (DB-enforced)
    - Events MUST be durable before considered committed
    - Supports "events with sequence > N" queries for SSE replay
    """

    __tablename__ = "workflow_events"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )

    # Workflow reference
    workflow_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Monotonic sequence number per workflow
    sequence: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Event type discriminator
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # Event payload (JSON)
    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'"),
    )

    # Timestamp (maps to Contract field "timestamp")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Relationships
    workflow: Mapped["Workflow"] = relationship(
        "Workflow",
        back_populates="events",
    )

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint("workflow_id", "sequence", name="uq_workflow_events_sequence"),
        Index("idx_workflow_events_workflow", "workflow_id"),
        Index("idx_workflow_events_sequence", "workflow_id", "sequence"),
        Index("idx_workflow_events_created", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<WorkflowEvent(id={self.id}, workflow_id={self.workflow_id}, "
            f"sequence={self.sequence}, event_type='{self.event_type}')>"
        )

    def to_sse_dict(self) -> dict:
        """Convert to SSE-compatible dict with required fields.

        Per Contract §12.3: SSE payloads must include event_id, event_type, sequence.
        Uses existing id (PK) as event_id - no separate column needed.

        Returns:
            Dict suitable for SSE event payload with all required fields.
        """
        return {
            "event_id": str(self.id),  # Use existing PK as event_id
            "event_type": self.event_type,
            "sequence": self.sequence,
            "timestamp": self.created_at.isoformat(),
            "workflow_id": str(self.workflow_id),
            **self.payload,
        }
