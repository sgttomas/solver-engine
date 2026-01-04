"""
Gate D Integration Tests - Restart/Recovery

P6.4: Tests Gate D criterion:
  "Restart + resume works mid-step and at awaiting_review with no lost artifacts."

Uses monkeypatched LLM calls for deterministic, offline testing.
Graph-level tests only (Gate E covers API endpoints).

Test Scenarios (Doc 3 Appendix A Gate D):
  - D1-D4: State, artifacts, and messages survive process restart
  - Resume: Workflow can continue after restart

Note: Mid-step recovery is not tested due to:
  - LangGraph checkpoints at interrupt boundaries, not mid-generation
  - Deterministic testing requires checkpoint-based restart points
  See plan for pragmatic limitation acknowledgment.
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
    return f"test-gate-d-{uuid4()}"


def make_initial_state(thread_id: str) -> WorkflowState:
    """Create Pass 2 workflow state for Gate D testing.

    Includes seeded messages for conversation history preservation test.
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
        original_problem="Test problem for Gate D restart/recovery verification",
        step_state=StepState(
            step_name=step,
            step_number=STEP_NUMBERS[step],
            pass_type=PassType.EXECUTION,
        ),
        # Seed messages for conversation history preservation test
        messages=[
            {"role": "user", "content": "Initial problem description for Gate D test"},
            {"role": "assistant", "content": "Acknowledged. Processing problem definition."},
        ],
    )


def assert_interrupted(result: dict) -> None:
    """Assert that the graph returned an interrupt."""
    assert "__interrupt__" in result, "Expected graph to interrupt but it completed"
    assert len(result["__interrupt__"]) > 0, "Expected interrupt data"


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
                    "statement": "Test problem statement for Gate D verification"
                },
                "stakeholders": [
                    {
                        "id": "SH-001",
                        "name_or_group": "Test User",
                        "role": "Tester",
                        "needs": ["Verify restart recovery"],
                        "concerns": ["State persistence"],
                        "impact": "High",
                    }
                ],
                "constraints": {
                    "hard": [{"id": "HC-001", "statement": "Must survive restart", "rationale": "Gate D requirement"}],
                    "soft": [],
                },
                "scope": {
                    "in": [{"id": "IN-001", "item": "Gate D testing"}],
                    "out": [{"id": "OUT-001", "item": "Gate C/E testing", "rationale": "Different slices"}],
                },
                "success_criteria": [
                    {
                        "id": "CRT-001",
                        "metric_or_signal": "State survives restart",
                        "target": "100%",
                        "how_verified": "pytest",
                    }
                ],
            }
        elif step == StepName.REQUIREMENTS:
            return {
                "overview": {
                    "summary": "Test requirements for Gate D",
                    "boundaries": ["Gate D scope"],
                    "total_requirements": 1,
                    "priority_distribution": {"must": 1, "should": 0, "could": 0},
                },
                "requirements": [
                    {
                        "id": "FR-001",
                        "category": "FR",
                        "priority": "must",
                        "statement": "State must survive restart",
                        "rationale": "Core Gate D requirement",
                        "source": {"type": "stakeholder", "id": "SH-001", "aspect": "need"},
                        "component": ["persistence"],
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
            # Step 3 (objectives) or beyond
            return {
                "overview": {
                    "intent": "Test objectives for Gate D",
                    "measurement_principles": ["Deterministic"],
                    "boundaries": ["Gate D"],
                    "total_objectives": 1,
                    "consolidation_ratio": 1.0,
                },
                "objectives": [
                    {
                        "id": "CAP-001",
                        "category": "CAP",
                        "tier": "primary",
                        "statement": "Gate D enforced",
                        "rationale": "Core requirement",
                        "owner_type": "system",
                        "linked_requirements": ["FR-001"],
                        "consolidated": False,
                        "success_criteria": {
                            "definition": "Restart works",
                            "verification": {
                                "method": "test",
                                "description": "pytest",
                                "evidence_artifacts": ["test_gate_d.py"],
                            },
                        },
                        "component": ["persistence"],
                        "acceptance_criteria": ["CRT-001"],
                    }
                ],
                "success_framework": {
                    "minimum_viable": {
                        "description": "Gate D works",
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
# Gate D Test Class
# =============================================================================


class TestGateDRestartRecovery:
    """Gate D: State survives restart; artifacts and messages preserved."""

    @pytest.mark.asyncio
    async def test_restart_preserves_state_and_artifacts(self, stub_llm_nodes):
        """D1-D4: State, artifacts, and messages survive process restart.

        GIVEN a workflow at Step 2 awaiting_review with Step 1 artifacts and messages
        WHEN process restarts (engine disposed, new checkpointer/graph created)
        THEN current_step == REQUIREMENTS
        AND step_state.status == AWAITING_REVIEW
        AND methodology["problem_definition"] exists (Step 1 artifact)
        AND messages preserved
        """
        thread_id = make_thread_id()

        # =====================================================================
        # Phase 1: Build to Step 2 awaiting_review with first engine
        # =====================================================================
        engine1 = create_async_engine(settings.postgres_url, echo=False)
        factory1 = async_sessionmaker(engine1, class_=AsyncSession, expire_on_commit=False)
        saver1 = SolverCheckpointSaver(factory1, engine=engine1)
        graph1 = create_graph(saver1)
        config = {"configurable": {"thread_id": thread_id}}

        initial_state = make_initial_state(thread_id)
        original_messages = initial_state.messages.copy()

        # Run to Step 1 review
        result1 = await graph1.ainvoke(initial_state, config)
        assert_interrupted(result1)
        assert result1["current_step"] == StepName.PROBLEM_DEFINITION
        assert result1["step_state"].status == StepStatus.AWAITING_REVIEW

        # Approve Step 1 to advance to Step 2
        await graph1.aupdate_state(
            config,
            {"human_decision": HumanAction.APPROVE},
            as_node="review",
        )
        result2 = await graph1.ainvoke(None, config)

        # Should now be at Step 2 (requirements) awaiting_review
        assert_interrupted(result2)
        assert result2["current_step"] == StepName.REQUIREMENTS
        assert result2["step_state"].status == StepStatus.AWAITING_REVIEW

        # Verify Step 1 artifact exists before restart
        # In Pass 2 (EXECUTION), artifacts are stored in 'artifacts' dict, not 'methodology'
        assert "problem_definition" in result2.get("artifacts", {}), \
            "Step 1 artifact should exist before restart"

        # Dispose engine to simulate process death
        await engine1.dispose()

        # =====================================================================
        # Phase 2: Create completely NEW everything, same thread_id
        # =====================================================================
        engine2 = create_async_engine(settings.postgres_url, echo=False)
        factory2 = async_sessionmaker(engine2, class_=AsyncSession, expire_on_commit=False)
        saver2 = SolverCheckpointSaver(factory2, engine=engine2)
        graph2 = create_graph(saver2)

        # Verify state persisted
        snapshot = await graph2.aget_state(config)
        assert snapshot is not None, "State should persist after restart"

        # Verify current step is REQUIREMENTS (Step 2)
        current_step = snapshot.values["current_step"]
        # May be enum or string value depending on serialization
        if isinstance(current_step, StepName):
            assert current_step == StepName.REQUIREMENTS
        else:
            assert current_step == StepName.REQUIREMENTS.value

        # Verify status is AWAITING_REVIEW
        step_state = snapshot.values["step_state"]
        step_status = step_state.get("status") if isinstance(step_state, dict) else step_state.status
        if isinstance(step_status, StepStatus):
            assert step_status == StepStatus.AWAITING_REVIEW
        else:
            assert step_status == StepStatus.AWAITING_REVIEW.value

        # Verify Step 1 artifact (problem_definition) preserved
        # In Pass 2 (EXECUTION), artifacts are stored in 'artifacts' dict
        artifacts = snapshot.values.get("artifacts", {})
        assert "problem_definition" in artifacts, \
            "Step 1 artifact should survive restart"

        # Verify messages preserved (conversation history)
        messages = snapshot.values.get("messages", [])
        assert len(messages) >= len(original_messages), \
            "Messages should survive restart"
        # Check original seeded messages are present
        assert any(
            m.get("content") == "Initial problem description for Gate D test"
            for m in messages
        ), "Original seeded message should survive restart"

        # Cleanup
        await saver2.adelete_thread(thread_id)
        await engine2.dispose()

    @pytest.mark.asyncio
    async def test_resume_continues_after_restart(self, stub_llm_nodes):
        """Resume: Workflow can continue after restart.

        GIVEN a workflow restarted at Step 2 awaiting_review
        WHEN I approve Step 2 after restart
        THEN workflow advances to Step 3
        """
        thread_id = make_thread_id()

        # =====================================================================
        # Phase 1: Build to Step 2 awaiting_review
        # =====================================================================
        engine1 = create_async_engine(settings.postgres_url, echo=False)
        factory1 = async_sessionmaker(engine1, class_=AsyncSession, expire_on_commit=False)
        saver1 = SolverCheckpointSaver(factory1, engine=engine1)
        graph1 = create_graph(saver1)
        config = {"configurable": {"thread_id": thread_id}}

        initial_state = make_initial_state(thread_id)

        # Run to Step 1 review
        result1 = await graph1.ainvoke(initial_state, config)
        assert_interrupted(result1)

        # Approve Step 1 to advance to Step 2
        await graph1.aupdate_state(
            config,
            {"human_decision": HumanAction.APPROVE},
            as_node="review",
        )
        result2 = await graph1.ainvoke(None, config)
        assert_interrupted(result2)
        assert result2["current_step"] == StepName.REQUIREMENTS

        # Dispose engine to simulate process death
        await engine1.dispose()

        # =====================================================================
        # Phase 2: Resume after restart and approve Step 2
        # =====================================================================
        engine2 = create_async_engine(settings.postgres_url, echo=False)
        factory2 = async_sessionmaker(engine2, class_=AsyncSession, expire_on_commit=False)
        saver2 = SolverCheckpointSaver(factory2, engine=engine2)
        graph2 = create_graph(saver2)

        # Verify we can load state
        snapshot = await graph2.aget_state(config)
        assert snapshot is not None, "State should persist after restart"

        # Approve Step 2 after restart
        await graph2.aupdate_state(
            config,
            {"human_decision": HumanAction.APPROVE},
            as_node="review",
        )

        # Resume workflow - should advance to Step 3
        result3 = await graph2.ainvoke(None, config)

        # Should have advanced to Step 3 (objectives)
        # In Pass 2, it will interrupt again at Step 3's review
        current_step = result3.get("current_step")
        if isinstance(current_step, StepName):
            assert current_step == StepName.OBJECTIVES, \
                f"Expected Step 3 (objectives), got {current_step}"
        else:
            assert current_step == StepName.OBJECTIVES.value, \
                f"Expected Step 3 (objectives), got {current_step}"

        # Cleanup
        await saver2.adelete_thread(thread_id)
        await engine2.dispose()
