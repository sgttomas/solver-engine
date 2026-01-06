"""
Gate Gamma-1 Integration Tests - Workflow Lifecycle

Tests γ1 criterion from Development Directive:
    "Create → execute → gate → approve → advance works end-to-end"

Scope: Lifecycle flow verification only.
    - Artifact counts are Gate A scope (Phase 8)
    - Trace validation is Gate B scope (Phase 8)
    - Staleness flows are Package 7.2 scope
    - Recovery scenarios are Package 7.3 scope

Uses monkeypatched LLM calls for deterministic testing.
Tests via httpx client with real uvicorn server.

Verification Steps (Package 7.1):
    1. Create workflow with problem statement
    2. Pass 1 steps execute and reach awaiting_review
    3. Approve all 3 Pass 1 steps
    4. Transition to Pass 2 after Step 3 Pass 1 approval
    5. Approve all 3 Pass 2 steps
    6. Workflow reaches completed status with:
       - status == "completed"
       - completed_at is not None
       - workflow.completed event emitted
"""

import httpx

API_PREFIX = "/api/v1/workflows"


# =============================================================================
# Test Helpers (reuse exact pattern from test_gate_b.py)
# =============================================================================


def approve_step(client: httpx.Client, workflow_id: str) -> dict:
    """Approve current step and return new state.

    Reuses exact pattern from test_gate_b.py to maintain schema alignment.
    """
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
# Gate γ1 Test Class
# =============================================================================


class TestGateGamma1WorkflowLifecycle:
    """Gate γ1: Workflow lifecycle from creation to completion."""

    def test_gamma1_full_workflow_lifecycle(self, client):
        """γ1: Complete workflow lifecycle from creation to completion.

        Verifies all 7 steps from Package 7.1:
        1. Create workflow with problem statement
        2. Pass 1 steps execute and reach awaiting_review
        3. Approve all 3 Pass 1 steps
        4. Transition to Pass 2 after Step 3 Pass 1 approval
        5. Approve all 3 Pass 2 steps
        6. Workflow reaches completed status with:
           - status == "completed"
           - completed_at is not None
           - workflow.completed event emitted
        """
        # =====================================================================
        # Step 1: Create workflow with problem statement
        # =====================================================================
        resp = client.post(
            API_PREFIX,
            json={
                "problem": "Gate γ1 workflow lifecycle integration test",
                "created_by": "gamma1-test-actor",
            },
        )
        assert resp.status_code == 201, f"Create failed: {resp.text}"
        workflow_id = resp.json()["workflow_id"]

        # Get initial state
        state = client.get(f"{API_PREFIX}/{workflow_id}").json()
        assert state["status"] == "active", f"Expected active status, got {state['status']}"

        # =====================================================================
        # Steps 2-4: Pass 1 - approve all 3 steps, verify Pass 2 transition
        # =====================================================================

        # Pass 1 Step 1 (problem_definition) - should auto-execute to awaiting_review
        assert state["current_pass"] == "definition", f"Expected definition pass, got {state['current_pass']}"
        assert state["current_step"] == "problem_definition", f"Expected problem_definition, got {state['current_step']}"
        assert state["step_state"]["status"] == "awaiting_review", (
            f"Expected awaiting_review, got {state['step_state']['status']}"
        )

        # NOTE: Artifact presence/counts are Gate A scope (Phase 8).
        # γ1 focuses on lifecycle flow only.

        # Approve Pass 1 Step 1 → Step 2
        state = approve_step(client, workflow_id)
        assert state["current_step"] == "requirements", f"Expected requirements, got {state['current_step']}"
        assert state["current_pass"] == "definition", "Should still be in Pass 1"

        # Approve Pass 1 Step 2 → Step 3
        state = approve_step(client, workflow_id)
        assert state["current_step"] == "objectives", f"Expected objectives, got {state['current_step']}"
        assert state["current_pass"] == "definition", "Should still be in Pass 1"

        # Approve Pass 1 Step 3 → Pass 2 Step 1 (TRANSITION POINT)
        state = approve_step(client, workflow_id)

        # Verify transition to Pass 2
        assert state["current_pass"] == "execution", (
            f"Expected execution pass after Pass 1 Step 3 approval, got {state['current_pass']}"
        )
        assert state["current_step"] == "problem_definition", (
            f"Expected problem_definition (Pass 2 Step 1), got {state['current_step']}"
        )

        # =====================================================================
        # Steps 5-6: Pass 2 - approve all 3 steps, verify completion
        # =====================================================================

        # Approve Pass 2 Step 1 → Step 2
        state = approve_step(client, workflow_id)
        assert state["current_step"] == "requirements", f"Expected requirements, got {state['current_step']}"
        assert state["current_pass"] == "execution", "Should still be in Pass 2"

        # Approve Pass 2 Step 2 → Step 3
        state = approve_step(client, workflow_id)
        assert state["current_step"] == "objectives", f"Expected objectives, got {state['current_step']}"
        assert state["current_pass"] == "execution", "Should still be in Pass 2"

        # Approve Pass 2 Step 3 → WORKFLOW COMPLETE
        state = approve_step(client, workflow_id)

        # =====================================================================
        # Terminal assertions: status, completed_at, workflow.completed event
        # =====================================================================

        # Refresh workflow state for final assertions
        final_state = client.get(f"{API_PREFIX}/{workflow_id}").json()

        # Assert status == "completed"
        assert final_state["status"] == "completed", (
            f"Expected completed status, got {final_state['status']}"
        )

        # Assert completed_at timestamp is set (Round 4: now exposed in API)
        assert final_state.get("completed_at") is not None, (
            "Expected completed_at timestamp to be set"
        )

        # Verify step approvals via /history endpoint
        # (following test_gate_f.py pattern - spec-compliant)
        history_resp = client.get(
            f"{API_PREFIX}/{workflow_id}/history?type=event&limit=100"
        )
        assert history_resp.status_code == 200, f"History query failed: {history_resp.text}"
        history = history_resp.json()

        # Verify we have step_approved events for all 6 gates (3 Pass 1 + 3 Pass 2)
        # This confirms the full lifecycle completed
        approval_events = [
            e for e in history["entries"]
            if e.get("event_type") and "approved" in e["event_type"].lower()
        ]
        assert len(approval_events) >= 6, (
            f"Expected at least 6 step_approved events (3 Pass 1 + 3 Pass 2), "
            f"found {len(approval_events)}. "
            f"Event types found: {[e.get('event_type') for e in history['entries'] if e.get('event_type')]}"
        )

        # Verify workflow.completed event in /history (Round 4: dot notation per spec §9.2.1)
        completed_events = [
            e for e in history["entries"]
            if e.get("event_type") == "workflow.completed"
        ]
        assert len(completed_events) >= 1, (
            f"Expected workflow.completed event in history, "
            f"found events: {[e.get('event_type') for e in history['entries'] if e.get('event_type')]}"
        )

        # All verifications complete - γ1 criterion met:
        # "Create → execute → gate → approve → advance works end-to-end"
