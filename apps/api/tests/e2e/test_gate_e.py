"""
Gate E Integration Tests - API + SSE Event Sequence

P6.5: Tests Gate E criterion:
  "REST endpoints + SSE streaming support the full interactive review flow"

Uses monkeypatched LLM calls for deterministic testing.
Tests via httpx client with real uvicorn server (avoids TestClient SSE issues).

Test Scenarios (Doc 3 Appendix A Gate E):
  - E1/E3: Create workflow + verify SSE event order to first review
  - E2: GET workflow returns correct state (folded into E1)
  - E4: Approve → Step 2 starts via SSE
"""

import json
from typing import List, Tuple

import pytest
import httpx

API_PREFIX = "/api/v1/workflows"


# =============================================================================
# SSE Parsing Helper
# =============================================================================


def collect_sse_events(
    client: httpx.Client,
    url: str,
    stop_on: str,
    timeout: float = 5.0,
    max_events: int = 200,
) -> List[Tuple[str, dict]]:
    """Parse SSE frames until stop_on event_type or max_events.

    Args:
        client: httpx Client instance.
        url: Stream URL to connect to.
        stop_on: Event type to stop collecting on.
        timeout: Request timeout in seconds.
        max_events: Maximum events to collect (safety limit).

    Returns:
        List of (event_type, payload) tuples.

    Raises:
        httpx.ReadTimeout: If stream times out.
    """
    events: List[Tuple[str, dict]] = []

    with client.stream("GET", url, timeout=timeout) as stream:
        for line in stream.iter_lines():
            # Skip empty lines, comments, and event: lines
            if not line or line.startswith(":") or line.startswith("event:"):
                continue
            if not line.startswith("data:"):
                continue

            try:
                payload = json.loads(line[5:].strip())
            except json.JSONDecodeError:
                continue

            event_type = payload.get("event_type", "unknown")
            events.append((event_type, payload))

            if event_type == stop_on:
                break
            if len(events) >= max_events:
                break

    return events


# =============================================================================
# Gate E Test Class
# =============================================================================


class TestGateESSEFlow:
    """Gate E: Full SSE event sequence verification."""

    def test_sse_stream_emits_any_line(self, client):
        """Smoke: SSE stream yields at least one line."""
        resp = client.post(
            API_PREFIX,
            json={
                "problem": "Gate E smoke test",
                "created_by": "test-actor",
            },
        )
        assert resp.status_code == 201, f"Create failed: {resp.text}"
        workflow_id = resp.json()["workflow_id"]

        try:
            with client.stream(
                "GET", f"{API_PREFIX}/{workflow_id}/stream", timeout=5.0
            ) as stream:
                assert stream.status_code == 200
                assert "text/event-stream" in stream.headers.get("content-type", "")

                # Read a single line from the stream
                line = next(stream.iter_lines(), None)
                assert line is not None, "Expected at least one SSE line"
        except httpx.ReadTimeout:
            pytest.fail("SSE stream timed out waiting for any output")

    def test_create_workflow_sse_sequence(self, client):
        """E1/E3: Create workflow and verify SSE event order to first review.

        GIVEN a new workflow is created via POST /workflows
        WHEN I connect to GET /workflows/{id}/stream
        THEN I receive events in order:
          1. workflow.started
          2. step.started
          3. artifact.delta (>=1)
          4. artifact.final
          5. step.awaiting_review
        """
        # Create workflow
        resp = client.post(
            API_PREFIX,
            json={
                "problem": "Gate E test problem for SSE verification",
                "created_by": "test-actor",
            },
        )
        assert resp.status_code == 201, f"Create failed: {resp.text}"
        workflow_id = resp.json()["workflow_id"]

        # E2: Verify GET returns correct state
        get_resp = client.get(f"{API_PREFIX}/{workflow_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["workflow_id"] == workflow_id

        # Connect to stream and collect events (backlog replay)
        try:
            events = collect_sse_events(
                client,
                f"{API_PREFIX}/{workflow_id}/stream",
                stop_on="step.awaiting_review",
                timeout=5.0,
            )
        except httpx.ReadTimeout:
            pytest.fail("SSE stream timed out waiting for events")

        # Assert we got events
        assert len(events) > 0, "No events received from stream"

        # Assert event order
        event_types = [e[0] for e in events]

        # First event should be workflow.started
        assert event_types[0] == "workflow.started", (
            f"Expected workflow.started first, got: {event_types}"
        )

        # Second event should be step.started
        assert event_types[1] == "step.started", (
            f"Expected step.started second, got: {event_types}"
        )

        # Should have artifact.final
        assert "artifact.final" in event_types, (
            f"Expected artifact.final in events: {event_types}"
        )

        # Last event should be step.awaiting_review
        assert event_types[-1] == "step.awaiting_review", (
            f"Expected step.awaiting_review last, got: {event_types}"
        )

        # Assert payload fields
        for event_type, payload in events:
            assert payload["workflow_id"] == workflow_id, "workflow_id mismatch"
            assert "timestamp" in payload, "Missing timestamp"
            assert "event_id" in payload, "Missing event_id"

            # Step events should have status in data
            if event_type.startswith("step."):
                # step.started may not have status yet, but others should
                if event_type != "step.started":
                    assert payload.get("data", {}).get("status") is not None, (
                        f"Missing status in {event_type}"
                    )

    def test_approve_advances_via_sse(self, client):
        """E4: Approve Step 1 → Step 2 starts, verify via SSE.

        GIVEN a workflow at step.awaiting_review for Step 1
        WHEN I POST /actions/approve
        THEN SSE stream shows:
          1. step.approved (Step 1)
          2. step.started (Step 2)
          3. artifact.delta (>=1)
          4. artifact.final
          5. step.awaiting_review (Step 2)
        AND step_number == 2, step_name == "requirements"
        """
        # Create workflow (reaches step.awaiting_review for Step 1)
        resp = client.post(
            API_PREFIX,
            json={
                "problem": "Gate E approve test for SSE verification",
                "created_by": "test-actor",
            },
        )
        assert resp.status_code == 201, f"Create failed: {resp.text}"
        workflow_id = resp.json()["workflow_id"]

        # Verify at awaiting_review
        state = client.get(f"{API_PREFIX}/{workflow_id}").json()
        assert state["step_state"]["status"] == "awaiting_review", (
            f"Expected awaiting_review, got: {state['step_state']['status']}"
        )
        assert state["current_step_number"] == 1

        # Approve Step 1
        approve_resp = client.post(
            f"{API_PREFIX}/{workflow_id}/actions/approve",
            json={"actor_id": "test-actor"},
        )
        assert approve_resp.status_code == 200, f"Approve failed: {approve_resp.text}"

        # Connect to stream and collect events (backlog replay includes all events)
        # Need to get past the first step.awaiting_review (from create) to find
        # the approve events and second step.awaiting_review
        try:
            all_events = collect_sse_events(
                client,
                f"{API_PREFIX}/{workflow_id}/stream",
                stop_on="step.awaiting_review",
                timeout=5.0,
                max_events=50,
            )
            # If we only got 4 events, we stopped at first awaiting_review
            # The approve events should be after that, so get more
            if len(all_events) <= 5:
                # Reconnect and get all events without early stop
                import time
                time.sleep(0.2)  # Small delay for events to settle
                all_events = []
                with client.stream(
                    "GET", f"{API_PREFIX}/{workflow_id}/stream", timeout=5.0
                ) as stream:
                    awaiting_count = 0
                    for line in stream.iter_lines():
                        if not line or line.startswith(":") or line.startswith("event:"):
                            continue
                        if not line.startswith("data:"):
                            continue
                        try:
                            payload = json.loads(line[5:].strip())
                        except json.JSONDecodeError:
                            continue
                        event_type = payload.get("event_type", "unknown")
                        all_events.append((event_type, payload))
                        if event_type == "step.awaiting_review":
                            awaiting_count += 1
                            if awaiting_count >= 2:
                                break
                        if len(all_events) >= 50:
                            break
            events = all_events
        except httpx.ReadTimeout:
            pytest.fail("SSE stream timed out waiting for events")

        # Should have events from approval
        event_types = [e[0] for e in events]

        # Should have step.approved somewhere
        assert "step.approved" in event_types, (
            f"Expected step.approved in events: {event_types}"
        )

        # Should have step.started for Step 2
        step_started_events = [
            (e, p) for e, p in events if e == "step.started"
        ]
        # At least 2 step.started: one for Step 1, one for Step 2
        assert len(step_started_events) >= 2, (
            f"Expected >=2 step.started, got {len(step_started_events)}"
        )

        # Verify Step 2 metadata in the last step.started
        last_step_started = step_started_events[-1][1]
        assert last_step_started["step_number"] == 2, (
            f"Expected step_number=2, got {last_step_started['step_number']}"
        )
        assert last_step_started["step_name"] == "requirements", (
            f"Expected step_name='requirements', got {last_step_started['step_name']}"
        )

        # Verify final state via GET
        final_state = client.get(f"{API_PREFIX}/{workflow_id}").json()
        assert final_state["current_step_number"] == 2
        assert final_state["current_step"] == "requirements"
        assert final_state["step_state"]["status"] == "awaiting_review"
