"""
ExecutionLock Model - Workflow execution lease management.

Maps to 'workflow_execution_locks' table from 006_add_workflow_execution_locks.py.
Per Tech Spec V2.8.4 Section 16.5 and Contract §15.2 (Exclusive Execution).
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.models.base import Base


class ExecutionLock(Base):
    """
    Workflow execution lock record.

    Tracks exclusive execution leases for workflows. Only one runner
    can hold a lease at a time. Expired leases can be taken over.

    Per Design Intent §4.8: Time-bounded leases stored in database,
    per-workflow, enabling crash recovery via expiry.
    """

    __tablename__ = "workflow_execution_locks"

    # Primary key (also foreign key to workflows)
    workflow_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Lock holder identifier (runner/process ID)
    locked_by: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # When lock was acquired
    locked_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # When lock expires (allows takeover)
    expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
    )

    # Index for finding expired locks
    __table_args__ = (
        Index("idx_locks_expiry", "expires_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<ExecutionLock(workflow_id={self.workflow_id}, "
            f"locked_by='{self.locked_by}', expires_at={self.expires_at})>"
        )

    @property
    def is_expired(self) -> bool:
        """Check if lock has expired."""
        return datetime.now(UTC) > self.expires_at
