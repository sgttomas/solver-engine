"""
SOLVER API - Workflow Service

Use cases for workflow management.
P4.1: DB-only create/get/resume.
P4.2: DB-only action endpoints (approve/revise/message/clarify).
Graph integration deferred to P4.4.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import (
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
    """Raised when workflow is in invalid state for action."""

    def __init__(self, workflow_id: str, current_status: str, expected_status: str):
        self.workflow_id = workflow_id
        self.current_status = current_status
        self.expected_status = expected_status
        super().__init__(
            f"Workflow {workflow_id} is in {current_status}, expected {expected_status}"
        )


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

    async def create_workflow(
        self,
        problem: str,
        created_by: str,
        instance_number: int = 0,
        domain: Optional[str] = None,
    ) -> tuple[Workflow, StepExecution]:
        """Create a new workflow with initial step execution.

        Creates Workflow and initial StepExecution records in one transaction.
        Does NOT invoke graph (deferred to P4.4).

        Args:
            problem: The problem statement
            created_by: Actor ID creating the workflow
            instance_number: Instance number (default 0 = Universal Methodology)
            domain: Optional domain classification

        Returns:
            Tuple of (Workflow, StepExecution) for the created workflow

        Raises:
            InstanceNotFoundError: If instance_number doesn't exist
        """
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

        return workflow, step_execution

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
    ) -> tuple[Workflow, StepExecution]:
        """Approve current step.

        P4.2: DB-only (updates status to APPROVED).
        P4.4 will add graph invocation to advance workflow.

        Args:
            workflow_id: Unique workflow identifier
            actor_id: Actor performing action (defaults to workflow.created_by)

        Returns:
            Tuple of (Workflow, StepExecution)

        Raises:
            WorkflowNotFoundError: If workflow doesn't exist
            InvalidStateError: If step is not AWAITING_REVIEW
        """
        workflow, step_execution = await self._get_workflow_and_step(
            workflow_id, StepStatus.AWAITING_REVIEW
        )

        actor = self._resolve_actor_id(actor_id, workflow)

        # Capture before state for audit
        from_status = step_execution.status
        from_phase = step_execution.phase

        # Update last_actor_id FIRST (before status change for audit trigger)
        workflow.last_actor_id = actor
        workflow.updated_at = datetime.utcnow()

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

        await self._session.flush()
        return workflow, step_execution

    async def revise_step(
        self,
        workflow_id: str,
        feedback: str,
        actor_id: Optional[str] = None,
    ) -> tuple[Workflow, StepExecution]:
        """Request revision of current step.

        P4.2: DB-only (updates status to REVISION_REQUESTED).
        P4.4 will add graph invocation to re-run step.

        Args:
            workflow_id: Unique workflow identifier
            feedback: Revision feedback/instructions
            actor_id: Actor performing action (defaults to workflow.created_by)

        Returns:
            Tuple of (Workflow, StepExecution)

        Raises:
            WorkflowNotFoundError: If workflow doesn't exist
            InvalidStateError: If step is not AWAITING_REVIEW
        """
        workflow, step_execution = await self._get_workflow_and_step(
            workflow_id, StepStatus.AWAITING_REVIEW
        )

        actor = self._resolve_actor_id(actor_id, workflow)

        # Capture before state for audit
        from_status = step_execution.status
        from_phase = step_execution.phase

        # Update last_actor_id FIRST
        workflow.last_actor_id = actor
        workflow.updated_at = datetime.utcnow()

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

        await self._session.flush()
        return workflow, step_execution

    async def send_message(
        self,
        workflow_id: str,
        content: str,
        actor_id: Optional[str] = None,
    ) -> tuple[Workflow, StepExecution]:
        """Send message without changing workflow state.

        Gate C: Status remains AWAITING_REVIEW.
        Message is persisted for conversation history.

        Args:
            workflow_id: Unique workflow identifier
            content: Message content
            actor_id: Actor performing action (defaults to workflow.created_by)

        Returns:
            Tuple of (Workflow, StepExecution)

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
        return workflow, step_execution

    async def submit_clarification(
        self,
        workflow_id: str,
        answers: dict,
        actor_id: Optional[str] = None,
    ) -> tuple[Workflow, StepExecution]:
        """Submit clarification answers.

        P4.2: DB-only (updates status to IN_PROGRESS).
        P4.4 will add graph invocation to resume.

        Args:
            workflow_id: Unique workflow identifier
            answers: Clarification responses keyed by question ID
            actor_id: Actor performing action (defaults to workflow.created_by)

        Returns:
            Tuple of (Workflow, StepExecution)

        Raises:
            WorkflowNotFoundError: If workflow doesn't exist
            InvalidStateError: If step is not AWAITING_CLARIFICATION
        """
        workflow, step_execution = await self._get_workflow_and_step(
            workflow_id, StepStatus.AWAITING_CLARIFICATION
        )

        actor = self._resolve_actor_id(actor_id, workflow)

        # Capture before state for audit
        from_status = step_execution.status
        from_phase = step_execution.phase

        # Update last_actor_id FIRST
        workflow.last_actor_id = actor
        workflow.updated_at = datetime.utcnow()

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

        await self._session.flush()
        return workflow, step_execution

    # =========================================================================
    # P4.4: Graph State Synchronization
    # =========================================================================

    async def sync_db_from_state(self, workflow_id: str, result: dict) -> None:
        """Sync DB state from graph execution result.

        Per Co-Developer-1 feedback:
        - Updates Workflow position fields + updated_at + status=completed
        - Ensures StepExecution row exists for current step
        - Updates all step_state fields (status, phase, started_at, etc.)
        - Only updates current step, not prior steps
        """
        from domain.state import (
            ensure_workflow_state,
            StepStatus as DomainStepStatus,
            PassType as DomainPassType,
            StepName as DomainStepName,
        )
        from infrastructure.db.models import WorkflowStatus

        workflow = await self._workflow_repo.get_by_workflow_id(workflow_id)
        if workflow is None:
            raise WorkflowNotFoundError(workflow_id)

        state = ensure_workflow_state(result)
        step_state = state.step_state

        # Update workflow position
        workflow.current_pass = PassType(state.current_pass.value)
        workflow.current_step = StepName(state.current_step.value)
        workflow.current_step_number = step_state.step_number
        workflow.updated_at = datetime.utcnow()

        # Check if workflow completed (Step 3 Pass 2 approved)
        if (
            state.current_pass == DomainPassType.EXECUTION
            and state.current_step == DomainStepName.OBJECTIVES
            and step_state.status == DomainStepStatus.APPROVED
        ):
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = datetime.utcnow()

        # Ensure StepExecution exists for current step
        step_execution = await self._step_repo.get_by_composite(
            workflow_id=workflow.id,
            pass_type=workflow.current_pass,
            step_name=workflow.current_step,
        )

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

        # Update step execution fields from graph state
        step_execution.status = StepStatus(step_state.status.value)
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
