"""
Integration tests for SolverCheckpointSaver.

Tests the custom LangGraph checkpoint saver against real PostgreSQL.
P2.3 scope: raw saver operations only (no LangGraph graph wiring).
"""

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings
from infrastructure.db.checkpoint_saver import SolverCheckpointSaver
from infrastructure.db.models import Checkpoint as CheckpointModel


def make_thread_id() -> str:
    """Generate unique thread_id for test isolation."""
    return f"test-thread-{uuid4()}"


def make_checkpoint_id(step: int = 0) -> str:
    """Generate checkpoint_id with sortable format."""
    # LangGraph uses uuid6 which is time-sortable
    # We use a simpler format for testing
    return f"1ef00000-0000-0000-0000-{step:012d}"


def make_checkpoint(checkpoint_id: str, step: int = 0) -> dict:
    """Create a minimal valid LangGraph checkpoint dict."""
    return {
        "v": 2,
        "id": checkpoint_id,
        "ts": datetime.now(timezone.utc).isoformat(),
        "channel_values": {"count": step, "messages": []},
        "channel_versions": {"count": "1.0", "messages": "1.0"},
        "versions_seen": {"node1": {"count": "1.0"}},
        "pending_sends": [],
        "updated_channels": None,
    }


class TestSolverCheckpointSaver:
    """Tests for SolverCheckpointSaver round-trip operations."""

    @pytest_asyncio.fixture
    async def saver(self) -> SolverCheckpointSaver:
        """Create a checkpoint saver with its own engine.

        Uses unique thread_ids per test for isolation instead of
        transaction rollback (saver manages its own transactions).
        """
        engine = create_async_engine(settings.postgres_url, echo=False)
        factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        saver = SolverCheckpointSaver(factory, engine=engine)
        # Track thread_ids for cleanup
        saver._test_thread_ids = []
        yield saver
        # Cleanup test data
        for thread_id in getattr(saver, '_test_thread_ids', []):
            try:
                await saver.adelete_thread(thread_id)
            except Exception:
                pass  # Ignore cleanup errors
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_put_and_get_checkpoint(
        self,
        saver: SolverCheckpointSaver,
    ):
        """Test basic round-trip: write checkpoint, read back, verify equality."""
        thread_id = make_thread_id()
        checkpoint_id = make_checkpoint_id(0)
        checkpoint = make_checkpoint(checkpoint_id, step=0)
        metadata = {"source": "input", "step": 0}

        config = {"configurable": {"thread_id": thread_id}}

        # Put checkpoint
        result_config = await saver.aput(config, checkpoint, metadata, {})

        assert result_config["configurable"]["thread_id"] == thread_id
        assert result_config["configurable"]["checkpoint_id"] == checkpoint_id

        # Get checkpoint back
        tuple_result = await saver.aget_tuple(result_config)

        assert tuple_result is not None
        assert tuple_result.checkpoint["id"] == checkpoint_id
        assert tuple_result.checkpoint["v"] == 2
        assert tuple_result.checkpoint["channel_values"]["count"] == 0
        assert tuple_result.metadata["source"] == "input"

    @pytest.mark.asyncio
    async def test_put_writes_and_retrieve(
        self,
        saver: SolverCheckpointSaver,
    ):
        """Test writes attached to checkpoint, verify in pending_writes."""
        thread_id = make_thread_id()
        checkpoint_id = make_checkpoint_id(0)
        checkpoint = make_checkpoint(checkpoint_id, step=0)
        metadata = {"source": "loop", "step": 1}

        config = {"configurable": {"thread_id": thread_id}}

        # Put checkpoint first
        result_config = await saver.aput(config, checkpoint, metadata, {})

        # Put writes
        writes = [
            ("messages", {"role": "user", "content": "Hello"}),
            ("count", 42),
        ]
        await saver.aput_writes(result_config, writes, task_id="task-001")

        # Get checkpoint with writes
        tuple_result = await saver.aget_tuple(result_config)

        assert tuple_result is not None
        assert tuple_result.pending_writes is not None
        assert len(tuple_result.pending_writes) == 2

        # Verify write content (task_id, channel, value)
        channels = {w[1] for w in tuple_result.pending_writes}
        assert "messages" in channels
        assert "count" in channels

    @pytest.mark.asyncio
    async def test_list_checkpoints_ordered(
        self,
        saver: SolverCheckpointSaver,
    ):
        """Test multiple checkpoints, verify DESC order by checkpoint_id."""
        thread_id = make_thread_id()
        config = {"configurable": {"thread_id": thread_id}}

        # Create multiple checkpoints
        for step in range(3):
            checkpoint_id = make_checkpoint_id(step)
            checkpoint = make_checkpoint(checkpoint_id, step=step)
            metadata = {"source": "loop", "step": step}

            # Each checkpoint's parent is the previous one
            await saver.aput(config, checkpoint, metadata, {})
            config = {"configurable": {"thread_id": thread_id, "checkpoint_id": checkpoint_id}}

        # List all checkpoints
        checkpoints = []
        async for cp in saver.alist({"configurable": {"thread_id": thread_id}}):
            checkpoints.append(cp)

        assert len(checkpoints) == 3

        # Should be in DESC order (newest first)
        ids = [cp.checkpoint["id"] for cp in checkpoints]
        assert ids == sorted(ids, reverse=True)

    @pytest.mark.asyncio
    async def test_checkpoint_parent_chain(
        self,
        saver: SolverCheckpointSaver,
    ):
        """Test parent config resolution via parent_checkpoint_id."""
        thread_id = make_thread_id()

        # Create parent checkpoint
        parent_id = make_checkpoint_id(0)
        parent_checkpoint = make_checkpoint(parent_id, step=0)
        parent_config = {"configurable": {"thread_id": thread_id}}

        await saver.aput(parent_config, parent_checkpoint, {"step": 0}, {})

        # Create child checkpoint with parent reference
        child_id = make_checkpoint_id(1)
        child_checkpoint = make_checkpoint(child_id, step=1)
        child_config = {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": parent_id,  # Parent reference
            }
        }

        await saver.aput(child_config, child_checkpoint, {"step": 1}, {})

        # Get child and verify parent_config
        result = await saver.aget_tuple({
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": child_id,
            }
        })

        assert result is not None
        assert result.parent_config is not None
        assert result.parent_config["configurable"]["checkpoint_id"] == parent_id

    @pytest.mark.asyncio
    async def test_delete_thread(
        self,
        saver: SolverCheckpointSaver,
    ):
        """Test clean deletion of checkpoints and writes."""
        thread_id = make_thread_id()
        checkpoint_id = make_checkpoint_id(0)
        checkpoint = make_checkpoint(checkpoint_id, step=0)
        config = {"configurable": {"thread_id": thread_id}}

        # Create checkpoint
        result_config = await saver.aput(config, checkpoint, {}, {})

        # Add writes
        await saver.aput_writes(result_config, [("channel1", "value1")], "task-001")

        # Verify exists
        before = await saver.aget_tuple(result_config)
        assert before is not None

        # Delete thread
        await saver.adelete_thread(thread_id)

        # Verify deleted
        after = await saver.aget_tuple(result_config)
        assert after is None

    @pytest.mark.asyncio
    async def test_upsert_idempotent(
        self,
        saver: SolverCheckpointSaver,
    ):
        """Test that repeated aput() calls don't fail."""
        thread_id = make_thread_id()
        checkpoint_id = make_checkpoint_id(0)
        config = {"configurable": {"thread_id": thread_id}}

        # First put
        checkpoint1 = make_checkpoint(checkpoint_id, step=0)
        checkpoint1["channel_values"]["count"] = 1
        await saver.aput(config, checkpoint1, {"version": 1}, {})

        # Second put with same checkpoint_id (update)
        checkpoint2 = make_checkpoint(checkpoint_id, step=0)
        checkpoint2["channel_values"]["count"] = 2
        await saver.aput(config, checkpoint2, {"version": 2}, {})

        # Verify latest value
        result = await saver.aget_tuple({
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
            }
        })

        assert result is not None
        assert result.checkpoint["channel_values"]["count"] == 2
        assert result.metadata["version"] == 2

    @pytest.mark.asyncio
    async def test_get_latest_checkpoint(
        self,
        saver: SolverCheckpointSaver,
    ):
        """Test getting latest checkpoint when no checkpoint_id specified."""
        thread_id = make_thread_id()
        config = {"configurable": {"thread_id": thread_id}}

        # Create multiple checkpoints
        for step in range(3):
            checkpoint_id = make_checkpoint_id(step)
            checkpoint = make_checkpoint(checkpoint_id, step=step)
            await saver.aput(config, checkpoint, {"step": step}, {})
            config = {"configurable": {"thread_id": thread_id, "checkpoint_id": checkpoint_id}}

        # Get without checkpoint_id should return latest
        latest = await saver.aget_tuple({"configurable": {"thread_id": thread_id}})

        assert latest is not None
        assert latest.checkpoint["id"] == make_checkpoint_id(2)

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(
        self,
        saver: SolverCheckpointSaver,
    ):
        """Test that missing checkpoint returns None."""
        result = await saver.aget_tuple({
            "configurable": {
                "thread_id": "nonexistent-thread",
                "checkpoint_id": "nonexistent-checkpoint",
            }
        })

        assert result is None

    @pytest.mark.asyncio
    async def test_list_with_limit(
        self,
        saver: SolverCheckpointSaver,
    ):
        """Test list with limit parameter."""
        thread_id = make_thread_id()
        config = {"configurable": {"thread_id": thread_id}}

        # Create 5 checkpoints
        for step in range(5):
            checkpoint_id = make_checkpoint_id(step)
            checkpoint = make_checkpoint(checkpoint_id, step=step)
            await saver.aput(config, checkpoint, {}, {})
            config = {"configurable": {"thread_id": thread_id, "checkpoint_id": checkpoint_id}}

        # List with limit
        checkpoints = []
        async for cp in saver.alist({"configurable": {"thread_id": thread_id}}, limit=2):
            checkpoints.append(cp)

        assert len(checkpoints) == 2


class TestSolverCheckpointSaverSyncMethods:
    """Test that sync methods raise NotImplementedError."""

    @pytest.fixture
    def saver(self) -> SolverCheckpointSaver:
        """Create a checkpoint saver for sync method tests."""
        # Just need a saver instance, not a real connection
        # since sync methods should raise immediately
        engine = create_async_engine(settings.postgres_url, echo=False)
        factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        return SolverCheckpointSaver(factory, engine=engine)

    def test_get_tuple_raises(self, saver: SolverCheckpointSaver):
        """Sync get_tuple should raise NotImplementedError."""
        with pytest.raises(NotImplementedError, match="async-first"):
            saver.get_tuple({"configurable": {"thread_id": "test"}})

    def test_list_raises(self, saver: SolverCheckpointSaver):
        """Sync list should raise NotImplementedError."""
        with pytest.raises(NotImplementedError, match="async-first"):
            list(saver.list({"configurable": {"thread_id": "test"}}))

    def test_put_raises(self, saver: SolverCheckpointSaver):
        """Sync put should raise NotImplementedError."""
        with pytest.raises(NotImplementedError, match="async-first"):
            saver.put({}, {}, {}, {})

    def test_put_writes_raises(self, saver: SolverCheckpointSaver):
        """Sync put_writes should raise NotImplementedError."""
        with pytest.raises(NotImplementedError, match="async-first"):
            saver.put_writes({}, [], "task-id")

    def test_delete_thread_raises(self, saver: SolverCheckpointSaver):
        """Sync delete_thread should raise NotImplementedError."""
        with pytest.raises(NotImplementedError, match="async-first"):
            saver.delete_thread("thread-id")
