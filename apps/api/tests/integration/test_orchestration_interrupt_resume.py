"""
Integration tests for LangGraph interrupt/resume behavior.

P3.4 scope: Verify Gates C and D
- Gate C: Cannot advance without explicit `approve` action
- Gate D: State survives restart

Uses real PostgreSQL via SolverCheckpointSaver.

NOTE: These tests require a valid LLM API key (OpenAI, Anthropic, or Google).
They will be skipped if no valid API key is configured.
"""

import os
import pytest
import pytest_asyncio
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings


# Skip entire module unless RUN_LLM_TESTS=1 is set
# These tests require a VALID LLM API key (calls real OpenAI/Anthropic/Google APIs)
pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LLM_TESTS", "0") != "1",
    reason="LLM tests require RUN_LLM_TESTS=1 and valid API key"
)

from domain.state import (
    WorkflowState,
    StepState,
    StepPhase,
    StepStatus,
    PassType,
    StepName,
    GatePolicy,
    HumanAction,
    STEP_NUMBERS,
)
from infrastructure.db.checkpoint_saver import SolverCheckpointSaver
from orchestration.graph import create_graph


def make_thread_id() -> str:
    """Generate unique thread_id for test isolation."""
    return f"test-interrupt-{uuid4()}"


def make_initial_state(thread_id: str, pass_type: PassType = PassType.EXECUTION) -> WorkflowState:
    """Create initial workflow state for testing.

    Args:
        thread_id: Unique thread identifier
        pass_type: DEFINITION (Pass 1) or EXECUTION (Pass 2)

    Returns:
        WorkflowState ready for graph execution
    """
    step = StepName.PROBLEM_DEFINITION
    return WorkflowState(
        workflow_id=thread_id,
        thread_id=thread_id,
        instance_id="test-instance",
        instance_number=0,
        gate_policy=GatePolicy.NONE,  # NONE would skip gates in Pass 1
        current_pass=pass_type,
        current_step=step,
        original_problem="Test problem for interrupt/resume verification",
        step_state=StepState(
            step_name=step,
            step_number=STEP_NUMBERS[step],
            pass_type=pass_type,
        ),
    )


def assert_interrupted(result: dict) -> None:
    """Assert that the graph returned an interrupt.

    LangGraph returns results with __interrupt__ key when interrupt() is called.
    """
    assert "__interrupt__" in result, "Expected graph to interrupt but it completed"
    assert len(result["__interrupt__"]) > 0, "Expected interrupt data"


@pytest_asyncio.fixture
async def checkpointer():
    """Create checkpointer with cleanup.

    Each test gets a fresh checkpointer with unique thread_ids.
    Cleanup deletes test threads after test completes.
    """
    engine = create_async_engine(settings.postgres_url, echo=False)
    factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    saver = SolverCheckpointSaver(factory, engine=engine)
    saver._test_thread_ids = []

    yield saver

    # Cleanup
    for thread_id in saver._test_thread_ids:
        try:
            await saver.adelete_thread(thread_id)
        except Exception:
            pass  # Ignore cleanup errors

    await engine.dispose()


class TestPass2InterruptBehavior:
    """Test that Pass 2 always interrupts at review gate."""

    @pytest.mark.asyncio
    async def test_pass2_interrupts_at_review_with_none_policy(self, checkpointer):
        """Pass 2 must interrupt at review_node even with NONE gate policy.

        NONE policy would skip gates in Pass 1, but Pass 2 always requires
        human approval per Doc 2.
        """
        graph = create_graph(checkpointer)
        thread_id = make_thread_id()
        checkpointer._test_thread_ids.append(thread_id)
        config = {"configurable": {"thread_id": thread_id}}

        # Create Pass 2 state with NONE policy
        initial_state = make_initial_state(thread_id, PassType.EXECUTION)

        # Run until interrupt
        result = await graph.ainvoke(initial_state, config)
        assert_interrupted(result)

        # Verify at review gate (step_state in result is dataclass, not dict yet)
        step_state = result["step_state"]
        assert step_state.status == StepStatus.AWAITING_REVIEW
        assert step_state.phase == StepPhase.REVIEWING

        # Also verify via checkpoint (serialized as dict)
        snapshot = await graph.aget_state(config)
        assert snapshot is not None
        step_state_dict = snapshot.values["step_state"]
        assert step_state_dict["status"] == StepStatus.AWAITING_REVIEW.value
        assert step_state_dict["phase"] == StepPhase.REVIEWING.value


class TestGateDStateSurvivesRestart:
    """Test that state survives process restart (Gate D)."""

    @pytest.mark.asyncio
    async def test_state_survives_restart(self):
        """State persists across checkpointer/graph recreation.

        Simulates process death by disposing engine and creating
        completely new checkpointer and graph instances.
        """
        thread_id = make_thread_id()

        # --- Phase 1: Run to interrupt with first checkpointer ---
        engine1 = create_async_engine(settings.postgres_url, echo=False)
        factory1 = async_sessionmaker(engine1, class_=AsyncSession, expire_on_commit=False)
        saver1 = SolverCheckpointSaver(factory1, engine=engine1)
        graph1 = create_graph(saver1)
        config = {"configurable": {"thread_id": thread_id}}

        initial_state = make_initial_state(thread_id, PassType.EXECUTION)

        result1 = await graph1.ainvoke(initial_state, config)
        assert_interrupted(result1)

        # Dispose to simulate process death
        await engine1.dispose()

        # --- Phase 2: Create completely NEW everything, same thread_id ---
        engine2 = create_async_engine(settings.postgres_url, echo=False)
        factory2 = async_sessionmaker(engine2, class_=AsyncSession, expire_on_commit=False)
        saver2 = SolverCheckpointSaver(factory2, engine=engine2)
        graph2 = create_graph(saver2)

        # Load state from checkpoint
        snapshot = await graph2.aget_state(config)
        assert snapshot is not None, "State should persist after restart"

        # Verify state is correct (serialized as dict)
        step_state = snapshot.values["step_state"]
        assert step_state["status"] == StepStatus.AWAITING_REVIEW.value

        # Resume with approve (as_node tells LangGraph this completes the review)
        await graph2.aupdate_state(
            config,
            {"human_decision": HumanAction.APPROVE.value},
            as_node="review",
        )
        result = await graph2.ainvoke(None, config)

        # Check if we hit another interrupt (Step 2 review) or completed
        # For Pass 2 NONE policy, each step still requires approval
        if "__interrupt__" in result:
            # Advanced to Step 2 and interrupted at its review
            assert result["current_step"] == StepName.REQUIREMENTS
        else:
            # Workflow completed or advanced
            assert result["current_step"] == StepName.REQUIREMENTS.value

        # Cleanup
        await saver2.adelete_thread(thread_id)
        await engine2.dispose()


class TestGateCCannotAdvanceWithoutApprove:
    """Test that MESSAGE action does not advance state (Gate C)."""

    @pytest.mark.asyncio
    async def test_message_does_not_advance_state(self, checkpointer):
        """MESSAGE action keeps state at AWAITING_REVIEW.

        Per Doc 2: message action must NOT change state.
        """
        graph = create_graph(checkpointer)
        thread_id = make_thread_id()
        checkpointer._test_thread_ids.append(thread_id)
        config = {"configurable": {"thread_id": thread_id}}

        initial_state = make_initial_state(thread_id, PassType.EXECUTION)

        # Run to interrupt
        result1 = await graph.ainvoke(initial_state, config)
        assert_interrupted(result1)

        # Verify at review
        assert result1["step_state"].status == StepStatus.AWAITING_REVIEW

        # Update with MESSAGE (should not advance)
        await graph.aupdate_state(
            config,
            {"human_decision": HumanAction.MESSAGE},
            as_node="review",
        )

        # Resume - should still interrupt at review (MESSAGE routes to "end")
        result2 = await graph.ainvoke(None, config)

        # With MESSAGE action, route_after_decision returns "end" so workflow ends
        # Gate C is actually about approve being required - MESSAGE shouldn't advance
        # The state should remain at Step 1, not advance to Step 2
        snapshot = await graph.aget_state(config)
        step_state = snapshot.values["step_state"]
        # Still at problem_definition (Step 1), not advanced to requirements (Step 2)
        assert snapshot.values["current_step"] == StepName.PROBLEM_DEFINITION.value

    @pytest.mark.asyncio
    async def test_approve_does_advance_state(self, checkpointer):
        """APPROVE action advances state to next step."""
        graph = create_graph(checkpointer)
        thread_id = make_thread_id()
        checkpointer._test_thread_ids.append(thread_id)
        config = {"configurable": {"thread_id": thread_id}}

        initial_state = make_initial_state(thread_id, PassType.EXECUTION)

        # Run to interrupt
        result1 = await graph.ainvoke(initial_state, config)
        assert_interrupted(result1)

        # Approve (as_node tells LangGraph this completes the review)
        await graph.aupdate_state(
            config,
            {"human_decision": HumanAction.APPROVE},
            as_node="review",
        )

        # Resume - should advance to Step 2 and interrupt again (Pass 2)
        result = await graph.ainvoke(None, config)

        # Should have advanced to Step 2 (requirements)
        # In Pass 2, it will interrupt again at Step 2's review
        if "__interrupt__" in result:
            assert result["current_step"] == StepName.REQUIREMENTS
        else:
            assert result["current_step"] == StepName.REQUIREMENTS.value


class TestFullRestartResumeCycle:
    """Test complete interrupt → restart → resume → advance cycle."""

    @pytest.mark.asyncio
    async def test_full_cycle_with_artifact_verification(self):
        """Full workflow: interrupt → restart → approve → advance.

        Verifies:
        - State survives restart
        - Approve advances workflow
        - Artifact stored in methodology dict
        """
        thread_id = make_thread_id()

        # --- Run to interrupt ---
        engine1 = create_async_engine(settings.postgres_url, echo=False)
        factory1 = async_sessionmaker(engine1, class_=AsyncSession, expire_on_commit=False)
        saver1 = SolverCheckpointSaver(factory1, engine=engine1)
        graph1 = create_graph(saver1)
        config = {"configurable": {"thread_id": thread_id}}

        # Use Pass 1 with PER_STEP policy to test artifact storage
        initial_state = WorkflowState(
            workflow_id=thread_id,
            thread_id=thread_id,
            instance_id="test-instance",
            instance_number=0,
            gate_policy=GatePolicy.PER_STEP,
            current_pass=PassType.DEFINITION,
            current_step=StepName.PROBLEM_DEFINITION,
            original_problem="Test problem",
            step_state=StepState(
                step_name=StepName.PROBLEM_DEFINITION,
                step_number=1,
                pass_type=PassType.DEFINITION,
            ),
        )

        result1 = await graph1.ainvoke(initial_state, config)
        assert_interrupted(result1)

        await engine1.dispose()

        # --- Restart and resume ---
        engine2 = create_async_engine(settings.postgres_url, echo=False)
        factory2 = async_sessionmaker(engine2, class_=AsyncSession, expire_on_commit=False)
        saver2 = SolverCheckpointSaver(factory2, engine=engine2)
        graph2 = create_graph(saver2)

        # Approve (as_node tells LangGraph this completes the review)
        await graph2.aupdate_state(
            config,
            {"human_decision": HumanAction.APPROVE},
            as_node="review",
        )
        result = await graph2.ainvoke(None, config)

        # Should advance to Step 2 and interrupt again (PER_STEP policy)
        if "__interrupt__" in result:
            # Advanced to Step 2 and interrupted
            assert result["current_step"] == StepName.REQUIREMENTS
            assert "problem_definition" in result["methodology"]
        else:
            # Check serialized values
            assert result["current_step"] == StepName.REQUIREMENTS.value
            assert "problem_definition" in result["methodology"]

        # Cleanup
        await saver2.adelete_thread(thread_id)
        await engine2.dispose()
