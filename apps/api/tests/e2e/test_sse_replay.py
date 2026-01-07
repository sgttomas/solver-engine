"""
SSE Replay Tests - Verify replay ordering, monotonicity, and correctness.

Per Fix 2 (SSE Replay Correctness): Tests the subscribe_live() + DB replay pattern.
Tests that events are replayed correctly from DB, with monotonic sequences,
and that from_sequence parameter works correctly.
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
    stop_on: str = None,
    timeout: float = 5.0,
    max_events: int = 200,
) -> List[Tuple[str, dict]]:
    """Parse SSE frames until stop_on event_type or max_events.

    Args:
        client: httpx Client instance.
        url: Stream URL to connect to.
        stop_on: Event type to stop collecting on (None = don't stop early).
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

            if stop_on and event_type == stop_on:
                break
            if len(events) >= max_events:
                break

    return events


# =============================================================================
# SSE Replay Test Class
# =============================================================================


class TestSSEReplay:
    """SSE replay correctness tests."""

    def test_replay_sequence_monotonicity(self, client):
        """Events replayed from DB have monotonically increasing sequence numbers.

        GIVEN a workflow is created (generates events with sequences 1,2,3,...)
        WHEN I connect to the SSE stream
        THEN all events have monotonically increasing sequence numbers
        AND there are no gaps in the sequence
        """
        # Create workflow
        resp = client.post(
            API_PREFIX,
            json={
                "problem": "Test replay sequence monotonicity",
                "created_by": "test-actor",
            },
        )
        assert resp.status_code == 201, f"Create failed: {resp.text}"
        workflow_id = resp.json()["workflow_id"]

        # Collect events from stream
        try:
            events = collect_sse_events(
                client,
                f"{API_PREFIX}/{workflow_id}/stream",
                stop_on="step.awaiting_review",
                timeout=5.0,
            )
        except httpx.ReadTimeout:
            pytest.fail("SSE stream timed out waiting for events")

        # Verify we got events
        assert len(events) > 0, "No events received"

        # Extract sequences
        sequences = [e[1].get("sequence") for e in events]

        # All sequences must be present
        assert all(s is not None for s in sequences), (
            f"Some events missing sequence: {[e[0] for e, s in zip(events, sequences) if s is None]}"
        )

        # Verify monotonicity: each sequence > previous
        for i in range(1, len(sequences)):
            assert sequences[i] > sequences[i - 1], (
                f"Sequence not monotonically increasing at index {i}: "
                f"{sequences[i - 1]} -> {sequences[i]}"
            )

        # Verify no gaps (sequences should be consecutive)
        for i in range(1, len(sequences)):
            assert sequences[i] == sequences[i - 1] + 1, (
                f"Gap in sequence at index {i}: {sequences[i - 1]} -> {sequences[i]}"
            )

        # Verify sequence starts at 1
        assert sequences[0] == 1, f"Sequence should start at 1, got {sequences[0]}"

    def test_replay_event_ordering(self, client):
        """Events are replayed in correct order.

        GIVEN a workflow is created
        WHEN I reconnect to the SSE stream
        THEN events are in the expected order:
          workflow.started -> step.started -> artifact.delta(s) -> artifact.final -> step.awaiting_review
        """
        # Create workflow
        resp = client.post(
            API_PREFIX,
            json={
                "problem": "Test replay event ordering",
                "created_by": "test-actor",
            },
        )
        assert resp.status_code == 201, f"Create failed: {resp.text}"
        workflow_id = resp.json()["workflow_id"]

        # Connect TWICE to ensure replay works (first connection establishes, second replays)
        for _ in range(2):
            try:
                events = collect_sse_events(
                    client,
                    f"{API_PREFIX}/{workflow_id}/stream",
                    stop_on="step.awaiting_review",
                    timeout=5.0,
                )
            except httpx.ReadTimeout:
                pytest.fail("SSE stream timed out waiting for events")

        # Verify order
        event_types = [e[0] for e in events]

        # First should be workflow.started
        assert event_types[0] == "workflow.started", (
            f"Expected workflow.started first, got: {event_types[0]}"
        )

        # Second should be step.started
        assert event_types[1] == "step.started", (
            f"Expected step.started second, got: {event_types[1]}"
        )

        # artifact.delta should come before artifact.final
        if "artifact.delta" in event_types and "artifact.final" in event_types:
            first_delta = event_types.index("artifact.delta")
            final_idx = event_types.index("artifact.final")
            assert first_delta < final_idx, (
                f"artifact.delta should come before artifact.final: {event_types}"
            )

        # artifact.final should come before step.awaiting_review
        if "artifact.final" in event_types:
            final_idx = event_types.index("artifact.final")
            awaiting_idx = event_types.index("step.awaiting_review")
            assert final_idx < awaiting_idx, (
                f"artifact.final should come before step.awaiting_review: {event_types}"
            )

        # Last should be step.awaiting_review
        assert event_types[-1] == "step.awaiting_review", (
            f"Expected step.awaiting_review last, got: {event_types[-1]}"
        )

    def test_from_sequence_parameter(self, client):
        """from_sequence parameter filters events correctly.

        GIVEN a workflow is created (generates events with sequences 1,2,3,4,5,...)
        WHEN I connect with from_sequence=3
        THEN I only receive events with sequence > 3
        """
        # Create workflow
        resp = client.post(
            API_PREFIX,
            json={
                "problem": "Test from_sequence parameter filtering",
                "created_by": "test-actor",
            },
        )
        assert resp.status_code == 201, f"Create failed: {resp.text}"
        workflow_id = resp.json()["workflow_id"]

        # First, get all events to know the max sequence
        try:
            all_events = collect_sse_events(
                client,
                f"{API_PREFIX}/{workflow_id}/stream",
                stop_on="step.awaiting_review",
                timeout=5.0,
            )
        except httpx.ReadTimeout:
            pytest.fail("SSE stream timed out waiting for events")

        assert len(all_events) >= 5, f"Expected at least 5 events, got {len(all_events)}"

        # Get sequences
        all_sequences = [e[1].get("sequence") for e in all_events]
        max_seq = max(all_sequences)

        # Now connect with from_sequence=3 (should skip first 3 events)
        from_sequence = 3
        try:
            filtered_events = collect_sse_events(
                client,
                f"{API_PREFIX}/{workflow_id}/stream?from_sequence={from_sequence}",
                stop_on="step.awaiting_review",
                timeout=5.0,
            )
        except httpx.ReadTimeout:
            pytest.fail("SSE stream timed out waiting for filtered events")

        # Verify filtered events have sequence > from_sequence
        filtered_sequences = [e[1].get("sequence") for e in filtered_events]
        for seq in filtered_sequences:
            assert seq > from_sequence, (
                f"Event with sequence {seq} should not be included (from_sequence={from_sequence})"
            )

        # Verify we got fewer events
        assert len(filtered_events) < len(all_events), (
            f"Filtered events ({len(filtered_events)}) should be less than all events ({len(all_events)})"
        )

        # Verify the first filtered event has sequence = from_sequence + 1
        assert filtered_sequences[0] == from_sequence + 1, (
            f"First filtered event should have sequence {from_sequence + 1}, got {filtered_sequences[0]}"
        )

    def test_reconnect_no_duplicates(self, client):
        """Reconnecting with last_seq doesn't produce duplicates.

        GIVEN a workflow is created (generates events)
        WHEN I connect, collect events, note last sequence, disconnect
        AND I reconnect with from_sequence=last_seq
        THEN I receive no duplicate events (next event has sequence > last_seq)
        """
        # Create workflow
        resp = client.post(
            API_PREFIX,
            json={
                "problem": "Test reconnect no duplicates",
                "created_by": "test-actor",
            },
        )
        assert resp.status_code == 201, f"Create failed: {resp.text}"
        workflow_id = resp.json()["workflow_id"]

        # First connection: collect all events
        try:
            first_events = collect_sse_events(
                client,
                f"{API_PREFIX}/{workflow_id}/stream",
                stop_on="step.awaiting_review",
                timeout=5.0,
            )
        except httpx.ReadTimeout:
            pytest.fail("SSE stream timed out on first connection")

        assert len(first_events) > 0, "No events received on first connection"

        # Get the last sequence from first connection
        last_seq = first_events[-1][1].get("sequence")
        assert last_seq is not None, "Last event missing sequence"

        # Reconnect with from_sequence=last_seq (should get no events from DB)
        # Since workflow is at awaiting_review, no new live events either
        try:
            second_events = collect_sse_events(
                client,
                f"{API_PREFIX}/{workflow_id}/stream?from_sequence={last_seq}",
                timeout=2.0,  # Short timeout since we expect no events
                max_events=10,
            )
        except httpx.ReadTimeout:
            # Timeout is expected when no events - this is correct behavior
            second_events = []

        # Either no events, or only events with sequence > last_seq
        for event_type, payload in second_events:
            seq = payload.get("sequence")
            if seq is not None:
                assert seq > last_seq, (
                    f"Duplicate event with sequence {seq} (last_seq={last_seq})"
                )

    def test_workflow_id_consistency(self, client):
        """All events in a stream have the correct workflow_id.

        GIVEN a workflow is created
        WHEN I connect to the SSE stream
        THEN all events have workflow_id matching the created workflow
        """
        # Create workflow
        resp = client.post(
            API_PREFIX,
            json={
                "problem": "Test workflow_id consistency",
                "created_by": "test-actor",
            },
        )
        assert resp.status_code == 201, f"Create failed: {resp.text}"
        workflow_id = resp.json()["workflow_id"]

        # Collect events from stream
        try:
            events = collect_sse_events(
                client,
                f"{API_PREFIX}/{workflow_id}/stream",
                stop_on="step.awaiting_review",
                timeout=5.0,
            )
        except httpx.ReadTimeout:
            pytest.fail("SSE stream timed out waiting for events")

        # Verify all events have correct workflow_id
        for event_type, payload in events:
            event_workflow_id = payload.get("workflow_id")
            assert event_workflow_id == workflow_id, (
                f"Event {event_type} has wrong workflow_id: {event_workflow_id} != {workflow_id}"
            )

    def test_workflow_completed_event_replay(self, client):
        """workflow.completed event is replayed correctly.

        Per P7.1-DEF-001: Explicit test for workflow.completed event replay.

        GIVEN a workflow is created and completed (all 6 steps approved)
        WHEN I connect to the SSE stream with from_sequence=0
        THEN the workflow.completed event is present
        AND it has the correct sequence number (monotonic with all other events)

        Per Contract §12: Replay via /stream?from_sequence includes all events
        with sequence > from_sequence, in gap-free monotonic order.
        """
        # Create workflow
        resp = client.post(
            API_PREFIX,
            json={
                "problem": "Test workflow.completed event replay (P7.1-DEF-001)",
                "created_by": "test-actor",
            },
        )
        assert resp.status_code == 201, f"Create failed: {resp.text}"
        workflow_id = resp.json()["workflow_id"]

        # Approve all 6 steps to reach completion
        for step_num in range(6):
            state = client.get(f"{API_PREFIX}/{workflow_id}").json()

            # Check if already completed
            if state["status"] == "completed":
                break

            approve_resp = client.post(
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
            assert approve_resp.status_code == 200, (
                f"Approve step {step_num + 1} failed: {approve_resp.text}"
            )

        # Verify workflow is completed
        final_state = client.get(f"{API_PREFIX}/{workflow_id}").json()
        assert final_state["status"] == "completed", (
            f"Workflow should be completed, got: {final_state['status']}"
        )

        # Collect all events via replay (from_sequence=0)
        try:
            events = collect_sse_events(
                client,
                f"{API_PREFIX}/{workflow_id}/stream?from_sequence=0",
                stop_on="workflow.completed",
                timeout=10.0,
                max_events=500,  # Completed workflow has many events
            )
        except httpx.ReadTimeout:
            pytest.fail("SSE stream timed out waiting for workflow.completed event")

        # Extract event types and sequences
        event_types = [e[0] for e in events]
        sequences = [e[1].get("sequence") for e in events]

        # Verify workflow.completed event is present
        assert "workflow.completed" in event_types, (
            f"workflow.completed event not found in replay. Events: {event_types}"
        )

        # Verify workflow.completed is the last event
        completed_idx = event_types.index("workflow.completed")
        assert completed_idx == len(events) - 1, (
            f"workflow.completed should be the last event, but found at index {completed_idx} "
            f"out of {len(events)} events"
        )

        # Verify all sequences are monotonically increasing (gap-free)
        assert all(s is not None for s in sequences), "Some events missing sequence"
        for i in range(1, len(sequences)):
            assert sequences[i] == sequences[i - 1] + 1, (
                f"Gap in sequence at index {i}: {sequences[i - 1]} -> {sequences[i]}"
            )

        # Verify workflow.completed event has expected fields
        completed_event = events[completed_idx][1]
        assert completed_event.get("workflow_id") == workflow_id
        assert completed_event.get("event_type") == "workflow.completed"
        assert "timestamp" in completed_event
        assert "sequence" in completed_event
