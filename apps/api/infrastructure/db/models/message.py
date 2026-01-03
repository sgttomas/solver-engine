"""
Message Model - Conversation history.

Maps to 'messages' table from 001_initial_schema.py.
"""

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Column,
    ForeignKey,
    Index,
    Integer,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db.models.base import Base
from infrastructure.db.models.enums import MessageRole, MessageRoleEnum

# pgvector support
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    # Fallback if pgvector not installed - will fail at runtime if used
    Vector = None

if TYPE_CHECKING:
    from infrastructure.db.models.workflow import Workflow
    from infrastructure.db.models.step_execution import StepExecution


class Message(Base):
    """
    Conversation message in a workflow.

    Stores user, assistant, and system messages with optional embeddings
    for semantic search.
    """

    __tablename__ = "messages"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )

    # Workflow and step references
    workflow_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
    )

    step_execution_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("step_executions.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Message content
    role: Mapped[MessageRole] = mapped_column(
        MessageRoleEnum,
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Metadata - mapped to 'metadata_' to avoid SQLAlchemy attribute clash
    metadata_: Mapped[dict] = mapped_column(
        "metadata",  # Actual column name in DB
        JSONB,
        nullable=False,
        server_default=text("'{}'"),
    )

    # Token tracking
    input_tokens: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    output_tokens: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Vector embedding for semantic search
    # Using Column() directly since mapped_column doesn't work well with Vector
    embedding: Mapped[Optional[List[float]]] = Column(
        Vector(1536) if Vector else None,
        nullable=True,
    )

    # Relationships
    workflow: Mapped["Workflow"] = relationship(
        "Workflow",
        back_populates="messages",
    )

    step_execution: Mapped["StepExecution"] = relationship(
        "StepExecution",
        back_populates="messages",
    )

    # Indexes
    __table_args__ = (
        Index("idx_messages_workflow", "workflow_id"),
        Index("idx_messages_step", "step_execution_id"),
        # Note: ivfflat index with vector_cosine_ops is created in migration
        # SQLAlchemy doesn't support USING clause directly, but the index exists in DB
        Index(
            "idx_messages_embedding",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    def __repr__(self) -> str:
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<Message(id={self.id}, role={self.role.value}, content='{content_preview}')>"
