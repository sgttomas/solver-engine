"""
Message Repository - Conversation history data access.

Provides data access for conversation messages.
"""

from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import Message
from infrastructure.db.repositories.base import BaseRepository


class MessageRepository(BaseRepository[Message]):
    """Repository for Message entities.

    Messages store conversation history with optional embeddings
    for semantic search.

    Note: Use `metadata_` attribute (not `metadata`) due to
    SQLAlchemy attribute name remapping.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Message)

    async def list_for_workflow(self, workflow_id: UUID) -> List[Message]:
        """List all messages for a workflow.

        Args:
            workflow_id: Workflow UUID

        Returns:
            List of messages ordered by creation time
        """
        stmt = (
            select(Message)
            .where(Message.workflow_id == workflow_id)
            .order_by(Message.created_at)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_for_step(self, step_execution_id: UUID) -> List[Message]:
        """List all messages for a step execution.

        Args:
            step_execution_id: StepExecution UUID

        Returns:
            List of messages for the step ordered by creation time
        """
        stmt = (
            select(Message)
            .where(Message.step_execution_id == step_execution_id)
            .order_by(Message.created_at)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
