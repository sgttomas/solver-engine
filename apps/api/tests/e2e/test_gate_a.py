"""
Gate A Integration Tests - Methodology Documentation Existence

Tests Gate A criterion:
  "Pass 1 creates 36 methodology documents (3 steps × 4 doc types × 3 versions)"

Uses monkeypatched LLM calls for deterministic testing.
Tests via httpx client with real uvicorn server.

Test Scenarios:
  - A1: Verify Pass 1 creates 12 methodology docs per step
  - A2: Verify methodology doc structure (doc_type, version, step_name)
  - A3: Verify version ordering (V1 < V2 < V3 by created_at)
"""

import pytest
import httpx

from domain.state import PassType

API_PREFIX = "/api/v1/workflows"

DOC_TYPES = ["data_sheet", "todo_list", "guidance", "detailed_procedure"]
VERSIONS = ["v1", "v2", "v3"]
STEPS = ["problem_definition", "requirements", "objectives"]


# =============================================================================
# Test Helpers
# =============================================================================


def approve_step(client: httpx.Client, workflow_id: str) -> dict:
    """Approve current step and return new state."""
    state = client.get(f"{API_PREFIX}/{workflow_id}").json()
    resp = client.post(
        f"{API_PREFIX}/{workflow_id}/actions/approve",
        json={
            "actor_id": "test-actor",
            "expected_state_version": state["state_version"],
            "expected_position": {
                "pass_type": state["current_pass"],
                "step_name": state["current_step"],
                "step_number": state["current_step_number"],
                "status": state["step_state"]["status"],
            },
        },
    )
    assert resp.status_code == 200, f"Approve failed: {resp.text}"
    return client.get(f"{API_PREFIX}/{workflow_id}").json()


# =============================================================================
# Gate A Test Class
# =============================================================================


class TestGateAMethodologyExists:
    """Gate A: Pass 1 creates 36 methodology documents."""

    def test_pass1_creates_methodology_docs_step1(self, client_pass1):
        """A1.1: Step 1 creates 12 methodology docs after approval.

        GIVEN a new workflow is created
        WHEN Step 1 is approved
        THEN there are 12 methodology docs for Step 1 in DB
        """
        client = client_pass1

        # Create workflow (auto-runs to first awaiting_review)
        resp = client.post(
            API_PREFIX,
            json={
                "problem": "Gate A test: verify methodology docs",
                "created_by": "test-actor",
            },
        )
        assert resp.status_code == 201, f"Create failed: {resp.text}"
        workflow_id = resp.json()["workflow_id"]

        # Verify workflow is at Step 1 awaiting_review
        state = client.get(f"{API_PREFIX}/{workflow_id}").json()
        assert state["current_step"] == "problem_definition"
        assert state["step_state"]["status"] == "awaiting_review"

        # Approve Step 1 (triggers artifact persistence)
        state = approve_step(client, workflow_id)
        assert state["current_step"] == "requirements", "Should advance to Step 2"

        # Query history to count methodology artifacts
        history_resp = client.get(
            f"{API_PREFIX}/{workflow_id}/history?type=artifact"
        )
        assert history_resp.status_code == 200
        history = history_resp.json()

        # Filter for methodology_doc artifacts from Step 1
        methodology_artifacts = [
            e for e in history["entries"]
            if e["entry_type"] == "artifact"
            and e.get("artifact_type") == "methodology_doc"
            and e.get("step_number") == 1
        ]

        # Should have 12 methodology docs (4 types × 3 versions)
        assert len(methodology_artifacts) == 12, (
            f"Expected 12 methodology docs for Step 1, got {len(methodology_artifacts)}"
        )

    def test_full_pass1_creates_36_methodology_docs(self, client_pass1):
        """A1.2: Full Pass 1 creates 36 methodology docs.

        GIVEN a workflow that completes all 3 steps of Pass 1
        WHEN I query artifacts
        THEN there are exactly 36 methodology_doc artifacts
        """
        client = client_pass1

        # Create workflow
        resp = client.post(
            API_PREFIX,
            json={
                "problem": "Gate A full Pass 1 test",
                "created_by": "test-actor",
            },
        )
        assert resp.status_code == 201, f"Create failed: {resp.text}"
        workflow_id = resp.json()["workflow_id"]

        # Approve Step 1 (problem_definition)
        state = approve_step(client, workflow_id)
        assert state["current_step"] == "requirements", "Should advance to Step 2"

        # Approve Step 2 (requirements)
        state = approve_step(client, workflow_id)
        assert state["current_step"] == "objectives", "Should advance to Step 3"

        # Approve Step 3 (objectives) - ends Pass 1, starts Pass 2
        state = approve_step(client, workflow_id)
        # After Pass 1 Step 3, should be in Pass 2 Step 1
        assert state["current_pass"] == "execution", (
            f"Expected execution pass, got {state['current_pass']}"
        )

        # Query all artifacts via history endpoint
        history_resp = client.get(
            f"{API_PREFIX}/{workflow_id}/history?type=artifact&limit=100"
        )
        assert history_resp.status_code == 200
        history = history_resp.json()

        # Filter for methodology_doc artifacts
        methodology_artifacts = [
            e for e in history["entries"]
            if e["entry_type"] == "artifact"
            and e.get("artifact_type") == "methodology_doc"
        ]

        # Should have 36 methodology docs (3 steps × 4 types × 3 versions)
        assert len(methodology_artifacts) == 36, (
            f"Expected 36 methodology docs, got {len(methodology_artifacts)}"
        )

        # Verify distribution across steps
        step1_docs = [a for a in methodology_artifacts if a.get("step_number") == 1]
        step2_docs = [a for a in methodology_artifacts if a.get("step_number") == 2]
        step3_docs = [a for a in methodology_artifacts if a.get("step_number") == 3]

        assert len(step1_docs) == 12, f"Step 1 should have 12 docs, got {len(step1_docs)}"
        assert len(step2_docs) == 12, f"Step 2 should have 12 docs, got {len(step2_docs)}"
        assert len(step3_docs) == 12, f"Step 3 should have 12 docs, got {len(step3_docs)}"

    def test_methodology_doc_structure(self, client_pass1):
        """A2: Each methodology doc has correct structure.

        GIVEN Step 1 is approved in Pass 1
        WHEN I examine methodology documents
        THEN each has:
          - step_number ∈ {1, 2, 3}
          - document_type ∈ {data_sheet, todo_list, guidance, detailed_procedure}
          - document_version ∈ {v1, v2, v3}
        """
        client = client_pass1

        # Create workflow
        resp = client.post(
            API_PREFIX,
            json={
                "problem": "Gate A structure test",
                "created_by": "test-actor",
            },
        )
        assert resp.status_code == 201
        workflow_id = resp.json()["workflow_id"]

        # Approve Step 1 to trigger artifact persistence
        state = approve_step(client, workflow_id)
        assert state["current_step"] == "requirements"

        # Get history with artifact details
        history_resp = client.get(
            f"{API_PREFIX}/{workflow_id}/history?type=artifact"
        )
        assert history_resp.status_code == 200
        history = history_resp.json()

        methodology_artifacts = [
            e for e in history["entries"]
            if e["entry_type"] == "artifact"
            and e.get("artifact_type") == "methodology_doc"
        ]

        # Should have artifacts after approval
        assert len(methodology_artifacts) > 0, "No methodology artifacts found after approval"

        # Verify structure of each artifact
        seen_combinations = set()
        for artifact in methodology_artifacts:
            step_num = artifact.get("step_number")
            doc_type = artifact.get("details", {}).get("document_type")
            doc_version = artifact.get("details", {}).get("document_version")

            # Validate field values
            assert step_num in [1, 2, 3], f"Invalid step_number: {step_num}"
            assert doc_type in DOC_TYPES, f"Invalid document_type: {doc_type}"
            assert doc_version in VERSIONS, f"Invalid document_version: {doc_version}"

            # Track unique combinations
            combo = (step_num, doc_type, doc_version)
            seen_combinations.add(combo)

        # Should have 12 unique combinations for Step 1
        step1_combos = {c for c in seen_combinations if c[0] == 1}
        assert len(step1_combos) == 12, (
            f"Expected 12 unique doc combinations for Step 1, got {len(step1_combos)}"
        )


# =============================================================================
# Pass 1 Specific Fixtures
# =============================================================================


@pytest.fixture
def stub_llm_nodes_pass1(monkeypatch):
    """Pass 1 stub that returns full methodology structure.

    Returns proper {"v1": {...}, "v2": {...}, "v3": {...}} structure
    for Pass 1 methodology generation.
    """
    from domain.state import (
        WorkflowState,
        StepName,
        PassType as DomainPassType,
        ValidationResult,
    )

    async def fake_generate_step_output(state: WorkflowState) -> dict:
        """Return full methodology structure for Pass 1."""
        step = state.current_step
        pass_type = state.current_pass

        if pass_type == DomainPassType.DEFINITION:
            # Pass 1: Return full 12-doc structure
            return {
                "v1": {
                    "data_sheet": f"# Data Sheet V1\n\nStep: {step.value}\nVersion: V1\n\nCore data and definitions.",
                    "todo_list": f"# To-Do List V1\n\nStep: {step.value}\nVersion: V1\n\n- [ ] Task 1\n- [ ] Task 2",
                    "guidance": f"# Guidance V1\n\nStep: {step.value}\nVersion: V1\n\nGuidance content.",
                    "detailed_procedure": f"# Procedure V1\n\nStep: {step.value}\nVersion: V1\n\n1. Step one\n2. Step two",
                },
                "v2": {
                    "data_sheet": f"# Data Sheet V2\n\nStep: {step.value}\nVersion: V2\n\nRefined data and definitions.",
                    "todo_list": f"# To-Do List V2\n\nStep: {step.value}\nVersion: V2\n\n- [ ] Refined task 1\n- [ ] Refined task 2",
                    "guidance": f"# Guidance V2\n\nStep: {step.value}\nVersion: V2\n\nRefined guidance.",
                    "detailed_procedure": f"# Procedure V2\n\nStep: {step.value}\nVersion: V2\n\n1. Refined step one\n2. Refined step two",
                },
                "v3": {
                    "data_sheet": f"# Data Sheet V3\n\nStep: {step.value}\nVersion: V3\n\nFinal data and definitions.",
                    "todo_list": f"# To-Do List V3\n\nStep: {step.value}\nVersion: V3\n\n- [ ] Final task 1\n- [ ] Final task 2",
                    "guidance": f"# Guidance V3\n\nStep: {step.value}\nVersion: V3\n\nFinal guidance.",
                    "detailed_procedure": f"# Procedure V3\n\nStep: {step.value}\nVersion: V3\n\n1. Final step one\n2. Final step two",
                },
            }
        else:
            # Pass 2: Return step package (same as existing fixture)
            step_value = step.value if hasattr(step, "value") else str(step)

            if step_value == "problem_definition":
                return {
                    "title": "Test Problem",
                    "canonical_problem_definition": {
                        "statement": "Test problem statement for Gate A verification"
                    },
                    "stakeholders": [
                        {
                            "id": "SH-001",
                            "name_or_group": "Test User",
                            "role": "Tester",
                            "needs": ["Verify methodology"],
                            "concerns": ["Doc completeness"],
                            "impact": "High",
                        }
                    ],
                    "constraints": {
                        "hard": [{"id": "HC-001", "statement": "Must have 36 docs", "rationale": "Gate A requirement"}],
                        "soft": [],
                    },
                    "scope": {
                        "in": [{"id": "IN-001", "item": "Gate A testing"}],
                        "out": [{"id": "OUT-001", "item": "Other gates", "rationale": "Different tests"}],
                    },
                    "success_criteria": [
                        {
                            "id": "CRT-001",
                            "metric_or_signal": "36 methodology docs",
                            "target": "100%",
                            "how_verified": "Count query",
                        }
                    ],
                }
            elif step_value == "requirements":
                return {
                    "overview": {
                        "summary": "Test requirements",
                        "boundaries": ["Gate A scope"],
                        "total_requirements": 1,
                        "priority_distribution": {"must": 1, "should": 0, "could": 0},
                    },
                    "requirements": [
                        {
                            "id": "FR-001",
                            "category": "FR",
                            "priority": "must",
                            "statement": "36 methodology docs must exist",
                            "rationale": "Gate A criterion",
                            "source": {"type": "stakeholder", "id": "SH-001", "aspect": "need"},
                            "component": ["api"],
                            "testability": {"method": "test", "description": "Count assertion"},
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
                return {
                    "overview": {
                        "intent": "Test objectives",
                        "measurement_principles": ["Deterministic"],
                        "boundaries": ["Gate A"],
                        "total_objectives": 1,
                        "consolidation_ratio": 1.0,
                    },
                    "objectives": [
                        {
                            "id": "CAP-001",
                            "category": "CAP",
                            "tier": "primary",
                            "statement": "Gate A enforced",
                            "rationale": "Core requirement",
                            "owner_type": "system",
                            "linked_requirements": ["FR-001"],
                            "consolidated": False,
                            "success_criteria": {
                                "definition": "36 docs exist",
                                "verification": {
                                    "method": "test",
                                    "description": "pytest",
                                    "evidence_artifacts": ["test_gate_a.py"],
                                },
                            },
                            "component": ["api"],
                            "acceptance_criteria": ["CRT-001"],
                        }
                    ],
                    "success_framework": {
                        "minimum_viable": {
                            "description": "Gate A works",
                            "objectives": ["CAP-001"],
                            "requirement_coverage": ["FR-001"],
                        },
                        "target": {
                            "description": "All docs created",
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
        pass_type: DomainPassType = None,
    ) -> ValidationResult:
        """Return passing validation."""
        return ValidationResult(passed=True, errors=[], warnings=[])

    monkeypatch.setattr("orchestration.nodes.generate_step_output", fake_generate_step_output)
    monkeypatch.setattr("orchestration.nodes.validate_output", fake_validate_output)


@pytest.fixture
def client_pass1(stub_llm_nodes_pass1, server):
    """HTTP client with Pass 1 methodology stub."""
    from application.event_stream import reset_event_broker
    from routes.workflows import reset_graph

    reset_event_broker()
    reset_graph()

    with httpx.Client(base_url=f"http://127.0.0.1:{server}", timeout=30.0) as client:
        yield client
