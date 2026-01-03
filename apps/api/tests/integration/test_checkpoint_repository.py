"""
Integration tests for CheckpointRepository.

Tests composite primary key handling.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import Checkpoint, CheckpointWrite
from infrastructure.db.repositories import CheckpointRepository, CheckpointWriteRepository


class TestCheckpointRepository:
    """Tests for CheckpointRepository with composite PK."""

    @pytest.mark.asyncio
    async def test_put_creates_new_checkpoint(
        self,
        db_session: AsyncSession,
    ):
        """Test creating a new checkpoint via put (upsert)."""
        repo = CheckpointRepository(db_session)

        checkpoint = Checkpoint(
            thread_id="test-thread-cp",
            checkpoint_id="cp-001",
            parent_checkpoint_id=None,
            checkpoint={"state": "initial", "step": 1},
            metadata_={"source": "test"},
        )

        result = await repo.put(checkpoint)

        assert result is not None
        assert result.thread_id == "test-thread-cp"
        assert result.checkpoint_id == "cp-001"
        assert result.checkpoint == {"state": "initial", "step": 1}
        assert result.created_at is not None

    @pytest.mark.asyncio
    async def test_put_updates_existing_checkpoint(
        self,
        db_session: AsyncSession,
    ):
        """Test updating an existing checkpoint via put (upsert)."""
        repo = CheckpointRepository(db_session)

        # Create initial
        checkpoint1 = Checkpoint(
            thread_id="test-thread-upsert",
            checkpoint_id="cp-upsert",
            parent_checkpoint_id=None,
            checkpoint={"state": "v1"},
            metadata_={"version": 1},
        )
        await repo.put(checkpoint1)

        # Update via put
        checkpoint2 = Checkpoint(
            thread_id="test-thread-upsert",
            checkpoint_id="cp-upsert",
            parent_checkpoint_id="cp-000",
            checkpoint={"state": "v2"},
            metadata_={"version": 2},
        )
        result = await repo.put(checkpoint2)

        assert result.checkpoint == {"state": "v2"}
        assert result.parent_checkpoint_id == "cp-000"

    @pytest.mark.asyncio
    async def test_get_by_composite_pk(
        self,
        db_session: AsyncSession,
    ):
        """Test getting checkpoint by composite primary key."""
        repo = CheckpointRepository(db_session)

        # Create checkpoint
        checkpoint = Checkpoint(
            thread_id="test-get-thread",
            checkpoint_id="test-get-cp",
            checkpoint={"data": "test"},
            metadata_={},
        )
        await repo.put(checkpoint)

        # Get by composite PK
        result = await repo.get("test-get-thread", "test-get-cp")

        assert result is not None
        assert result.thread_id == "test-get-thread"
        assert result.checkpoint_id == "test-get-cp"

    @pytest.mark.asyncio
    async def test_get_returns_none_for_missing(
        self,
        db_session: AsyncSession,
    ):
        """Test that missing checkpoint returns None."""
        repo = CheckpointRepository(db_session)

        result = await repo.get("nonexistent", "nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_list_for_thread(
        self,
        db_session: AsyncSession,
    ):
        """Test listing all checkpoints for a thread."""
        repo = CheckpointRepository(db_session)

        # Create multiple checkpoints
        for i in range(3):
            checkpoint = Checkpoint(
                thread_id="test-list-thread",
                checkpoint_id=f"cp-{i:03d}",
                parent_checkpoint_id=f"cp-{i-1:03d}" if i > 0 else None,
                checkpoint={"step": i},
                metadata_={},
            )
            await repo.put(checkpoint)

        results = await repo.list_for_thread("test-list-thread")

        assert len(results) == 3
        # Should be ordered by created_at
        steps = [r.checkpoint["step"] for r in results]
        assert steps == [0, 1, 2]

    @pytest.mark.asyncio
    async def test_delete_checkpoint(
        self,
        db_session: AsyncSession,
    ):
        """Test deleting a checkpoint."""
        repo = CheckpointRepository(db_session)

        # Create and then delete
        checkpoint = Checkpoint(
            thread_id="test-delete-thread",
            checkpoint_id="cp-delete",
            checkpoint={"to": "delete"},
            metadata_={},
        )
        await repo.put(checkpoint)

        await repo.delete("test-delete-thread", "cp-delete")

        result = await repo.get("test-delete-thread", "cp-delete")
        assert result is None


class TestCheckpointWriteRepository:
    """Tests for CheckpointWriteRepository with composite PK."""

    @pytest.mark.asyncio
    async def test_put_creates_checkpoint_write(
        self,
        db_session: AsyncSession,
    ):
        """Test creating a checkpoint write."""
        repo = CheckpointWriteRepository(db_session)

        write = CheckpointWrite(
            thread_id="test-write-thread",
            checkpoint_id="cp-write",
            task_id="task-001",
            idx=0,
            channel="messages",
            value={"content": "Hello"},
        )

        result = await repo.put(write)

        assert result is not None
        assert result.thread_id == "test-write-thread"
        assert result.channel == "messages"
        assert result.value == {"content": "Hello"}

    @pytest.mark.asyncio
    async def test_get_by_composite_pk(
        self,
        db_session: AsyncSession,
    ):
        """Test getting checkpoint write by 4-part composite PK."""
        repo = CheckpointWriteRepository(db_session)

        write = CheckpointWrite(
            thread_id="test-get-write",
            checkpoint_id="cp-get-write",
            task_id="task-get",
            idx=5,
            channel="state",
            value={"key": "value"},
        )
        await repo.put(write)

        result = await repo.get("test-get-write", "cp-get-write", "task-get", 5)

        assert result is not None
        assert result.idx == 5
        assert result.channel == "state"

    @pytest.mark.asyncio
    async def test_list_for_checkpoint(
        self,
        db_session: AsyncSession,
    ):
        """Test listing all writes for a checkpoint."""
        repo = CheckpointWriteRepository(db_session)

        # Create multiple writes
        for i in range(3):
            write = CheckpointWrite(
                thread_id="test-list-write",
                checkpoint_id="cp-list-write",
                task_id="task-list",
                idx=i,
                channel=f"channel-{i}",
                value={"idx": i},
            )
            await repo.put(write)

        results = await repo.list_for_checkpoint("test-list-write", "cp-list-write")

        assert len(results) == 3
        # Should be ordered by idx
        indices = [r.idx for r in results]
        assert indices == [0, 1, 2]
