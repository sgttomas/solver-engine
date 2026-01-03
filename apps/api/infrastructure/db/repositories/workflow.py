"""
Workflow Repository - Workflow data access.

Provides data access for master workflow records.
"""

from typing import Optional, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import Workflow, WorkflowStatus
from infrastructure.db.repositories.base import BaseRepository


class WorkflowRepository(BaseRepository[Workflow]):
    """Repository for Workflow entities.

    Workflows track the overall state of a structured reasoning session,
    including current position (pass/step) and status.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Workflow)

    async def get_by_workflow_id(self, workflow_id: str) -> Optional[Workflow]:
        """Get workflow by its unique string identifier.

        Args:
            workflow_id: Unique workflow identifier (VARCHAR(255))

        Returns:
            Workflow if found, None otherwise
        """
        stmt = select(Workflow).where(Workflow.workflow_id == workflow_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_thread_id(self, thread_id: str) -> Optional[Workflow]:
        """Get workflow by its thread identifier.

        Thread ID is used for LangGraph checkpoint correlation.

        Args:
            thread_id: Unique thread identifier (VARCHAR(255))

        Returns:
            Workflow if found, None otherwise
        """
        stmt = select(Workflow).where(Workflow.thread_id == thread_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_instance(self, instance_id: UUID) -> List[Workflow]:
        """List all workflows for an instance.

        Args:
            instance_id: Instance UUID

        Returns:
            List of workflows for the instance
        """
        stmt = select(Workflow).where(Workflow.instance_id == instance_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_status(self, status: WorkflowStatus) -> List[Workflow]:
        """List all workflows with a given status.

        Args:
            status: Workflow status to filter by

        Returns:
            List of workflows with the given status
        """
        stmt = select(Workflow).where(Workflow.status == status)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
