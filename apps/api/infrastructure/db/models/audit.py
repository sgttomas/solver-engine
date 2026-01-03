"""
AuditLog Model - Immutable event record.

Maps to 'audit_log' table from 001_initial_schema.py.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db.models.base import Base
from infrastructure.db.models.enums import (
    PassType,
    PassTypeEnum,
    StepName,
    StepNameEnum,
    StepStatus,
    StepStatusEnum,
    StepPhase,
    StepPhaseEnum,
)

if TYPE_CHECKING:
    from infrastructure.db.models.workflow import Workflow


class AuditLog(Base):
    """
    Immutable audit log entry.

    Records all state transitions and human actions for full
    timeline reconstruction (Gate F requirement).

    Note: artifact_id is a plain UUID, NOT a foreign key, to allow
    loose coupling and avoid circular deletion issues.
    """

    __tablename__ = "audit_log"

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

    # Event identification
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    actor_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Step context (optional - not all events are step-specific)
    pass_type: Mapped[Optional[PassType]] = mapped_column(
        PassTypeEnum,
        nullable=True,
    )

    step_name: Mapped[Optional[StepName]] = mapped_column(
        StepNameEnum,
        nullable=True,
    )

    step_number: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    # State transition tracking
    from_status: Mapped[Optional[StepStatus]] = mapped_column(
        StepStatusEnum,
        nullable=True,
    )

    to_status: Mapped[Optional[StepStatus]] = mapped_column(
        StepStatusEnum,
        nullable=True,
    )

    from_phase: Mapped[Optional[StepPhase]] = mapped_column(
        StepPhaseEnum,
        nullable=True,
    )

    to_phase: Mapped[Optional[StepPhase]] = mapped_column(
        StepPhaseEnum,
        nullable=True,
    )

    # Artifact reference (plain UUID, NOT a foreign key)
    artifact_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )

    # Additional event details
    details: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'"),
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Relationships
    workflow: Mapped["Workflow"] = relationship(
        "Workflow",
        back_populates="audit_logs",
    )

    # Indexes
    __table_args__ = (
        Index("idx_audit_workflow", "workflow_id"),
        Index("idx_audit_event", "event_type"),
        Index("idx_audit_created", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, event={self.event_type}, "
            f"actor={self.actor_id}, step={self.step_name})>"
        )
