"""
WorkflowEvent Repository - Durable event log operations.

Implements Contract §9.2 (Event Log) and §11.3 (Transactional Transition).
Uses pg_advisory_xact_lock for gap-free sequence allocation.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models.workflow_event import WorkflowEvent
from infrastructure.db.repositories.base import BaseRepository


class WorkflowEventRepository(BaseRepository[WorkflowEvent]):
    """Repository for workflow events with sequence management.

    Per Contract §9.2, §11.3, §11.4:
    - sequence MUST be monotonic and gap-free per workflow
    - Events MUST be persisted BEFORE broadcast
    - Uses pg_advisory_xact_lock for gap-free sequence allocation
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with async session.

        Args:
            session: Async SQLAlchemy session
        """
        super().__init__(session, WorkflowEvent)

    async def get_next_sequence(self, workflow_id: UUID) -> int:
        """Get next sequence number using advisory lock.

        Uses the database function get_next_event_sequence() which:
        1. Acquires pg_advisory_xact_lock based on workflow_id
        2. Gets MAX(sequence) + 1
        3. Lock released automatically when transaction ends

        Per Contract §9.2: sequence MUST be monotonic and gap-free.

        Args:
            workflow_id: Workflow ID to get next sequence for

        Returns:
            Next sequence number (1 for first event)
        """
        result = await self._session.execute(
            text("SELECT get_next_event_sequence(:workflow_id)"),
            {"workflow_id": str(workflow_id)},
        )
        return result.scalar_one()

    async def get_events_after(
        self,
        workflow_id: UUID,
        from_sequence: int,
        limit: Optional[int] = None,
    ) -> List[WorkflowEvent]:
        """Get events with sequence > from_sequence.

        Per Contract §12.1: replay all events with sequence > N in order.

        Args:
            workflow_id: Workflow ID to get events for
            from_sequence: Return events with sequence > this value
            limit: Optional limit on number of events

        Returns:
            List of events ordered by sequence (ascending)
        """
        stmt = (
            select(WorkflowEvent)
            .where(WorkflowEvent.workflow_id == workflow_id)
            .where(WorkflowEvent.sequence > from_sequence)
            .order_by(WorkflowEvent.sequence)
        )
        if limit:
            stmt = stmt.limit(limit)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_sequence(self, workflow_id: UUID) -> int:
        """Get the current highest sequence number for a workflow.

        Args:
            workflow_id: Workflow ID to query

        Returns:
            Highest sequence number, or 0 if no events exist
        """
        result = await self._session.execute(
            text(
                "SELECT COALESCE(MAX(sequence), 0) FROM workflow_events "
                "WHERE workflow_id = :workflow_id"
            ),
            {"workflow_id": str(workflow_id)},
        )
        return result.scalar_one()

    async def create_event(
        self,
        workflow_id: UUID,
        event_type: str,
        payload: dict,
    ) -> WorkflowEvent:
        """Create a new event with automatic sequence allocation.

        Uses get_next_sequence to ensure gap-free monotonic sequence.
        Per Contract §11.4: Events MUST be persisted before broadcast.

        Args:
            workflow_id: Workflow ID for the event
            event_type: Type of event (e.g., "workflow.started", "step.approved")
            payload: Event payload dict

        Returns:
            Created event with assigned sequence
        """
        sequence = await self.get_next_sequence(workflow_id)
        event = WorkflowEvent(
            workflow_id=workflow_id,
            sequence=sequence,
            event_type=event_type,
            payload=payload,
        )
        return await self.create(event)
