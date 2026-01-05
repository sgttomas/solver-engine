"""
Artifact Model - Pass 1 methodology + Pass 2 packages.

Maps to 'artifacts' table from 001_initial_schema.py.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
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
    DocumentType,
    DocumentTypeEnum,
    DocumentVersion,
    DocumentVersionEnum,
)

if TYPE_CHECKING:
    from infrastructure.db.models.workflow import Workflow


class Artifact(Base):
    """
    Artifact storage for methodology documents and step packages.

    Two artifact types:
    - 'methodology_doc': Pass 1 documents (DataSheet, ToDoList, etc.) with markdown content
    - 'step_package': Pass 2 deliverables (ProblemDefinitionPackage, etc.) with JSONB content
    """

    __tablename__ = "artifacts"

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

    # Artifact type discriminator
    artifact_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # Methodology doc fields (artifact_type = 'methodology_doc')
    document_type: Mapped[Optional[DocumentType]] = mapped_column(
        DocumentTypeEnum,
        nullable=True,
    )

    document_version: Mapped[Optional[DocumentVersion]] = mapped_column(
        DocumentVersionEnum,
        nullable=True,
    )

    content_markdown: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Step package fields (artifact_type = 'step_package')
    package_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    content_jsonb: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
    )

    revision: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("1"),
    )

    # Schema validation
    schema_version: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )

    validation_status: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Lineage tracking (Contract §7 - insert-per-revision model)
    supersedes: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("artifacts.id"),
        nullable=True,
    )

    superseded_by: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("artifacts.id"),
        nullable=True,
    )

    # Staleness tracking (Contract §9.4)
    # Note: Column is 'stale' per spec, not 'is_stale'
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

    # Relationships
    workflow: Mapped["Workflow"] = relationship(
        "Workflow",
        back_populates="artifacts",
    )

    # Constraints and indexes
    __table_args__ = (
        CheckConstraint(
            """
            (artifact_type = 'methodology_doc' AND document_type IS NOT NULL AND document_version IS NOT NULL) OR
            (artifact_type = 'step_package' AND package_type IS NOT NULL AND content_jsonb IS NOT NULL)
            """,
            name="valid_artifact_type",
        ),
        Index("idx_artifacts_workflow", "workflow_id"),
        Index("idx_artifacts_step", "step_name"),
    )

    def __repr__(self) -> str:
        if self.artifact_type == "methodology_doc":
            return (
                f"<Artifact(id={self.id}, type='methodology_doc', "
                f"doc={self.document_type.value if self.document_type else None}, "
                f"version={self.document_version.value if self.document_version else None})>"
            )
        else:
            return (
                f"<Artifact(id={self.id}, type='step_package', "
                f"package={self.package_type}, revision={self.revision})>"
            )
