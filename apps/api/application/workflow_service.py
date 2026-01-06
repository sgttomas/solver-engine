"""
SOLVER API - Workflow Service

Use cases for workflow management.
P4.1: DB-only create/get/resume.
P4.2: DB-only action endpoints (approve/revise/message/clarify).
Graph integration deferred to P4.4.
"""

import logging
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import (
    Artifact,
    Workflow,
    StepExecution,
    Instance,
    Message,
    AuditLog,
    PassType,
    StepName,
    StepStatus,
    StepPhase,
    WorkflowStatus,
    MessageRole,
)
from infrastructure.db.repositories.workflow import WorkflowRepository
from infrastructure.db.repositories.step_execution import StepExecutionRepository
from infrastructure.db.repositories.instance import InstanceRepository
from infrastructure.db.repositories.message import MessageRepository
from infrastructure.db.repositories.audit import AuditLogRepository
from infrastructure.db.repositories.artifact import ArtifactRepository
from infrastructure.db.repositories.workflow_event import WorkflowEventRepository
from infrastructure.db.models.workflow_event import WorkflowEvent
from application.artifact_service import ArtifactService
from application.traceability_service import (
    TraceabilityService,
    TraceabilityExtractionError,
)


logger = logging.getLogger(__name__)


def _chunk_string(s: str, num_chunks: int) -> list:
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


class WorkflowNotFoundError(Exception):
    """Raised when workflow is not found."""

    def __init__(self, workflow_id: str):
        self.workflow_id = workflow_id
        super().__init__(f"Workflow not found: {workflow_id}")


class InstanceNotFoundError(Exception):
    """Raised when instance is not found."""

    def __init__(self, instance_number: int):
        self.instance_number = instance_number
        super().__init__(f"Instance not found: {instance_number}")


class InvalidStateError(Exception):
    """Raised when workflow is in invalid state for action (semantic violation).

    Results in 422 Unprocessable Entity - the action is semantically invalid
    for the current workflow state (e.g., approve when not awaiting_review).
    """

    def __init__(self, workflow_id: str, current_status: str, expected_status: str):
        self.workflow_id = workflow_id
        self.current_status = current_status
        self.expected_status = expected_status
        super().__init__(
            f"Workflow {workflow_id} is in {current_status}, expected {expected_status}"
        )


class StateVersionMismatchError(Exception):
    """Raised when expected_state_version doesn't match current (optimistic concurrency).

    Per Contract §10.5, §11.1-§11.2: Results in 409 Conflict with StateConflictResponse.
    Client should refetch state and retry with updated expected_state_version.
    """

    def __init__(
        self,
        workflow_id: str,
        expected_version: int,
        current_version: int,
        current_pass: str,
        current_step: str,
        current_step_number: int,
        current_status: str,
    ):
        self.workflow_id = workflow_id
        self.expected_version = expected_version
        self.current_version = current_version
        self.current_pass = current_pass
        self.current_step = current_step
        self.current_step_number = current_step_number
        self.current_status = current_status
        super().__init__(
            f"State version mismatch: expected {expected_version}, got {current_version}"
        )


class ArtifactNotFoundError(Exception):
    """Raised when artifact is not found.

    Per Tech Spec V2.8.0 Appendix C.4: Results in 404.
    """

    def __init__(self, artifact_id: UUID):
        self.artifact_id = artifact_id
        super().__init__(f"Artifact not found: {artifact_id}")


class ArtifactNotBelongError(Exception):
    """Raised when artifact doesn't belong to specified workflow.

    Per Tech Spec V2.8.0 Appendix C.4: Results in 400.
    """

    def __init__(self, artifact_id: UUID, workflow_id: str):
        self.artifact_id = artifact_id
        self.workflow_id = workflow_id
        super().__init__(f"Artifact {artifact_id} does not belong to workflow {workflow_id}")


class WorkflowService:
    """Service for workflow lifecycle operations.

    P4.1: DB-only create/get/resume.
    P4.2: DB-only action endpoints.
    P4.4 will add graph integration.
    """

    def __init__(self, session: AsyncSession):
        """Initialize service with database session.

        Args:
            session: Async SQLAlchemy session
        """
        self._session = session
        self._workflow_repo = WorkflowRepository(session)
        self._step_repo = StepExecutionRepository(session)
        self._instance_repo = InstanceRepository(session)
        self._message_repo = MessageRepository(session)
        self._audit_repo = AuditLogRepository(session)
        self._artifact_repo = ArtifactRepository(session)
        self._event_repo = WorkflowEventRepository(session)
        self._artifact_service = ArtifactService(session)
        self._traceability_service = TraceabilityService(session)

    async def create_workflow(
        self,
        problem: str,
        created_by: str,
        instance_number: int = 0,
        domain: Optional[str] = None,
    ) -> tuple[Workflow, StepExecution, list[WorkflowEvent]]:
        """Create a new workflow with initial step execution.

        Creates Workflow and initial StepExecution records in one transaction.
        Does NOT invoke graph (deferred to P4.4).

        Per Fix 1 (Atomic Event Persistence): Persists workflow.started event
        and returns it for route to publish after transaction commits.

        Args:
            problem: The problem statement
            created_by: Actor ID creating the workflow
            instance_number: Instance number (default 0 = Universal Methodology)
            domain: Optional domain classification

        Returns:
            Tuple of (Workflow, StepExecution, events) for the created workflow

        Raises:
            InstanceNotFoundError: If instance_number doesn't exist
        """
        events: list[WorkflowEvent] = []

        # Resolve instance by number
        instance = await self._instance_repo.get_by_number(instance_number)
        if instance is None:
            raise InstanceNotFoundError(instance_number)

        # Generate unique identifiers
        workflow_id = str(uuid4())
        thread_id = str(uuid4())

        # Create workflow record
        workflow = Workflow(
            workflow_id=workflow_id,
            thread_id=thread_id,
            instance_id=instance.id,
            original_problem=problem,
            domain=domain,
            current_pass=PassType.DEFINITION,
            current_step=StepName.PROBLEM_DEFINITION,
            current_step_number=1,
            status=WorkflowStatus.ACTIVE,
            pass_1_gate_policy=instance.pass_1_gate_policy,
            created_by=created_by,
            last_actor_id=created_by,
        )
        self._session.add(workflow)
        await self._session.flush()  # Get workflow.id for FK

        # Create initial step execution
        step_execution = StepExecution(
            workflow_id=workflow.id,
            pass_type=PassType.DEFINITION,
            step_name=StepName.PROBLEM_DEFINITION,
            step_number=1,
            status=StepStatus.NOT_STARTED,
            phase=StepPhase.RECEIVED,
        )
        self._session.add(step_execution)
        await self._session.flush()

        # Persist workflow.started event (Fix 1: persist before publish)
        event = await self._persist_event(
            workflow=workflow,
            event_type="workflow.started",
            step_execution=step_execution,
            data={"problem": problem, "created_by": created_by},
        )
        events.append(event)

        return workflow, step_execution, events

    async def get_workflow(
        self,
        workflow_id: str,
    ) -> tuple[Workflow, Optional[StepExecution]]:
        """Get workflow and its current step execution.

        Args:
            workflow_id: Unique workflow identifier

        Returns:
            Tuple of (Workflow, StepExecution or None)

        Raises:
            WorkflowNotFoundError: If workflow doesn't exist
        """
        workflow = await self._workflow_repo.get_by_workflow_id(workflow_id)
        if workflow is None:
            raise WorkflowNotFoundError(workflow_id)

        # Get current step execution
        step_execution = await self._step_repo.get_by_composite(
            workflow_id=workflow.id,
            pass_type=workflow.current_pass,
            step_name=workflow.current_step,
        )

        return workflow, step_execution

    async def resume_workflow(
        self,
        workflow_id: str,
    ) -> tuple[Workflow, Optional[StepExecution]]:
        """Resume workflow from persisted state.

        P4.1: Returns current DB state only.
        P4.4 will add graph invocation.

        Args:
            workflow_id: Unique workflow identifier

        Returns:
            Tuple of (Workflow, StepExecution or None)

        Raises:
            WorkflowNotFoundError: If workflow doesn't exist
        """
        # For P4.1, resume is identical to get (DB-only)
        return await self.get_workflow(workflow_id)

    async def get_artifact(
        self,
        workflow_id: str,
        artifact_id: UUID,
    ) -> tuple[Artifact, Workflow]:
        """Get artifact by ID, validating it belongs to workflow.

        Per Tech Spec V2.8.0 Appendix C.4.

        Args:
            workflow_id: Workflow ID (external string ID)
            artifact_id: Artifact UUID

        Returns:
            Tuple of (Artifact, Workflow)

        Raises:
            WorkflowNotFoundError: If workflow doesn't exist
            ArtifactNotFoundError: If artifact doesn't exist
            ArtifactNotBelongError: If artifact doesn't belong to workflow
        """
        workflow, _ = await self.get_workflow(workflow_id)

        artifact = await self._artifact_repo.get_by_id(artifact_id)
        if artifact is None:
            raise ArtifactNotFoundError(artifact_id)

        if artifact.workflow_id != workflow.id:
            raise ArtifactNotBelongError(artifact_id, workflow_id)

        return artifact, workflow

    # =========================================================================
    # P4.2: Action Endpoints (DB-only)
    # =========================================================================

    async def _get_workflow_and_step(
        self,
        workflow_id: str,
        expected_status: StepStatus,
    ) -> tuple[Workflow, StepExecution]:
        """Helper to load workflow and validate step status.

        Args:
            workflow_id: Unique workflow identifier
            expected_status: Required step status for action

        Returns:
            Tuple of (Workflow, StepExecution)

        Raises:
            WorkflowNotFoundError: If workflow doesn't exist
            InvalidStateError: If step is not in expected status or doesn't exist
        """
        workflow = await self._workflow_repo.get_by_workflow_id(workflow_id)
        if workflow is None:
            raise WorkflowNotFoundError(workflow_id)

        step_execution = await self._step_repo.get_by_composite(
            workflow_id=workflow.id,
            pass_type=workflow.current_pass,
            step_name=workflow.current_step,
        )

        if step_execution is None:
            raise InvalidStateError(
                workflow_id=workflow_id,
                current_status="no_step_execution",
                expected_status=expected_status.value,
            )

        if step_execution.status != expected_status:
            raise InvalidStateError(
                workflow_id=workflow_id,
                current_status=step_execution.status.value,
                expected_status=expected_status.value,
            )

        return workflow, step_execution

    def _resolve_actor_id(self, actor_id: Optional[str], workflow: Workflow) -> str:
        """Resolve actor ID with fallback to workflow.created_by."""
        return actor_id if actor_id else workflow.created_by

    def _validate_optimistic_concurrency(
        self,
        workflow: Workflow,
        step_execution: StepExecution,
        expected_state_version: int,
        expected_position: dict,
    ) -> None:
        """Validate optimistic concurrency for action endpoints.

        Per Contract §11.1-§11.2: Actions MUST include expected_state_version
        and expected_position. Both are REQUIRED - no None bypass.

        Raises StateVersionMismatchError (409) if:
        - expected_state_version != current state_version
        - expected_position doesn't match current position (pass, step, step_number, status)

        Args:
            workflow: Current workflow state
            step_execution: Current step execution
            expected_state_version: Required version client expects
            expected_position: Required position dict with pass_type, step_name, step_number, status

        Raises:
            StateVersionMismatchError: If version or position mismatch
        """
        # Version check
        if expected_state_version != workflow.state_version:
            raise StateVersionMismatchError(
                workflow_id=workflow.workflow_id,
                expected_version=expected_state_version,
                current_version=workflow.state_version,
                current_pass=workflow.current_pass.value,
                current_step=workflow.current_step.value,
                current_step_number=workflow.current_step_number,
                current_status=step_execution.status.value if step_execution else "unknown",
            )

        # Full position check (includes step_name)
        current_pass = workflow.current_pass.value
        current_step = workflow.current_step.value
        current_step_number = workflow.current_step_number
        current_status = step_execution.status.value if step_execution else "unknown"

        position_mismatch = (
            expected_position.get("pass_type") != current_pass or
            expected_position.get("step_name") != current_step or
            expected_position.get("step_number") != current_step_number or
            expected_position.get("status") != current_status
        )

        if position_mismatch:
            raise StateVersionMismatchError(
                workflow_id=workflow.workflow_id,
                expected_version=expected_state_version,
                current_version=workflow.state_version,
                current_pass=current_pass,
                current_step=current_step,
                current_step_number=current_step_number,
                current_status=current_status,
            )

    async def _increment_state_version(self, workflow: Workflow) -> int:
        """Increment workflow state_version for optimistic concurrency.

        Per Contract §9.1: state_version MUST be a monotonically increasing integer
        Per Contract §11.3: state_version increment MUST occur on every accepted state transition

        Args:
            workflow: Workflow to update

        Returns:
            New state_version value
        """
        workflow.state_version = workflow.state_version + 1
        return workflow.state_version

    def _build_event_payload(
        self,
        workflow: Workflow,
        step_execution: Optional[StepExecution] = None,
        artifact_id: Optional[str] = None,
        data: Optional[dict] = None,
        actor_id: Optional[str] = None,
    ) -> dict:
        """Build consistent event payload for SSE events.

        Per Fix 1 (Atomic Event Persistence): All events use consistent payload structure.
        Per V2.8.0 Spec Appendix C: All events MUST include nested `position` object.

        Args:
            workflow: Workflow for context
            step_execution: Optional step execution for status/phase
            artifact_id: Optional artifact ID for artifact events
            data: Optional additional data to include
            actor_id: Optional actor ID for user-initiated events

        Returns:
            Event payload dict (excluding event_id, sequence, timestamp - added by model)
        """
        # Build position object per V2.8.0 spec Appendix C.1
        status = step_execution.status.value if step_execution else "unknown"
        phase = step_execution.phase.value if step_execution else "unknown"

        position = {
            "instance_number": workflow.instance_number if hasattr(workflow, 'instance_number') else 1,
            "step_number": workflow.current_step_number,
            "step_name": workflow.current_step.value,
            "pass_type": workflow.current_pass.value,
            "status": status,
            "phase": phase,
        }

        payload = {
            "workflow_id": workflow.workflow_id,  # External workflow ID string for SSE
            "instance_id": str(workflow.instance_id),  # Internal UUID per V2.8.0
            "position": position,
            "data": {},
        }

        if artifact_id:
            payload["artifact_id"] = artifact_id

        if actor_id:
            payload["actor_id"] = actor_id

        if data:
            payload["data"].update(data)

        return payload

    async def _persist_event(
        self,
        workflow: Workflow,
        event_type: str,
        step_execution: Optional[StepExecution] = None,
        artifact_id: Optional[str] = None,
        data: Optional[dict] = None,
        actor_id: Optional[str] = None,
    ):
        """Persist workflow event to durable log and return it.

        Per Contract §9.2: Events stored in workflow_events table
        Per Contract §11.4: Events MUST be persisted BEFORE broadcast
        Per Fix 1: Returns event for route to publish after commit
        Per V2.8.0 Spec: User-initiated events MUST include actor_id

        Args:
            workflow: Workflow the event belongs to
            event_type: Event type (e.g., 'step.approved')
            step_execution: Optional step execution for status/phase
            artifact_id: Optional artifact ID for artifact events
            data: Optional additional data to include
            actor_id: Optional actor ID for user-initiated events

        Returns:
            Created WorkflowEvent for publishing after transaction commit
        """
        payload = self._build_event_payload(
            workflow, step_execution, artifact_id, data, actor_id
        )
        return await self._event_repo.create_event(
            workflow_id=workflow.id,
            event_type=event_type,
            payload=payload,
        )

    async def _create_audit_entry(
        self,
        workflow: Workflow,
        step_execution: StepExecution,
        event_type: str,
        actor_id: str,
        from_status: StepStatus,
        to_status: StepStatus,
        from_phase: StepPhase,
        to_phase: StepPhase,
        details: Optional[dict] = None,
    ) -> AuditLog:
        """Create audit log entry with full context for Gate F."""
        audit_log = AuditLog(
            workflow_id=workflow.id,
            event_type=event_type,
            actor_id=actor_id,
            pass_type=step_execution.pass_type,
            step_name=step_execution.step_name,
            step_number=step_execution.step_number,
            from_status=from_status,
            to_status=to_status,
            from_phase=from_phase,
            to_phase=to_phase,
            details=details or {},
        )
        return await self._audit_repo.append(audit_log)

    async def approve_step(
        self,
        workflow_id: str,
        actor_id: Optional[str] = None,
        expected_state_version: int = 0,
        expected_position: Optional[dict] = None,
    ) -> tuple[Workflow, StepExecution, list[WorkflowEvent]]:
        """Approve current step.

        P4.2: DB-only (updates status to APPROVED).
        P4.4 will add graph invocation to advance workflow.

        Per Fix 1 (Atomic Event Persistence): Persists step.approved event
        and returns it for route to publish after transaction commits.

        Args:
            workflow_id: Unique workflow identifier
            actor_id: Actor performing action (defaults to workflow.created_by)
            expected_state_version: Required version for optimistic concurrency (§11.1)
            expected_position: Required position dict for optimistic concurrency (§11.1)

        Returns:
            Tuple of (Workflow, StepExecution, events)

        Raises:
            WorkflowNotFoundError: If workflow doesn't exist
            InvalidStateError: If step is not AWAITING_REVIEW (422)
            StateVersionMismatchError: If expected_state_version or position mismatch (409)
        """
        events: list[WorkflowEvent] = []

        workflow, step_execution = await self._get_workflow_and_step(
            workflow_id, StepStatus.AWAITING_REVIEW
        )

        # Validate optimistic concurrency (Contract §11.1-§11.2)
        self._validate_optimistic_concurrency(
            workflow, step_execution, expected_state_version, expected_position or {}
        )

        actor = self._resolve_actor_id(actor_id, workflow)

        # Capture before state for audit
        from_status = step_execution.status
        from_phase = step_execution.phase

        # Update last_actor_id FIRST (before status change for audit trigger)
        workflow.last_actor_id = actor
        workflow.updated_at = datetime.utcnow()

        # Increment state_version for optimistic concurrency (Contract §9.1, §11.3)
        await self._increment_state_version(workflow)

        # Update step execution
        step_execution.status = StepStatus.APPROVED
        step_execution.phase = StepPhase.COMPLETE
        step_execution.completed_at = datetime.utcnow()

        # Create audit entry
        await self._create_audit_entry(
            workflow=workflow,
            step_execution=step_execution,
            event_type="step_approved",
            actor_id=actor,
            from_status=from_status,
            to_status=StepStatus.APPROVED,
            from_phase=from_phase,
            to_phase=StepPhase.COMPLETE,
        )

        # Persist event to durable log (Fix 1: persist before publish, return for route)
        # Per V2.8.0 Spec: actor_id MUST be top-level for user-initiated events
        event = await self._persist_event(
            workflow=workflow,
            event_type="step.approved",
            step_execution=step_execution,
            data={"state_version": workflow.state_version},
            actor_id=actor,
        )
        events.append(event)

        await self._session.flush()
        return workflow, step_execution, events

    async def revise_step(
        self,
        workflow_id: str,
        feedback: str,
        actor_id: Optional[str] = None,
        expected_state_version: int = 0,
        expected_position: Optional[dict] = None,
    ) -> tuple[Workflow, StepExecution, list[WorkflowEvent]]:
        """Request revision of current step.

        P4.2: DB-only (updates status to REVISION_REQUESTED).
        P4.4 will add graph invocation to re-run step.

        Per Fix 1 (Atomic Event Persistence): Persists step.revised event
        and returns it for route to publish after transaction commits.

        Args:
            workflow_id: Unique workflow identifier
            feedback: Revision feedback/instructions
            actor_id: Actor performing action (defaults to workflow.created_by)
            expected_state_version: Required version for optimistic concurrency (§11.1)
            expected_position: Required position dict for optimistic concurrency (§11.1)

        Returns:
            Tuple of (Workflow, StepExecution, events)

        Raises:
            WorkflowNotFoundError: If workflow doesn't exist
            InvalidStateError: If step is not AWAITING_REVIEW (422)
            StateVersionMismatchError: If expected_state_version or position mismatch (409)
        """
        events: list[WorkflowEvent] = []

        workflow, step_execution = await self._get_workflow_and_step(
            workflow_id, StepStatus.AWAITING_REVIEW
        )

        # Validate optimistic concurrency (Contract §11.1-§11.2)
        self._validate_optimistic_concurrency(
            workflow, step_execution, expected_state_version, expected_position or {}
        )

        actor = self._resolve_actor_id(actor_id, workflow)

        # Capture before state for audit
        from_status = step_execution.status
        from_phase = step_execution.phase

        # Update last_actor_id FIRST
        workflow.last_actor_id = actor
        workflow.updated_at = datetime.utcnow()

        # Increment state_version for optimistic concurrency (Contract §9.1, §11.3)
        await self._increment_state_version(workflow)

        # Update step execution
        step_execution.status = StepStatus.REVISION_REQUESTED
        step_execution.phase = StepPhase.STRUCTURING
        step_execution.human_feedback = feedback

        # Create message record for feedback
        message = Message(
            workflow_id=workflow.id,
            step_execution_id=step_execution.id,
            role=MessageRole.USER,
            content=feedback,
            metadata_={},
        )
        self._session.add(message)

        # Create audit entry
        await self._create_audit_entry(
            workflow=workflow,
            step_execution=step_execution,
            event_type="revision_requested",
            actor_id=actor,
            from_status=from_status,
            to_status=StepStatus.REVISION_REQUESTED,
            from_phase=from_phase,
            to_phase=StepPhase.STRUCTURING,
            details={"feedback": feedback},
        )

        # Persist event to durable log (Fix 1: persist before publish, return for route)
        # Per V2.8.0 Spec: event type is "step.revision_requested", actor_id top-level
        event = await self._persist_event(
            workflow=workflow,
            event_type="step.revision_requested",
            step_execution=step_execution,
            data={
                "state_version": workflow.state_version,
                "feedback": feedback,
            },
            actor_id=actor,
        )
        events.append(event)

        await self._session.flush()
        return workflow, step_execution, events

    async def send_message(
        self,
        workflow_id: str,
        content: str,
        actor_id: Optional[str] = None,
    ) -> tuple[Workflow, StepExecution, Message]:
        """Send message without changing workflow state.

        Gate C: Status remains AWAITING_REVIEW.
        Message is persisted for conversation history.

        Per Tech Spec V2.8.2 §16.7: Message action is non-state-mutating,
        returns minimal {message_id, status} response at API layer.

        Args:
            workflow_id: Unique workflow identifier
            content: Message content
            actor_id: Actor performing action (defaults to workflow.created_by)

        Returns:
            Tuple of (Workflow, StepExecution, Message) - Message contains persisted ID
            for API response per §16.7.

        Raises:
            WorkflowNotFoundError: If workflow doesn't exist
            InvalidStateError: If step is not AWAITING_REVIEW
        """
        workflow, step_execution = await self._get_workflow_and_step(
            workflow_id, StepStatus.AWAITING_REVIEW
        )

        actor = self._resolve_actor_id(actor_id, workflow)

        # Update last_actor_id (NO status change - Gate C)
        workflow.last_actor_id = actor
        workflow.updated_at = datetime.utcnow()

        # Create message record
        message = Message(
            workflow_id=workflow.id,
            step_execution_id=step_execution.id,
            role=MessageRole.USER,
            content=content,
            metadata_={},
        )
        self._session.add(message)

        # Create audit entry (no status transition)
        await self._create_audit_entry(
            workflow=workflow,
            step_execution=step_execution,
            event_type="message_sent",
            actor_id=actor,
            from_status=step_execution.status,
            to_status=step_execution.status,  # No change
            from_phase=step_execution.phase,
            to_phase=step_execution.phase,  # No change
            details={"content": content},
        )

        await self._session.flush()
        return workflow, step_execution, message

    async def submit_clarification(
        self,
        workflow_id: str,
        answers: dict,
        actor_id: Optional[str] = None,
        expected_state_version: int = 0,
        expected_position: Optional[dict] = None,
    ) -> tuple[Workflow, StepExecution, list[WorkflowEvent]]:
        """Submit clarification answers.

        P4.2: DB-only (updates status to IN_PROGRESS).
        P4.4 will add graph invocation to resume.

        Per Fix 1 (Atomic Event Persistence): Persists step.clarified event
        and returns it for route to publish after transaction commits.

        Args:
            workflow_id: Unique workflow identifier
            answers: Clarification responses keyed by question ID
            actor_id: Actor performing action (defaults to workflow.created_by)
            expected_state_version: Required version for optimistic concurrency (§11.1)
            expected_position: Required position dict for optimistic concurrency (§11.1)

        Returns:
            Tuple of (Workflow, StepExecution, events)

        Raises:
            WorkflowNotFoundError: If workflow doesn't exist
            InvalidStateError: If step is not AWAITING_CLARIFICATION (422)
            StateVersionMismatchError: If expected_state_version or position mismatch (409)
        """
        events: list[WorkflowEvent] = []

        workflow, step_execution = await self._get_workflow_and_step(
            workflow_id, StepStatus.AWAITING_CLARIFICATION
        )

        # Validate optimistic concurrency (Contract §11.1-§11.2)
        self._validate_optimistic_concurrency(
            workflow, step_execution, expected_state_version, expected_position or {}
        )

        actor = self._resolve_actor_id(actor_id, workflow)

        # Capture before state for audit
        from_status = step_execution.status
        from_phase = step_execution.phase

        # Update last_actor_id FIRST
        workflow.last_actor_id = actor
        workflow.updated_at = datetime.utcnow()

        # Increment state_version for optimistic concurrency (Contract §9.1, §11.3)
        await self._increment_state_version(workflow)

        # Update step execution
        step_execution.status = StepStatus.IN_PROGRESS
        step_execution.phase = StepPhase.STRUCTURING

        # Create message record with answers (content required by schema)
        message = Message(
            workflow_id=workflow.id,
            step_execution_id=step_execution.id,
            role=MessageRole.USER,
            content="Clarification response submitted",
            metadata_={"answers": answers},
        )
        self._session.add(message)

        # Create audit entry
        await self._create_audit_entry(
            workflow=workflow,
            step_execution=step_execution,
            event_type="clarification_submitted",
            actor_id=actor,
            from_status=from_status,
            to_status=StepStatus.IN_PROGRESS,
            from_phase=from_phase,
            to_phase=StepPhase.STRUCTURING,
            details={"answers": answers},
        )

        # Persist event to durable log (Fix 1: persist before publish, return for route)
        # Per V2.8.0 Spec: actor_id MUST be top-level for user-initiated events
        event = await self._persist_event(
            workflow=workflow,
            event_type="step.clarified",
            step_execution=step_execution,
            data={"state_version": workflow.state_version},
            actor_id=actor,
        )
        events.append(event)

        await self._session.flush()
        return workflow, step_execution, events

    # =========================================================================
    # P4.4: Graph State Synchronization
    # =========================================================================

    async def sync_db_from_state(
        self,
        workflow_id: str,
        result: dict,
        artifact_output: Optional[str] = None,
        actor_id: Optional[str] = None,
    ) -> list[WorkflowEvent]:
        """Sync DB state from graph execution result.

        Per Co-Developer-1 feedback:
        - Updates Workflow position fields + updated_at + status=completed
        - Ensures StepExecution row exists for current step
        - Updates all step_state fields (status, phase, started_at, etc.)
        - Only updates current step, not prior steps

        Per Fix 1 (Atomic Event Persistence): Persists native events and returns
        them for route to publish after transaction commits:
        - step.started when new step begins
        - step.awaiting_review when status changes to awaiting_review
        - workflow.completed when workflow finishes

        Returns:
            List of persisted events for route to publish after commit.
        """
        from domain.state import (
            ensure_workflow_state,
            StepStatus as DomainStepStatus,
            PassType as DomainPassType,
            StepName as DomainStepName,
        )
        from infrastructure.db.models import WorkflowStatus

        events: list[WorkflowEvent] = []

        workflow = await self._workflow_repo.get_by_workflow_id(workflow_id)
        if workflow is None:
            raise WorkflowNotFoundError(workflow_id)

        state = ensure_workflow_state(result)
        step_state = state.step_state

        # Capture state BEFORE changes for state-eligibility comparison (Contract §11.3)
        old_pass = workflow.current_pass
        old_step = workflow.current_step
        old_step_number = workflow.current_step_number

        # Get current step execution status/phase (if exists)
        old_step_execution = await self._step_repo.get_by_composite(
            workflow_id=workflow.id,
            pass_type=PassType(state.current_pass.value),
            step_name=StepName(state.current_step.value),
        )
        old_status = old_step_execution.status if old_step_execution else None
        old_phase = old_step_execution.phase if old_step_execution else None

        # Update workflow position
        workflow.current_pass = PassType(state.current_pass.value)
        workflow.current_step = StepName(state.current_step.value)
        workflow.current_step_number = step_state.step_number
        workflow.updated_at = datetime.utcnow()

        # Track if workflow completed
        workflow_completed = False

        # Check if workflow completed (Step 3 Pass 2 approved)
        if (
            state.current_pass == DomainPassType.EXECUTION
            and state.current_step == DomainStepName.OBJECTIVES
            and step_state.status == DomainStepStatus.APPROVED
        ):
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = datetime.utcnow()
            workflow_completed = True

        # Ensure StepExecution exists for current step
        step_execution = await self._step_repo.get_by_composite(
            workflow_id=workflow.id,
            pass_type=workflow.current_pass,
            step_name=workflow.current_step,
        )

        # Track if this is a new step (for step.started event)
        new_step_created = False

        if step_execution is None:
            # Create new step execution (advanced to new step)
            step_execution = StepExecution(
                workflow_id=workflow.id,
                pass_type=PassType(state.current_pass.value),
                step_name=StepName(state.current_step.value),
                step_number=step_state.step_number,
                status=StepStatus.NOT_STARTED,
                phase=StepPhase.RECEIVED,
            )
            self._session.add(step_execution)
            await self._session.flush()  # Get step_execution.id
            new_step_created = True

        # P6.6: Capture IN_PROGRESS transition for audit trail (Gate F)
        # If transitioning from NOT_STARTED to a later status, add intermediate
        # IN_PROGRESS state to ensure audit captures the full transition chain.
        final_status = StepStatus(step_state.status.value)
        if (
            step_execution.status == StepStatus.NOT_STARTED
            and final_status not in (StepStatus.NOT_STARTED, StepStatus.IN_PROGRESS)
        ):
            step_execution.status = StepStatus.IN_PROGRESS
            step_execution.phase = StepPhase.RECEIVED  # Initial phase (not analyzing yet)
            await self._session.flush()  # Trigger audit: NOT_STARTED -> IN_PROGRESS

        # Update step execution fields from graph state
        step_execution.status = final_status
        step_execution.phase = StepPhase(step_state.phase.value)

        if step_state.started_at:
            step_execution.started_at = step_state.started_at
        if step_state.completed_at:
            step_execution.completed_at = step_state.completed_at
        if step_state.human_feedback:
            step_execution.human_feedback = step_state.human_feedback
        if step_state.clarification_request:
            step_execution.clarification_request = [
                q.__dict__ for q in step_state.clarification_request
            ]
        if step_state.validation_result:
            step_execution.validation_status = (
                "passed" if step_state.validation_result.passed else "failed"
            )
            step_execution.validation_errors = step_state.validation_result.errors
            step_execution.validation_warnings = step_state.validation_result.warnings

        await self._session.flush()

        # P5.3: Sync artifacts from state (scan-based persistence)
        artifact_results = await self.sync_artifacts_from_state(
            workflow_db_id=workflow.id,
            workflow_external_id=workflow.workflow_id,
            instance_id=str(workflow.instance_id),
            state=state,
        )

        # Update latest_artifact_id for any newly persisted artifacts
        # Results are keyed by (pass_type, step_key) to avoid ambiguity
        for (result_pass_type, step_key), artifact_id in artifact_results.items():
            step_name_enum = StepName(step_key)

            step_exec = await self._step_repo.get_by_composite(
                workflow_id=workflow.id,
                pass_type=result_pass_type,
                step_name=step_name_enum,
            )
            if step_exec:
                step_exec.latest_artifact_id = artifact_id

        # Detect state-eligibility changes (Contract §11.3)
        # Increment state_version ONLY if something affecting action eligibility changed
        # This includes: position, status, phase, or new artifacts created
        new_status = step_execution.status
        new_phase = step_execution.phase

        state_eligibility_changed = (
            # Position changes
            old_pass != workflow.current_pass or
            old_step != workflow.current_step or
            old_step_number != workflow.current_step_number or
            # Status changes (EVEN without position change)
            (old_status is not None and old_status != new_status) or
            # Phase changes (EVEN without position change)
            (old_phase is not None and old_phase != new_phase) or
            # New step execution created (old_status was None)
            old_status is None or
            # New artifacts created
            len(artifact_results) > 0
        )

        if state_eligibility_changed:
            await self._increment_state_version(workflow)

        await self._session.flush()

        # Fix 1: Persist native events AFTER state is updated
        # These events are persisted in DB and returned for route to publish after commit
        # Order: step.started -> artifact.delta/final -> step.awaiting_review

        # step.started when:
        # - New step is created (advanced from previous step), OR
        # - Step transitions from NOT_STARTED to a running state (initial step start)
        step_started = (
            new_step_created or
            (old_status == StepStatus.NOT_STARTED and new_status != StepStatus.NOT_STARTED)
        )
        if step_started:
            event = await self._persist_event(
                workflow=workflow,
                event_type="step.started",
                step_execution=step_execution,
            )
            events.append(event)

        # Persist artifact events AFTER step.started but BEFORE step.awaiting_review
        # This ensures correct event ordering per Gate E expectations
        if artifact_output:
            # Split output into chunks for artifact.delta events
            chunks = _chunk_string(artifact_output, 3)
            for i, chunk in enumerate(chunks):
                delta_event = await self._persist_event(
                    workflow=workflow,
                    event_type="artifact.delta",
                    step_execution=step_execution,
                    data={"delta": chunk, "index": i},
                )
                events.append(delta_event)

            # artifact.final when output is complete
            final_event = await self._persist_event(
                workflow=workflow,
                event_type="artifact.final",
                step_execution=step_execution,
            )
            events.append(final_event)

        # step.awaiting_review when status changes to awaiting_review
        if (
            old_status != StepStatus.AWAITING_REVIEW
            and new_status == StepStatus.AWAITING_REVIEW
        ):
            event = await self._persist_event(
                workflow=workflow,
                event_type="step.awaiting_review",
                step_execution=step_execution,
            )
            events.append(event)

        # workflow.completed when workflow finishes
        if workflow_completed:
            event = await self._persist_event(
                workflow=workflow,
                event_type="workflow.completed",
                step_execution=step_execution,
            )
            events.append(event)

            # Create audit entry for workflow completion (Bug 1 fix + Round 4 refinements)
            # Event name uses dot notation per spec §9.2.1
            # Actor always resolved to ensure audit entry is written reliably
            resolved_actor = self._resolve_actor_id(actor_id, workflow)
            await self._create_audit_entry(
                workflow=workflow,
                step_execution=step_execution,
                event_type="workflow.completed",
                actor_id=resolved_actor,
                from_status=StepStatus.APPROVED,
                to_status=StepStatus.APPROVED,
                from_phase=StepPhase.COMPLETE,
                to_phase=StepPhase.COMPLETE,
                details={"workflow_status": "completed"},
            )

        await self._session.flush()
        return events

    async def sync_artifacts_from_state(
        self,
        workflow_db_id: UUID,
        workflow_external_id: str,
        instance_id: str,
        state: Any,
    ) -> dict[tuple[PassType, str], UUID]:
        """Scan state dictionaries and persist any missing artifacts.

        Scan-based persistence per plan:
        - Scans state.methodology for Pass 1 docs needing persistence
        - Scans state.artifacts for Pass 2 packages needing persistence
        - Idempotent: skips artifacts that already exist or haven't changed

        Args:
            workflow_db_id: Database workflow UUID.
            workflow_external_id: External workflow ID string.
            instance_id: Instance ID string.
            state: WorkflowState from graph execution.

        Returns:
            Dict mapping (pass_type, step_key) to latest artifact_id created/updated.
        """
        from domain.state import StepName as DomainStepName

        result: dict[tuple[PassType, str], UUID] = {}

        # Pass 1: Scan state.methodology for missing docs
        for step_key, methodology_output in state.methodology.items():
            step_name = DomainStepName(step_key)

            # Check if docs already persisted (idempotent)
            existing = await self._artifact_repo.list_methodology_docs(
                workflow_id=workflow_db_id,
                step_name=step_name,
            )

            # 12 docs per step (4 doc_types × 3 versions)
            if len(existing) < 12:
                logger.info(
                    f"Persisting methodology docs for {step_key} "
                    f"({len(existing)}/12 exist)"
                )
                artifacts = await self._artifact_service.store_methodology_docs(
                    workflow_id=workflow_db_id,
                    step_name=step_name,
                    methodology_output=methodology_output,
                )
                if artifacts:
                    # Return V3 detailed_procedure as latest
                    result[(PassType.DEFINITION, step_key)] = artifacts[-1].id

        # Pass 2: Scan state.artifacts for approved steps needing persistence
        for step_key, package_content in state.artifacts.items():
            step_name = DomainStepName(step_key)

            # Only persist if step is approved (check step_executions table)
            step_exec = await self._step_repo.get_by_composite(
                workflow_id=workflow_db_id,
                pass_type=PassType.EXECUTION,
                step_name=step_name,
            )

            if step_exec and step_exec.status == StepStatus.APPROVED:
                # Let store_step_package handle idempotency via content comparison
                # It will return existing artifact if content unchanged, or create
                # new revision if content changed (e.g., after modify action)
                logger.info(f"Syncing step package for {step_key}")
                try:
                    artifact = await self._artifact_service.store_step_package(
                        workflow_id=workflow_db_id,
                        instance_id=instance_id,
                        workflow_external_id=workflow_external_id,
                        step_name=step_name,
                        package_content=package_content,
                        validate=True,
                    )
                    result[(PassType.EXECUTION, step_key)] = artifact.id

                    # P5.4: Extract and persist traceability links
                    # Use artifact.content_jsonb which has injected metadata
                    await self._traceability_service.extract_and_persist_links(
                        workflow_id=workflow_db_id,
                        step_name=step_name,
                        package_content=artifact.content_jsonb,
                    )
                    logger.info(f"Extracted traceability links for {step_key}")

                except TraceabilityExtractionError as e:
                    logger.error(f"Traceability extraction failed for {step_key}: {e}")
                    raise  # Fail sync - Gate B requirement

                except Exception as e:
                    logger.error(
                        f"Failed to persist step package for {step_key}: {e}"
                    )
                    raise  # Don't silently continue

        return result
