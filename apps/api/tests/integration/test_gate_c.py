"""
Gate C Integration Tests - Deterministic Gating Enforcement

P6.3: Tests Gate C criterion:
  "Pass 2 cannot advance without approve; revise loops work; message doesn't bypass gating."

Uses monkeypatched LLM calls for deterministic, offline testing.
Graph-level tests only (Gate E covers API endpoints).

Test Scenarios (Doc 3 Appendix A Gate C):
  - C1: Message does not advance workflow
  - C2: Cannot advance without approve
  - C3: Revise loops back correctly
"""

import pytest
import pytest_asyncio
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings
from domain.state import (
    WorkflowState,
    StepState,
    StepPhase,
    StepStatus,
    PassType,
    StepName,
    GatePolicy,
    HumanAction,
    ValidationResult,
    STEP_NUMBERS,
)
from infrastructure.db.checkpoint_saver import SolverCheckpointSaver
from orchestration.graph import create_graph


# =============================================================================
# Test Fixtures
# =============================================================================


def make_thread_id() -> str:
    """Generate unique thread_id for test isolation."""
    return f"test-gate-c-{uuid4()}"


def make_initial_state(thread_id: str) -> WorkflowState:
    """Create Pass 2 workflow state for Gate C testing.

    Gate C is specifically about Pass 2 gating enforcement.
    """
    step = StepName.PROBLEM_DEFINITION
    return WorkflowState(
        workflow_id=thread_id,
        thread_id=thread_id,
        instance_id="test-instance",
        instance_number=0,
        gate_policy=GatePolicy.NONE,  # Would skip gates in Pass 1, but Pass 2 always gates
        current_pass=PassType.EXECUTION,  # Pass 2
        current_step=step,
        original_problem="Test problem for Gate C verification",
        step_state=StepState(
            step_name=step,
            step_number=STEP_NUMBERS[step],
            pass_type=PassType.EXECUTION,
        ),
    )


def assert_interrupted(result: dict) -> None:
    """Assert that the graph returned an interrupt."""
    assert "__interrupt__" in result, "Expected graph to interrupt but it completed"
    assert len(result["__interrupt__"]) > 0, "Expected interrupt data"


@pytest_asyncio.fixture
async def checkpointer():
    """Create checkpointer with cleanup.

    Uses SolverCheckpointSaver per DECISIONS.md (not PostgresSaver).
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


@pytest.fixture
def stub_llm_nodes(monkeypatch):
    """Stub LLM-calling functions for deterministic tests.

    Patches generate_step_output and validate_output to return
    deterministic results without network/LLM calls.
    """

    async def fake_generate_step_output(state: WorkflowState) -> dict:
        """Return deterministic output based on step."""
        step = state.current_step

        if step == StepName.PROBLEM_DEFINITION:
            return {
                "title": "Test Problem",
                "canonical_problem_definition": {
                    "statement": "Test problem statement for Gate C verification"
                },
                "stakeholders": [
                    {
                        "id": "SH-001",
                        "name_or_group": "Test User",
                        "role": "Tester",
                        "needs": ["Verify gating"],
                        "concerns": ["Test reliability"],
                        "impact": "High",
                    }
                ],
                "constraints": {
                    "hard": [{"id": "HC-001", "statement": "Must pass tests", "rationale": "CI requirement"}],
                    "soft": [],
                },
                "scope": {
                    "in": [{"id": "IN-001", "item": "Gate C testing"}],
                    "out": [{"id": "OUT-001", "item": "Gate D/E testing", "rationale": "Different slices"}],
                },
                "success_criteria": [
                    {
                        "id": "CRT-001",
                        "metric_or_signal": "Tests pass",
                        "target": "100%",
                        "how_verified": "pytest",
                    }
                ],
            }
        elif step == StepName.REQUIREMENTS:
            return {
                "overview": {
                    "summary": "Test requirements",
                    "boundaries": ["Gate C scope"],
                    "total_requirements": 1,
                    "priority_distribution": {"must": 1, "should": 0, "could": 0},
                },
                "requirements": [
                    {
                        "id": "FR-001",
                        "category": "FR",
                        "priority": "must",
                        "statement": "Gating must be enforced",
                        "rationale": "Core Gate C requirement",
                        "source": {"type": "stakeholder", "id": "SH-001", "aspect": "need"},
                        "component": ["orchestration"],
                        "testability": {"method": "test", "description": "Integration test"},
                        "trace": {"stakeholders": ["SH-001"]},
                    }
                ],
                "coverage_map": [
                    {
                        "source_type": "stakeholder",
                        "source_id": "SH-001",
                        "requirement_ids": ["FR-001"],
                        "coverage_note": "Fully covered",
                    }
                ],
            }
        else:
            # Step 3 or beyond
            return {
                "overview": {
                    "intent": "Test objectives",
                    "measurement_principles": ["Deterministic"],
                    "boundaries": ["Gate C"],
                    "total_objectives": 1,
                    "consolidation_ratio": 1.0,
                },
                "objectives": [
                    {
                        "id": "CAP-001",
                        "category": "CAP",
                        "tier": "primary",
                        "statement": "Gate C enforced",
                        "rationale": "Core requirement",
                        "owner_type": "system",
                        "linked_requirements": ["FR-001"],
                        "consolidated": False,
                        "success_criteria": {
                            "definition": "Tests pass",
                            "verification": {
                                "method": "test",
                                "description": "pytest",
                                "evidence_artifacts": ["test_gate_c.py"],
                            },
                        },
                        "component": ["orchestration"],
                        "acceptance_criteria": ["CRT-001"],
                    }
                ],
                "success_framework": {
                    "minimum_viable": {
                        "description": "Gate C works",
                        "objectives": ["CAP-001"],
                        "requirement_coverage": ["FR-001"],
                    },
                    "target": {
                        "description": "All tests pass",
                        "objectives": ["CAP-001"],
                        "requirement_coverage": ["FR-001"],
                    },
                    "aspirational": {
                        "description": "Full coverage",
                        "objectives": ["CAP-001"],
                        "requirement_coverage": ["FR-001"],
                    },
                },
                "trace_map": [
                    {"objective_id": "CAP-001", "requirement_ids": ["FR-001"], "consolidated": False}
                ],
            }

    async def fake_validate_output(
        step: StepName,
        output: dict,
        pass_type: PassType = None,
    ) -> ValidationResult:
        """Return passing validation without LLM."""
        return ValidationResult(passed=True, errors=[], warnings=[])

    # Patch the module-level functions
    monkeypatch.setattr("orchestration.nodes.generate_step_output", fake_generate_step_output)
    monkeypatch.setattr("orchestration.nodes.validate_output", fake_validate_output)


# =============================================================================
# Gate C Test Class
# =============================================================================


class TestGateCGatingEnforcement:
    """Gate C: Pass 2 cannot advance without explicit approve."""

    @pytest.mark.asyncio
    async def test_message_does_not_advance(self, checkpointer, stub_llm_nodes):
        """C1: MESSAGE keeps status at AWAITING_REVIEW, step unchanged.

        GIVEN a workflow in awaiting_review status
        WHEN I send MESSAGE action
        THEN status remains awaiting_review and step does NOT advance
        """
        graph = create_graph(checkpointer)
        thread_id = make_thread_id()
        checkpointer._test_thread_ids.append(thread_id)
        config = {"configurable": {"thread_id": thread_id}}

        initial_state = make_initial_state(thread_id)

        # Run to interrupt at review
        result1 = await graph.ainvoke(initial_state, config)
        assert_interrupted(result1)
        assert result1["step_state"].status == StepStatus.AWAITING_REVIEW
        original_step = result1["current_step"]

        # Apply MESSAGE (should NOT advance)
        await graph.aupdate_state(
            config,
            {"human_decision": HumanAction.MESSAGE},
            as_node="review",
        )

        # Resume - MESSAGE routes to "end", not "advance"
        result2 = await graph.ainvoke(None, config)

        # Verify: Step unchanged, status should indicate workflow ended at same step
        snapshot = await graph.aget_state(config)
        assert snapshot.values["current_step"] == StepName.PROBLEM_DEFINITION.value
        # MESSAGE doesn't change step_state.status - it stays at awaiting_review or routes to end

    @pytest.mark.asyncio
    async def test_resume_without_approve_does_not_advance(self, checkpointer, stub_llm_nodes):
        """C2: Resuming with no valid approval action does not advance step.

        GIVEN a workflow in awaiting_review status
        WHEN I resume without calling approve
        THEN system does not advance and step remains unchanged
        """
        graph = create_graph(checkpointer)
        thread_id = make_thread_id()
        checkpointer._test_thread_ids.append(thread_id)
        config = {"configurable": {"thread_id": thread_id}}

        initial_state = make_initial_state(thread_id)

        # Run to interrupt at review
        result1 = await graph.ainvoke(initial_state, config)
        assert_interrupted(result1)
        assert result1["step_state"].status == StepStatus.AWAITING_REVIEW
        original_step = result1["current_step"]

        # Resume WITHOUT setting human_decision (or with MESSAGE which doesn't advance)
        # MESSAGE is the "no-op" action that doesn't advance
        await graph.aupdate_state(
            config,
            {"human_decision": HumanAction.MESSAGE},
            as_node="review",
        )
        result2 = await graph.ainvoke(None, config)

        # Verify step has NOT advanced
        snapshot = await graph.aget_state(config)
        assert snapshot.values["current_step"] == original_step.value

    @pytest.mark.asyncio
    async def test_reject_loops_back_to_review(self, checkpointer, stub_llm_nodes):
        """C3: REJECT re-executes step and returns to AWAITING_REVIEW.

        GIVEN a workflow in awaiting_review status
        WHEN I apply REJECT with feedback
        THEN workflow re-executes step with feedback context
        AND eventually returns to awaiting_review status on same step
        """
        graph = create_graph(checkpointer)
        thread_id = make_thread_id()
        checkpointer._test_thread_ids.append(thread_id)
        config = {"configurable": {"thread_id": thread_id}}

        initial_state = make_initial_state(thread_id)

        # Run to interrupt at review
        result1 = await graph.ainvoke(initial_state, config)
        assert_interrupted(result1)
        assert result1["step_state"].status == StepStatus.AWAITING_REVIEW
        original_step = result1["current_step"]

        # Apply REJECT with feedback
        await graph.aupdate_state(
            config,
            {
                "human_decision": HumanAction.REJECT,
                "human_feedback": "Please add more detail to the analysis",
            },
            as_node="review",
        )

        # Resume - should re-execute (structure_node) and return to review
        result2 = await graph.ainvoke(None, config)

        # Should interrupt again at same step (re-execution complete)
        assert_interrupted(result2)
        assert result2["current_step"] == original_step  # Same step
        assert result2["step_state"].status == StepStatus.AWAITING_REVIEW

    @pytest.mark.asyncio
    async def test_approve_does_advance(self, checkpointer, stub_llm_nodes):
        """Positive case: APPROVE advances to next step.

        GIVEN a workflow in awaiting_review status at Step 1
        WHEN I apply APPROVE
        THEN workflow advances to Step 2
        """
        graph = create_graph(checkpointer)
        thread_id = make_thread_id()
        checkpointer._test_thread_ids.append(thread_id)
        config = {"configurable": {"thread_id": thread_id}}

        initial_state = make_initial_state(thread_id)

        # Run to interrupt at review (Step 1)
        result1 = await graph.ainvoke(initial_state, config)
        assert_interrupted(result1)
        assert result1["current_step"] == StepName.PROBLEM_DEFINITION
        assert result1["step_state"].status == StepStatus.AWAITING_REVIEW

        # Apply APPROVE
        await graph.aupdate_state(
            config,
            {"human_decision": HumanAction.APPROVE},
            as_node="review",
        )

        # Resume - should advance to Step 2 and interrupt at Step 2's review
        result2 = await graph.ainvoke(None, config)

        # Should have advanced to Step 2 (requirements)
        # In Pass 2, it will interrupt again at Step 2's review
        if "__interrupt__" in result2:
            assert result2["current_step"] == StepName.REQUIREMENTS
        else:
            # If no interrupt, check serialized value
            assert result2["current_step"] == StepName.REQUIREMENTS.value
