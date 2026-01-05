"""
SOLVER API - Domain State Models

Pure domain models for workflow and step state per Doc 3 Section 8.1.
No external dependencies - standard library only.
"""

from enum import Enum
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime


# =============================================================================
# Enums
# =============================================================================


class PassType(str, Enum):
    """Pass type: definition (Pass 1) or execution (Pass 2)."""
    DEFINITION = "definition"
    EXECUTION = "execution"


class StepName(str, Enum):
    """The 10 workflow steps."""
    PROBLEM_DEFINITION = "problem_definition"
    REQUIREMENTS = "requirements"
    OBJECTIVES = "objectives"
    VERIFICATION_DESIGN = "verification_design"
    VALIDATION_DESIGN = "validation_design"
    EVALUATION_CRITERIA = "evaluation_criteria"
    ASSESSMENT_PROTOCOL = "assessment_protocol"
    IMPLEMENTATION = "implementation"
    REFLECTION = "reflection"
    RESOLUTION = "resolution"


class StepStatus(str, Enum):
    """Coarse-grained step status (external visibility)."""
    NOT_STARTED = "not_started"
    PENDING = "pending"  # Queued for (re-)execution per V2.8.0 spec
    IN_PROGRESS = "in_progress"
    AWAITING_CLARIFICATION = "awaiting_clarification"
    AWAITING_REVIEW = "awaiting_review"
    APPROVED = "approved"
    REVISION_REQUESTED = "revision_requested"


class StepPhase(str, Enum):
    """Fine-grained step phase (internal state)."""
    RECEIVED = "received"
    ANALYZING = "analyzing"
    ELICITING = "eliciting"
    STRUCTURING = "structuring"
    VALIDATING = "validating"
    REVIEWING = "reviewing"
    COMPLETE = "complete"


class HumanAction(str, Enum):
    """Human actions at gates."""
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"
    MESSAGE = "message"


class GatePolicy(str, Enum):
    """Pass 1 gate policy."""
    NONE = "none"
    PER_STEP = "per_step"
    END_OF_PASS = "end_of_pass"


# =============================================================================
# Step Number Mapping
# =============================================================================


STEP_NUMBERS: Dict[StepName, int] = {
    StepName.PROBLEM_DEFINITION: 1,
    StepName.REQUIREMENTS: 2,
    StepName.OBJECTIVES: 3,
    StepName.VERIFICATION_DESIGN: 4,
    StepName.VALIDATION_DESIGN: 5,
    StepName.EVALUATION_CRITERIA: 6,
    StepName.ASSESSMENT_PROTOCOL: 7,
    StepName.IMPLEMENTATION: 8,
    StepName.REFLECTION: 9,
    StepName.RESOLUTION: 10,
}


# =============================================================================
# Supporting Dataclasses
# =============================================================================


@dataclass
class ClarificationQuestion:
    """Question generated when input is insufficient."""
    question: str
    context: str
    impact_if_unresolved: str


@dataclass
class ValidationResult:
    """Result of validating step output."""
    passed: bool
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)


# =============================================================================
# State Dataclasses
# =============================================================================


@dataclass
class StepState:
    """Internal step state tracking."""
    step_name: StepName
    step_number: int
    pass_type: PassType
    status: StepStatus = StepStatus.NOT_STARTED
    phase: StepPhase = StepPhase.RECEIVED

    output: Optional[Dict[str, Any]] = None
    human_feedback: Optional[str] = None
    clarification_request: Optional[List[ClarificationQuestion]] = None
    clarification_response: Optional[Dict[str, str]] = None
    validation_result: Optional[ValidationResult] = None

    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class WorkflowState:
    """LangGraph state object."""
    workflow_id: str
    thread_id: str
    instance_id: str
    instance_number: int

    gate_policy: GatePolicy

    current_pass: PassType
    current_step: StepName

    original_problem: str
    domain: Optional[str] = None

    step_state: StepState = None

    methodology: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    artifacts: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    messages: List[Dict[str, Any]] = field(default_factory=list)

    human_decision: Optional[HumanAction] = None
    human_feedback: Optional[str] = None
    human_modifications: Optional[Dict[str, Any]] = None

    last_actor_id: str = "system"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


# =============================================================================
# State Reconstruction Helpers
# =============================================================================


def _parse_datetime(value: Any) -> Optional[datetime]:
    """Parse datetime from various formats."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        # ISO format
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


def ensure_validation_result(obj: Any) -> Optional[ValidationResult]:
    """Convert dict to ValidationResult if needed."""
    if obj is None:
        return None
    if isinstance(obj, ValidationResult):
        return obj
    if isinstance(obj, dict):
        return ValidationResult(
            passed=obj.get("passed", False),
            errors=obj.get("errors", []),
            warnings=obj.get("warnings", []),
        )
    return obj


def ensure_step_state(obj: Any) -> Optional[StepState]:
    """Convert dict to StepState if needed.

    Used when resuming from checkpoint where state is deserialized as dict.
    Also fixes string-typed enum/datetime fields when already a StepState.
    """
    if obj is None:
        return None
    if isinstance(obj, StepState):
        # Fix string-typed fields (LangGraph may create StepState with strings)
        if isinstance(obj.step_name, str):
            obj.step_name = StepName(obj.step_name)
        if isinstance(obj.pass_type, str):
            obj.pass_type = PassType(obj.pass_type)
        if isinstance(obj.status, str):
            obj.status = StepStatus(obj.status)
        if isinstance(obj.phase, str):
            obj.phase = StepPhase(obj.phase)
        if isinstance(obj.started_at, str):
            obj.started_at = _parse_datetime(obj.started_at)
        if isinstance(obj.completed_at, str):
            obj.completed_at = _parse_datetime(obj.completed_at)
        if obj.validation_result is not None and not isinstance(obj.validation_result, ValidationResult):
            obj.validation_result = ensure_validation_result(obj.validation_result)
        return obj
    if isinstance(obj, dict):
        # Reconstruct StepState from dict
        step_name = obj.get("step_name")
        if isinstance(step_name, str):
            step_name = StepName(step_name)

        pass_type = obj.get("pass_type")
        if isinstance(pass_type, str):
            pass_type = PassType(pass_type)

        status = obj.get("status", "not_started")
        if isinstance(status, str):
            status = StepStatus(status)

        phase = obj.get("phase", "received")
        if isinstance(phase, str):
            phase = StepPhase(phase)

        return StepState(
            step_name=step_name,
            step_number=obj.get("step_number", 1),
            pass_type=pass_type,
            status=status,
            phase=phase,
            output=obj.get("output"),
            human_feedback=obj.get("human_feedback"),
            clarification_request=obj.get("clarification_request"),
            clarification_response=obj.get("clarification_response"),
            validation_result=ensure_validation_result(obj.get("validation_result")),
            started_at=_parse_datetime(obj.get("started_at")),
            completed_at=_parse_datetime(obj.get("completed_at")),
        )
    return obj


def ensure_workflow_state(obj: Any) -> WorkflowState:
    """Convert dict to WorkflowState if needed.

    Used when resuming from checkpoint where state is deserialized as dict.
    Also fixes string-typed enum/datetime fields when already a WorkflowState.
    """
    if isinstance(obj, WorkflowState):
        # Fix string-typed fields (LangGraph may create WorkflowState with strings)
        if isinstance(obj.gate_policy, str):
            obj.gate_policy = GatePolicy(obj.gate_policy)
        if isinstance(obj.current_pass, str):
            obj.current_pass = PassType(obj.current_pass)
        if isinstance(obj.current_step, str):
            obj.current_step = StepName(obj.current_step)
        if obj.human_decision is not None and isinstance(obj.human_decision, str):
            obj.human_decision = HumanAction(obj.human_decision)
        if isinstance(obj.created_at, str):
            obj.created_at = _parse_datetime(obj.created_at)
        if isinstance(obj.updated_at, str):
            obj.updated_at = _parse_datetime(obj.updated_at)
        # Ensure nested step_state is also properly typed
        if obj.step_state is not None:
            obj.step_state = ensure_step_state(obj.step_state)
        return obj

    if isinstance(obj, dict):
        # Reconstruct WorkflowState from dict
        gate_policy = obj.get("gate_policy")
        if isinstance(gate_policy, str):
            gate_policy = GatePolicy(gate_policy)

        current_pass = obj.get("current_pass")
        if isinstance(current_pass, str):
            current_pass = PassType(current_pass)

        current_step = obj.get("current_step")
        if isinstance(current_step, str):
            current_step = StepName(current_step)

        human_decision = obj.get("human_decision")
        if isinstance(human_decision, str):
            human_decision = HumanAction(human_decision)

        return WorkflowState(
            workflow_id=obj.get("workflow_id", ""),
            thread_id=obj.get("thread_id", ""),
            instance_id=obj.get("instance_id", ""),
            instance_number=obj.get("instance_number", 0),
            gate_policy=gate_policy,
            current_pass=current_pass,
            current_step=current_step,
            original_problem=obj.get("original_problem", ""),
            domain=obj.get("domain"),
            step_state=ensure_step_state(obj.get("step_state")),
            methodology=obj.get("methodology", {}),
            artifacts=obj.get("artifacts", {}),
            messages=obj.get("messages", []),
            human_decision=human_decision,
            human_feedback=obj.get("human_feedback"),
            human_modifications=obj.get("human_modifications"),
            last_actor_id=obj.get("last_actor_id", "system"),
            created_at=_parse_datetime(obj.get("created_at")) or datetime.utcnow(),
            updated_at=_parse_datetime(obj.get("updated_at")) or datetime.utcnow(),
        )

    raise TypeError(f"Cannot convert {type(obj)} to WorkflowState")
