"""
ExecutionLock Repository - Lease management data access.

Provides lease acquisition, renewal, and release operations per Tech Spec V2.8.4
Section 16.5 and Contract §15.2 (Exclusive Execution).
"""

import os
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models.execution_lock import ExecutionLock

# Configurable via environment variable
LEASE_DURATION_SECONDS = int(os.getenv("RUNNER_LEASE_DURATION", "60"))
RENEWAL_INTERVAL_SECONDS = LEASE_DURATION_SECONDS // 2  # 30s default


class LeaseRepository:
    """Repository for workflow execution lock operations.

    Manages exclusive execution leases. Thread-safe via DB constraints.
    Per Design Intent §4.8: Time-bounded, per-workflow, database-backed leases.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def acquire(
        self,
        workflow_id: UUID,
        runner_id: str,
    ) -> bool:
        """Attempt to acquire exclusive lease.

        Uses UPSERT pattern to atomically:
        - Insert new lease if none exists
        - Take over expired lease
        - Extend if we already hold the lease

        Args:
            workflow_id: Internal workflow UUID (from workflows.id)
            runner_id: Identifier for this runner/process

        Returns:
            True if lease acquired, False otherwise
        """
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=LEASE_DURATION_SECONDS)

        try:
            # UPSERT: Insert or update if expired or same holder
            await self._session.execute(
                text("""
                    INSERT INTO workflow_execution_locks
                        (workflow_id, locked_by, locked_at, expires_at)
                    VALUES (:workflow_id, :runner_id, :now, :expires_at)
                    ON CONFLICT (workflow_id) DO UPDATE
                    SET locked_by = :runner_id,
                        locked_at = :now,
                        expires_at = :expires_at
                    WHERE workflow_execution_locks.expires_at < :now
                       OR workflow_execution_locks.locked_by = :runner_id
                """),
                {
                    "workflow_id": workflow_id,
                    "runner_id": runner_id,
                    "now": now,
                    "expires_at": expires_at,
                },
            )
            await self._session.flush()

            # Verify we actually hold the lease
            result = await self._session.execute(
                text("""
                    SELECT locked_by FROM workflow_execution_locks
                    WHERE workflow_id = :workflow_id AND expires_at > :now
                """),
                {"workflow_id": workflow_id, "now": now},
            )
            row = result.fetchone()
            return row is not None and row[0] == runner_id

        except Exception:
            return False

    async def renew(
        self,
        workflow_id: UUID,
        runner_id: str,
    ) -> bool:
        """Renew lease if we still hold it.

        Args:
            workflow_id: Internal workflow UUID
            runner_id: Identifier for this runner

        Returns:
            True if lease renewed, False if not held or expired
        """
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=LEASE_DURATION_SECONDS)

        result = await self._session.execute(
            text("""
                UPDATE workflow_execution_locks
                SET expires_at = :expires_at
                WHERE workflow_id = :workflow_id
                  AND locked_by = :runner_id
                  AND expires_at > :now
            """),
            {
                "expires_at": expires_at,
                "workflow_id": workflow_id,
                "runner_id": runner_id,
                "now": now,
            },
        )
        await self._session.flush()
        return result.rowcount > 0

    async def release(
        self,
        workflow_id: UUID,
        runner_id: str,
    ) -> None:
        """Release lease after completion.

        Only releases if we hold the lease (guarded release per Co-Developer-1 review).
        This prevents wiping a new holder if our lease was already taken over.

        Args:
            workflow_id: Internal workflow UUID
            runner_id: Identifier for this runner
        """
        await self._session.execute(
            text("""
                DELETE FROM workflow_execution_locks
                WHERE workflow_id = :workflow_id AND locked_by = :runner_id
            """),
            {"workflow_id": workflow_id, "runner_id": runner_id},
        )
        await self._session.flush()

    async def get_lock_info(
        self,
        workflow_id: UUID,
    ) -> ExecutionLock | None:
        """Get current lock information for a workflow.

        Args:
            workflow_id: Internal workflow UUID

        Returns:
            ExecutionLock if exists, None otherwise
        """
        result = await self._session.execute(
            select(ExecutionLock).where(ExecutionLock.workflow_id == workflow_id)
        )
        return result.scalar_one_or_none()
