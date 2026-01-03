"""
StepExecution Model - Per-step state tracking.

Maps to 'step_executions' table from 001_initial_schema.py.
"""

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
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
    from infrastructure.db.models.message import Message


class StepExecution(Base):
    """
    Per-step execution state.

    Tracks the status and phase of each step within a workflow,
    including validation state and token usage.
    """

    __tablename__ = "step_executions"

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

    # Step identification
    pass_type: Mapped[PassType] = mapped_column(
        PassTypeEnum,
        nullable=False,
    )

    step_name: Mapped[StepName] = mapped_column(
        StepNameEnum,
        nullable=False,
    )

    step_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Step state (dual tracking per Doc 2)
    status: Mapped[StepStatus] = mapped_column(
        StepStatusEnum,
        nullable=False,
        server_default=text("'not_started'"),
    )

    phase: Mapped[StepPhase] = mapped_column(
        StepPhaseEnum,
        nullable=False,
        server_default=text("'received'"),
    )

    # Latest artifact reference (plain UUID, NOT a FK per migration)
    latest_artifact_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )

    # Human feedback
    human_feedback: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Clarification request
    clarification_request: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Validation state
    validation_status: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )

    validation_errors: Mapped[list] = mapped_column(
        JSONB,
        nullable=True,
        server_default=text("'[]'"),
    )

    validation_warnings: Mapped[list] = mapped_column(
        JSONB,
        nullable=True,
        server_default=text("'[]'"),
    )

    # Timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    # Usage tracking
    turn_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )

    total_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )

    # Relationships
    workflow: Mapped["Workflow"] = relationship(
        "Workflow",
        back_populates="step_executions",
    )

    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="step_execution",
        cascade="all, delete-orphan",
    )

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint(
            "workflow_id", "pass_type", "step_name",
            name="step_executions_workflow_id_pass_type_step_name_key",
        ),
        Index("idx_steps_workflow", "workflow_id"),
        Index("idx_steps_status", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<StepExecution(id={self.id}, "
            f"step={self.step_name.value}, "
            f"pass={self.pass_type.value}, "
            f"status={self.status.value})>"
        )
