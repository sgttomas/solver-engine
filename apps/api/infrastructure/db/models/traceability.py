"""
TraceabilityLink Model - Forward/backward trace relationships.

Maps to 'traceability_links' table from 001_initial_schema.py.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db.models.base import Base

if TYPE_CHECKING:
    from infrastructure.db.models.workflow import Workflow


class TraceabilityLink(Base):
    """
    Traceability links between artifacts across steps.

    Links elements from earlier steps (stakeholders, requirements)
    to elements in later steps (requirements, objectives).

    Link types:
    - 'derives': Target derives from source
    - 'achieves': Target achieves source
    - 'traces_to': Generic trace relationship
    """

    __tablename__ = "traceability_links"

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

    # Source element
    from_step: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    from_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    from_id: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    # Target element
    to_step: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    to_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    to_id: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    # Link metadata
    link_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    consolidated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("FALSE"),
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Staleness tracking (Contract §7)
    stale: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("FALSE"),
    )

    stale_reason: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    stale_since: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    validated_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    # Relationships
    workflow: Mapped["Workflow"] = relationship(
        "Workflow",
        back_populates="traceability_links",
    )

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint(
            "workflow_id", "from_id", "to_id", "link_type",
            name="traceability_links_workflow_id_from_id_to_id_link_type_key",
        ),
        Index("idx_trace_workflow", "workflow_id"),
        Index("idx_trace_from", "from_id"),
        Index("idx_trace_to", "to_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<TraceabilityLink(id={self.id}, "
            f"{self.from_type}:{self.from_id} --[{self.link_type}]--> "
            f"{self.to_type}:{self.to_id})>"
        )
