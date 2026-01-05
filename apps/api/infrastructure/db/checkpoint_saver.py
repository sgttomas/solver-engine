"""
SolverCheckpointSaver - Custom LangGraph checkpoint saver for SOLVER.

Implements BaseCheckpointSaver interface using SOLVER's existing schema.
This is a deviation from Doc 3's reference to PostgresSaver due to
schema incompatibility (see docs/spec/DECISIONS.md P2.3 entry).

Key differences from langgraph-checkpoint-postgres:
- No checkpoint_ns column (hardcoded to "")
- No checkpoint_blobs table (values stored inline in checkpoint JSONB)
- Uses JSONB for writes.value instead of BYTEA blob
- No type column for writes
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator, Sequence
from contextlib import asynccontextmanager
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    WRITES_IDX_MAP,
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    get_checkpoint_id,
)
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from infrastructure.db.models import Checkpoint as CheckpointModel
from infrastructure.db.models import CheckpointWrite as CheckpointWriteModel


class SolverCheckpointSaver(BaseCheckpointSaver[str]):
    """Custom checkpoint saver using SOLVER's existing schema.

    Adapts LangGraph checkpoint interface to our checkpoints/checkpoint_writes
    tables which lack checkpoint_ns, checkpoint_blobs, and use JSONB instead
    of BYTEA for writes.

    Note: checkpoint_ns is treated as empty string (no subgraph support).

    Transaction Ownership:
        This saver does not auto-commit. The caller owns the transaction.
        For standalone use, wrap operations in async with session.begin().

    Usage:
        # With existing session factory
        saver = SolverCheckpointSaver(async_session_factory)

        # From connection string (Doc 3 API alignment)
        saver = SolverCheckpointSaver.from_conn_string(settings.postgres_url)
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        engine: AsyncEngine | None = None,
    ) -> None:
        """Initialize saver with async session factory.

        Args:
            session_factory: SQLAlchemy async session factory
            engine: Optional engine reference for cleanup
        """
        super().__init__()
        self._session_factory = session_factory
        self._engine = engine

    @classmethod
    def from_conn_string(cls, conn_string: str) -> "SolverCheckpointSaver":
        """Create saver from connection string (Doc 3 API alignment).

        Creates internal async engine and session factory.

        Args:
            conn_string: PostgreSQL connection string (asyncpg format)

        Returns:
            Configured SolverCheckpointSaver instance
        """
        engine = create_async_engine(conn_string, echo=False)
        factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        return cls(factory, engine=engine)

    @asynccontextmanager
    async def _get_session(self) -> AsyncIterator[AsyncSession]:
        """Get a session with automatic transaction management."""
        async with self._session_factory() as session:
            async with session.begin():
                yield session

    # =========================================================================
    # Sync Methods - Not Implemented (async-first API)
    # =========================================================================

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        """Sync get_tuple - not implemented.

        SOLVER uses async-first API. Use aget_tuple() instead.
        """
        raise NotImplementedError(
            "SOLVER uses async-first API. Use aget_tuple() instead."
        )

    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        """Sync list - not implemented.

        SOLVER uses async-first API. Use alist() instead.
        """
        raise NotImplementedError(
            "SOLVER uses async-first API. Use alist() instead."
        )

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        """Sync put - not implemented.

        SOLVER uses async-first API. Use aput() instead.
        """
        raise NotImplementedError(
            "SOLVER uses async-first API. Use aput() instead."
        )

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        """Sync put_writes - not implemented.

        SOLVER uses async-first API. Use aput_writes() instead.
        """
        raise NotImplementedError(
            "SOLVER uses async-first API. Use aput_writes() instead."
        )

    def delete_thread(self, thread_id: str) -> None:
        """Sync delete_thread - not implemented.

        SOLVER uses async-first API. Use adelete_thread() instead.
        """
        raise NotImplementedError(
            "SOLVER uses async-first API. Use adelete_thread() instead."
        )

    # =========================================================================
    # Async Methods - Full Implementation
    # =========================================================================

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        """Fetch a checkpoint tuple using the given configuration.

        Args:
            config: Configuration with thread_id and optional checkpoint_id

        Returns:
            CheckpointTuple if found, None otherwise
        """
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = get_checkpoint_id(config)

        async with self._get_session() as session:
            if checkpoint_id:
                # Get specific checkpoint
                stmt = select(CheckpointModel).where(
                    CheckpointModel.thread_id == thread_id,
                    CheckpointModel.checkpoint_id == checkpoint_id,
                )
            else:
                # Get latest checkpoint for thread
                stmt = (
                    select(CheckpointModel)
                    .where(CheckpointModel.thread_id == thread_id)
                    .order_by(CheckpointModel.checkpoint_id.desc())
                    .limit(1)
                )

            result = await session.execute(stmt)
            row = result.scalar_one_or_none()

            if row is None:
                return None

            # Get pending writes for this checkpoint
            writes_stmt = (
                select(CheckpointWriteModel)
                .where(
                    CheckpointWriteModel.thread_id == thread_id,
                    CheckpointWriteModel.checkpoint_id == row.checkpoint_id,
                )
                .order_by(CheckpointWriteModel.idx)
            )
            writes_result = await session.execute(writes_stmt)
            writes = list(writes_result.scalars().all())

            return self._row_to_tuple(row, writes)

    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[CheckpointTuple]:
        """List checkpoints that match the given criteria.

        Args:
            config: Base configuration for filtering (thread_id)
            filter: Additional filtering criteria for metadata
            before: List checkpoints before this checkpoint_id
            limit: Maximum number of checkpoints to return

        Yields:
            Matching checkpoint tuples in descending order
        """
        async with self._get_session() as session:
            stmt = select(CheckpointModel)

            # Apply filters
            if config:
                thread_id = config["configurable"]["thread_id"]
                stmt = stmt.where(CheckpointModel.thread_id == thread_id)

            if before:
                before_id = get_checkpoint_id(before)
                if before_id:
                    stmt = stmt.where(CheckpointModel.checkpoint_id < before_id)

            # Order by checkpoint_id DESC (newest first)
            stmt = stmt.order_by(CheckpointModel.checkpoint_id.desc())

            if limit is not None:
                stmt = stmt.limit(limit)

            result = await session.execute(stmt)
            rows = list(result.scalars().all())

            for row in rows:
                # Get writes for each checkpoint
                writes_stmt = (
                    select(CheckpointWriteModel)
                    .where(
                        CheckpointWriteModel.thread_id == row.thread_id,
                        CheckpointWriteModel.checkpoint_id == row.checkpoint_id,
                    )
                    .order_by(CheckpointWriteModel.idx)
                )
                writes_result = await session.execute(writes_stmt)
                writes = list(writes_result.scalars().all())

                yield self._row_to_tuple(row, writes)

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        """Store a checkpoint with its configuration and metadata.

        Uses get-then-update pattern for upsert safety.

        Args:
            config: Configuration for the checkpoint
            checkpoint: The checkpoint to store
            metadata: Additional metadata
            new_versions: New channel versions (stored in checkpoint)

        Returns:
            Updated configuration with checkpoint_id
        """
        thread_id = config["configurable"]["thread_id"]
        parent_checkpoint_id = get_checkpoint_id(config)
        checkpoint_id = checkpoint["id"]

        async with self._get_session() as session:
            # Check for existing checkpoint
            existing_stmt = select(CheckpointModel).where(
                CheckpointModel.thread_id == thread_id,
                CheckpointModel.checkpoint_id == checkpoint_id,
            )
            result = await session.execute(existing_stmt)
            existing = result.scalar_one_or_none()

            # Prepare checkpoint data for storage
            checkpoint_data = self._serialize_checkpoint(checkpoint)
            metadata_data = dict(metadata) if metadata else {}

            if existing is None:
                # Insert new checkpoint
                new_row = CheckpointModel(
                    thread_id=thread_id,
                    checkpoint_id=checkpoint_id,
                    parent_checkpoint_id=parent_checkpoint_id,
                    checkpoint=checkpoint_data,
                    metadata_=metadata_data,
                )
                session.add(new_row)
            else:
                # Update existing checkpoint
                existing.parent_checkpoint_id = parent_checkpoint_id
                existing.checkpoint = checkpoint_data
                existing.metadata_ = metadata_data

            await session.flush()

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": "",  # Not supported
                "checkpoint_id": checkpoint_id,
            }
        }

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        """Store intermediate writes linked to a checkpoint.

        Args:
            config: Configuration of the related checkpoint
            writes: List of (channel, value) tuples to store
            task_id: Identifier for the task creating the writes
            task_path: Path of the task (ignored - not in our schema)
        """
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = get_checkpoint_id(config)

        if not checkpoint_id:
            raise ValueError("checkpoint_id required in config for put_writes")

        async with self._get_session() as session:
            for idx, (channel, value) in enumerate(writes):
                # Use WRITES_IDX_MAP for special writes (errors, interrupts)
                write_idx = WRITES_IDX_MAP.get(channel, idx)

                # Check for existing write
                existing_stmt = select(CheckpointWriteModel).where(
                    CheckpointWriteModel.thread_id == thread_id,
                    CheckpointWriteModel.checkpoint_id == checkpoint_id,
                    CheckpointWriteModel.task_id == task_id,
                    CheckpointWriteModel.idx == write_idx,
                )
                result = await session.execute(existing_stmt)
                existing = result.scalar_one_or_none()

                # Serialize value for JSONB storage
                serialized_value = self._serialize_value(value)

                if existing is None:
                    # Insert new write
                    new_write = CheckpointWriteModel(
                        thread_id=thread_id,
                        checkpoint_id=checkpoint_id,
                        task_id=task_id,
                        idx=write_idx,
                        channel=channel,
                        value=serialized_value,
                    )
                    session.add(new_write)
                else:
                    # Update existing write
                    existing.channel = channel
                    existing.value = serialized_value

            await session.flush()

    async def adelete_thread(self, thread_id: str) -> None:
        """Delete all checkpoints and writes for a thread.

        Args:
            thread_id: The thread ID to delete
        """
        async with self._get_session() as session:
            # Delete writes first (no FK, but good practice)
            await session.execute(
                delete(CheckpointWriteModel).where(
                    CheckpointWriteModel.thread_id == thread_id
                )
            )

            # Delete checkpoints
            await session.execute(
                delete(CheckpointModel).where(
                    CheckpointModel.thread_id == thread_id
                )
            )

            await session.flush()

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _serialize_checkpoint(self, checkpoint: Checkpoint) -> dict[str, Any]:
        """Serialize a LangGraph checkpoint for JSONB storage.

        Stores the entire checkpoint dict directly since we don't have
        a separate checkpoint_blobs table.

        Handles dataclass and enum serialization for JSONB compatibility.
        """
        import dataclasses
        from datetime import datetime
        from enum import Enum

        def make_serializable(obj: Any) -> Any:
            """Recursively convert objects to JSON-serializable types."""
            if obj is None:
                return None
            if isinstance(obj, (str, int, float, bool)):
                return obj
            if isinstance(obj, Enum):
                return obj.value
            if isinstance(obj, datetime):
                return obj.isoformat()
            if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
                return {k: make_serializable(v) for k, v in dataclasses.asdict(obj).items()}
            if isinstance(obj, dict):
                return {k: make_serializable(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [make_serializable(item) for item in obj]
            # Fallback: try to convert to string
            return str(obj)

        # Store the full checkpoint structure with serialized values
        return make_serializable(dict(checkpoint))

    def _deserialize_checkpoint(self, data: dict[str, Any]) -> Checkpoint:
        """Deserialize a checkpoint from JSONB storage."""
        return Checkpoint(
            v=data.get("v", 1),
            id=data["id"],
            ts=data["ts"],
            channel_values=data.get("channel_values", {}),
            channel_versions=data.get("channel_versions", {}),
            versions_seen=data.get("versions_seen", {}),
            pending_sends=data.get("pending_sends", []),
            updated_channels=data.get("updated_channels"),
        )

    def _serialize_value(self, value: Any) -> dict[str, Any] | None:
        """Serialize a write value for JSONB storage.

        Uses serde for complex types, stores as base64 for JSONB compatibility.
        """
        import base64

        if value is None:
            return None
        # For JSONB, we store a wrapper with type info
        # serde.dumps_typed returns msgpack bytes, so we base64 encode
        type_str, serialized = self.serde.dumps_typed(value)
        if isinstance(serialized, bytes):
            serialized_str = base64.b64encode(serialized).decode("ascii")
        else:
            serialized_str = serialized
        return {
            "_type": type_str,
            "_value": serialized_str,
            "_encoding": "base64" if isinstance(serialized, bytes) else "raw",
        }

    def _deserialize_value(self, data: dict[str, Any] | None) -> Any:
        """Deserialize a write value from JSONB storage."""
        import base64

        if data is None:
            return None
        type_str = data.get("_type", "json")
        value = data.get("_value")
        encoding = data.get("_encoding", "base64")

        if encoding == "base64" and isinstance(value, str):
            value = base64.b64decode(value)
        elif isinstance(value, str):
            value = value.encode("utf-8")
        return self.serde.loads_typed((type_str, value))

    def _row_to_tuple(
        self,
        row: CheckpointModel,
        writes: list[CheckpointWriteModel],
    ) -> CheckpointTuple:
        """Convert database row to CheckpointTuple."""
        checkpoint = self._deserialize_checkpoint(row.checkpoint)

        # Build pending writes list: (task_id, channel, value)
        pending_writes = [
            (w.task_id, w.channel, self._deserialize_value(w.value))
            for w in writes
        ]

        # Build parent config if parent exists
        parent_config = None
        if row.parent_checkpoint_id:
            parent_config = {
                "configurable": {
                    "thread_id": row.thread_id,
                    "checkpoint_ns": "",
                    "checkpoint_id": row.parent_checkpoint_id,
                }
            }

        return CheckpointTuple(
            config={
                "configurable": {
                    "thread_id": row.thread_id,
                    "checkpoint_ns": "",  # Not supported
                    "checkpoint_id": row.checkpoint_id,
                }
            },
            checkpoint=checkpoint,
            metadata=row.metadata_,
            parent_config=parent_config,
            pending_writes=pending_writes if pending_writes else None,
        )

    def get_next_version(self, current: str | None, channel: None) -> str:
        """Generate the next version ID for a channel.

        Uses string versions with format "N.random" for uniqueness.
        """
        import random

        if current is None:
            current_v = 0
        elif isinstance(current, int):
            current_v = current
        else:
            current_v = int(current.split(".")[0])

        next_v = current_v + 1
        next_h = random.random()
        return f"{next_v:032}.{next_h:016}"
