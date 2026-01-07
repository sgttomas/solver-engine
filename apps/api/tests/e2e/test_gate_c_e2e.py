"""
Gate C E2E Tests - Gating Enforcement at API Level

Tests Gate C criterion at the API level:
  "Pass 2 cannot advance without approve; revise loops work;
   message doesn't bypass gating."

Complements integration/test_gate_c.py which tests at the graph level.
These tests verify API-level behaviors like state_version semantics.

Test Scenarios:
  - C5: Message action does not increment state_version (API-level invariant)
"""

import pytest
import httpx

API_PREFIX = "/api/v1/workflows"


# =============================================================================
# Test Helpers
# =============================================================================


def create_workflow(client: httpx.Client) -> tuple[str, dict]:
    """Create a workflow and return (workflow_id, state)."""
    resp = client.post(
        API_PREFIX,
        json={
            "problem": "Gate C e2e test - state_version",
            "created_by": "test-actor",
        },
    )
    assert resp.status_code == 201, f"Create failed: {resp.text}"
    data = resp.json()
    return data["workflow_id"], client.get(f"{API_PREFIX}/{data['workflow_id']}").json()


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
# Gate C E2E Test Class
# =============================================================================


class TestGateCStateVersion:
    """Gate C: State version semantics for gating actions."""

    def test_message_does_not_increment_state_version(self, client):
        """C5: MESSAGE action does not increment state_version.

        GIVEN a workflow in awaiting_review status
        WHEN I send a MESSAGE action
        THEN state_version remains unchanged (message is a no-op for state)
        AND workflow remains at same step and status

        Per Gate C criterion: "message doesn't bypass gating"
        Per Tech Spec §9.1: MESSAGE does not change workflow state, only audit log
        """
        workflow_id, state = create_workflow(client)

        # Verify we're at awaiting_review
        assert state["step_state"]["status"] == "awaiting_review"
        original_version = state["state_version"]
        original_step = state["current_step"]
        original_step_number = state["current_step_number"]

        # Send MESSAGE action
        message_resp = client.post(
            f"{API_PREFIX}/{workflow_id}/actions/message",
            json={
                "actor_id": "test-actor",
                "content": "This is a comment, should not change state",
            },
        )
        assert message_resp.status_code == 200, f"Message failed: {message_resp.text}"

        # Get updated state
        new_state = client.get(f"{API_PREFIX}/{workflow_id}").json()

        # State version should NOT have changed
        assert new_state["state_version"] == original_version, (
            f"state_version changed from {original_version} to {new_state['state_version']} "
            "after MESSAGE action. MESSAGE should not increment state_version."
        )

        # Step should remain unchanged
        assert new_state["current_step"] == original_step
        assert new_state["current_step_number"] == original_step_number
        assert new_state["step_state"]["status"] == "awaiting_review"

    def test_approve_increments_state_version(self, client):
        """C6: APPROVE action increments state_version.

        GIVEN a workflow in awaiting_review status
        WHEN I send an APPROVE action
        THEN state_version increases

        Positive case for comparison with MESSAGE behavior.
        """
        workflow_id, state = create_workflow(client)

        original_version = state["state_version"]

        # Approve the step
        new_state = approve_step(client, workflow_id)

        # State version SHOULD have changed
        assert new_state["state_version"] > original_version, (
            f"state_version did not increase after APPROVE. "
            f"Was {original_version}, now {new_state['state_version']}"
        )

    def test_multiple_messages_do_not_increment_version(self, client):
        """C7: Multiple MESSAGE actions do not increment state_version.

        GIVEN a workflow in awaiting_review status
        WHEN I send 3 MESSAGE actions
        THEN state_version remains unchanged after all messages

        Verifies MESSAGE is truly a no-op for state versioning.
        """
        workflow_id, state = create_workflow(client)

        original_version = state["state_version"]

        # Send 3 messages
        for i in range(3):
            message_resp = client.post(
                f"{API_PREFIX}/{workflow_id}/actions/message",
                json={
                    "actor_id": "test-actor",
                    "content": f"Comment #{i + 1}",
                },
            )
            assert message_resp.status_code == 200, f"Message {i + 1} failed: {message_resp.text}"

        # Get final state
        final_state = client.get(f"{API_PREFIX}/{workflow_id}").json()

        # State version should STILL be original (3 messages = 0 version change)
        assert final_state["state_version"] == original_version, (
            f"state_version changed from {original_version} to {final_state['state_version']} "
            f"after 3 MESSAGE actions. Multiple MESSAGEs should not increment state_version."
        )
