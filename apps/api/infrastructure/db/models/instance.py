"""
Instance Model - Instance 0/1/N hierarchy.

Maps to 'instances' table from 001_initial_schema.py.
"""

from typing import Optional, List, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db.models.base import Base
from infrastructure.db.models.enums import (
    InstanceType,
    InstanceTypeEnum,
    GatePolicy,
    GatePolicyEnum,
)

if TYPE_CHECKING:
    from infrastructure.db.models.workflow import Workflow


class Instance(Base):
    """
    Instance hierarchy model.

    - Instance 0: Universal Methodology (abstract, domain-agnostic)
    - Instance 1: SOLVER Software Implementation
    - Instance N (N>=2): Domain Specializations
    """

    __tablename__ = "instances"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )

    # Instance identification
    instance_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        unique=True,
    )

    instance_type: Mapped[InstanceType] = mapped_column(
        InstanceTypeEnum,
        nullable=False,
    )

    # Self-referential parent relationship
    parent_instance_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("instances.id"),
        nullable=True,
    )

    # Descriptive fields
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Gate policy for Pass 1
    pass_1_gate_policy: Mapped[GatePolicy] = mapped_column(
        GatePolicyEnum,
        nullable=False,
        server_default=text("'per_step'"),
    )

    # Instance pack manifest (optional JSONB)
    pack_manifest: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Timestamp
    created_at: Mapped[TIMESTAMP] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Relationships
    parent: Mapped[Optional["Instance"]] = relationship(
        "Instance",
        remote_side=[id],
        back_populates="children",
    )

    children: Mapped[List["Instance"]] = relationship(
        "Instance",
        back_populates="parent",
    )

    workflows: Mapped[List["Workflow"]] = relationship(
        "Workflow",
        back_populates="instance",
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            """
            (instance_number = 0 AND instance_type = 'universal' AND parent_instance_id IS NULL) OR
            (instance_number = 1 AND instance_type = 'implementation') OR
            (instance_number >= 2 AND instance_type = 'domain')
            """,
            name="valid_instance_hierarchy",
        ),
    )

    def __repr__(self) -> str:
        return f"<Instance(id={self.id}, number={self.instance_number}, name='{self.name}')>"
