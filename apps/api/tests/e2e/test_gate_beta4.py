"""
Gate β4 - Exclusive Execution (Lease) Tests

Tests runner lease management per Tech Spec V2.8.4 Section 16.5 and
Contract §15.2 (Exclusive Execution).

Verifies:
  - β4-1: Lease acquired before graph execution (implicit success)
  - β4-4: Lease released after completion

Phase 7R: Resolves P7.3-DEF-001 deferral.

Note: Repository-level tests (β4-2, β4-3, β4-5, β4-6) are in
tests/integration/test_lease_repository.py where database connections
are properly managed.

Exit Gate: β4 (Exclusive Execution)
"""

API_PREFIX = "/api/v1/workflows"


class TestGateBeta4ExclusiveExecution:
    """Gate β4: Exclusive execution via leases."""

    def test_b4_1_lease_acquired_on_create(self, client):
        """β4-1: Lease is acquired during workflow creation.

        GIVEN no prior workflow exists
        WHEN I create a new workflow
        THEN the endpoint succeeds (lease acquired/released internally)
        AND the workflow reaches awaiting_review status
        """
        resp = client.post(
            API_PREFIX,
            json={
                "problem": "β4-1: Lease acquired on create",
                "created_by": "b4-test-actor",
            },
        )
        assert resp.status_code == 201, f"Create failed: {resp.text}"
        data = resp.json()
        assert data["status"] == "active"
        assert data["step_state"]["status"] == "awaiting_review"

    def test_b4_4_lease_released_after_completion(self, client):
        """β4-4: Lease is released after step completion.

        GIVEN a workflow at awaiting_review
        WHEN I approve the step
        THEN the endpoint succeeds
        AND subsequent operations work (no stale lease blocking)
        """
        # Create workflow
        resp = client.post(
            API_PREFIX,
            json={
                "problem": "β4-4: Lease release test",
                "created_by": "b4-test-actor",
            },
        )
        assert resp.status_code == 201
        workflow_id = resp.json()["workflow_id"]

        # Approve step
        state = client.get(f"{API_PREFIX}/{workflow_id}").json()
        approve_resp = client.post(
            f"{API_PREFIX}/{workflow_id}/actions/approve",
            json={
                "actor_id": "b4-test-actor",
                "expected_state_version": state["state_version"],
                "expected_position": {
                    "pass_type": state["current_pass"],
                    "step_name": state["current_step"],
                    "step_number": state["current_step_number"],
                    "status": state["step_state"]["status"],
                },
            },
        )
        assert approve_resp.status_code == 200, f"Approve failed: {approve_resp.text}"

        # Verify subsequent operations work (lease was released)
        # Get the new state and approve again
        state = client.get(f"{API_PREFIX}/{workflow_id}").json()
        assert state["step_state"]["status"] == "awaiting_review"

        # Another approve should succeed (no stale lease)
        approve_resp2 = client.post(
            f"{API_PREFIX}/{workflow_id}/actions/approve",
            json={
                "actor_id": "b4-test-actor",
                "expected_state_version": state["state_version"],
                "expected_position": {
                    "pass_type": state["current_pass"],
                    "step_name": state["current_step"],
                    "step_number": state["current_step_number"],
                    "status": state["step_state"]["status"],
                },
            },
        )
        assert approve_resp2.status_code == 200, f"Second approve failed: {approve_resp2.text}"

    def test_b4_multiple_sequential_operations(self, client):
        """β4: Multiple sequential operations succeed (no lease leakage).

        GIVEN a workflow
        WHEN I perform multiple approve operations in sequence
        THEN all operations succeed (leases properly acquired and released)
        """
        # Create workflow
        resp = client.post(
            API_PREFIX,
            json={
                "problem": "β4: Sequential operations test",
                "created_by": "b4-test-actor",
            },
        )
        assert resp.status_code == 201
        workflow_id = resp.json()["workflow_id"]

        # Perform 4 sequential approves (4 out of 6 steps)
        for i in range(4):
            state = client.get(f"{API_PREFIX}/{workflow_id}").json()
            if state["status"] != "active":
                break

            approve_resp = client.post(
                f"{API_PREFIX}/{workflow_id}/actions/approve",
                json={
                    "actor_id": "b4-test-actor",
                    "expected_state_version": state["state_version"],
                    "expected_position": {
                        "pass_type": state["current_pass"],
                        "step_name": state["current_step"],
                        "step_number": state["current_step_number"],
                        "status": state["step_state"]["status"],
                    },
                },
            )
            assert approve_resp.status_code == 200, f"Approve {i+1} failed: {approve_resp.text}"
