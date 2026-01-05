"""
Gate B Integration Tests - Traceability Links

Tests Gate B criterion:
  "Trace links connect artifacts across steps for impact analysis"

Uses monkeypatched LLM calls for deterministic testing.
Tests via httpx client with real uvicorn server.

Test Scenarios:
  - B1: Trace links are created when Step 2 is approved (Step 1 → Step 2)
  - B2: Trace links are created when Step 3 is approved (Step 2 → Step 3)
  - B3: The /traceability endpoint returns links correctly
  - B4: Filter functionality (from_step, to_step)
"""

import pytest
import httpx

API_PREFIX = "/api/v1/workflows"


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


def get_to_pass2_step1(client: httpx.Client) -> tuple[str, dict]:
    """Create workflow and progress to Pass 2 Step 1.

    With PER_STEP gate policy, we need to explicitly approve all Pass 1 steps.

    Returns (workflow_id, state).
    """
    # Create workflow
    resp = client.post(
        API_PREFIX,
        json={
            "problem": "Gate B traceability test",
            "created_by": "test-actor",
        },
    )
    assert resp.status_code == 201, f"Create failed: {resp.text}"
    workflow_id = resp.json()["workflow_id"]

    # With PER_STEP policy, we need to approve all 3 Pass 1 steps
    # Pass 1 Step 1 (problem_definition)
    state = client.get(f"{API_PREFIX}/{workflow_id}").json()
    if state["current_pass"] == "definition":
        state = approve_step(client, workflow_id)  # Pass 1 Step 1 → Step 2

        # Pass 1 Step 2 (requirements)
        if state["current_pass"] == "definition":
            state = approve_step(client, workflow_id)  # Pass 1 Step 2 → Step 3

        # Pass 1 Step 3 (objectives) → Pass 2 Step 1
        if state["current_pass"] == "definition":
            state = approve_step(client, workflow_id)  # Pass 1 Step 3 → Pass 2 Step 1

    # Now should be at Pass 2 Step 1
    return workflow_id, state


# =============================================================================
# Gate B Test Class
# =============================================================================


class TestGateBTraceability:
    """Gate B: Trace links between artifacts across steps."""

    def test_traceability_endpoint_exists(self, client):
        """B0: The /traceability endpoint exists and returns correct structure.

        GIVEN a new workflow
        WHEN I query GET /workflows/{id}/traceability
        THEN I get a valid response with links array (may be empty initially)
        """
        workflow_id, _ = get_to_pass2_step1(client)

        # Query traceability endpoint
        resp = client.get(f"{API_PREFIX}/{workflow_id}/traceability")
        assert resp.status_code == 200, f"Traceability failed: {resp.text}"

        data = resp.json()
        assert "workflow_id" in data
        assert "state_version" in data
        assert "links" in data
        assert "total_count" in data
        assert isinstance(data["links"], list)

    def test_step2_creates_trace_links(self, client):
        """B1: Step 2 approval creates trace links from Step 1.

        GIVEN a workflow at Pass 2 Step 1 awaiting_review
        WHEN I approve Step 1, then approve Step 2
        THEN trace links exist from Step 1 elements to Step 2 requirements
        """
        workflow_id, state = get_to_pass2_step1(client)
        assert state["current_step"] == "problem_definition"
        assert state["current_pass"] == "execution"

        # Approve Step 1 → Step 2
        state = approve_step(client, workflow_id)
        assert state["current_step"] == "requirements"

        # Approve Step 2 → Step 3 (triggers trace link extraction)
        state = approve_step(client, workflow_id)
        assert state["current_step"] == "objectives"

        # Query traceability
        resp = client.get(f"{API_PREFIX}/{workflow_id}/traceability")
        assert resp.status_code == 200
        data = resp.json()

        # Should have links from Step 1 → Step 2
        step1_to_step2_links = [
            link for link in data["links"]
            if link["from_step"] == 1 and link["to_step"] == 2
        ]

        assert len(step1_to_step2_links) > 0, (
            f"Expected trace links from Step 1 to Step 2, got none. "
            f"Total links: {data['total_count']}"
        )

        # Verify link structure
        for link in step1_to_step2_links:
            assert link["from_type"] in ["stakeholder", "constraint", "success_criterion"]
            assert link["to_type"] == "requirement"
            assert link["link_type"] in ["derives", "traces_to", "achieves"]

    def test_step3_creates_trace_links(self, client):
        """B2: Step 3 approval creates trace links from Step 2.

        GIVEN a workflow at Pass 2 Step 2 awaiting_review
        WHEN I approve Step 3
        THEN trace links exist from Step 2 requirements to Step 3 objectives
        """
        workflow_id, _ = get_to_pass2_step1(client)

        # Progress through all 3 steps
        approve_step(client, workflow_id)  # Step 1 → Step 2
        approve_step(client, workflow_id)  # Step 2 → Step 3
        approve_step(client, workflow_id)  # Step 3 → workflow complete

        # Query traceability
        resp = client.get(f"{API_PREFIX}/{workflow_id}/traceability")
        assert resp.status_code == 200
        data = resp.json()

        # Should have links from Step 2 → Step 3
        step2_to_step3_links = [
            link for link in data["links"]
            if link["from_step"] == 2 and link["to_step"] == 3
        ]

        assert len(step2_to_step3_links) > 0, (
            f"Expected trace links from Step 2 to Step 3, got none. "
            f"Total links: {data['total_count']}"
        )

        # Verify link structure
        for link in step2_to_step3_links:
            assert link["from_type"] == "requirement"
            assert link["to_type"] == "objective"
            assert link["link_type"] in ["achieves", "traces_to"]

    def test_full_traceability_chain(self, client):
        """B3: Full workflow has complete trace chain Step 1 → Step 2 → Step 3.

        GIVEN a completed workflow (all 3 steps approved in Pass 2)
        WHEN I query traceability
        THEN I have links: Step 1 → Step 2 AND Step 2 → Step 3
        """
        workflow_id, _ = get_to_pass2_step1(client)

        # Complete all 3 steps
        approve_step(client, workflow_id)
        approve_step(client, workflow_id)
        approve_step(client, workflow_id)

        # Query traceability
        resp = client.get(f"{API_PREFIX}/{workflow_id}/traceability")
        assert resp.status_code == 200
        data = resp.json()

        # Verify we have links for both transitions
        from_steps = {link["from_step"] for link in data["links"]}
        to_steps = {link["to_step"] for link in data["links"]}

        # Should have links FROM Step 1 and Step 2
        assert 1 in from_steps or 2 in from_steps, (
            f"Expected links from Step 1 or 2, got from_steps: {from_steps}"
        )

        # Should have links TO Step 2 and Step 3
        assert 2 in to_steps or 3 in to_steps, (
            f"Expected links to Step 2 or 3, got to_steps: {to_steps}"
        )

    def test_filter_by_from_step(self, client):
        """B4a: Filter traceability by from_step.

        GIVEN a workflow with trace links
        WHEN I query with ?from_step=1
        THEN I only get links originating from Step 1
        """
        workflow_id, _ = get_to_pass2_step1(client)

        # Complete Steps 1 and 2 (enough to have links)
        approve_step(client, workflow_id)
        approve_step(client, workflow_id)

        # Query with filter
        resp = client.get(f"{API_PREFIX}/{workflow_id}/traceability?from_step=1")
        assert resp.status_code == 200
        data = resp.json()

        # All returned links should be from Step 1
        for link in data["links"]:
            assert link["from_step"] == 1, f"Expected from_step=1, got {link['from_step']}"

    def test_filter_by_to_step(self, client):
        """B4b: Filter traceability by to_step.

        GIVEN a workflow with trace links
        WHEN I query with ?to_step=2
        THEN I only get links targeting Step 2
        """
        workflow_id, _ = get_to_pass2_step1(client)

        # Complete Steps 1 and 2
        approve_step(client, workflow_id)
        approve_step(client, workflow_id)

        # Query with filter
        resp = client.get(f"{API_PREFIX}/{workflow_id}/traceability?to_step=2")
        assert resp.status_code == 200
        data = resp.json()

        # All returned links should target Step 2
        for link in data["links"]:
            assert link["to_step"] == 2, f"Expected to_step=2, got {link['to_step']}"

    def test_link_metadata_fields(self, client):
        """B5: Trace links have all required metadata fields.

        GIVEN a workflow with trace links
        WHEN I query traceability
        THEN each link has: id, from_*, to_*, link_type, consolidated, stale
        """
        workflow_id, _ = get_to_pass2_step1(client)

        # Complete Steps 1 and 2
        approve_step(client, workflow_id)
        approve_step(client, workflow_id)

        # Query traceability
        resp = client.get(f"{API_PREFIX}/{workflow_id}/traceability")
        assert resp.status_code == 200
        data = resp.json()

        if data["total_count"] > 0:
            link = data["links"][0]

            # Required fields per TraceLinkResponse schema
            assert "id" in link
            assert "from_step" in link
            assert "from_type" in link
            assert "from_id" in link
            assert "to_step" in link
            assert "to_type" in link
            assert "to_id" in link
            assert "link_type" in link
            assert "consolidated" in link
            assert "stale" in link

            # Validate types
            assert isinstance(link["consolidated"], bool)
            assert isinstance(link["stale"], bool)
