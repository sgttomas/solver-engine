"""
Checkpoint Models - LangGraph state persistence.

Maps to 'checkpoints' and 'checkpoint_writes' tables from 001_initial_schema.py.

These tables use composite primary keys (no surrogate id column)
as required by LangGraph's PostgresSaver.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.models.base import Base


class Checkpoint(Base):
    """
    LangGraph checkpoint storage.

    Stores serialized graph state for interrupt/resume functionality.
    Uses composite primary key (thread_id, checkpoint_id).
    """

    __tablename__ = "checkpoints"

    # Composite primary key components
    thread_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    checkpoint_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Parent checkpoint for history chain
    parent_checkpoint_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # Serialized checkpoint state
    checkpoint: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    # Checkpoint metadata - mapped to 'metadata_' to avoid SQLAlchemy clash
    metadata_: Mapped[dict] = mapped_column(
        "metadata",  # Actual column name in DB
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

    # Composite primary key and indexes
    __table_args__ = (
        PrimaryKeyConstraint("thread_id", "checkpoint_id"),
        Index("idx_checkpoints_thread", "thread_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<Checkpoint(thread_id='{self.thread_id}', "
            f"checkpoint_id='{self.checkpoint_id}')>"
        )


class CheckpointWrite(Base):
    """
    LangGraph checkpoint writes.

    Stores individual channel writes within a checkpoint for
    fine-grained state tracking.

    Uses composite primary key (thread_id, checkpoint_id, task_id, idx).
    Note: This table has no id, no created_at - minimal LangGraph schema.
    """

    __tablename__ = "checkpoint_writes"

    # Composite primary key components
    thread_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    checkpoint_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    task_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    idx: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Channel data
    channel: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    value: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Composite primary key
    __table_args__ = (
        PrimaryKeyConstraint("thread_id", "checkpoint_id", "task_id", "idx"),
    )

    def __repr__(self) -> str:
        return (
            f"<CheckpointWrite(thread_id='{self.thread_id}', "
            f"checkpoint_id='{self.checkpoint_id}', "
            f"task_id='{self.task_id}', idx={self.idx})>"
        )
