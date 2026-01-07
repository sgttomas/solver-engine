"""
LeaseRepository Integration Tests

Tests lease management operations per Tech Spec V2.8.4 Section 16.5 and
Contract §15.2 (Exclusive Execution).

Verifies:
  - β4-2: Concurrent acquire blocked
  - β4-3: Expired lease takeover
  - β4-5: Crash recovery scenario
  - β4-6: Renewal extends lease

Phase 7R: Resolves P7.3-DEF-001 deferral.
"""

import asyncio
from datetime import datetime, timedelta, UTC
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings
from infrastructure.db.repositories.execution_lock import (
    LeaseRepository,
    LEASE_DURATION_SECONDS,
)
from infrastructure.db.models.execution_lock import ExecutionLock


def create_test_session_factory():
    """Create a fresh session factory for test isolation.

    This avoids event loop issues when using the global async_session_factory
    which is bound to a different event loop than pytest-asyncio uses.
    """
    engine = create_async_engine(settings.postgres_url, echo=False)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def test_workflow_id():
    """Create a test workflow and return its ID for lease testing."""
    # Create a fresh engine for this test to avoid event loop issues
    engine = create_async_engine(settings.postgres_url, echo=False)
    test_session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with test_session_factory() as session:
        # Get the first instance (seeded in migration)
        result = await session.execute(
            text("SELECT id FROM instances ORDER BY instance_number LIMIT 1")
        )
        instance_row = result.fetchone()
        if not instance_row:
            pytest.skip("No instances in database - run migrations first")
        instance_id = instance_row[0]

        # Create a test workflow directly
        workflow_id = uuid4()
        workflow_uuid = f"test-lease-{uuid4().hex[:8]}"
        thread_id = f"thread-lease-{uuid4().hex[:8]}"

        await session.execute(
            text("""
                INSERT INTO workflows (
                    id, workflow_id, thread_id, instance_id,
                    original_problem, created_by, last_actor_id
                ) VALUES (
                    :id, :workflow_id, :thread_id, :instance_id,
                    :problem, :created_by, :last_actor_id
                )
            """),
            {
                "id": workflow_id,
                "workflow_id": workflow_uuid,
                "thread_id": thread_id,
                "instance_id": instance_id,
                "problem": "Lease repository test workflow",
                "created_by": "test",
                "last_actor_id": "test",
            },
        )
        await session.commit()

        yield workflow_id

        # Cleanup: delete the test workflow
        await session.execute(
            text("DELETE FROM workflow_execution_locks WHERE workflow_id = :id"),
            {"id": workflow_id},
        )
        await session.execute(
            text("DELETE FROM workflows WHERE id = :id"),
            {"id": workflow_id},
        )
        await session.commit()


class TestLeaseRepository:
    """Integration tests for LeaseRepository operations."""

    @pytest.mark.asyncio
    async def test_b4_2_concurrent_acquire_blocked(self, test_workflow_id):
        """β4-2: Second runner cannot acquire active lease.

        GIVEN runner A holds a lease on a workflow
        WHEN runner B attempts to acquire the same lease
        THEN runner B's acquire returns False
        """
        runner_a = "runner-A"
        runner_b = "runner-B"

        # Runner A acquires lease
        async with create_test_session_factory()() as session:
            lease_repo = LeaseRepository(session)
            acquired_a = await lease_repo.acquire(test_workflow_id, runner_a)
            assert acquired_a is True, "Runner A should acquire lease"
            await session.commit()

        # Runner B tries to acquire (different session to simulate different process)
        async with create_test_session_factory()() as session:
            lease_repo = LeaseRepository(session)
            acquired_b = await lease_repo.acquire(test_workflow_id, runner_b)
            assert acquired_b is False, "Runner B should not acquire active lease"

        # Cleanup
        async with create_test_session_factory()() as session:
            lease_repo = LeaseRepository(session)
            await lease_repo.release(test_workflow_id, runner_a)
            await session.commit()

    @pytest.mark.asyncio
    async def test_b4_3_expired_lease_takeover(self, test_workflow_id):
        """β4-3: Expired lease can be taken over.

        GIVEN runner A holds an expired lease
        WHEN runner B attempts to acquire
        THEN runner B's acquire succeeds
        """
        runner_a = "runner-A"
        runner_b = "runner-B"

        # Create an expired lease for runner A directly
        # Note: expires_at must be > locked_at per valid_expiry constraint
        async with create_test_session_factory()() as session:
            locked_time = datetime.now(UTC) - timedelta(seconds=20)
            expired_time = datetime.now(UTC) - timedelta(seconds=10)  # Past but > locked_time
            await session.execute(
                text("""
                    INSERT INTO workflow_execution_locks
                        (workflow_id, locked_by, locked_at, expires_at)
                    VALUES (:workflow_id, :locked_by, :locked_at, :expires_at)
                    ON CONFLICT (workflow_id) DO UPDATE
                    SET locked_by = :locked_by,
                        locked_at = :locked_at,
                        expires_at = :expires_at
                """),
                {
                    "workflow_id": test_workflow_id,
                    "locked_by": runner_a,
                    "locked_at": locked_time,
                    "expires_at": expired_time,  # Already expired, but > locked_time
                },
            )
            await session.commit()

        # Runner B should be able to take over
        async with create_test_session_factory()() as session:
            lease_repo = LeaseRepository(session)
            acquired_b = await lease_repo.acquire(test_workflow_id, runner_b)
            assert acquired_b is True, "Runner B should take over expired lease"
            await session.commit()

        # Verify runner B now holds the lease
        async with create_test_session_factory()() as session:
            lease_repo = LeaseRepository(session)
            lock_info = await lease_repo.get_lock_info(test_workflow_id)
            assert lock_info is not None
            assert lock_info.locked_by == runner_b

        # Cleanup
        async with create_test_session_factory()() as session:
            lease_repo = LeaseRepository(session)
            await lease_repo.release(test_workflow_id, runner_b)
            await session.commit()

    @pytest.mark.asyncio
    async def test_b4_5_crash_recovery_scenario(self, test_workflow_id):
        """β4-5: Crash recovery - new runner takes over after lease expiry.

        GIVEN runner A crashed while holding a lease (simulated)
        AND the lease has expired
        WHEN a new runner B attempts to acquire
        THEN runner B succeeds (crash recovery via expiry)
        """
        runner_a = "crashed-runner"
        runner_b = "recovery-runner"

        # Simulate crashed runner by creating an expired lease
        # Note: expires_at must be > locked_at per valid_expiry constraint
        async with create_test_session_factory()() as session:
            locked_time = datetime.now(UTC) - timedelta(seconds=LEASE_DURATION_SECONDS + 20)
            expired_time = datetime.now(UTC) - timedelta(seconds=LEASE_DURATION_SECONDS + 10)
            await session.execute(
                text("""
                    INSERT INTO workflow_execution_locks
                        (workflow_id, locked_by, locked_at, expires_at)
                    VALUES (:workflow_id, :locked_by, :locked_at, :expires_at)
                    ON CONFLICT (workflow_id) DO UPDATE
                    SET locked_by = :locked_by,
                        locked_at = :locked_at,
                        expires_at = :expires_at
                """),
                {
                    "workflow_id": test_workflow_id,
                    "locked_by": runner_a,
                    "locked_at": locked_time,
                    "expires_at": expired_time,  # Expired but > locked_time
                },
            )
            await session.commit()

        # Recovery runner should acquire the lease
        async with create_test_session_factory()() as session:
            lease_repo = LeaseRepository(session)
            acquired = await lease_repo.acquire(test_workflow_id, runner_b)
            assert acquired is True, "Recovery runner should acquire expired lease"
            await session.commit()

        # Cleanup
        async with create_test_session_factory()() as session:
            lease_repo = LeaseRepository(session)
            await lease_repo.release(test_workflow_id, runner_b)
            await session.commit()

    @pytest.mark.asyncio
    async def test_b4_6_renew_extends_lease(self, test_workflow_id):
        """β4-6: Renewal extends lease expiry time.

        GIVEN a runner holds a lease
        WHEN the runner renews the lease
        THEN the expires_at time is extended
        """
        runner = "renewing-runner"

        # Acquire lease
        async with create_test_session_factory()() as session:
            lease_repo = LeaseRepository(session)
            acquired = await lease_repo.acquire(test_workflow_id, runner)
            assert acquired is True

            # Get initial expiry
            lock_info = await lease_repo.get_lock_info(test_workflow_id)
            initial_expiry = lock_info.expires_at
            await session.commit()

        # Wait a moment then renew
        await asyncio.sleep(0.1)

        async with create_test_session_factory()() as session:
            lease_repo = LeaseRepository(session)
            renewed = await lease_repo.renew(test_workflow_id, runner)
            assert renewed is True, "Renewal should succeed for holder"

            # Get new expiry
            lock_info = await lease_repo.get_lock_info(test_workflow_id)
            new_expiry = lock_info.expires_at
            await session.commit()

        # New expiry should be later than initial
        assert new_expiry > initial_expiry, "Renewal should extend expiry time"

        # Cleanup
        async with create_test_session_factory()() as session:
            lease_repo = LeaseRepository(session)
            await lease_repo.release(test_workflow_id, runner)
            await session.commit()

    @pytest.mark.asyncio
    async def test_renew_fails_for_non_holder(self, test_workflow_id):
        """Renewal fails if caller doesn't hold the lease.

        GIVEN runner A holds a lease
        WHEN runner B attempts to renew
        THEN the renewal returns False
        """
        runner_a = "holder"
        runner_b = "non-holder"

        # Runner A acquires
        async with create_test_session_factory()() as session:
            lease_repo = LeaseRepository(session)
            await lease_repo.acquire(test_workflow_id, runner_a)
            await session.commit()

        # Runner B tries to renew (should fail)
        async with create_test_session_factory()() as session:
            lease_repo = LeaseRepository(session)
            renewed = await lease_repo.renew(test_workflow_id, runner_b)
            assert renewed is False, "Non-holder should not be able to renew"

        # Cleanup
        async with create_test_session_factory()() as session:
            lease_repo = LeaseRepository(session)
            await lease_repo.release(test_workflow_id, runner_a)
            await session.commit()

    @pytest.mark.asyncio
    async def test_guarded_release(self, test_workflow_id):
        """Release only works if caller holds the lease (guarded release).

        GIVEN runner A holds a lease
        WHEN runner B attempts to release
        THEN the lease remains (runner B's release has no effect)
        """
        runner_a = "holder"
        runner_b = "non-holder"

        # Runner A acquires
        async with create_test_session_factory()() as session:
            lease_repo = LeaseRepository(session)
            await lease_repo.acquire(test_workflow_id, runner_a)
            await session.commit()

        # Runner B tries to release (should have no effect)
        async with create_test_session_factory()() as session:
            lease_repo = LeaseRepository(session)
            await lease_repo.release(test_workflow_id, runner_b)
            await session.commit()

        # Lease should still be held by runner A
        async with create_test_session_factory()() as session:
            lease_repo = LeaseRepository(session)
            lock_info = await lease_repo.get_lock_info(test_workflow_id)
            assert lock_info is not None, "Lease should still exist"
            assert lock_info.locked_by == runner_a, "Runner A should still hold lease"

        # Cleanup - proper release by holder
        async with create_test_session_factory()() as session:
            lease_repo = LeaseRepository(session)
            await lease_repo.release(test_workflow_id, runner_a)
            await session.commit()

    @pytest.mark.asyncio
    async def test_stuck_runner_expiry_takeover(self, test_workflow_id):
        """Stuck runner's lease can be taken over after expiry.

        Per Co-Developer-1 review and Design Intent §4.8: A stuck runner
        (event loop alive, transaction open) should NOT hold lease indefinitely.
        With transaction isolation fix, lease is committed immediately and
        expires_at is visible to other runners.

        GIVEN runner A acquires a lease (committed, visible to others)
        AND runner A stops renewing (simulating stuck event loop)
        AND sufficient time passes for the lease to expire
        WHEN runner B attempts to acquire
        THEN runner B succeeds (takes over expired lease)
        """
        runner_a = "stuck-runner"
        runner_b = "takeover-runner"

        # Runner A acquires lease with immediate commit (per transaction isolation fix)
        async with create_test_session_factory()() as session:
            lease_repo = LeaseRepository(session)
            acquired = await lease_repo.acquire(test_workflow_id, runner_a)
            assert acquired is True, "Runner A should acquire lease"
            await session.commit()  # Lease visible to other runners NOW

        # Verify runner A holds the lease
        async with create_test_session_factory()() as session:
            lease_repo = LeaseRepository(session)
            lock_info = await lease_repo.get_lock_info(test_workflow_id)
            assert lock_info is not None
            assert lock_info.locked_by == runner_a
            original_expiry = lock_info.expires_at

        # Simulate stuck runner by manually expiring the lease
        # (In production, this happens naturally when renewal loop stops)
        # Note: expires_at must be > locked_at per valid_expiry constraint
        async with create_test_session_factory()() as session:
            locked_time = datetime.now(UTC) - timedelta(seconds=20)
            expired_time = datetime.now(UTC) - timedelta(seconds=10)  # Past but > locked_time
            await session.execute(
                text("""
                    UPDATE workflow_execution_locks
                    SET locked_at = :locked_at, expires_at = :expires_at
                    WHERE workflow_id = :workflow_id
                """),
                {
                    "workflow_id": test_workflow_id,
                    "locked_at": locked_time,
                    "expires_at": expired_time,
                },
            )
            await session.commit()

        # Runner B should now be able to take over
        async with create_test_session_factory()() as session:
            lease_repo = LeaseRepository(session)
            acquired = await lease_repo.acquire(test_workflow_id, runner_b)
            assert acquired is True, (
                "Runner B should take over expired lease from stuck runner"
            )
            await session.commit()

        # Verify runner B now holds the lease
        async with create_test_session_factory()() as session:
            lease_repo = LeaseRepository(session)
            lock_info = await lease_repo.get_lock_info(test_workflow_id)
            assert lock_info is not None
            assert lock_info.locked_by == runner_b, (
                f"Runner B should hold lease, but {lock_info.locked_by} holds it"
            )
            assert lock_info.expires_at > original_expiry, (
                "New lease should have fresh expiry time"
            )

        # Cleanup
        async with create_test_session_factory()() as session:
            lease_repo = LeaseRepository(session)
            await lease_repo.release(test_workflow_id, runner_b)
            await session.commit()
