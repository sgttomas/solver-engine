"""
SOLVER API - Workflow Routes

Endpoints for workflow management per Doc 3 Section 9.
P4.1: create/get/resume (DB-only).
P4.2: action endpoints (approve/revise/message/clarify).
P4.3: SSE streaming (event types + generator).
P4.4: Wire to orchestration (graph invocation, resume).
"""

import asyncio
import json
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from application.workflow_service import (
    WorkflowService,
    WorkflowNotFoundError,
    InstanceNotFoundError,
    InvalidStateError,
    StateVersionMismatchError,
)
from application.event_stream import get_event_broker, SSEEvent, HEARTBEAT_EVENT
from infrastructure.postgres import get_session, async_session_factory
from infrastructure.db.repositories.workflow_event import WorkflowEventRepository
from infrastructure.db.repositories.step_execution import StepExecutionRepository
from infrastructure.db.checkpoint_saver import SolverCheckpointSaver
from orchestration.graph import create_graph
from domain.state import (
    WorkflowState,
    StepState,
    PassType,
    StepName,
    GatePolicy,
    HumanAction,
)


router = APIRouter(prefix="/workflows", tags=["workflows"])


# =============================================================================
# P4.4: Graph Singleton (LangGraph standard pattern)
# =============================================================================

# Lazy initialization to ensure graph is created in correct event loop context
_checkpointer = None
_graph = None


def get_graph():
    """Get or create cached graph instance.

    Uses lazy initialization to ensure creation happens in correct
    event loop context for async operations.
    """
    global _checkpointer, _graph
    if _graph is None:
        _checkpointer = SolverCheckpointSaver(async_session_factory)
        _graph = create_graph(_checkpointer)
    return _graph


def reset_graph():
    """Reset graph singleton (for testing).

    Forces re-creation of graph on next get_graph() call.
    """
    global _checkpointer, _graph
    _checkpointer = None
    _graph = None


# =============================================================================
# P4.3: SSE Constants and Helpers (inline per revised plan)
# =============================================================================

# SSE event types per Doc 3 §9.2
SSE_EVENT_TYPES = {
    "workflow.started": "Workflow execution began",
    "workflow.completed": "Workflow finished",
    "step.started": "Step execution began",
    "step.awaiting_clarification": "Step needs user input",
    "step.awaiting_review": "Step output ready for approval",
    "step.approved": "Step approved by human",
    "step.revision_requested": "Step revision requested",
    "artifact.delta": "Streaming output chunk",
    "artifact.final": "Final artifact ready",
    "error": "Error occurred",
}

# Map StepStatus to SSE event type for state snapshots
STATUS_TO_EVENT = {
    "not_started": "step.started",
    "in_progress": "step.started",
    "awaiting_clarification": "step.awaiting_clarification",
    "awaiting_review": "step.awaiting_review",
    "approved": "step.approved",
    "revision_requested": "step.revision_requested",
}


def format_sse_event(event_type: str, data: dict) -> str:
    """Format SSE event frame (ASCII, json.dumps).

    Per SSE spec: event: {type}\ndata: {json}\n\n
    """
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


def format_sse_comment(comment: str) -> str:
    """Format SSE comment line (for heartbeat).

    Per SSE spec: lines starting with : are comments.
    """
    return f": {comment}\n\n"


# =============================================================================
# P6.5: Event Emission Helpers (Gate E SSE compliance)
# =============================================================================


def chunk_string(s: str, num_chunks: int) -> list:
    """Split string into approximately equal chunks.

    Args:
        s: String to split.
        num_chunks: Number of chunks to create.

    Returns:
        List of string chunks.
    """
    if not s or num_chunks <= 0:
        return [s] if s else []
    chunk_size = max(1, len(s) // num_chunks)
    chunks = []
    for i in range(0, len(s), chunk_size):
        chunks.append(s[i : i + chunk_size])
    # Merge last small chunk if needed
    if len(chunks) > num_chunks and chunks:
        chunks[-2] = chunks[-2] + chunks[-1]
        chunks.pop()
    return chunks


def _extract_artifact_output(result) -> Optional[str]:
    """Extract artifact output from graph execution result.

    Handles both WorkflowState object and dict representations.

    Args:
        result: Graph execution result (WorkflowState or dict).

    Returns:
        JSON string of output if present, None otherwise.
    """
    output = None

    # Try to get step_state.output from either object or dict
    if hasattr(result, "step_state"):
        # WorkflowState object
        step_state = result.step_state
        if step_state is not None:
            if hasattr(step_state, "output"):
                output = step_state.output
            elif isinstance(step_state, dict):
                output = step_state.get("output")
    elif isinstance(result, dict):
        # Dict representation
        step_state_data = result.get("step_state", {})
        if isinstance(step_state_data, dict):
            output = step_state_data.get("output")
        elif hasattr(step_state_data, "output"):
            output = step_state_data.output

    return json.dumps(output) if output else None


def build_sse_payload(
    workflow,
    step_execution,
    event_type: str = None,
    data: dict = None,
    artifact_id: str = None,
) -> tuple:
    """Build SSE payload aligned with STATUS_TO_EVENT mapping.

    Args:
        workflow: Workflow DB model.
        step_execution: StepExecution DB model (may be None).
        event_type: Override event type (optional).
        data: Additional data to include (optional).
        artifact_id: Artifact ID for artifact events (optional).

    Returns:
        Tuple of (resolved_event_type, payload_dict).
    """
    status = step_execution.status.value if step_execution else None
    phase = step_execution.phase.value if step_execution else None

    # Use STATUS_TO_EVENT for step-state events when no override
    resolved_event = event_type or STATUS_TO_EVENT.get(status, "step.started")

    payload = {
        "event_id": str(uuid4()),
        "event_type": resolved_event,
        "workflow_id": workflow.workflow_id,
        "instance_id": str(workflow.instance_id),
        "pass_type": workflow.current_pass.value,
        "step_number": workflow.current_step_number,
        "step_name": workflow.current_step.value,
        "timestamp": datetime.utcnow().isoformat(),
        "artifact_id": artifact_id,
        "data": {},
    }

    # Include status/phase for step events
    if status is not None:
        payload["data"]["status"] = status
    if phase is not None:
        payload["data"]["phase"] = phase

    # Merge additional data
    if data:
        payload["data"].update(data)

    return resolved_event, payload


async def emit_event(
    workflow,
    step_execution,
    event_type: str = None,
    data: dict = None,
    artifact_id: str = None,
) -> None:
    """Emit SSE event to broker (for synthetic events not persisted to DB).

    Use this for artifact.delta and artifact.final events that are generated
    in routes after graph execution.

    Args:
        workflow: Workflow DB model.
        step_execution: StepExecution DB model (may be None).
        event_type: Override event type (optional).
        data: Additional data to include (optional).
        artifact_id: Artifact ID for artifact events (optional).
    """
    broker = get_event_broker()
    resolved_type, payload = build_sse_payload(
        workflow, step_execution, event_type, data, artifact_id
    )
    await broker.publish(workflow.workflow_id, SSEEvent(resolved_type, payload))


async def publish_persisted_events(
    workflow_id: str,
    events: list,
) -> None:
    """Publish persisted events to SSE broker AFTER transaction commit.

    Per Fix 1 (Atomic Event Persistence): Events must be persisted to DB first,
    then published to broker after transaction commits. This function handles
    the publishing step.

    Args:
        workflow_id: External workflow ID string for broker routing.
        events: List of WorkflowEvent model instances to publish.
    """
    broker = get_event_broker()
    for event in events:
        # Use to_sse_dict() which includes event_id, event_type, sequence, timestamp
        payload = event.to_sse_dict()
        await broker.publish(workflow_id, SSEEvent(event.event_type, payload))


# =============================================================================
# Request/Response Schemas (inline per P4.1 plan)
# =============================================================================


class CreateWorkflowRequest(BaseModel):
    """Request to create a new workflow.

    Per Doc 3 curl example: problem + created_by required.
    """

    problem: str = Field(..., description="The problem statement")
    created_by: str = Field(..., description="Actor ID creating the workflow")
    instance_number: int = Field(
        default=0, description="Instance number (default 0 = Universal Methodology)"
    )
    domain: Optional[str] = Field(
        default=None, description="Optional domain classification"
    )


# P4.2: Action Request Schemas


class ExpectedPosition(BaseModel):
    """Expected workflow position for optimistic concurrency.

    Per Contract §11.1: Full position check including step_name.
    Client must provide expected position to detect concurrent state changes.
    """

    pass_type: str = Field(..., description="Expected pass type (definition or execution)")
    step_name: str = Field(..., description="Expected step name")
    step_number: int = Field(..., description="Expected step number")
    status: str = Field(..., description="Expected step status")


class ApproveRequest(BaseModel):
    """Request to approve current step.

    Per Contract §11.1: Both expected_state_version and expected_position required
    for optimistic concurrency control.
    """

    actor_id: Optional[str] = Field(
        default=None, description="Actor ID (defaults to workflow.created_by)"
    )
    expected_state_version: int = Field(
        ..., description="Required: Expected state version for optimistic concurrency (§11.1)"
    )
    expected_position: ExpectedPosition = Field(
        ..., description="Required: Expected workflow position for optimistic concurrency (§11.1)"
    )


class ReviseRequest(BaseModel):
    """Request to revise current step.

    Per Contract §11.1: Both expected_state_version and expected_position required
    for optimistic concurrency control.
    """

    feedback: str = Field(..., description="Revision feedback/instructions")
    actor_id: Optional[str] = Field(
        default=None, description="Actor ID (defaults to workflow.created_by)"
    )
    expected_state_version: int = Field(
        ..., description="Required: Expected state version for optimistic concurrency (§11.1)"
    )
    expected_position: ExpectedPosition = Field(
        ..., description="Required: Expected workflow position for optimistic concurrency (§11.1)"
    )


class MessageRequest(BaseModel):
    """Request to send a message without changing state."""

    content: str = Field(..., description="Message content")
    actor_id: Optional[str] = Field(
        default=None, description="Actor ID (defaults to workflow.created_by)"
    )


class ClarifyRequest(BaseModel):
    """Request to submit clarification answers.

    Per Contract §11.1: Both expected_state_version and expected_position required
    for optimistic concurrency control.
    """

    answers: dict = Field(..., description="Clarification responses keyed by question ID")
    actor_id: Optional[str] = Field(
        default=None, description="Actor ID (defaults to workflow.created_by)"
    )
    expected_state_version: int = Field(
        ..., description="Required: Expected state version for optimistic concurrency (§11.1)"
    )
    expected_position: ExpectedPosition = Field(
        ..., description="Required: Expected workflow position for optimistic concurrency (§11.1)"
    )


class StepStateResponse(BaseModel):
    """Step state within workflow response.

    Provides status/phase for test patterns per Doc 3.
    """

    step_name: str
    step_number: int
    pass_type: str
    status: str
    phase: str

    class Config:
        from_attributes = True


class WorkflowResponse(BaseModel):
    """Workflow state response.

    Includes step_state for Doc 3 test patterns.
    Enums serialized as strings for stable API payloads.
    Per Contract §9.1: state_version for optimistic concurrency.
    """

    workflow_id: str
    thread_id: str
    instance_id: UUID
    status: str
    current_pass: str
    current_step: str
    current_step_number: int
    original_problem: str
    domain: Optional[str]
    step_state: Optional[StepStateResponse]
    state_version: int = Field(..., description="Optimistic concurrency version (§9.1)")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PositionResponse(BaseModel):
    """Current workflow position for StateConflictResponse.

    Per Contract §10.5: returned in 409 responses.
    """

    pass_type: str
    step_number: int
    step_name: str
    status: str


class StateConflictResponse(BaseModel):
    """409 Conflict response for state version mismatch.

    Per Contract §10.5: Returned when expected_state_version doesn't match.
    Client should refetch state and retry.
    """

    error_code: Literal["STATE_CONFLICT"] = "STATE_CONFLICT"
    message: str
    current_position: PositionResponse
    current_state_version: int


class StepProgressEntry(BaseModel):
    """Per-step progress entry for ProgressResponse.

    Per Contract §10.3: detailed step progress including artifact info.
    """

    pass_type: str
    step_number: int
    step_name: str
    status: str
    phase: str
    latest_artifact_id: Optional[UUID] = None
    latest_artifact_revision: Optional[int] = None
    artifact_stale: bool = False
    updated_at: Optional[datetime] = None


class ProgressResponse(BaseModel):
    """Workflow progress response.

    Per Contract §10.3: Part of canonical refetch bundle.
    Includes state_version for optimistic concurrency.
    """

    workflow_id: str
    state_version: int
    current_pass: str
    current_step: str
    current_step_number: int
    steps: list[StepProgressEntry]


class StaleArtifactEntry(BaseModel):
    """Stale artifact entry for StalenessResponse.

    Per Contract §10.2: detailed staleness info.
    """

    artifact_id: UUID
    step_name: str
    pass_type: str
    reason: Optional[str] = None
    stale_since: Optional[datetime] = None


class StaleLinkEntry(BaseModel):
    """Stale traceability link entry for StalenessResponse.

    Per Contract §10.2: detailed staleness info for links.
    """

    link_id: UUID
    from_step: str
    to_step: str
    link_type: str
    reason: Optional[str] = None
    stale_since: Optional[datetime] = None


class StalenessResponse(BaseModel):
    """Workflow staleness response.

    Per Contract §10.2: Part of canonical refetch bundle.
    Indicates if workflow can complete (no blocking stale artifacts/links).
    Includes position and blocking_reasons per spec.
    """

    workflow_id: str
    position: PositionResponse
    can_complete: bool
    blocking_reasons: list[str]
    stale_artifacts: list[StaleArtifactEntry]
    stale_links: list[StaleLinkEntry]


# =============================================================================
# Helper Functions
# =============================================================================


def build_workflow_response(workflow, step_execution) -> WorkflowResponse:
    """Build WorkflowResponse from DB models.

    Serializes enums as strings for stable API payloads.
    """
    step_state = None
    if step_execution is not None:
        step_state = StepStateResponse(
            step_name=step_execution.step_name.value,
            step_number=step_execution.step_number,
            pass_type=step_execution.pass_type.value,
            status=step_execution.status.value,
            phase=step_execution.phase.value,
        )

    return WorkflowResponse(
        workflow_id=workflow.workflow_id,
        thread_id=workflow.thread_id,
        instance_id=workflow.instance_id,
        status=workflow.status.value,
        current_pass=workflow.current_pass.value,
        current_step=workflow.current_step.value,
        current_step_number=workflow.current_step_number,
        original_problem=workflow.original_problem,
        domain=workflow.domain,
        step_state=step_state,
        state_version=workflow.state_version,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    request: CreateWorkflowRequest,
    session: AsyncSession = Depends(get_session),
):
    """Create a new workflow.

    Creates Workflow and initial StepExecution records, then invokes graph.

    P4.4: DB create + graph invocation.
    Per Fix 1: Persisted events published AFTER transaction commits.
    """
    service = WorkflowService(session)

    try:
        # Collect all persisted events to publish after commits
        all_events = []

        # P4.1: Create DB records (Fix 1: events persisted in transaction)
        async with session.begin():
            workflow, step_execution, create_events = await service.create_workflow(
                problem=request.problem,
                created_by=request.created_by,
                instance_number=request.instance_number,
                domain=request.domain,
            )
            all_events.extend(create_events)

        # Fix 1: Publish persisted events AFTER transaction commits
        await publish_persisted_events(workflow.workflow_id, all_events)
        all_events.clear()

        # P4.4: Invoke graph with initial state
        graph = get_graph()
        config = {"configurable": {"thread_id": workflow.thread_id}}

        initial_state = WorkflowState(
            workflow_id=workflow.workflow_id,
            thread_id=workflow.thread_id,
            instance_id=str(workflow.instance_id),
            instance_number=request.instance_number,
            gate_policy=GatePolicy(workflow.pass_1_gate_policy.value),
            current_pass=PassType.DEFINITION,
            current_step=StepName.PROBLEM_DEFINITION,
            original_problem=workflow.original_problem,
            domain=workflow.domain,
            step_state=StepState(
                step_name=StepName.PROBLEM_DEFINITION,
                step_number=1,
                pass_type=PassType.DEFINITION,
            ),
        )

        result = await graph.ainvoke(initial_state, config)

        # Sync DB with graph result (Fix 1: events persisted in transaction)
        # Extract artifact output to pass to sync_db_from_state for correct event ordering
        # Handle both WorkflowState object and dict representations
        artifact_output = _extract_artifact_output(result)

        async with session.begin():
            # sync_db_from_state handles ALL events in correct order:
            # step.started -> artifact.delta -> artifact.final -> step.awaiting_review
            sync_events = await service.sync_db_from_state(
                workflow.workflow_id, result, artifact_output=artifact_output
            )
            all_events.extend(sync_events)

        # Fix 1: Publish persisted events AFTER transaction commits
        await publish_persisted_events(workflow.workflow_id, all_events)

        # Reload for response (force refresh from DB to get updated status/phase)
        # Note: expire_on_commit=False means identity map has stale objects
        workflow, step_execution = await service.get_workflow(workflow.workflow_id)
        await session.refresh(workflow)
        if step_execution:
            await session.refresh(step_execution)

        return build_workflow_response(workflow, step_execution)

    except InstanceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance not found: {e.instance_number}",
        )


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get workflow state.

    Returns current DB state including step_state.

    P4.1: DB-only.
    """
    service = WorkflowService(session)

    try:
        workflow, step_execution = await service.get_workflow(workflow_id)
        return build_workflow_response(workflow, step_execution)

    except WorkflowNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow not found: {workflow_id}",
        )


@router.get("/{workflow_id}/progress", response_model=ProgressResponse)
async def get_workflow_progress(
    workflow_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get workflow progress with per-step details.

    Per Contract §10.3: Part of canonical refetch bundle.
    Includes state_version for optimistic concurrency.

    Returns all step executions with their current status, phase,
    and latest artifact info (including staleness).
    """
    service = WorkflowService(session)

    try:
        workflow, _ = await service.get_workflow(workflow_id)
    except WorkflowNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow not found: {workflow_id}",
        )

    # Get all step executions for this workflow
    step_repo = StepExecutionRepository(session)
    step_executions = await step_repo.list_for_workflow(workflow.id)

    # Build step progress entries
    steps = []
    for step_exec in step_executions:
        # Query artifact for staleness and revision info (if exists)
        artifact_stale = False
        latest_artifact_revision = None
        if step_exec.latest_artifact_id:
            from infrastructure.db.repositories.artifact import ArtifactRepository
            artifact_repo = ArtifactRepository(session)
            artifact = await artifact_repo.get(step_exec.latest_artifact_id)
            if artifact:
                artifact_stale = artifact.stale  # Note: column is 'stale', not 'is_stale'
                latest_artifact_revision = artifact.revision

        steps.append(
            StepProgressEntry(
                pass_type=step_exec.pass_type.value,
                step_number=step_exec.step_number,
                step_name=step_exec.step_name.value,
                status=step_exec.status.value,
                phase=step_exec.phase.value,
                latest_artifact_id=step_exec.latest_artifact_id,
                latest_artifact_revision=latest_artifact_revision,
                artifact_stale=artifact_stale,
                updated_at=step_exec.updated_at,
            )
        )

    return ProgressResponse(
        workflow_id=workflow.workflow_id,
        state_version=workflow.state_version,
        current_pass=workflow.current_pass.value,
        current_step=workflow.current_step.value,
        current_step_number=workflow.current_step_number,
        steps=steps,
    )


@router.get("/{workflow_id}/staleness", response_model=StalenessResponse)
async def get_workflow_staleness(
    workflow_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get workflow staleness status.

    Per Contract §10.2: Part of canonical refetch bundle.
    Returns whether workflow can complete (no stale blocking artifacts/links)
    and list of any stale artifacts and links with details.
    """
    service = WorkflowService(session)

    try:
        workflow, step_execution = await service.get_workflow(workflow_id)
    except WorkflowNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow not found: {workflow_id}",
        )

    # Build position response
    position = PositionResponse(
        pass_type=workflow.current_pass.value,
        step_number=workflow.current_step_number,
        step_name=workflow.current_step.value,
        status=step_execution.status.value if step_execution else "unknown",
    )

    # Query stale artifacts
    from infrastructure.db.repositories.artifact import ArtifactRepository
    artifact_repo = ArtifactRepository(session)
    stale_artifacts_db = await artifact_repo.list_stale_artifacts(workflow.id)

    stale_artifacts = [
        StaleArtifactEntry(
            artifact_id=artifact.id,
            step_name=artifact.step_name.value,
            pass_type=artifact.pass_type.value,
            reason=artifact.stale_reason,
            stale_since=artifact.stale_since,
        )
        for artifact in stale_artifacts_db
    ]

    # Query stale traceability links
    from infrastructure.db.repositories.traceability import TraceabilityLinkRepository
    link_repo = TraceabilityLinkRepository(session)
    stale_links_db = await link_repo.list_stale_links(workflow.id)

    stale_links = [
        StaleLinkEntry(
            link_id=link.id,
            from_step=str(link.from_step),
            to_step=str(link.to_step),
            link_type=link.link_type,
            reason=link.stale_reason,
            stale_since=link.stale_since,
        )
        for link in stale_links_db
    ]

    # Build blocking reasons
    blocking_reasons = []
    if stale_artifacts:
        blocking_reasons.append(f"{len(stale_artifacts)} stale artifact(s) require re-execution")
    if stale_links:
        blocking_reasons.append(f"{len(stale_links)} stale traceability link(s) require validation")

    # can_complete = no stale artifacts and no stale links
    can_complete = len(stale_artifacts) == 0 and len(stale_links) == 0

    return StalenessResponse(
        workflow_id=workflow.workflow_id,
        position=position,
        can_complete=can_complete,
        blocking_reasons=blocking_reasons,
        stale_artifacts=stale_artifacts,
        stale_links=stale_links,
    )


class AcknowledgeStaleRequest(BaseModel):
    """Request to acknowledge stale artifacts/links.

    Per Contract §10.2: Acknowledge that staleness has been reviewed.
    """

    artifact_ids: list[UUID] = Field(
        default_factory=list, description="Artifact IDs to acknowledge as reviewed"
    )
    link_ids: list[UUID] = Field(
        default_factory=list, description="Traceability link IDs to acknowledge as reviewed"
    )
    actor_id: Optional[str] = Field(
        default=None, description="Actor ID (defaults to workflow.created_by)"
    )


class AcknowledgeStaleResponse(BaseModel):
    """Response for acknowledge-stale action.

    Per Contract §10.2: Confirms acknowledgement.
    """

    workflow_id: str
    acknowledged_artifacts: int
    acknowledged_links: int


@router.post("/{workflow_id}/actions/acknowledge-stale", response_model=AcknowledgeStaleResponse)
async def acknowledge_stale(
    workflow_id: str,
    request: AcknowledgeStaleRequest,
    session: AsyncSession = Depends(get_session),
):
    """Acknowledge stale artifacts and links.

    Per Contract §10.2: Allows human to acknowledge they've reviewed
    stale artifacts/links without triggering re-execution.
    This is a read-only acknowledgement, not a state change.
    """
    service = WorkflowService(session)

    try:
        workflow, _ = await service.get_workflow(workflow_id)
    except WorkflowNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow not found: {workflow_id}",
        )

    # For now, this is a no-op acknowledgement endpoint
    # Future: Could persist acknowledgement to audit log
    return AcknowledgeStaleResponse(
        workflow_id=workflow.workflow_id,
        acknowledged_artifacts=len(request.artifact_ids),
        acknowledged_links=len(request.link_ids),
    )


class ReExecuteRequest(BaseModel):
    """Request to re-execute a stale step.

    Per Contract §10.2: Trigger re-execution of a stale step.
    """

    step_name: str = Field(..., description="Step name to re-execute")
    pass_type: str = Field(..., description="Pass type (definition or execution)")
    actor_id: Optional[str] = Field(
        default=None, description="Actor ID (defaults to workflow.created_by)"
    )


@router.post("/{workflow_id}/actions/re-execute", response_model=WorkflowResponse)
async def re_execute_step(
    workflow_id: str,
    request: ReExecuteRequest,
    session: AsyncSession = Depends(get_session),
):
    """Re-execute a stale step.

    Per Contract §10.2: Triggers re-execution of a step that has
    become stale due to upstream revisions.

    Note: This is a placeholder - full implementation requires
    integration with the graph execution system.
    """
    service = WorkflowService(session)

    try:
        workflow, step_execution = await service.get_workflow(workflow_id)
    except WorkflowNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow not found: {workflow_id}",
        )

    # Validate the requested step exists and is stale
    # This is a placeholder - full implementation would:
    # 1. Navigate to the stale step
    # 2. Trigger graph re-execution
    # 3. Update staleness flags after successful execution

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Re-execute step is not yet implemented. Use revise action to trigger re-generation.",
    )


@router.post("/{workflow_id}/resume", response_model=WorkflowResponse)
async def resume_workflow(
    workflow_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Resume workflow from persisted state.

    P4.4: Gate D compliance - at interrupt: sync DB only; not at interrupt: continue.
    """
    service = WorkflowService(session)

    try:
        workflow, step_execution = await service.get_workflow(workflow_id)

        graph = get_graph()
        config = {"configurable": {"thread_id": workflow.thread_id}}

        # Check if at interrupt (Gate D: state survives restart, don't auto-advance)
        snapshot = await graph.aget_state(config)

        if snapshot and snapshot.values.get("__interrupt__"):
            # At gate - sync DB from checkpoint state, don't advance
            # No artifact_output for resume at interrupt (state already persisted)
            async with session.begin():
                await service.sync_db_from_state(workflow_id, snapshot.values)
        else:
            # Not at gate (crashed mid-execution or no checkpoint) - continue
            if snapshot:
                result = await graph.ainvoke(None, config)
                # Extract artifact output for correct event ordering
                # Handle both WorkflowState object and dict representations
                artifact_output = _extract_artifact_output(result)
                async with session.begin():
                    await service.sync_db_from_state(
                        workflow_id, result, artifact_output=artifact_output
                    )

        # Reload for response
        workflow, step_execution = await service.get_workflow(workflow_id)
        return build_workflow_response(workflow, step_execution)

    except WorkflowNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow not found: {workflow_id}",
        )


# =============================================================================
# P4.2: Action Endpoints
# =============================================================================


@router.post("/{workflow_id}/actions/approve", response_model=WorkflowResponse)
async def approve_step(
    workflow_id: str,
    request: ApproveRequest,
    session: AsyncSession = Depends(get_session),
):
    """Approve current step.

    P4.4: DB update + graph resume via aupdate_state + ainvoke.
    Per Fix 1: Persisted events published AFTER transaction commits.

    Requires step to be in AWAITING_REVIEW status.
    """
    service = WorkflowService(session)

    try:
        # Collect all persisted events to publish after commits
        all_events = []

        # P4.2: DB update with optimistic concurrency validation
        # Fix 1: events persisted in transaction, returned for publishing
        async with session.begin():
            workflow, step_execution, approve_events = await service.approve_step(
                workflow_id=workflow_id,
                actor_id=request.actor_id,
                expected_state_version=request.expected_state_version,
                expected_position=request.expected_position.model_dump(),
            )
            all_events.extend(approve_events)

        # Fix 1: Publish persisted events AFTER transaction commits
        await publish_persisted_events(workflow.workflow_id, all_events)
        all_events.clear()

        # P4.4: Update graph state and resume
        graph = get_graph()
        config = {"configurable": {"thread_id": workflow.thread_id}}

        await graph.aupdate_state(
            config,
            {"human_decision": HumanAction.APPROVE},
            as_node="review",  # Critical: tells LangGraph review is complete
        )

        result = await graph.ainvoke(None, config)

        # Sync DB with graph result (Fix 1: events persisted in transaction)
        # Extract artifact output to pass to sync_db_from_state for correct event ordering
        # Handle both WorkflowState object and dict representations
        artifact_output = _extract_artifact_output(result)

        async with session.begin():
            # sync_db_from_state handles ALL events in correct order:
            # step.started -> artifact.delta -> artifact.final -> step.awaiting_review
            sync_events = await service.sync_db_from_state(
                workflow_id, result, artifact_output=artifact_output
            )
            all_events.extend(sync_events)

        # Fix 1: Publish persisted events AFTER transaction commits
        await publish_persisted_events(workflow.workflow_id, all_events)

        # Reload for response (force refresh from DB to get updated status/phase)
        # Note: expire_on_commit=False means identity map has stale objects
        workflow, step_execution = await service.get_workflow(workflow_id)
        await session.refresh(workflow)
        if step_execution:
            await session.refresh(step_execution)

        return build_workflow_response(workflow, step_execution)

    except WorkflowNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow not found: {workflow_id}",
        )
    except StateVersionMismatchError as e:
        # 409: Optimistic concurrency failure (Contract §10.5)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=StateConflictResponse(
                message=str(e),
                current_position=PositionResponse(
                    pass_type=e.current_pass,
                    step_number=e.current_step_number,
                    step_name=e.current_step,
                    status=e.current_status,
                ),
                current_state_version=e.current_version,
            ).model_dump(),
        )
    except InvalidStateError as e:
        # 422: Semantic violation (action invalid for current state)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid state: {e.current_status}, expected {e.expected_status}",
        )


@router.post("/{workflow_id}/actions/revise", response_model=WorkflowResponse)
async def revise_step(
    workflow_id: str,
    request: ReviseRequest,
    session: AsyncSession = Depends(get_session),
):
    """Request revision of current step.

    P4.4: DB update + graph resume via aupdate_state + ainvoke.
    Per Fix 1: Persisted events published AFTER transaction commits.

    Requires step to be in AWAITING_REVIEW status.
    """
    service = WorkflowService(session)

    try:
        # Collect all persisted events to publish after commits
        all_events = []

        # P4.2: DB update with optimistic concurrency validation
        # Fix 1: events persisted in transaction, returned for publishing
        async with session.begin():
            workflow, step_execution, revise_events = await service.revise_step(
                workflow_id=workflow_id,
                feedback=request.feedback,
                actor_id=request.actor_id,
                expected_state_version=request.expected_state_version,
                expected_position=request.expected_position.model_dump(),
            )
            all_events.extend(revise_events)

        # Fix 1: Publish persisted events AFTER transaction commits
        await publish_persisted_events(workflow.workflow_id, all_events)
        all_events.clear()

        # P4.4: Update graph state and resume
        graph = get_graph()
        config = {"configurable": {"thread_id": workflow.thread_id}}

        await graph.aupdate_state(
            config,
            {
                "human_decision": HumanAction.REJECT,
                "human_feedback": request.feedback,
            },
            as_node="review",  # Critical: tells LangGraph review is complete
        )

        result = await graph.ainvoke(None, config)

        # Sync DB with graph result (Fix 1: events persisted in transaction)
        # Extract artifact output to pass to sync_db_from_state for correct event ordering
        # Handle both WorkflowState object and dict representations
        artifact_output = _extract_artifact_output(result)

        async with session.begin():
            # sync_db_from_state handles ALL events in correct order:
            # step.started -> artifact.delta -> artifact.final -> step.awaiting_review
            sync_events = await service.sync_db_from_state(
                workflow_id, result, artifact_output=artifact_output
            )
            all_events.extend(sync_events)

        # Fix 1: Publish persisted events AFTER transaction commits
        await publish_persisted_events(workflow.workflow_id, all_events)

        # Reload for response
        workflow, step_execution = await service.get_workflow(workflow_id)
        return build_workflow_response(workflow, step_execution)

    except WorkflowNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow not found: {workflow_id}",
        )
    except StateVersionMismatchError as e:
        # 409: Optimistic concurrency failure (Contract §10.5)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=StateConflictResponse(
                message=str(e),
                current_position=PositionResponse(
                    pass_type=e.current_pass,
                    step_number=e.current_step_number,
                    step_name=e.current_step,
                    status=e.current_status,
                ),
                current_state_version=e.current_version,
            ).model_dump(),
        )
    except InvalidStateError as e:
        # 422: Semantic violation (action invalid for current state)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid state: {e.current_status}, expected {e.expected_status}",
        )


@router.post("/{workflow_id}/actions/message", response_model=WorkflowResponse)
async def send_message(
    workflow_id: str,
    request: MessageRequest,
    session: AsyncSession = Depends(get_session),
):
    """Send message without changing workflow state.

    Gate C: Status remains AWAITING_REVIEW.
    Message is persisted for conversation history.

    Requires step to be in AWAITING_REVIEW status.
    """
    service = WorkflowService(session)

    try:
        async with session.begin():
            workflow, step_execution = await service.send_message(
                workflow_id=workflow_id,
                content=request.content,
                actor_id=request.actor_id,
            )

        return build_workflow_response(workflow, step_execution)

    except WorkflowNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow not found: {workflow_id}",
        )
    except InvalidStateError as e:
        # 422: Semantic violation (action invalid for current state)
        # Note: send_message doesn't change state, so no version mismatch possible
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid state: {e.current_status}, expected {e.expected_status}",
        )


@router.post("/{workflow_id}/actions/clarify", response_model=WorkflowResponse)
async def submit_clarification(
    workflow_id: str,
    request: ClarifyRequest,
    session: AsyncSession = Depends(get_session),
):
    """Submit clarification answers.

    P4.4: DB update + graph resume via aupdate_state + ainvoke.
    Per Fix 1: Persisted events published AFTER transaction commits.

    Requires step to be in AWAITING_CLARIFICATION status.
    """
    service = WorkflowService(session)

    try:
        # Collect all persisted events to publish after commits
        all_events = []

        # P4.2: DB update with optimistic concurrency validation
        # Fix 1: events persisted in transaction, returned for publishing
        async with session.begin():
            workflow, step_execution, clarify_events = await service.submit_clarification(
                workflow_id=workflow_id,
                answers=request.answers,
                actor_id=request.actor_id,
                expected_state_version=request.expected_state_version,
                expected_position=request.expected_position.model_dump(),
            )
            all_events.extend(clarify_events)

        # Fix 1: Publish persisted events AFTER transaction commits
        await publish_persisted_events(workflow.workflow_id, all_events)
        all_events.clear()

        # P4.4: Update graph state and resume
        graph = get_graph()
        config = {"configurable": {"thread_id": workflow.thread_id}}

        await graph.aupdate_state(
            config,
            {
                "step_state": {"clarification_response": request.answers},
            },
            as_node="elicit",  # Critical: tells LangGraph elicit is complete
        )

        result = await graph.ainvoke(None, config)

        # Sync DB with graph result (Fix 1: events persisted in transaction)
        # Extract artifact output to pass to sync_db_from_state for correct event ordering
        # Handle both WorkflowState object and dict representations
        artifact_output = _extract_artifact_output(result)

        async with session.begin():
            # sync_db_from_state handles ALL events in correct order:
            # step.started -> artifact.delta -> artifact.final -> step.awaiting_review
            sync_events = await service.sync_db_from_state(
                workflow_id, result, artifact_output=artifact_output
            )
            all_events.extend(sync_events)

        # Fix 1: Publish persisted events AFTER transaction commits
        await publish_persisted_events(workflow.workflow_id, all_events)

        # Reload for response
        workflow, step_execution = await service.get_workflow(workflow_id)
        return build_workflow_response(workflow, step_execution)

    except WorkflowNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow not found: {workflow_id}",
        )
    except StateVersionMismatchError as e:
        # 409: Optimistic concurrency failure (Contract §10.5)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=StateConflictResponse(
                message=str(e),
                current_position=PositionResponse(
                    pass_type=e.current_pass,
                    step_number=e.current_step_number,
                    step_name=e.current_step,
                    status=e.current_status,
                ),
                current_state_version=e.current_version,
            ).model_dump(),
        )
    except InvalidStateError as e:
        # 422: Semantic violation (action invalid for current state)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid state: {e.current_status}, expected {e.expected_status}",
        )


# =============================================================================
# P4.3: SSE Streaming Endpoint
# =============================================================================


@router.get("/{workflow_id}/stream")
async def stream_workflow(
    workflow_id: str,
    from_sequence: int = 0,  # Default to 0 for full replay
    session: AsyncSession = Depends(get_session),
):
    """SSE stream for real-time events.

    Gate E: Supports full interactive flow via EventBroker.

    Per Contract §12.1: from_sequence parameter for replay.
    - Replays events with sequence > from_sequence from DB
    - Uses subscribe_live to avoid broker backlog mixing
    - Drops live events with sequence <= max_seq at subscription time
    - All events include sequence field in payload

    Fix 2 (Remediation): Race-free replay using subscribe_live.
    """
    # Validate workflow exists BEFORE starting stream
    service = WorkflowService(session)
    try:
        workflow, step_execution = await service.get_workflow(workflow_id)
    except WorkflowNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow not found: {workflow_id}",
        )

    broker = get_event_broker()
    event_repo = WorkflowEventRepository(session)

    # Step 1: Get max sequence at subscription time BEFORE subscribing
    # This ensures we know which events are "historical" vs "live"
    max_seq = await event_repo.get_latest_sequence(workflow.id)

    # Step 2: Get historical events: from_sequence < seq <= max_seq
    db_events = await event_repo.get_events_after(
        workflow_id=workflow.id,
        from_sequence=from_sequence,
    )
    # Filter to only events with seq <= max_seq (in case new events were added)
    historical_events = [e for e in db_events if e.sequence <= max_seq]

    async def event_generator():
        try:
            # Phase 1: Replay historical events from DB (Contract §12.1)
            for db_event in historical_events:
                sse_dict = db_event.to_sse_dict()
                yield format_sse_event(sse_dict["event_type"], sse_dict)

            # Phase 2: Subscribe to LIVE events from broker (no backlog replay)
            # Fix 1 complete: Events are now persisted to DB before broker publish,
            # so we use subscribe_live() to avoid broker backlog mixing with DB replay.
            # Drop any events with sequence <= max_seq to avoid duplicates.
            # Use 5s timeout for heartbeats (keeps tests fast, production responsive)
            async for event in broker.subscribe_live(workflow_id, timeout=5.0):
                # Handle heartbeat events as SSE comments (not data events)
                if event is HEARTBEAT_EVENT or event.event_type == "__heartbeat__":
                    yield format_sse_comment("keep-alive")
                else:
                    # Drop events already replayed from DB
                    event_seq = event.payload.get("sequence", 0)
                    if event_seq > max_seq:
                        yield format_sse_event(event.event_type, event.payload)

        except asyncio.CancelledError:
            # Client disconnected - clean shutdown
            return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
