"""
Checkpoint Repository - LangGraph checkpoint data access.

Provides data access for checkpoints and checkpoint writes.
These tables use composite primary keys (no UUID id column).
"""

from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import Checkpoint, CheckpointWrite


class CheckpointRepository:
    """Repository for Checkpoint entities.

    Checkpoints store serialized LangGraph state for interrupt/resume.
    Uses composite primary key: (thread_id, checkpoint_id).

    Note: Uses `metadata_` attribute (not `metadata`) due to
    SQLAlchemy attribute name remapping.

    Note: Does not extend BaseRepository since composite PKs
    require different handling than UUID-based entities.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self,
        thread_id: str,
        checkpoint_id: str,
    ) -> Optional[Checkpoint]:
        """Get checkpoint by composite primary key.

        Args:
            thread_id: Thread identifier
            checkpoint_id: Checkpoint identifier

        Returns:
            Checkpoint if found, None otherwise
        """
        stmt = select(Checkpoint).where(
            Checkpoint.thread_id == thread_id,
            Checkpoint.checkpoint_id == checkpoint_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def put(self, checkpoint: Checkpoint) -> Checkpoint:
        """Upsert a checkpoint (insert or update).

        Uses get-then-create-or-update pattern for compatibility
        with column name remapping (metadata_ attribute).

        Args:
            checkpoint: Checkpoint to save

        Returns:
            Saved checkpoint
        """
        existing = await self.get(checkpoint.thread_id, checkpoint.checkpoint_id)

        if existing is None:
            # Insert new checkpoint
            self._session.add(checkpoint)
            await self._session.flush()
            await self._session.refresh(checkpoint)
            return checkpoint
        else:
            # Update existing checkpoint
            existing.parent_checkpoint_id = checkpoint.parent_checkpoint_id
            existing.checkpoint = checkpoint.checkpoint
            existing.metadata_ = checkpoint.metadata_
            await self._session.flush()
            await self._session.refresh(existing)
            return existing

    async def list_for_thread(self, thread_id: str) -> List[Checkpoint]:
        """List all checkpoints for a thread.

        Args:
            thread_id: Thread identifier

        Returns:
            List of checkpoints ordered by creation time
        """
        stmt = (
            select(Checkpoint)
            .where(Checkpoint.thread_id == thread_id)
            .order_by(Checkpoint.created_at)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, thread_id: str, checkpoint_id: str) -> None:
        """Delete a checkpoint.

        Args:
            thread_id: Thread identifier
            checkpoint_id: Checkpoint identifier
        """
        checkpoint = await self.get(thread_id, checkpoint_id)
        if checkpoint:
            await self._session.delete(checkpoint)
            await self._session.flush()


class CheckpointWriteRepository:
    """Repository for CheckpointWrite entities.

    Checkpoint writes store individual channel writes within a checkpoint.
    Uses composite primary key: (thread_id, checkpoint_id, task_id, idx).

    Note: Does not extend BaseRepository since composite PKs
    require different handling.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self,
        thread_id: str,
        checkpoint_id: str,
        task_id: str,
        idx: int,
    ) -> Optional[CheckpointWrite]:
        """Get checkpoint write by composite primary key.

        Args:
            thread_id: Thread identifier
            checkpoint_id: Checkpoint identifier
            task_id: Task identifier
            idx: Write index

        Returns:
            CheckpointWrite if found, None otherwise
        """
        stmt = select(CheckpointWrite).where(
            CheckpointWrite.thread_id == thread_id,
            CheckpointWrite.checkpoint_id == checkpoint_id,
            CheckpointWrite.task_id == task_id,
            CheckpointWrite.idx == idx,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def put(self, write: CheckpointWrite) -> CheckpointWrite:
        """Upsert a checkpoint write.

        Uses get-then-create-or-update pattern.

        Args:
            write: CheckpointWrite to save

        Returns:
            Saved checkpoint write
        """
        existing = await self.get(
            write.thread_id,
            write.checkpoint_id,
            write.task_id,
            write.idx,
        )

        if existing is None:
            # Insert new write
            self._session.add(write)
            await self._session.flush()
            await self._session.refresh(write)
            return write
        else:
            # Update existing write
            existing.channel = write.channel
            existing.value = write.value
            await self._session.flush()
            await self._session.refresh(existing)
            return existing

    async def list_for_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str,
    ) -> List[CheckpointWrite]:
        """List all writes for a checkpoint.

        Args:
            thread_id: Thread identifier
            checkpoint_id: Checkpoint identifier

        Returns:
            List of checkpoint writes ordered by idx
        """
        stmt = (
            select(CheckpointWrite)
            .where(
                CheckpointWrite.thread_id == thread_id,
                CheckpointWrite.checkpoint_id == checkpoint_id,
            )
            .order_by(CheckpointWrite.idx)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete(
        self,
        thread_id: str,
        checkpoint_id: str,
        task_id: str,
        idx: int,
    ) -> None:
        """Delete a checkpoint write.

        Args:
            thread_id: Thread identifier
            checkpoint_id: Checkpoint identifier
            task_id: Task identifier
            idx: Write index
        """
        write = await self.get(thread_id, checkpoint_id, task_id, idx)
        if write:
            await self._session.delete(write)
            await self._session.flush()
