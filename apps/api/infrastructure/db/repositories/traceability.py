"""
TraceabilityLink Repository - Trace relationship data access.

Provides data access for forward/backward trace links.
"""

from typing import Optional, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import TraceabilityLink
from infrastructure.db.repositories.base import BaseRepository


class TraceabilityLinkRepository(BaseRepository[TraceabilityLink]):
    """Repository for TraceabilityLink entities.

    TraceabilityLinks connect elements across steps:
    - Stakeholder needs → Requirements
    - Requirements → Objectives
    - Requirements → Verification cases

    Note: This table uses UUID primary key with a separate
    unique constraint on (workflow_id, from_id, to_id, link_type).
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, TraceabilityLink)

    async def find_by_unique(
        self,
        workflow_id: UUID,
        from_id: str,
        to_id: str,
        link_type: str,
    ) -> Optional[TraceabilityLink]:
        """Find link by its unique constraint fields.

        Args:
            workflow_id: Workflow UUID
            from_id: Source element ID (e.g., 'SH-001', 'FR-001')
            to_id: Target element ID
            link_type: Link type (e.g., 'derives', 'achieves')

        Returns:
            TraceabilityLink if found, None otherwise
        """
        stmt = select(TraceabilityLink).where(
            TraceabilityLink.workflow_id == workflow_id,
            TraceabilityLink.from_id == from_id,
            TraceabilityLink.to_id == to_id,
            TraceabilityLink.link_type == link_type,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_workflow(self, workflow_id: UUID) -> List[TraceabilityLink]:
        """List all traceability links for a workflow.

        Args:
            workflow_id: Workflow UUID

        Returns:
            List of all traceability links
        """
        stmt = (
            select(TraceabilityLink)
            .where(TraceabilityLink.workflow_id == workflow_id)
            .order_by(TraceabilityLink.from_step, TraceabilityLink.to_step)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_from_element(
        self,
        workflow_id: UUID,
        from_id: str,
    ) -> List[TraceabilityLink]:
        """List all links originating from an element.

        Args:
            workflow_id: Workflow UUID
            from_id: Source element ID

        Returns:
            List of links from the element
        """
        stmt = (
            select(TraceabilityLink)
            .where(
                TraceabilityLink.workflow_id == workflow_id,
                TraceabilityLink.from_id == from_id,
            )
            .order_by(TraceabilityLink.to_step)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_to_element(
        self,
        workflow_id: UUID,
        to_id: str,
    ) -> List[TraceabilityLink]:
        """List all links pointing to an element.

        Args:
            workflow_id: Workflow UUID
            to_id: Target element ID

        Returns:
            List of links to the element
        """
        stmt = (
            select(TraceabilityLink)
            .where(
                TraceabilityLink.workflow_id == workflow_id,
                TraceabilityLink.to_id == to_id,
            )
            .order_by(TraceabilityLink.from_step)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
