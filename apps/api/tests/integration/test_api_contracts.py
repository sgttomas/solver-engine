"""
API Contract Tests for V2.8.2 Response Shapes.

Verifies Pydantic response models match Tech Spec V2.8.2 schemas:
- Message response: §16.7 {message_id, status} (exception to §9.3 position wrapper)
- Progress response: C.3 unified schema with current_step (string) + current_step_number
- Staleness response: C.5 with has_stale_artifacts, stale_trace_links, can_complete

PART 1: Model Shape Tests (this file)
These tests verify Pydantic model field presence and serialization via model_dump().
They catch model definition errors but do NOT verify HTTP serialization or route behavior.

PART 2: HTTP Integration Tests
See test_http_contracts.py for full HTTP-level integration tests that verify actual
endpoint responses match the spec (including message_id persistence, etc.).
"""

import pytest
from uuid import uuid4
from datetime import datetime

from routes.workflows import (
    MessageResponse,
    PositionResponse,
    StepProgressEntry,
    ProgressResponse,
    StaleArtifactEntry,
    StaleLinkEntry,
    StalenessResponse,
    ArtifactResponse,
)


# =============================================================================
# Test: Message Response Shape (V2.8.2 §16.7)
# =============================================================================


def test_message_response_model_shape():
    """MessageResponse has only {message_id, status} per §16.7."""
    response = MessageResponse(message_id=str(uuid4()))
    data = response.model_dump()

    # V2.8.2 §16.7: Message response should have exactly these fields
    assert "message_id" in data, "Missing message_id field"
    assert "status" in data, "Missing status field"
    assert data["status"] == "sent", f"Expected status='sent', got '{data['status']}'"

    # Should only have these 2 fields (no WorkflowResponse fields)
    assert set(data.keys()) == {"message_id", "status"}, \
        f"Expected only {{message_id, status}}, got {set(data.keys())}"


def test_message_response_excludes_workflow_fields():
    """MessageResponse does NOT include WorkflowResponse fields."""
    response = MessageResponse(message_id=str(uuid4()))
    data = response.model_dump()

    # Should NOT have WorkflowResponse fields
    workflow_fields = ["workflow_id", "position", "state_version", "thread_id"]
    for field in workflow_fields:
        assert field not in data, f"Should not have {field} (V2.8.2)"


# =============================================================================
# Test: Progress Response Shape (V2.8.2 C.3)
# =============================================================================


def test_step_progress_entry_has_timestamps():
    """StepProgressEntry includes V2.8.2 timestamp fields."""
    now = datetime.utcnow()
    entry = StepProgressEntry(
        pass_type="definition",
        step_number=1,
        step_name="problem_definition",
        status="approved",
        phase="complete",
        has_artifact=True,
        artifact_id=uuid4(),
        artifact_revision=1,
        is_stale=False,
        started_at=now,
        completed_at=now,
        updated_at=now,
    )
    data = entry.model_dump()

    # V2.8.2 C.3 required fields
    assert "pass_type" in data
    assert "step_number" in data
    assert "step_name" in data
    assert "status" in data
    assert "phase" in data
    assert "has_artifact" in data
    assert "is_stale" in data
    assert "artifact_id" in data
    assert "artifact_revision" in data

    # V2.8.2 timestamp fields
    assert "started_at" in data, "Missing started_at (V2.8.2)"
    assert "completed_at" in data, "Missing completed_at (V2.8.2)"
    assert "updated_at" in data, "Missing updated_at (V2.8.2)"


def test_progress_response_unified_schema():
    """ProgressResponse has V2.8.2 unified schema."""
    response = ProgressResponse(
        workflow_id="test-workflow",
        state_version=5,
        current_pass="definition",
        current_step="requirements",
        current_step_number=2,
        steps=[],
    )
    data = response.model_dump()

    # Required fields
    assert "workflow_id" in data
    assert "state_version" in data
    assert "current_pass" in data
    assert "current_step" in data
    assert "current_step_number" in data
    assert "steps" in data


# =============================================================================
# Test: Staleness Response Shape (V2.8.2 C.5)
# =============================================================================


def test_stale_artifact_entry_v281_fields():
    """StaleArtifactEntry has V2.8.2 C.5 fields."""
    entry = StaleArtifactEntry(
        artifact_id=uuid4(),
        step_number=2,
        step_name="requirements",
        pass_type="definition",
        artifact_type="requirements",
        stale_reason="upstream_revision",
        stale_since=datetime.utcnow(),
        blocking=True,
    )
    data = entry.model_dump()

    # Required fields
    assert "artifact_id" in data
    assert "step_name" in data
    assert "pass_type" in data
    assert "stale_since" in data

    # V2.8.2 additions per C.5
    assert "step_number" in data, "Missing step_number (V2.8.2)"
    assert "artifact_type" in data, "Missing artifact_type (V2.8.2)"
    assert "stale_reason" in data, "Missing stale_reason (V2.8.2 field name)"
    assert "blocking" in data, "Missing blocking (V2.8.2)"

    # blocking should be boolean
    assert isinstance(data["blocking"], bool)


def test_staleness_response_v281_schema():
    """StalenessResponse has V2.8.2 C.5 schema with renamed field."""
    position = PositionResponse(
        instance_number=0,
        step_number=2,
        step_name="requirements",
        pass_type="definition",
        status="awaiting_review",
        phase="reviewing",
    )

    response = StalenessResponse(
        workflow_id="test-workflow",
        state_version=5,
        position=position,
        has_stale_artifacts=False,
        can_complete=True,
        blocking_reasons=[],
        stale_artifacts=[],
        stale_trace_links=[],
    )
    data = response.model_dump()

    # Required fields
    assert "workflow_id" in data
    assert "state_version" in data
    assert "can_complete" in data
    assert "stale_artifacts" in data

    # V2.8.2 additions
    assert "position" in data, "Missing position (V2.8.2)"
    assert "has_stale_artifacts" in data, "Missing has_stale_artifacts (V2.8.2)"
    assert "blocking_reasons" in data, "Missing blocking_reasons (V2.8.2)"

    # V2.8.2 renamed field
    assert "stale_trace_links" in data, "Missing stale_trace_links (V2.8.2 renamed)"

    # Old field name should NOT be present
    assert "stale_links" not in data, "Should use stale_trace_links, not stale_links"


def test_staleness_response_position_shape():
    """StalenessResponse.position has required fields."""
    position = PositionResponse(
        instance_number=0,
        step_number=2,
        step_name="requirements",
        pass_type="definition",
        status="awaiting_review",
        phase="reviewing",
    )

    response = StalenessResponse(
        workflow_id="test-workflow",
        state_version=5,
        position=position,
        has_stale_artifacts=False,
        can_complete=True,
        blocking_reasons=[],
        stale_artifacts=[],
        stale_trace_links=[],
    )
    data = response.model_dump()

    # Verify position object shape
    pos_data = data["position"]
    assert "instance_number" in pos_data
    assert "step_number" in pos_data
    assert "step_name" in pos_data
    assert "pass_type" in pos_data
    assert "status" in pos_data
    assert "phase" in pos_data


# =============================================================================
# Test: Artifact Response Shape (V2.8.0 C.4 - unchanged in V2.8.2)
# =============================================================================


def test_artifact_response_c4_schema():
    """ArtifactResponse has C.4 required fields."""
    response = ArtifactResponse(
        id=uuid4(),
        workflow_id="test-workflow",
        pass_type="definition",
        step_name="requirements",
        step_number=2,
        artifact_type="requirements",
        revision=1,
        supersedes=None,
        superseded_by=None,
        content_jsonb={"test": "data"},
        stale=False,
        stale_reason=None,
        stale_since=None,
        trace_id=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    data = response.model_dump()

    # Required fields per C.4
    assert "id" in data
    assert "workflow_id" in data
    assert "pass_type" in data
    assert "step_name" in data
    assert "step_number" in data
    assert "artifact_type" in data
    assert "revision" in data
    assert "stale" in data
    assert "created_at" in data
    assert "updated_at" in data

    # Optional/nullable fields
    assert "supersedes" in data
    assert "superseded_by" in data
    assert "content_jsonb" in data
    assert "stale_reason" in data
    assert "stale_since" in data
    assert "trace_id" in data


# =============================================================================
# Test: Type Assertions
# =============================================================================


def test_has_stale_artifacts_is_boolean():
    """has_stale_artifacts field serializes as boolean."""
    position = PositionResponse(
        instance_number=0,
        step_number=1,
        step_name="problem_definition",
        pass_type="definition",
        status="approved",
        phase="complete",
    )

    # Test True
    response_true = StalenessResponse(
        workflow_id="test",
        state_version=1,
        position=position,
        has_stale_artifacts=True,
        can_complete=False,
        blocking_reasons=["stale"],
        stale_artifacts=[],
        stale_trace_links=[],
    )
    assert response_true.model_dump()["has_stale_artifacts"] is True

    # Test False
    response_false = StalenessResponse(
        workflow_id="test",
        state_version=1,
        position=position,
        has_stale_artifacts=False,
        can_complete=True,
        blocking_reasons=[],
        stale_artifacts=[],
        stale_trace_links=[],
    )
    assert response_false.model_dump()["has_stale_artifacts"] is False


def test_blocking_reasons_is_list():
    """blocking_reasons field serializes as list."""
    position = PositionResponse(
        instance_number=0,
        step_number=1,
        step_name="problem_definition",
        pass_type="definition",
        status="approved",
        phase="complete",
    )

    response = StalenessResponse(
        workflow_id="test",
        state_version=1,
        position=position,
        has_stale_artifacts=True,
        can_complete=False,
        blocking_reasons=["reason1", "reason2"],
        stale_artifacts=[],
        stale_trace_links=[],
    )
    data = response.model_dump()

    assert isinstance(data["blocking_reasons"], list)
    assert len(data["blocking_reasons"]) == 2
