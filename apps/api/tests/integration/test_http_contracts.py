"""
HTTP Contract Tests for V2.8.2 Endpoints.

Verifies actual HTTP responses match Tech Spec V2.8.2 schemas:
- Message endpoint: Returns persisted message_id (not random UUID)
- Progress endpoint: Returns current_step (string) + current_step_number (int)
- Staleness endpoint: Returns can_complete based on artifacts AND trace links

These tests use FastAPI's TestClient with ASGI transport to make real HTTP calls
and verify JSON response shapes and semantics.

Complements test_api_contracts.py which tests Pydantic model shapes only.

Note on transaction handling:
- GET endpoints (progress, staleness) use session override with transactional fixture
- POST endpoints (message) use real sessions since endpoints call session.begin()
  which conflicts with the test's outer transaction. These tests commit data
  and clean up afterward.
"""

import pytest
import pytest_asyncio
from uuid import uuid4, UUID
from datetime import datetime
from typing import AsyncGenerator

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from main import app
from config import settings
from infrastructure.postgres import get_session
from infrastructure.db.models import (
    Workflow,
    WorkflowStatus,
    PassType,
    StepName,
    StepStatus,
    StepPhase,
    GatePolicy,
    StepExecution,
    Message,
)
from infrastructure.db.models.traceability import TraceabilityLink
from infrastructure.db.repositories.workflow import WorkflowRepository
from infrastructure.db.repositories.step_execution import StepExecutionRepository
from infrastructure.db.repositories.message import MessageRepository


# =============================================================================
# Fixtures for Read Endpoints (GET)
# =============================================================================


@pytest_asyncio.fixture
async def http_client_readonly(db_session: AsyncSession):
    """Async HTTP client for read-only endpoints.

    Overrides get_session dependency to use the test's transactional session,
    ensuring test data is visible to API routes and rolled back after test.

    Use this for GET endpoints only - POST endpoints that call session.begin()
    conflict with the test's outer transaction.
    """
    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def awaiting_review_workflow(
    db_session: AsyncSession,
    instance_0,
) -> tuple[Workflow, StepExecution]:
    """Create a workflow in AWAITING_REVIEW status for message tests."""
    workflow_repo = WorkflowRepository(db_session)
    step_repo = StepExecutionRepository(db_session)

    workflow = Workflow(
        workflow_id=f"http-test-{uuid4()}",
        thread_id=f"thread-{uuid4()}",
        instance_id=instance_0.id,
        original_problem="Test problem for HTTP contract tests",
        current_pass=PassType.DEFINITION,
        current_step=StepName.REQUIREMENTS,
        current_step_number=2,
        status=WorkflowStatus.ACTIVE,
        pass_1_gate_policy=GatePolicy.PER_STEP,
        created_by="test-user",
        last_actor_id="test-user",
    )
    workflow = await workflow_repo.create(workflow)

    step = StepExecution(
        workflow_id=workflow.id,
        pass_type=PassType.DEFINITION,
        step_name=StepName.REQUIREMENTS,
        step_number=2,
        status=StepStatus.AWAITING_REVIEW,
        phase=StepPhase.COMPLETE,
    )
    step = await step_repo.create(step)

    await db_session.flush()  # Flush to make data visible, but don't commit (rollback at end)
    return workflow, step


# =============================================================================
# Fixtures for Write Endpoints (POST)
# =============================================================================


@pytest_asyncio.fixture
async def http_client_write():
    """Async HTTP client for write endpoints.

    Uses app's real sessions (no override) since POST endpoints call
    session.begin() which conflicts with the transactional test fixture.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def committed_workflow() -> tuple[str, UUID]:
    """Create a committed workflow for write endpoint tests.

    Creates and commits a workflow with AWAITING_REVIEW status.
    Returns (workflow_id, workflow_uuid) for tests and cleanup.
    Cleans up after test completes.
    """
    engine = create_async_engine(settings.postgres_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    workflow_id = f"http-write-test-{uuid4()}"
    workflow_uuid = None

    async with session_factory() as session:
        # Get instance_0
        from infrastructure.db.repositories.instance import InstanceRepository
        instance_repo = InstanceRepository(session)
        instance = await instance_repo.get_by_number(0)

        workflow_repo = WorkflowRepository(session)
        step_repo = StepExecutionRepository(session)

        workflow = Workflow(
            workflow_id=workflow_id,
            thread_id=f"thread-{uuid4()}",
            instance_id=instance.id,
            original_problem="Test problem for HTTP write tests",
            current_pass=PassType.DEFINITION,
            current_step=StepName.REQUIREMENTS,
            current_step_number=2,
            status=WorkflowStatus.ACTIVE,
            pass_1_gate_policy=GatePolicy.PER_STEP,
            created_by="test-user",
            last_actor_id="test-user",
        )
        workflow = await workflow_repo.create(workflow)
        workflow_uuid = workflow.id

        step = StepExecution(
            workflow_id=workflow.id,
            pass_type=PassType.DEFINITION,
            step_name=StepName.REQUIREMENTS,
            step_number=2,
            status=StepStatus.AWAITING_REVIEW,
            phase=StepPhase.COMPLETE,
        )
        await step_repo.create(step)

        await session.commit()

    yield workflow_id, workflow_uuid

    # Cleanup: delete test data using raw SQL for simplicity
    async with session_factory() as session:
        from sqlalchemy import text

        # Delete messages for all step executions of this workflow
        await session.execute(
            text("""
                DELETE FROM messages
                WHERE step_execution_id IN (
                    SELECT id FROM step_executions WHERE workflow_id = :workflow_uuid
                )
            """),
            {"workflow_uuid": workflow_uuid}
        )
        # Delete step executions
        await session.execute(
            text("DELETE FROM step_executions WHERE workflow_id = :workflow_uuid"),
            {"workflow_uuid": workflow_uuid}
        )
        # Delete workflow
        await session.execute(
            text("DELETE FROM workflows WHERE id = :workflow_uuid"),
            {"workflow_uuid": workflow_uuid}
        )
        await session.commit()

    await engine.dispose()


# =============================================================================
# Test: Message Endpoint - HTTP Response Shape (V2.8.2 §16.7)
# =============================================================================


@pytest.mark.asyncio
async def test_message_endpoint_returns_persisted_id(
    http_client_write: AsyncClient,
    committed_workflow: tuple[str, UUID],
):
    """Message endpoint returns actual persisted message_id, not random UUID.

    V2.8.2 Fix: The message_id in response MUST match a persisted Message record.
    Also verifies response shape per §16.7: {message_id, status} only (no position).
    """
    workflow_id, workflow_uuid = committed_workflow

    # Send message via HTTP
    response = await http_client_write.post(
        f"/api/v1/workflows/{workflow_id}/actions/message",
        json={"content": "Test message for HTTP contract verification"},
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    data = response.json()

    # V2.8.2 §16.7: Response shape is {message_id, status}
    assert "message_id" in data, "Response missing message_id"
    assert "status" in data, "Response missing status"
    assert data["status"] == "sent", f"Expected status='sent', got '{data['status']}'"

    # V2.8.2 §9.3 exception: Should only have message_id and status (no position wrapper)
    assert set(data.keys()) == {"message_id", "status"}, \
        f"Expected only {{message_id, status}}, got {set(data.keys())}"

    # V2.8.2 Fix: Verify message_id is a valid UUID
    message_id = data["message_id"]
    try:
        parsed_uuid = UUID(message_id)
    except ValueError:
        pytest.fail(f"message_id is not a valid UUID: {message_id}")

    # V2.8.2 Fix: Verify message_id corresponds to a persisted record
    # Use a fresh session to verify (the endpoint committed its own transaction)
    engine = create_async_engine(settings.postgres_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        message_repo = MessageRepository(session)
        message = await message_repo.get_by_id(parsed_uuid)
        assert message is not None, f"No Message record found for ID {message_id}"
        assert message.content == "Test message for HTTP contract verification"
    await engine.dispose()


# =============================================================================
# Test: Progress Endpoint - HTTP Response Shape (V2.8.2 C.3)
# =============================================================================


@pytest.mark.asyncio
async def test_progress_endpoint_schema(
    http_client_readonly: AsyncClient,
    awaiting_review_workflow: tuple[Workflow, StepExecution],
):
    """Progress endpoint returns current_step (string) + current_step_number (int).

    V2.8.2 C.3: current_step is step name, current_step_number is 1-indexed position.
    """
    workflow, step = awaiting_review_workflow

    response = await http_client_readonly.get(
        f"/api/v1/workflows/{workflow.workflow_id}/progress"
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    data = response.json()

    # V2.8.2 C.3: Required fields
    assert "workflow_id" in data
    assert "state_version" in data
    assert "current_pass" in data
    assert "steps" in data

    # V2.8.2 C.3: current_step is string (step name), current_step_number is int
    assert "current_step" in data, "Missing current_step"
    assert "current_step_number" in data, "Missing current_step_number"

    assert isinstance(data["current_step"], str), "current_step should be string"
    assert isinstance(data["current_step_number"], int), "current_step_number should be int"

    # Verify values match expected
    assert data["current_step"] == "requirements", \
        f"Expected current_step='requirements', got '{data['current_step']}'"
    assert data["current_step_number"] == 2, \
        f"Expected current_step_number=2, got {data['current_step_number']}"


# =============================================================================
# Test: Staleness Endpoint - HTTP Response Shape (V2.8.2 C.5)
# =============================================================================


@pytest.mark.asyncio
async def test_staleness_endpoint_schema(
    http_client_readonly: AsyncClient,
    awaiting_review_workflow: tuple[Workflow, StepExecution],
):
    """Staleness endpoint returns V2.8.2 C.5 schema.

    Includes: has_stale_artifacts, stale_trace_links (not stale_links), position.
    """
    workflow, step = awaiting_review_workflow

    response = await http_client_readonly.get(
        f"/api/v1/workflows/{workflow.workflow_id}/staleness"
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    data = response.json()

    # V2.8.2 C.5: Required fields
    assert "workflow_id" in data
    assert "state_version" in data
    assert "can_complete" in data
    assert "stale_artifacts" in data

    # V2.8.2 additions
    assert "has_stale_artifacts" in data, "Missing has_stale_artifacts"
    assert "position" in data, "Missing position"
    assert "blocking_reasons" in data, "Missing blocking_reasons"

    # V2.8.2: Renamed from stale_links
    assert "stale_trace_links" in data, "Missing stale_trace_links"
    assert "stale_links" not in data, "Should use stale_trace_links, not stale_links"

    # Type checks
    assert isinstance(data["has_stale_artifacts"], bool)
    assert isinstance(data["can_complete"], bool)
    assert isinstance(data["blocking_reasons"], list)
    assert isinstance(data["stale_artifacts"], list)
    assert isinstance(data["stale_trace_links"], list)


@pytest.mark.asyncio
async def test_staleness_can_complete_with_no_stale_content(
    http_client_readonly: AsyncClient,
    awaiting_review_workflow: tuple[Workflow, StepExecution],
):
    """can_complete is True when no stale artifacts or trace links.

    V2.8.2 C.5: can_complete = not (any blocking artifacts OR any stale trace links).
    """
    workflow, step = awaiting_review_workflow

    response = await http_client_readonly.get(
        f"/api/v1/workflows/{workflow.workflow_id}/staleness"
    )

    assert response.status_code == 200
    data = response.json()

    # Fresh workflow should have no stale content
    assert data["has_stale_artifacts"] is False
    assert data["can_complete"] is True
    assert len(data["stale_artifacts"]) == 0
    assert len(data["stale_trace_links"]) == 0


@pytest_asyncio.fixture
async def workflow_with_stale_link(
    db_session: AsyncSession,
    instance_0,
) -> tuple[Workflow, StepExecution, TraceabilityLink]:
    """Create a workflow with a stale trace link for testing can_complete semantics."""
    workflow_repo = WorkflowRepository(db_session)
    step_repo = StepExecutionRepository(db_session)

    workflow = Workflow(
        workflow_id=f"stale-link-test-{uuid4()}",
        thread_id=f"thread-{uuid4()}",
        instance_id=instance_0.id,
        original_problem="Test problem with stale trace link",
        current_pass=PassType.DEFINITION,
        current_step=StepName.REQUIREMENTS,
        current_step_number=2,
        status=WorkflowStatus.ACTIVE,
        pass_1_gate_policy=GatePolicy.PER_STEP,
        created_by="test-user",
        last_actor_id="test-user",
    )
    workflow = await workflow_repo.create(workflow)

    step = StepExecution(
        workflow_id=workflow.id,
        pass_type=PassType.DEFINITION,
        step_name=StepName.REQUIREMENTS,
        step_number=2,
        status=StepStatus.AWAITING_REVIEW,
        phase=StepPhase.COMPLETE,
    )
    step = await step_repo.create(step)

    # Create a stale trace link
    stale_link = TraceabilityLink(
        workflow_id=workflow.id,
        from_step=1,
        from_type="stakeholder",
        from_id="SH-001",
        to_step=2,
        to_type="requirement",
        to_id="FR-001",
        link_type="derives",
        stale=True,
        stale_reason="upstream_revision",
        stale_since=datetime.utcnow(),
    )
    db_session.add(stale_link)

    await db_session.flush()
    return workflow, step, stale_link


@pytest.mark.asyncio
async def test_staleness_can_complete_false_with_stale_trace_link(
    http_client_readonly: AsyncClient,
    workflow_with_stale_link: tuple[Workflow, StepExecution, TraceabilityLink],
):
    """can_complete is False when stale trace links exist.

    V2.8.2 C.5: can_complete = not (any blocking artifacts OR any stale trace links).
    This test locks in the trace link blocking semantics.
    """
    workflow, step, stale_link = workflow_with_stale_link

    response = await http_client_readonly.get(
        f"/api/v1/workflows/{workflow.workflow_id}/staleness"
    )

    assert response.status_code == 200
    data = response.json()

    # With stale trace link, can_complete should be False
    assert data["can_complete"] is False, \
        "can_complete should be False when stale trace links exist"
    assert len(data["stale_trace_links"]) == 1, \
        f"Expected 1 stale trace link, got {len(data['stale_trace_links'])}"

    # Verify the stale link details
    link = data["stale_trace_links"][0]
    assert link["from_step"] == "1"
    assert link["to_step"] == "2"
    assert link["link_type"] == "derives"
    assert link["reason"] == "upstream_revision"

    # Verify blocking_reasons includes trace links
    assert any("stale traceability link" in reason.lower() for reason in data["blocking_reasons"]), \
        f"Expected blocking_reasons to mention trace links: {data['blocking_reasons']}"
