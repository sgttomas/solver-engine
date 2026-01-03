"""
Workflow Model - Master workflow record.

Maps to 'workflows' table from 001_initial_schema.py.
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
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db.models.base import Base
from infrastructure.db.models.enums import (
    PassType,
    PassTypeEnum,
    StepName,
    StepNameEnum,
    WorkflowStatus,
    WorkflowStatusEnum,
    GatePolicy,
    GatePolicyEnum,
)

if TYPE_CHECKING:
    from infrastructure.db.models.instance import Instance
    from infrastructure.db.models.step_execution import StepExecution
    from infrastructure.db.models.artifact import Artifact
    from infrastructure.db.models.traceability import TraceabilityLink
    from infrastructure.db.models.message import Message
    from infrastructure.db.models.audit import AuditLog


class Workflow(Base):
    """
    Master workflow record.

    Tracks the overall state of a structured reasoning workflow,
    including current position (pass/step) and status.
    """

    __tablename__ = "workflows"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )

    # Unique identifiers
    workflow_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    thread_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    # Instance reference
    instance_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("instances.id"),
        nullable=False,
    )

    # Problem definition
    original_problem: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    domain: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # Current position
    current_pass: Mapped[PassType] = mapped_column(
        PassTypeEnum,
        nullable=False,
        server_default=text("'definition'"),
    )

    current_step: Mapped[StepName] = mapped_column(
        StepNameEnum,
        nullable=False,
        server_default=text("'problem_definition'"),
    )

    current_step_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("1"),
    )

    # Workflow status
    status: Mapped[WorkflowStatus] = mapped_column(
        WorkflowStatusEnum,
        nullable=False,
        server_default=text("'active'"),
    )

    # Gate policy
    pass_1_gate_policy: Mapped[GatePolicy] = mapped_column(
        GatePolicyEnum,
        nullable=False,
        server_default=text("'per_step'"),
    )

    # Actor tracking
    created_by: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    last_actor_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    # Relationships
    instance: Mapped["Instance"] = relationship(
        "Instance",
        back_populates="workflows",
    )

    step_executions: Mapped[List["StepExecution"]] = relationship(
        "StepExecution",
        back_populates="workflow",
        cascade="all, delete-orphan",
    )

    artifacts: Mapped[List["Artifact"]] = relationship(
        "Artifact",
        back_populates="workflow",
        cascade="all, delete-orphan",
    )

    traceability_links: Mapped[List["TraceabilityLink"]] = relationship(
        "TraceabilityLink",
        back_populates="workflow",
        cascade="all, delete-orphan",
    )

    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="workflow",
        cascade="all, delete-orphan",
    )

    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="workflow",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("idx_workflows_thread", "thread_id"),
        Index("idx_workflows_instance", "instance_id"),
        Index("idx_workflows_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<Workflow(id={self.id}, workflow_id='{self.workflow_id}', status={self.status.value})>"
