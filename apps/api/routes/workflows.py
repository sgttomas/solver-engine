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
from typing import Any, Literal, Optional
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
    ArtifactNotFoundError,
    ArtifactNotBelongError,
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
    StepStatus as DomainStepStatus,
    StepPhase as DomainStepPhase,
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

# SSE event types per V2.8.2 Tech Spec §9.2
SSE_EVENT_TYPES = {
    # Workflow lifecycle
    "workflow.started": "Workflow execution began",
    "workflow.completed": "Workflow finished",
    # Step lifecycle
    "step.started": "Step execution began",
    "step.awaiting_clarification": "Step needs user input",
    "step.awaiting_review": "Step output ready for approval",
    "step.approved": "Step approved by human",
    "step.revision_requested": "Step revision requested",
    "step.reexecute_started": "Step re-execution initiated",
    # Artifact events
    "artifact.delta": "Streaming output chunk",
    "artifact.final": "Final artifact ready",
    "artifact.stale": "Artifact marked stale due to upstream revision",
    "artifact.stale_cleared": "Stale artifact acknowledged by user",
    # Message events
    "message.created": "Message sent",
    "message.delta": "Message streaming chunk",
    "message.final": "Message completed",
    # Connection events
    "heartbeat": "Connection keep-alive",
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


class MessageResponse(BaseModel):
    """Response from send_message endpoint.

    Per Tech Spec V2.8.2 §16.7: Message is NOT state-mutating,
    returns minimal response with message_id and status.

    Note: This is an exception to §9.3 - message endpoint returns minimal
    {message_id, status} without position wrapper.
    """

    message_id: str = Field(..., description="UUID of the created message")
    status: Literal["sent"] = Field(default="sent", description="Message status (always 'sent')")


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


class PositionResponse(BaseModel):
    """Current workflow position.

    Per V2.8.2 Spec: Used in WorkflowResponse, StateConflictResponse, StalenessResponse.
    All position-related fields in one object for consistency.
    """

    instance_number: int = Field(default=1, description="Workflow instance number")
    step_number: int
    step_name: str
    pass_type: str
    status: str
    phase: str = Field(default="unknown", description="Current execution phase")


class WorkflowResponse(BaseModel):
    """Workflow state response.

    Per V2.8.2 Spec: Includes nested `position` object for consistency with SSE events.
    Also includes step_state for detailed step info.
    Enums serialized as strings for stable API payloads.
    Per Contract §9.1: state_version for optimistic concurrency.

    Note: Flat fields (current_pass, current_step, current_step_number) retained
    for backward compatibility. Use `position` for new integrations.
    """

    workflow_id: str
    thread_id: str
    instance_id: UUID
    status: str
    position: PositionResponse = Field(..., description="Current workflow position (V2.8.2)")
    # Flat fields for backward compatibility (mirror position object)
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

    Per V2.8.2 Spec: unified progress schema with artifact info and timestamps.
    """

    pass_type: str
    step_number: int
    step_name: str
    status: str
    phase: str
    has_artifact: bool = False
    artifact_id: Optional[UUID] = None
    artifact_revision: Optional[int] = None
    is_stale: bool = False
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
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

    Per V2.8.2 Spec Appendix C.5: detailed staleness info.
    """

    artifact_id: UUID
    step_number: int
    step_name: str
    pass_type: str
    artifact_type: str  # Same as step_name (e.g., "requirements")
    stale_reason: Optional[str] = None
    stale_since: Optional[datetime] = None
    blocking: bool = True  # Per C.5: drives can_complete gating


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

    Per V2.8.2 Spec Appendix C.5: Part of canonical refetch bundle.
    Indicates if workflow can complete (no blocking stale artifacts OR trace links).
    Includes state_version, position, has_stale_artifacts, and blocking_reasons.
    """

    workflow_id: str
    state_version: int  # Per V2.8.2 spec: required for optimistic concurrency
    position: PositionResponse
    has_stale_artifacts: bool  # V2.8.2: explicit boolean for quick check
    can_complete: bool
    blocking_reasons: list[str]
    stale_artifacts: list[StaleArtifactEntry]
    stale_trace_links: list[StaleLinkEntry]  # V2.8.2: renamed from stale_links


class ArtifactResponse(BaseModel):
    """Single artifact response per Tech Spec V2.8.2 Appendix C.4.

    Note: artifact_type uses step_name value (e.g., "requirements"),
    not the internal DB discriminator.
    """

    id: UUID
    workflow_id: str  # External workflow_id string
    pass_type: str
    step_name: str
    step_number: int
    artifact_type: str  # = step_name value per user decision
    revision: int
    supersedes: Optional[UUID] = None
    superseded_by: Optional[UUID] = None
    content_jsonb: Optional[dict] = None  # Methodology: {"markdown": "...", ...}
    stale: bool
    stale_reason: Optional[str] = None
    stale_since: Optional[datetime] = None
    trace_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# =============================================================================
# Helper Functions
# =============================================================================


def build_position_response(workflow, step_execution) -> PositionResponse:
    """Build PositionResponse from workflow and step_execution.

    Per V2.8.2 Spec line 2174: All API responses include position.
    Used by utility endpoints (history, traceability, replay, diff).
    """
    status = step_execution.status.value if step_execution else "unknown"
    phase = step_execution.phase.value if step_execution else "unknown"

    return PositionResponse(
        instance_number=workflow.instance_number if hasattr(workflow, 'instance_number') else 1,
        step_number=workflow.current_step_number,
        step_name=workflow.current_step.value,
        pass_type=workflow.current_pass.value,
        status=status,
        phase=phase,
    )


def build_workflow_response(workflow, step_execution) -> WorkflowResponse:
    """Build WorkflowResponse from DB models.

    Serializes enums as strings for stable API payloads.
    Per V2.8.2: Includes nested position object.
    """
    # Build position object per V2.8.2 spec (reuse helper)
    position = build_position_response(workflow, step_execution)

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
        position=position,
        # Flat fields for backward compatibility
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


def build_artifact_response(artifact, workflow) -> ArtifactResponse:
    """Build ArtifactResponse with C.4 field mapping.

    Per user decision:
    - artifact_type = step_name (not DB discriminator)
    - Methodology markdown wrapped in content_jsonb
    """
    # artifact_type = step_name value (not DB discriminator "methodology_doc"/"step_package")
    artifact_type = artifact.step_name.value

    # Wrap methodology markdown in content_jsonb structure
    if artifact.artifact_type == "methodology_doc":
        content_jsonb = {
            "markdown": artifact.content_markdown or "",
            "document_type": artifact.document_type.value if artifact.document_type else None,
            "version": artifact.document_version.value if artifact.document_version else None,
        }
    else:
        content_jsonb = artifact.content_jsonb

    return ArtifactResponse(
        id=artifact.id,
        workflow_id=workflow.workflow_id,  # External workflow_id string
        pass_type=artifact.pass_type.value,
        step_name=artifact.step_name.value,
        step_number=artifact.step_number,
        artifact_type=artifact_type,
        revision=artifact.revision,
        supersedes=artifact.supersedes,
        superseded_by=artifact.superseded_by,
        content_jsonb=content_jsonb,
        stale=artifact.stale,
        stale_reason=artifact.stale_reason,
        stale_since=artifact.stale_since,
        trace_id=artifact.trace_id,
        created_at=artifact.created_at,
        updated_at=artifact.updated_at,
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
        is_stale = False
        artifact_revision = None
        artifact_id = step_exec.latest_artifact_id
        has_artifact = artifact_id is not None

        if artifact_id:
            from infrastructure.db.repositories.artifact import ArtifactRepository
            artifact_repo = ArtifactRepository(session)
            artifact = await artifact_repo.get(artifact_id)
            if artifact:
                is_stale = artifact.stale  # Note: column is 'stale', not 'is_stale'
                artifact_revision = artifact.revision

        steps.append(
            StepProgressEntry(
                pass_type=step_exec.pass_type.value,
                step_number=step_exec.step_number,
                step_name=step_exec.step_name.value,
                status=step_exec.status.value,
                phase=step_exec.phase.value,
                has_artifact=has_artifact,
                artifact_id=artifact_id,
                artifact_revision=artifact_revision,
                is_stale=is_stale,
                started_at=step_exec.started_at,
                completed_at=step_exec.completed_at,
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

    # Build position response per V2.8.2 spec
    position = PositionResponse(
        instance_number=workflow.instance_number if hasattr(workflow, 'instance_number') else 1,
        step_number=workflow.current_step_number,
        step_name=workflow.current_step.value,
        pass_type=workflow.current_pass.value,
        status=step_execution.status.value if step_execution else "unknown",
        phase=step_execution.phase.value if step_execution else "unknown",
    )

    # Query stale artifacts
    from infrastructure.db.repositories.artifact import ArtifactRepository
    artifact_repo = ArtifactRepository(session)
    stale_artifacts_db = await artifact_repo.list_stale_artifacts(workflow.id)

    stale_artifacts = [
        StaleArtifactEntry(
            artifact_id=artifact.id,
            step_number=artifact.step_number,
            step_name=artifact.step_name.value,
            pass_type=artifact.pass_type.value,
            artifact_type=artifact.step_name.value,  # Per C.5: artifact_type = step_name
            stale_reason=artifact.stale_reason,
            stale_since=artifact.stale_since,
            blocking=True,  # All stale artifacts are blocking by default (C.5)
        )
        for artifact in stale_artifacts_db
    ]

    # Query stale traceability links
    from infrastructure.db.repositories.traceability import TraceabilityLinkRepository
    link_repo = TraceabilityLinkRepository(session)
    stale_links_db = await link_repo.list_stale_links(workflow.id)

    stale_trace_links = [
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
    if stale_trace_links:
        blocking_reasons.append(f"{len(stale_trace_links)} stale traceability link(s) require validation")

    # can_complete = no blocking artifacts and no stale links (C.5)
    has_stale_artifacts = len(stale_artifacts) > 0
    has_blocking_artifacts = any(a.blocking for a in stale_artifacts)
    can_complete = not has_blocking_artifacts and len(stale_trace_links) == 0

    return StalenessResponse(
        workflow_id=workflow.workflow_id,
        state_version=workflow.state_version,  # Per V2.8.2 spec
        position=position,
        has_stale_artifacts=has_stale_artifacts,
        can_complete=can_complete,
        blocking_reasons=blocking_reasons,
        stale_artifacts=stale_artifacts,
        stale_trace_links=stale_trace_links,
    )


# =============================================================================
# Artifact Endpoint (Tech Spec V2.8.2 Appendix C.4)
# =============================================================================


@router.get("/{workflow_id}/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    workflow_id: str,
    artifact_id: UUID,  # UUID type for 422 validation on invalid format
    session: AsyncSession = Depends(get_session),
):
    """Get a specific artifact by ID.

    Per Tech Spec V2.8.2 Appendix C.4.

    Status codes:
        200: Success
        404: Workflow or artifact not found
        400: Artifact doesn't belong to workflow
        422: Invalid UUID format
    """
    service = WorkflowService(session)

    try:
        artifact, workflow = await service.get_artifact(workflow_id, artifact_id)
        return build_artifact_response(artifact, workflow)
    except WorkflowNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow not found: {workflow_id}",
        )
    except ArtifactNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact not found: {artifact_id}",
        )
    except ArtifactNotBelongError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Artifact does not belong to specified workflow",
        )


# =============================================================================
# History Endpoint (Gate F Requirement)
# =============================================================================


class HistoryEntryResponse(BaseModel):
    """Single history entry for unified timeline.

    Per V2.8.2 Spec: Unified history including events, artifacts, and messages.
    """

    entry_id: UUID
    created_at: datetime
    entry_type: str = Field(..., description="Type: 'event', 'artifact', 'message'")
    actor_id: Optional[str] = None
    step_number: Optional[int] = None
    step_name: Optional[str] = None

    # For events (from audit_log)
    event_type: Optional[str] = None
    from_status: Optional[str] = None
    to_status: Optional[str] = None

    # For artifacts
    artifact_id: Optional[UUID] = None
    artifact_type: Optional[str] = None
    artifact_label: Optional[str] = None

    # For messages
    message_role: Optional[str] = None
    content_preview: Optional[str] = None

    details: Optional[dict] = None


class HistoryResponse(BaseModel):
    """Workflow history response.

    Per V2.8.2 Spec: Full audit trail for timeline reconstruction (Gate F).
    Per V2.8.2 Spec line 2174: All API responses include position.
    """

    workflow_id: str
    state_version: int
    position: PositionResponse
    entries: list[HistoryEntryResponse]
    total_count: int


@router.get("/{workflow_id}/history", response_model=HistoryResponse)
async def get_workflow_history(
    workflow_id: str,
    entry_type: Optional[str] = None,  # 'event', 'artifact', 'message', or None for all
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
):
    """Get workflow history for timeline reconstruction.

    Per V2.8.2 Spec (Gate F): Returns unified history including:
    - Audit log events (state transitions, actions)
    - Artifact creations/revisions
    - Messages (conversation history)

    Query params:
        entry_type: Filter by type ('event', 'artifact', 'message')
        limit: Max entries to return (default 50)
        offset: Skip entries for pagination
    """
    service = WorkflowService(session)

    try:
        workflow, step_execution = await service.get_workflow(workflow_id)
    except WorkflowNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow not found: {workflow_id}",
        )

    # Build position for response (per V2.8.2 spec line 2174)
    position = build_position_response(workflow, step_execution)

    entries: list[HistoryEntryResponse] = []

    # Collect audit log events
    if entry_type is None or entry_type == "event":
        from infrastructure.db.repositories.audit import AuditLogRepository
        audit_repo = AuditLogRepository(session)
        audit_logs = await audit_repo.list_for_workflow(workflow.id)

        for log in audit_logs:
            entries.append(
                HistoryEntryResponse(
                    entry_id=log.id,
                    created_at=log.created_at,
                    entry_type="event",
                    actor_id=log.actor_id,
                    step_number=log.step_number,
                    step_name=log.step_name.value if log.step_name else None,
                    event_type=log.event_type,
                    from_status=log.from_status.value if log.from_status else None,
                    to_status=log.to_status.value if log.to_status else None,
                    artifact_id=log.artifact_id,
                    details=log.details if log.details else None,
                )
            )

    # Collect artifacts
    if entry_type is None or entry_type == "artifact":
        from infrastructure.db.repositories.artifact import ArtifactRepository
        artifact_repo = ArtifactRepository(session)
        artifacts = await artifact_repo.list_for_workflow(workflow.id)

        for artifact in artifacts:
            # Build artifact label (e.g., "problem_definition v1 methodology_doc")
            label_parts = []
            if artifact.step_name:
                label_parts.append(artifact.step_name.value)
            if artifact.document_version:
                label_parts.append(artifact.document_version.value)
            if artifact.artifact_type:
                label_parts.append(artifact.artifact_type)
            artifact_label = " ".join(label_parts) if label_parts else None

            # Build details dict for methodology docs
            details = {}
            if artifact.artifact_type == "methodology_doc":
                if artifact.document_type:
                    details["document_type"] = artifact.document_type.value
                if artifact.document_version:
                    details["document_version"] = artifact.document_version.value
            elif artifact.artifact_type == "step_package":
                if artifact.package_type:
                    details["package_type"] = artifact.package_type
                details["revision"] = artifact.revision

            entries.append(
                HistoryEntryResponse(
                    entry_id=artifact.id,
                    created_at=artifact.created_at,
                    entry_type="artifact",
                    step_number=artifact.step_number,
                    step_name=artifact.step_name.value if artifact.step_name else None,
                    artifact_id=artifact.id,
                    artifact_type=artifact.artifact_type,
                    artifact_label=artifact_label,
                    details=details if details else None,
                )
            )

    # Collect messages
    if entry_type is None or entry_type == "message":
        from infrastructure.db.repositories.message import MessageRepository
        message_repo = MessageRepository(session)
        messages = await message_repo.list_for_workflow(workflow.id)

        for msg in messages:
            content_preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content

            entries.append(
                HistoryEntryResponse(
                    entry_id=msg.id,
                    created_at=msg.created_at,
                    entry_type="message",
                    message_role=msg.role.value if msg.role else None,
                    content_preview=content_preview,
                )
            )

    # Sort all entries by created_at
    entries.sort(key=lambda e: e.created_at)

    # Apply pagination
    total_count = len(entries)
    entries = entries[offset : offset + limit]

    return HistoryResponse(
        workflow_id=workflow.workflow_id,
        state_version=workflow.state_version,
        position=position,
        entries=entries,
        total_count=total_count,
    )


# =============================================================================
# Traceability Endpoint (Gate B Requirement)
# =============================================================================


class TraceLinkResponse(BaseModel):
    """Single traceability link.

    Per V2.8.2 Spec: Links connect elements across steps.
    """

    id: UUID
    from_step: int
    from_type: str
    from_id: str
    to_step: int
    to_type: str
    to_id: str
    link_type: str = Field(..., description="Link type: 'derives', 'achieves', 'traces_to'")
    consolidated: bool
    validated_at: Optional[datetime] = None
    stale: bool
    stale_reason: Optional[str] = None


class TraceabilityResponse(BaseModel):
    """Workflow traceability response.

    Per V2.8.2 Spec (Gate B): Trace links between artifacts.
    Per V2.8.2 Spec line 2174: All API responses include position.
    """

    workflow_id: str
    state_version: int
    position: PositionResponse
    links: list[TraceLinkResponse]
    total_count: int


@router.get("/{workflow_id}/traceability", response_model=TraceabilityResponse)
async def get_workflow_traceability(
    workflow_id: str,
    from_step: Optional[int] = None,
    to_step: Optional[int] = None,
    stale_only: bool = False,
    session: AsyncSession = Depends(get_session),
):
    """Get workflow traceability links.

    Per V2.8.2 Spec (Gate B): Returns trace links between artifacts.

    Query params:
        from_step: Filter by source step number
        to_step: Filter by target step number
        stale_only: Only return stale links
    """
    service = WorkflowService(session)

    try:
        workflow, step_execution = await service.get_workflow(workflow_id)
    except WorkflowNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow not found: {workflow_id}",
        )

    # Build position for response (per V2.8.2 spec line 2174)
    position = build_position_response(workflow, step_execution)

    from infrastructure.db.repositories.traceability import TraceabilityLinkRepository
    link_repo = TraceabilityLinkRepository(session)

    if stale_only:
        all_links = await link_repo.list_stale_links(workflow.id)
    else:
        all_links = await link_repo.list_for_workflow(workflow.id)

    # Apply filters
    filtered_links = all_links
    if from_step is not None:
        filtered_links = [l for l in filtered_links if l.from_step == from_step]
    if to_step is not None:
        filtered_links = [l for l in filtered_links if l.to_step == to_step]

    # Build response
    links = [
        TraceLinkResponse(
            id=link.id,
            from_step=link.from_step,
            from_type=link.from_type,
            from_id=link.from_id,
            to_step=link.to_step,
            to_type=link.to_type,
            to_id=link.to_id,
            link_type=link.link_type,
            consolidated=link.consolidated,
            validated_at=link.validated_at,
            stale=link.stale,
            stale_reason=link.stale_reason,
        )
        for link in filtered_links
    ]

    return TraceabilityResponse(
        workflow_id=workflow.workflow_id,
        state_version=workflow.state_version,
        position=position,
        links=links,
        total_count=len(links),
    )


# =============================================================================
# Replay Endpoint (Audit/Compliance)
# =============================================================================


class ReplayEventResponse(BaseModel):
    """Single event in replay response.

    Per V2.8.2 Spec: Event with position for audit replay.
    """

    sequence: int
    timestamp: datetime
    event_type: str
    position: PositionResponse
    artifact_id: Optional[UUID] = None
    decision_id: Optional[UUID] = None
    data: dict = Field(default_factory=dict)


class DecisionResponse(BaseModel):
    """Human decision (approve/revise/clarify) in replay.

    Per V2.8.2 Spec: Decisions from audit log for audit trail.
    """

    decision_id: UUID
    step_number: int
    decision_type: str = Field(..., description="Decision type: 'approve', 'revise', 'clarify'")
    actor_id: str
    created_at: datetime
    feedback: Optional[str] = None


class ReplayResponse(BaseModel):
    """Workflow replay response.

    Per V2.8.2 Spec: Full event sequence for audit, debug, comparison.
    Per V2.8.2 Spec line 2174: All API responses include position.
    """

    workflow_id: str
    state_version: int
    position: PositionResponse
    events: list[ReplayEventResponse]
    snapshots: dict[str, dict] = Field(default_factory=dict, description="artifact_id -> content")
    decisions: list[DecisionResponse]
    trace_hash: str = Field(..., description="SHA-256 for deterministic comparison")


@router.get("/{workflow_id}/replay", response_model=ReplayResponse)
async def get_workflow_replay(
    workflow_id: str,
    include_snapshots: bool = False,
    session: AsyncSession = Depends(get_session),
):
    """Get full workflow replay for audit/debug.

    Per V2.8.2 Spec: Returns complete event sequence with optional snapshots.

    Query params:
        include_snapshots: Include artifact content (default False for performance)
    """
    import hashlib
    import json

    service = WorkflowService(session)

    try:
        workflow, step_execution = await service.get_workflow(workflow_id)
    except WorkflowNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow not found: {workflow_id}",
        )

    # Build position for response (per V2.8.2 spec line 2174)
    current_position = build_position_response(workflow, step_execution)

    # Get all events
    from infrastructure.db.repositories.workflow_event import WorkflowEventRepository
    event_repo = WorkflowEventRepository(session)
    all_events = await event_repo.get_events_after(workflow.id, from_sequence=0)

    # Build event responses
    events = []
    for event in all_events:
        # Extract position from payload
        payload = event.payload
        position_data = payload.get("position", {})
        position = PositionResponse(
            instance_number=position_data.get("instance_number", 1),
            step_number=position_data.get("step_number", 1),
            step_name=position_data.get("step_name", "unknown"),
            pass_type=position_data.get("pass_type", "definition"),
            status=position_data.get("status", "unknown"),
            phase=position_data.get("phase", "unknown"),
        )

        # Extract artifact_id from payload
        artifact_id = None
        if "artifact_id" in payload:
            try:
                artifact_id = UUID(payload["artifact_id"]) if isinstance(payload["artifact_id"], str) else payload["artifact_id"]
            except (ValueError, TypeError):
                pass

        events.append(
            ReplayEventResponse(
                sequence=event.sequence,
                timestamp=event.created_at,
                event_type=event.event_type,
                position=position,
                artifact_id=artifact_id,
                data=payload.get("data", {}),
            )
        )

    # Get decisions from audit log
    from infrastructure.db.repositories.audit import AuditLogRepository
    audit_repo = AuditLogRepository(session)
    audit_logs = await audit_repo.list_for_workflow(workflow.id)

    decisions = []
    # Match actual audit event types from workflow_service.py
    # - "step_approved" (approve_step, line ~575)
    # - "revision_requested" (revise_step, line ~690)
    # - "clarification_submitted" (submit_clarification, line ~848)
    decision_types = {"step_approved", "revision_requested", "clarification_submitted"}
    for log in audit_logs:
        if log.event_type in decision_types:
            # Map event_type to decision_type
            decision_type_map = {
                "step_approved": "approve",
                "revision_requested": "revise",
                "clarification_submitted": "clarify",
            }
            decision_type = decision_type_map.get(log.event_type, log.event_type)

            decisions.append(
                DecisionResponse(
                    decision_id=log.id,
                    step_number=log.step_number or 1,
                    decision_type=decision_type,
                    actor_id=log.actor_id,
                    created_at=log.created_at,
                    feedback=log.details.get("feedback") if log.details else None,
                )
            )

    # Get artifacts (needed for snapshots AND trace_hash per spec lines 4193-4197)
    from infrastructure.db.repositories.artifact import ArtifactRepository
    artifact_repo = ArtifactRepository(session)
    artifacts = await artifact_repo.list_for_workflow(workflow.id)

    # Build snapshots if requested
    snapshots: dict[str, dict] = {}
    if include_snapshots:
        for artifact in artifacts:
            if artifact.content:
                snapshots[str(artifact.id)] = artifact.content

    # Compute trace_hash per V2.8.2 Spec (lines 4193-4197)
    # Includes events, artifact_ids, and decision_ids for deterministic comparison
    hash_input = {
        "events": [
            {"sequence": e.sequence, "event_type": e.event_type, "timestamp": e.timestamp.isoformat()}
            for e in events
        ],
        "artifact_ids": sorted([str(a.id) for a in artifacts]),
        "decision_ids": sorted([str(d.decision_id) for d in decisions]),
    }
    trace_hash = hashlib.sha256(json.dumps(hash_input, sort_keys=True).encode()).hexdigest()

    return ReplayResponse(
        workflow_id=workflow.workflow_id,
        state_version=workflow.state_version,
        position=current_position,
        events=events,
        snapshots=snapshots,
        decisions=decisions,
        trace_hash=trace_hash,
    )


# =============================================================================
# Artifact Diff Endpoint (Staleness Assessment)
# =============================================================================


class FieldChangeResponse(BaseModel):
    """Single field change in artifact diff.

    Per V2.8.2 Spec: Change tracking with JSON path.
    """

    path: str = Field(..., description="JSON path, e.g., 'stakeholders[0].needs[2]'")
    old_value: Any = None
    new_value: Any = None
    change_type: str = Field(..., description="Change type: 'added', 'removed', 'modified', 'type_changed'")


class ArtifactDiffResponse(BaseModel):
    """Artifact comparison response.

    Per V2.8.2 Spec (lines 2462-2468): Diff for staleness impact assessment.
    Per V2.8.2 Spec line 2174: All API responses include position.
    - added: dict keyed by path -> new_value
    - removed: dict keyed by path -> old_value
    - changed: list of FieldChangeResponse for modified values
    """

    workflow_id: str
    state_version: int
    position: PositionResponse
    artifact_a_id: UUID
    artifact_b_id: UUID
    added: dict[str, Any]  # path -> new_value (per spec)
    removed: dict[str, Any]  # path -> old_value (per spec)
    changed: list[FieldChangeResponse]  # modified values (list per spec)
    change_count: int
    material_change: bool = Field(..., description="Would invalidate downstream artifacts?")


def _compute_json_diff(
    a: Any,
    b: Any,
    path: str = "",
) -> tuple[dict[str, Any], dict[str, Any], list[FieldChangeResponse]]:
    """Compute recursive JSON diff per V2.8.2 spec algorithm.

    Per spec (lines 2462-2468):
    - added: Dict[str, Any] keyed by path -> new_value
    - removed: Dict[str, Any] keyed by path -> old_value
    - changed: List[FieldChange] for modified values

    Args:
        a: First value (old)
        b: Second value (new)
        path: Current JSON path

    Returns:
        Tuple of (added dict, removed dict, changed list)
    """
    added: dict[str, Any] = {}
    removed: dict[str, Any] = {}
    changed: list[FieldChangeResponse] = []

    # Different types
    if type(a) != type(b):
        changed.append(FieldChangeResponse(
            path=path or "(root)",
            old_value=a,
            new_value=b,
            change_type="type_changed",
        ))
        return added, removed, changed

    # Both are dicts
    if isinstance(a, dict) and isinstance(b, dict):
        all_keys = set(a.keys()) | set(b.keys())
        for key in all_keys:
            current_path = f"{path}.{key}" if path else key

            if key not in a:
                # New field added - store path -> new_value
                added[current_path] = b[key]
            elif key not in b:
                # Field removed - store path -> old_value
                removed[current_path] = a[key]
            else:
                # Recurse
                sub_added, sub_removed, sub_changed = _compute_json_diff(
                    a[key], b[key], current_path
                )
                added.update(sub_added)
                removed.update(sub_removed)
                changed.extend(sub_changed)

        return added, removed, changed

    # Both are lists
    if isinstance(a, list) and isinstance(b, list):
        max_len = max(len(a), len(b))
        for i in range(max_len):
            item_path = f"{path}[{i}]"

            if i >= len(a):
                # New item added - store path -> new_value
                added[item_path] = b[i]
            elif i >= len(b):
                # Item removed - store path -> old_value
                removed[item_path] = a[i]
            elif a[i] != b[i]:
                # Recurse for complex types
                if isinstance(a[i], (dict, list)) and isinstance(b[i], (dict, list)):
                    sub_added, sub_removed, sub_changed = _compute_json_diff(
                        a[i], b[i], item_path
                    )
                    added.update(sub_added)
                    removed.update(sub_removed)
                    changed.extend(sub_changed)
                else:
                    changed.append(FieldChangeResponse(
                        path=item_path,
                        old_value=a[i],
                        new_value=b[i],
                        change_type="modified",
                    ))

        return added, removed, changed

    # Primitive values
    if a != b:
        changed.append(FieldChangeResponse(
            path=path or "(root)",
            old_value=a,
            new_value=b,
            change_type="modified",
        ))

    return added, removed, changed


@router.get("/{workflow_id}/artifacts/{artifact_a_id}/diff/{artifact_b_id}", response_model=ArtifactDiffResponse)
async def get_artifact_diff(
    workflow_id: str,
    artifact_a_id: UUID,
    artifact_b_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Compare two artifacts for staleness assessment.

    Per V2.8.2 Spec: Returns structured diff for impact analysis.

    Path params:
        artifact_a_id: First artifact (typically older)
        artifact_b_id: Second artifact (typically newer)

    Error responses:
        404: Artifact not found
        400: Artifacts cannot be compared (different types)
        422: Same artifact ID for both
    """
    # Validate not same artifact
    if artifact_a_id == artifact_b_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot compare artifact to itself",
        )

    service = WorkflowService(session)

    try:
        workflow, step_execution = await service.get_workflow(workflow_id)
    except WorkflowNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow not found: {workflow_id}",
        )

    # Build position for response (per V2.8.2 spec line 2174)
    position = build_position_response(workflow, step_execution)

    from infrastructure.db.repositories.artifact import ArtifactRepository
    artifact_repo = ArtifactRepository(session)

    # Fetch both artifacts
    artifact_a = await artifact_repo.get(artifact_a_id)
    artifact_b = await artifact_repo.get(artifact_b_id)

    if not artifact_a:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact not found: {artifact_a_id}",
        )
    if not artifact_b:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact not found: {artifact_b_id}",
        )

    # Validate both belong to same workflow
    if artifact_a.workflow_id != workflow.id or artifact_b.workflow_id != workflow.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both artifacts must belong to the specified workflow",
        )

    # Validate same artifact type for meaningful comparison
    if artifact_a.artifact_type != artifact_b.artifact_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot compare different artifact types: {artifact_a.artifact_type} vs {artifact_b.artifact_type}",
        )

    # Get content (default to empty dict if None)
    content_a = artifact_a.content or {}
    content_b = artifact_b.content or {}

    # Compute diff
    added, removed, changed = _compute_json_diff(content_a, content_b)

    # Determine material change (significant enough to invalidate downstream)
    # Heuristic: >5 changes or any structural changes (added/removed)
    change_count = len(added) + len(removed) + len(changed)
    material_change = change_count > 5 or len(added) > 0 or len(removed) > 0

    return ArtifactDiffResponse(
        workflow_id=workflow.workflow_id,
        state_version=workflow.state_version,
        position=position,
        artifact_a_id=artifact_a_id,
        artifact_b_id=artifact_b_id,
        added=added,
        removed=removed,
        changed=changed,
        change_count=change_count,
        material_change=material_change,
    )


class AcknowledgeStaleRequest(BaseModel):
    """Request to acknowledge a stale artifact as still valid.

    Per V2.8.2 Spec lines 2303-2306: Single artifact acknowledgement
    with reviewer justification.
    """

    reviewer_id: str = Field(..., description="ID of reviewer acknowledging staleness")
    justification: str = Field(
        ..., description="Why artifact is still valid despite upstream changes"
    )
    expected_state_version: int = Field(
        ..., description="Expected state version for OCC (409 on mismatch)"
    )


class AcknowledgeStaleResponse(BaseModel):
    """Response for acknowledge-stale action.

    Per V2.8.2 Spec lines 2308-2311 + §9.3 (all responses include position).
    """

    artifact_id: UUID
    state_version: int
    position: PositionResponse  # Required per §9.3


@router.post(
    "/{workflow_id}/artifacts/{artifact_id}/acknowledge-stale",
    response_model=AcknowledgeStaleResponse,
)
async def acknowledge_stale(
    workflow_id: str,
    artifact_id: UUID,
    request: AcknowledgeStaleRequest,
    session: AsyncSession = Depends(get_session),
):
    """Acknowledge that a stale artifact has been reviewed and is still valid.

    Per V2.8.2 Spec lines 2238-2300: State-mutating endpoint that clears
    staleness flag on a single artifact. Requires OCC and emits audit/SSE events.

    Use case: Human reviews stale artifact and confirms it's still correct
    despite upstream changes.

    Error responses:
        404: Workflow or artifact not found
        409: State version conflict
    """
    from datetime import datetime
    from infrastructure.db.models import AuditLog
    from infrastructure.db.repositories.audit import AuditLogRepository
    from infrastructure.db.repositories.artifact import ArtifactRepository
    from infrastructure.db.repositories.workflow_event import WorkflowEventRepository

    service = WorkflowService(session)

    try:
        workflow, step_execution = await service.get_workflow(workflow_id)
    except WorkflowNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow not found: {workflow_id}",
        )

    # OCC check
    if workflow.state_version != request.expected_state_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=StateConflictResponse(
                message=f"State version mismatch: expected {request.expected_state_version}, current {workflow.state_version}",
                current_position=build_position_response(workflow, step_execution),
                current_state_version=workflow.state_version,
            ).model_dump(),
        )

    # Get and validate artifact
    artifact_repo = ArtifactRepository(session)
    artifact = await artifact_repo.get(artifact_id)
    if not artifact or artifact.workflow_id != workflow.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact not found: {artifact_id}",
        )

    # Clear stale flag
    artifact.stale = False
    artifact.stale_reason = None
    artifact.stale_since = None

    # Increment state_version
    workflow.state_version += 1
    workflow.updated_at = datetime.utcnow()

    # Create audit log entry
    audit_repo = AuditLogRepository(session)
    audit_log = AuditLog(
        workflow_id=workflow.id,
        event_type="staleness_acknowledged",
        actor_id=request.reviewer_id,
        details={
            "artifact_id": str(artifact_id),
            "justification": request.justification,
        },
    )
    await audit_repo.append(audit_log)

    # Create SSE event with spec-compliant payload
    # Per V2.8.2 spec: user-initiated events MUST have actor_id and position
    event_repo = WorkflowEventRepository(session)
    sse_event = await event_repo.create_event(
        workflow_id=workflow.id,
        event_type="artifact.stale_cleared",
        payload={
            "artifact_id": str(artifact_id),
            "cleared_by": request.reviewer_id,
            "method": "acknowledged",
            # Required for SSE envelope per V2.8.2 spec
            "workflow_id": workflow.workflow_id,  # External workflow ID
            "instance_id": str(workflow.instance_id),  # Internal UUID per V2.8.2
            "actor_id": request.reviewer_id,
            "position": {
                "instance_number": workflow.instance_number if hasattr(workflow, "instance_number") else 1,
                "step_number": workflow.current_step_number,
                "step_name": workflow.current_step.value,
                "pass_type": workflow.current_pass.value,
                "status": step_execution.status.value if step_execution else "not_started",
                "phase": step_execution.phase.value if step_execution else "received",
            },
        },
    )

    await session.commit()

    # Publish SSE event after commit
    await publish_persisted_events(workflow.workflow_id, [sse_event])

    return AcknowledgeStaleResponse(
        artifact_id=artifact_id,
        state_version=workflow.state_version,
        position=build_position_response(workflow, step_execution),
    )


class ReExecuteRequest(BaseModel):
    """Request to re-execute a stale step.

    Per V2.8.2 Spec: Trigger re-execution of a stale step.
    Requires OCC fields for concurrency control.
    """

    actor_id: str = Field(..., description="Actor ID performing re-execution")
    reason: str = Field(..., description="Reason for re-execution")
    preserve_feedback: bool = Field(default=True, description="Preserve prior feedback")
    expected_state_version: int = Field(
        ..., description="Expected state version for OCC (409 on mismatch)"
    )


class ReExecuteResponse(BaseModel):
    """Response for re-execute action.

    Per V2.8.2 Spec: Returns new state version after mutation.
    """

    step_number: int
    state_version: int


@router.post("/{workflow_id}/steps/{step_number}/re-execute", response_model=ReExecuteResponse)
async def re_execute_step(
    workflow_id: str,
    step_number: int,
    request: ReExecuteRequest,
    session: AsyncSession = Depends(get_session),
):
    """Re-execute a step for staleness recovery.

    Per V2.8.2 Spec: Triggers re-execution of a step that has
    become stale due to upstream revisions.

    This endpoint:
    1. Resets the target step to NOT_STARTED status
    2. Updates the LangGraph checkpoint state
    3. Triggers the runner to process the step
    4. Returns updated workflow state

    Path params:
        step_number: Step number to re-execute (1, 2, or 3)

    Error responses:
        404: Workflow or step not found
        409: State version conflict (include current_state_version)
        422: Cannot re-execute (step is pending or in_progress)
    """
    service = WorkflowService(session)

    try:
        workflow, current_step_execution = await service.get_workflow(workflow_id)
    except WorkflowNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow not found: {workflow_id}",
        )

    # OCC check
    if workflow.state_version != request.expected_state_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=StateConflictResponse(
                message=f"State version mismatch: expected {request.expected_state_version}, current {workflow.state_version}",
                current_position=PositionResponse(
                    instance_number=workflow.instance_number if hasattr(workflow, 'instance_number') else 1,
                    step_number=workflow.current_step_number,
                    step_name=workflow.current_step.value,
                    pass_type=workflow.current_pass.value,
                    status=current_step_execution.status.value if current_step_execution else "unknown",
                    phase=current_step_execution.phase.value if current_step_execution else "unknown",
                ),
                current_state_version=workflow.state_version,
            ).model_dump(),
        )

    # Get the step execution for the requested step
    from infrastructure.db.repositories.step_execution import StepExecutionRepository
    step_repo = StepExecutionRepository(session)
    step_executions = await step_repo.list_for_workflow(workflow.id)

    target_step = None
    for se in step_executions:
        if se.step_number == step_number:
            target_step = se
            break

    if not target_step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Step {step_number} not found for workflow",
        )

    # Validate step can be re-executed (not pending, in_progress, or not_started)
    # Per spec: Can only re-execute steps that have completed (awaiting_review, approved, etc.)
    from infrastructure.db.models.enums import StepStatus, StepPhase

    if target_step.status in (StepStatus.NOT_STARTED, StepStatus.PENDING, StepStatus.IN_PROGRESS):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot re-execute step {step_number}: current status is {target_step.status.value}",
        )

    # Store previous status for audit log
    previous_status = target_step.status

    # Collect all persisted events to publish after commits
    all_events = []

    # Mark current artifact as superseded (if exists)
    if target_step.latest_artifact_id:
        from infrastructure.db.repositories.artifact import ArtifactRepository
        artifact_repo = ArtifactRepository(session)
        artifact = await artifact_repo.get(target_step.latest_artifact_id)
        if artifact:
            # Set stale flag on current artifact
            artifact.stale = True
            artifact.stale_reason = f"Re-execution requested: {request.reason}"
            from datetime import datetime
            artifact.stale_since = datetime.utcnow()

    # Reset step_execution status and phase
    # Per V2.8.2 spec: use PENDING for queued re-execution
    target_step.status = StepStatus.PENDING
    target_step.phase = StepPhase.RECEIVED

    # Update workflow position to the re-executed step
    workflow.current_step = target_step.step_name
    workflow.current_step_number = step_number
    workflow.current_pass = target_step.pass_type

    # Increment state_version
    workflow.state_version += 1
    from datetime import datetime
    workflow.updated_at = datetime.utcnow()

    # Create audit log entry
    from infrastructure.db.models import AuditLog
    from infrastructure.db.repositories.audit import AuditLogRepository
    audit_repo = AuditLogRepository(session)
    audit_log = AuditLog(
        workflow_id=workflow.id,
        event_type="step_reexecute_requested",
        actor_id=request.actor_id,
        step_name=target_step.step_name,
        step_number=step_number,
        from_status=previous_status,
        to_status=StepStatus.PENDING,
        details={
            "reason": request.reason,
            "preserve_feedback": request.preserve_feedback,
        },
    )
    await audit_repo.append(audit_log)

    # Persist SSE event for reexecute_started
    from infrastructure.db.repositories.workflow_event import WorkflowEventRepository
    event_repo = WorkflowEventRepository(session)
    reexecute_event = await event_repo.create_event(
        workflow_id=workflow.id,
        event_type="step.reexecute_started",
        payload={
            "workflow_id": workflow.workflow_id,
            "instance_id": str(workflow.instance_id),
            "position": {
                "instance_number": workflow.instance_number if hasattr(workflow, 'instance_number') else 1,
                "step_number": step_number,
                "step_name": target_step.step_name.value,
                "pass_type": target_step.pass_type.value,
                "status": StepStatus.PENDING.value,
                "phase": StepPhase.RECEIVED.value,
            },
            "actor_id": request.actor_id,
            "data": {
                "reason": request.reason,
                "preserve_feedback": request.preserve_feedback,
            },
        },
    )
    all_events.append(reexecute_event)

    await session.commit()

    # Publish persisted events AFTER transaction commits
    await publish_persisted_events(workflow.workflow_id, all_events)
    all_events.clear()

    # Update LangGraph checkpoint state to reset to target step and trigger execution
    graph = get_graph()
    config = {"configurable": {"thread_id": workflow.thread_id}}

    # Build reset step state with preserved feedback if requested
    reset_step_state = StepState(
        step_name=target_step.step_name,
        step_number=step_number,
        pass_type=target_step.pass_type,
        status=DomainStepStatus.PENDING,
        phase=DomainStepPhase.RECEIVED,
        human_feedback=target_step.human_feedback if request.preserve_feedback else None,
    )

    # Update graph state to reset position and trigger re-execution
    await graph.aupdate_state(
        config,
        {
            "current_step": target_step.step_name,
            "step_state": reset_step_state,
            "human_decision": None,  # Clear any pending decision
        },
        as_node="receive",  # Start from receive node to process the step
    )

    # Invoke graph to trigger re-execution
    result = await graph.ainvoke(None, config)

    # Sync DB with graph result
    artifact_output = _extract_artifact_output(result)

    async with session.begin():
        sync_events = await service.sync_db_from_state(
            workflow_id, result, artifact_output=artifact_output
        )
        all_events.extend(sync_events)

    # Publish sync events AFTER transaction commits
    await publish_persisted_events(workflow.workflow_id, all_events)

    # Reload workflow for updated state_version
    workflow, _ = await service.get_workflow(workflow_id)

    # Per V2.8.2 Spec (lines 2390-2405): Return ReExecuteResponse, not full WorkflowResponse
    # Client monitors progress via SSE
    return ReExecuteResponse(
        step_number=step_number,
        state_version=workflow.state_version,
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


@router.post("/{workflow_id}/actions/message", response_model=MessageResponse)
async def send_message(
    workflow_id: str,
    request: MessageRequest,
    session: AsyncSession = Depends(get_session),
):
    """Send message without changing workflow state.

    Per Tech Spec V2.8.2 §16.7: Returns minimal {message_id, status} response.
    Exception to §9.3 - no position wrapper for non-state-mutating action.
    Gate C: Status remains AWAITING_REVIEW.
    Message is persisted for conversation history.

    Requires step to be in AWAITING_REVIEW status.
    """
    service = WorkflowService(session)

    try:
        async with session.begin():
            workflow, step_execution, message = await service.send_message(
                workflow_id=workflow_id,
                content=request.content,
                actor_id=request.actor_id,
            )

        # Per §16.7: Return minimal message response with actual persisted ID
        return MessageResponse(message_id=str(message.id), status="sent")

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
