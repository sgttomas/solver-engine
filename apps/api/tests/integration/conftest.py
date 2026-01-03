"""
Integration Test Fixtures.

Provides async database session with transaction rollback for test isolation.
Tests use real PostgreSQL with migrations applied.
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from config import settings
from infrastructure.db.models import (
    Base,
    Instance,
    InstanceType,
    GatePolicy,
    Workflow,
    WorkflowStatus,
    PassType,
    StepName,
    StepExecution,
    StepStatus,
    StepPhase,
)
from infrastructure.db.repositories import (
    InstanceRepository,
    WorkflowRepository,
    StepExecutionRepository,
)


# Create test engine using same connection string as app
# but with savepoint-based transaction isolation
@pytest.fixture(scope="session")
def event_loop_policy():
    """Use default event loop policy for async tests."""
    import asyncio
    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Async database session with transaction rollback.

    Each test runs in a transaction that is rolled back after
    the test completes, ensuring test isolation.
    """
    engine = create_async_engine(
        settings.postgres_url,
        echo=False,
    )

    async with engine.connect() as connection:
        # Start a transaction
        transaction = await connection.begin()

        # Create a session bound to this connection
        async_session_factory = async_sessionmaker(
            bind=connection,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        async with async_session_factory() as session:
            yield session

        # Rollback to clean up test data
        await transaction.rollback()

    await engine.dispose()


@pytest_asyncio.fixture
async def instance_0(db_session: AsyncSession) -> Instance:
    """Get Instance 0 (seeded in migration) or create for tests.

    Instance 0 is the Universal Methodology instance.
    It should exist from the migration seed.
    """
    repo = InstanceRepository(db_session)
    instance = await repo.get_by_number(0)

    if instance is None:
        # Create if not seeded (shouldn't happen with migrations)
        instance = Instance(
            instance_number=0,
            instance_type=InstanceType.UNIVERSAL,
            name="Universal Methodology",
            description="Domain-agnostic structured reasoning protocol",
            pass_1_gate_policy=GatePolicy.PER_STEP,
        )
        instance = await repo.create(instance)

    return instance


@pytest_asyncio.fixture
async def test_workflow(
    db_session: AsyncSession,
    instance_0: Instance,
) -> Workflow:
    """Create a test workflow.

    Depends on instance_0 for FK constraint.
    """
    repo = WorkflowRepository(db_session)

    workflow = Workflow(
        workflow_id="test-workflow-001",
        thread_id="test-thread-001",
        instance_id=instance_0.id,
        original_problem="Test problem for integration tests",
        current_pass=PassType.DEFINITION,
        current_step=StepName.PROBLEM_DEFINITION,
        current_step_number=1,
        status=WorkflowStatus.ACTIVE,
        pass_1_gate_policy=GatePolicy.PER_STEP,
        created_by="test-user",
        last_actor_id="test-user",
    )

    return await repo.create(workflow)


@pytest_asyncio.fixture
async def test_step_execution(
    db_session: AsyncSession,
    test_workflow: Workflow,
) -> StepExecution:
    """Create a test step execution.

    Depends on test_workflow for FK constraint.
    """
    repo = StepExecutionRepository(db_session)

    step = StepExecution(
        workflow_id=test_workflow.id,
        pass_type=PassType.DEFINITION,
        step_name=StepName.PROBLEM_DEFINITION,
        step_number=1,
        status=StepStatus.NOT_STARTED,
        phase=StepPhase.RECEIVED,
    )

    return await repo.create(step)
