"""
AuditLog Repository - Audit event data access.

Provides data access for immutable audit log entries.
"""

from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import AuditLog
from infrastructure.db.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    """Repository for AuditLog entities.

    AuditLog is append-only - entries are created but never
    updated or deleted. This ensures full timeline reconstruction
    for Gate F compliance.

    Note: The `delete` and `update` methods from BaseRepository
    should not be used on audit logs in production.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AuditLog)

    async def append(self, audit_log: AuditLog) -> AuditLog:
        """Append a new audit log entry.

        This is the preferred method for creating audit entries,
        making the append-only nature explicit.

        Args:
            audit_log: Audit log entry to append

        Returns:
            Created audit log with DB-generated values
        """
        return await self.create(audit_log)

    async def list_for_workflow(self, workflow_id: UUID) -> List[AuditLog]:
        """List all audit entries for a workflow.

        Returns entries in chronological order for timeline reconstruction.

        Args:
            workflow_id: Workflow UUID

        Returns:
            List of audit log entries ordered by creation time
        """
        stmt = (
            select(AuditLog)
            .where(AuditLog.workflow_id == workflow_id)
            .order_by(AuditLog.created_at)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_event_type(
        self,
        workflow_id: UUID,
        event_type: str,
    ) -> List[AuditLog]:
        """List audit entries by event type.

        Args:
            workflow_id: Workflow UUID
            event_type: Event type to filter by

        Returns:
            List of matching audit log entries
        """
        stmt = (
            select(AuditLog)
            .where(
                AuditLog.workflow_id == workflow_id,
                AuditLog.event_type == event_type,
            )
            .order_by(AuditLog.created_at)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_actor(
        self,
        workflow_id: UUID,
        actor_id: str,
    ) -> List[AuditLog]:
        """List audit entries by actor.

        Args:
            workflow_id: Workflow UUID
            actor_id: Actor ID to filter by

        Returns:
            List of audit entries for the actor
        """
        stmt = (
            select(AuditLog)
            .where(
                AuditLog.workflow_id == workflow_id,
                AuditLog.actor_id == actor_id,
            )
            .order_by(AuditLog.created_at)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
