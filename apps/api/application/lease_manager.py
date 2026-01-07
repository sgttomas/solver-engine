"""
SOLVER API - Lease Manager

Provides exclusive execution protection via leases per Contract §15.2
and Design Intent §4.8.

Usage:
    runner_id = generate_runner_id()
    result = await run_with_lease(workflow.id, runner_id, session, graph.ainvoke(...))

Per Co-Developer-1 review: Lease operations use a dedicated session that commits
independently, making lease state immediately visible to other runners. This ensures
the time-bounded, recoverable lease invariant from Design Intent §4.8 is enforced.
"""

import asyncio
import logging
from collections.abc import Coroutine
from datetime import datetime
from typing import Any, TypeVar
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.repositories.execution_lock import (
    RENEWAL_INTERVAL_SECONDS,
    LeaseRepository,
)
from infrastructure.postgres import async_session_factory

logger = logging.getLogger(__name__)

T = TypeVar("T")


class WorkflowLockedError(Exception):
    """Raised when workflow is locked by another runner.

    Per Contract §15.2: Only one runner can advance a workflow at a time.
    Results in 409 Conflict with error_code="WORKFLOW_LOCKED".
    """

    def __init__(self, workflow_id: UUID, locked_by: str, expires_at: datetime):
        self.workflow_id = workflow_id
        self.locked_by = locked_by
        self.expires_at = expires_at
        super().__init__(
            f"Workflow {workflow_id} is locked by {locked_by} until {expires_at}"
        )


class LeaseLostError(Exception):
    """Raised when lease renewal fails mid-execution.

    Per Co-Developer-1 review: Fail fast if we lose exclusivity.
    The in-flight operation should be aborted to prevent data corruption.
    Results in 409 Conflict with error_code="LEASE_LOST".
    """

    def __init__(self, workflow_id: UUID):
        self.workflow_id = workflow_id
        super().__init__(f"Lease was lost during execution for workflow {workflow_id}")


def generate_runner_id() -> str:
    """Generate unique runner ID for lease operations.

    Per Co-Developer-1 review: Runner ID should be stable across
    acquire/renew/release within a single execution.
    """
    return f"api-{uuid4().hex[:8]}"


async def run_with_lease(
    workflow_id: UUID,
    runner_id: str,
    session: AsyncSession,  # Kept for interface consistency; not used for lease ops
    coro: Coroutine[Any, Any, T],
) -> T:
    """Execute coroutine with exclusive lease protection.

    Per Contract §15.2 and Design Intent §4.8:
    - Acquires lease before execution (committed immediately)
    - Spawns renewal loop (interval = LEASE_DURATION / 2, commits each renewal)
    - On renewal failure: raises LeaseLostError (fail fast)
    - On completion: cancels renewal, releases lease (committed immediately)

    Per Co-Developer-1 review: Lease operations use a dedicated session that
    commits independently, making lease state visible to other runners immediately.
    This ensures stuck runners (event loop alive, transaction open) can be
    taken over after expires_at passes.

    Args:
        workflow_id: Internal workflow UUID (from workflows.id)
        runner_id: Identifier for this runner (from generate_runner_id())
        session: Database session (kept for interface; lease uses dedicated session)
        coro: Coroutine to execute (e.g., graph.ainvoke(...))

    Returns:
        Result of the coroutine execution

    Raises:
        WorkflowLockedError: If lease acquisition fails (another runner holds it)
        LeaseLostError: If lease renewal fails during execution
    """
    # Use dedicated session for lease operations - commits immediately
    # This ensures lease state is visible to other runners right away
    async with async_session_factory() as lease_session:
        lease_repo = LeaseRepository(lease_session)

        # Acquire lease
        if not await lease_repo.acquire(workflow_id, runner_id):
            lock_info = await lease_repo.get_lock_info(workflow_id)
            if lock_info:
                raise WorkflowLockedError(
                    workflow_id, lock_info.locked_by, lock_info.expires_at
                )
            else:
                # Lock info not found - race condition, treat as locked
                raise WorkflowLockedError(
                    workflow_id, "unknown", datetime.min
                )

        # Commit lease acquisition immediately - visible to other runners NOW
        await lease_session.commit()
        logger.debug(f"Lease acquired for workflow {workflow_id} by {runner_id}")

        # Track whether we lost the lease
        lease_lost = asyncio.Event()

        # Start renewal loop (uses lease_session with commits)
        renewal_task = asyncio.create_task(
            _renewal_loop(lease_session, workflow_id, runner_id, lease_lost)
        )

        try:
            # Run the actual work, but also monitor for lease loss
            work_task = asyncio.create_task(coro)

            # Wait for either work completion or lease loss
            done, pending = await asyncio.wait(
                [work_task, asyncio.create_task(lease_lost.wait())],
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Cancel pending tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            # Check if we lost the lease
            if lease_lost.is_set():
                # Cancel work if still running
                if not work_task.done():
                    work_task.cancel()
                    try:
                        await work_task
                    except asyncio.CancelledError:
                        pass
                raise LeaseLostError(workflow_id)

            # Work completed successfully
            return work_task.result()

        finally:
            # Cancel renewal task
            renewal_task.cancel()
            try:
                await renewal_task
            except asyncio.CancelledError:
                pass

            # Release lease (guarded - only if we still hold it)
            await lease_repo.release(workflow_id, runner_id)
            # Commit release immediately - visible to other runners NOW
            await lease_session.commit()
            logger.debug(f"Lease released for workflow {workflow_id} by {runner_id}")


async def _renewal_loop(
    lease_session: AsyncSession,
    workflow_id: UUID,
    runner_id: str,
    lease_lost: asyncio.Event,
) -> None:
    """Renew lease periodically. Sets lease_lost event on failure.

    Per Co-Developer-1 review: Each renewal commits immediately to make
    the extended expires_at visible to other runners right away.

    Args:
        lease_session: Dedicated session for lease operations (will commit)
        workflow_id: Workflow being executed
        runner_id: Our runner identifier
        lease_lost: Event to set if renewal fails
    """
    lease_repo = LeaseRepository(lease_session)
    interval = RENEWAL_INTERVAL_SECONDS

    while True:
        await asyncio.sleep(interval)
        if not await lease_repo.renew(workflow_id, runner_id):
            logger.warning(
                f"Lease renewal failed for workflow {workflow_id}, runner {runner_id}"
            )
            lease_lost.set()
            return
        # Commit renewal immediately - extended expiry visible to other runners NOW
        await lease_session.commit()
        logger.debug(f"Lease renewed for workflow {workflow_id} by {runner_id}")
