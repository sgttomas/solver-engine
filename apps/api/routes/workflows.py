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
from typing import Optional
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
)
from infrastructure.postgres import get_session, async_session_factory
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

# Module-level singleton - checkpointer manages its own sessions,
# thread_id in config provides per-workflow isolation
_checkpointer = SolverCheckpointSaver(async_session_factory)
_graph = create_graph(_checkpointer)


def get_graph():
    """Return cached graph instance."""
    return _graph


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


class ApproveRequest(BaseModel):
    """Request to approve current step."""

    actor_id: Optional[str] = Field(
        default=None, description="Actor ID (defaults to workflow.created_by)"
    )


class ReviseRequest(BaseModel):
    """Request to revise current step."""

    feedback: str = Field(..., description="Revision feedback/instructions")
    actor_id: Optional[str] = Field(
        default=None, description="Actor ID (defaults to workflow.created_by)"
    )


class MessageRequest(BaseModel):
    """Request to send a message without changing state."""

    content: str = Field(..., description="Message content")
    actor_id: Optional[str] = Field(
        default=None, description="Actor ID (defaults to workflow.created_by)"
    )


class ClarifyRequest(BaseModel):
    """Request to submit clarification answers."""

    answers: dict = Field(..., description="Clarification responses keyed by question ID")
    actor_id: Optional[str] = Field(
        default=None, description="Actor ID (defaults to workflow.created_by)"
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
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


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
    """
    service = WorkflowService(session)

    try:
        # P4.1: Create DB records
        async with session.begin():
            workflow, step_execution = await service.create_workflow(
                problem=request.problem,
                created_by=request.created_by,
                instance_number=request.instance_number,
                domain=request.domain,
            )

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

        # Sync DB with graph result
        async with session.begin():
            await service.sync_db_from_state(workflow.workflow_id, result)

        # Reload for response
        workflow, step_execution = await service.get_workflow(workflow.workflow_id)
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
            async with session.begin():
                await service.sync_db_from_state(workflow_id, snapshot.values)
        else:
            # Not at gate (crashed mid-execution or no checkpoint) - continue
            if snapshot:
                result = await graph.ainvoke(None, config)
                async with session.begin():
                    await service.sync_db_from_state(workflow_id, result)

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

    Requires step to be in AWAITING_REVIEW status.
    """
    service = WorkflowService(session)

    try:
        # P4.2: DB update
        async with session.begin():
            workflow, step_execution = await service.approve_step(
                workflow_id=workflow_id,
                actor_id=request.actor_id,
            )

        # P4.4: Update graph state and resume
        graph = get_graph()
        config = {"configurable": {"thread_id": workflow.thread_id}}

        await graph.aupdate_state(
            config,
            {"human_decision": HumanAction.APPROVE},
            as_node="review",  # Critical: tells LangGraph review is complete
        )

        result = await graph.ainvoke(None, config)

        # Sync DB with graph result
        async with session.begin():
            await service.sync_db_from_state(workflow_id, result)

        # Reload for response
        workflow, step_execution = await service.get_workflow(workflow_id)
        return build_workflow_response(workflow, step_execution)

    except WorkflowNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow not found: {workflow_id}",
        )
    except InvalidStateError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
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

    Requires step to be in AWAITING_REVIEW status.
    """
    service = WorkflowService(session)

    try:
        # P4.2: DB update
        async with session.begin():
            workflow, step_execution = await service.revise_step(
                workflow_id=workflow_id,
                feedback=request.feedback,
                actor_id=request.actor_id,
            )

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

        # Sync DB with graph result
        async with session.begin():
            await service.sync_db_from_state(workflow_id, result)

        # Reload for response
        workflow, step_execution = await service.get_workflow(workflow_id)
        return build_workflow_response(workflow, step_execution)

    except WorkflowNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow not found: {workflow_id}",
        )
    except InvalidStateError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
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
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
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

    Requires step to be in AWAITING_CLARIFICATION status.
    """
    service = WorkflowService(session)

    try:
        # P4.2: DB update
        async with session.begin():
            workflow, step_execution = await service.submit_clarification(
                workflow_id=workflow_id,
                answers=request.answers,
                actor_id=request.actor_id,
            )

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

        # Sync DB with graph result
        async with session.begin():
            await service.sync_db_from_state(workflow_id, result)

        # Reload for response
        workflow, step_execution = await service.get_workflow(workflow_id)
        return build_workflow_response(workflow, step_execution)

    except WorkflowNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow not found: {workflow_id}",
        )
    except InvalidStateError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid state: {e.current_status}, expected {e.expected_status}",
        )


# =============================================================================
# P4.3: SSE Streaming Endpoint
# =============================================================================


@router.get("/{workflow_id}/stream")
async def stream_workflow(
    workflow_id: str,
    session: AsyncSession = Depends(get_session),
):
    """SSE stream for real-time events.

    Gate E: Must support full interactive flow.

    P4.3: Returns current state snapshot + heartbeat.
    P4.4 will add real-time event streaming during graph execution.
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

    async def event_generator():
        try:
            # Yield initial state snapshot
            if step_execution:
                event_type = STATUS_TO_EVENT.get(
                    step_execution.status.value, "step.started"
                )
                payload = {
                    "event_id": str(uuid4()),
                    "event_type": event_type,
                    "workflow_id": workflow.workflow_id,
                    "instance_id": str(workflow.instance_id),
                    "pass_type": workflow.current_pass.value,
                    "step_number": workflow.current_step_number,
                    "step_name": workflow.current_step.value,
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {
                        "status": step_execution.status.value,
                        "phase": step_execution.phase.value,
                    },
                }
                yield format_sse_event(event_type, payload)

            # Heartbeat loop (P4.4 will add event queue here)
            while True:
                await asyncio.sleep(15)
                yield format_sse_comment("keep-alive")

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
