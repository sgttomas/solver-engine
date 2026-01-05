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

        Per V2.8.0 Spec Appendix C.1: SSE envelope MUST include:
        - sequence: Monotonic per workflow
        - event_type: Event discriminator
        - workflow_id: External workflow ID string
        - timestamp: ISO 8601 server timestamp
        - position: Current workflow position object (REQUIRED)
        - actor_id: Optional actor attribution
        - payload: Optional event-specific data

        Returns:
            Dict suitable for SSE event payload with all required fields.
        """
        # Use external workflow_id from payload if available, otherwise fall back to FK
        external_workflow_id = self.payload.get("workflow_id", str(self.workflow_id))
        # Get instance_id from payload if available (per V2.8.0)
        instance_id = self.payload.get("instance_id", str(self.workflow_id))

        result = {
            "event_id": str(self.id),  # Event unique identifier (PK)
            "sequence": self.sequence,
            "event_type": self.event_type,
            "workflow_id": external_workflow_id,
            "instance_id": instance_id,  # Internal UUID per V2.8.0
            "timestamp": self.created_at.isoformat(),
        }

        # Position object is required per V2.8.0 spec
        if "position" in self.payload:
            result["position"] = self.payload["position"]
        else:
            # Fallback for legacy events without nested position
            result["position"] = {
                "instance_number": self.payload.get("instance_number", 1),
                "step_number": self.payload.get("step_number", 1),
                "step_name": self.payload.get("step_name", "unknown"),
                "pass_type": self.payload.get("pass_type", "definition"),
                "status": self.payload.get("data", {}).get("status", "unknown"),
                "phase": self.payload.get("data", {}).get("phase", "unknown"),
            }

        # Optional actor_id for user-initiated events
        if "actor_id" in self.payload:
            result["actor_id"] = self.payload["actor_id"]

        # Include remaining payload data (data field, artifact_id, etc.)
        # Exclude fields that are now top-level: workflow_id, instance_id, position, actor_id
        payload_data = {
            k: v for k, v in self.payload.items()
            if k not in ("workflow_id", "instance_id", "position", "actor_id")
        }
        if payload_data:
            result["payload"] = payload_data

        return result
