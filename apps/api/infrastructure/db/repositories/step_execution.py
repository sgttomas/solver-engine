"""
StepExecution Repository - Step execution state data access.

Provides data access for per-step execution state.
"""

from typing import Optional, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import StepExecution, PassType, StepName
from infrastructure.db.repositories.base import BaseRepository


class StepExecutionRepository(BaseRepository[StepExecution]):
    """Repository for StepExecution entities.

    StepExecutions track the state of individual steps within a workflow,
    including status, phase, and validation state.

    Unique constraint: (workflow_id, pass_type, step_name)
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, StepExecution)

    async def get_by_composite(
        self,
        workflow_id: UUID,
        pass_type: PassType,
        step_name: StepName,
    ) -> Optional[StepExecution]:
        """Get step execution by its composite unique key.

        Args:
            workflow_id: Workflow UUID
            pass_type: Pass type (definition or execution)
            step_name: Step name enum

        Returns:
            StepExecution if found, None otherwise
        """
        stmt = select(StepExecution).where(
            StepExecution.workflow_id == workflow_id,
            StepExecution.pass_type == pass_type,
            StepExecution.step_name == step_name,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_workflow(self, workflow_id: UUID) -> List[StepExecution]:
        """List all step executions for a workflow.

        Args:
            workflow_id: Workflow UUID

        Returns:
            List of step executions ordered by step number
        """
        stmt = (
            select(StepExecution)
            .where(StepExecution.workflow_id == workflow_id)
            .order_by(StepExecution.pass_type, StepExecution.step_number)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_for_pass(
        self,
        workflow_id: UUID,
        pass_type: PassType,
    ) -> List[StepExecution]:
        """List all step executions for a specific pass.

        Args:
            workflow_id: Workflow UUID
            pass_type: Pass type (definition or execution)

        Returns:
            List of step executions for the pass
        """
        stmt = (
            select(StepExecution)
            .where(
                StepExecution.workflow_id == workflow_id,
                StepExecution.pass_type == pass_type,
            )
            .order_by(StepExecution.step_number)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
