"""
SOLVER API - LangGraph Node Implementations

Node implementations per Doc 3 Section 8.4.
Deviation: human_decision clearing moved from process_decision_node to
branch-specific nodes (see docs/DECISIONS.md P3.3).
"""

from datetime import datetime

from langgraph.types import interrupt

from domain.state import (
    WorkflowState,
    StepState,
    StepPhase,
    StepStatus,
    PassType,
    StepName,
    HumanAction,
    GatePolicy,
    ValidationResult,
    STEP_NUMBERS,
    ensure_workflow_state,
)


# =============================================================================
# Helper Functions
# =============================================================================


def coerce_state(state: WorkflowState) -> WorkflowState:
    """Coerce state to proper WorkflowState with correct types.

    LangGraph may restore state from checkpoint as dict or as WorkflowState
    with string-typed enum/datetime fields. This normalizes to proper types.
    """
    return ensure_workflow_state(state)


def _clear_human_decision(state: WorkflowState) -> None:
    """Clear human decision fields after routing completes.

    Called in advance_node (approve), structure_node (reject),
    and validate_node (modify) per DECISIONS.md P3.3 deviation.
    """
    state.human_decision = None
    state.human_feedback = None
    state.human_modifications = None


# =============================================================================
# Stub Functions (P5 scope - LLM integration)
# =============================================================================


async def check_sufficiency(state: WorkflowState) -> bool:
    """Check if input is sufficient or needs clarification.

    Stub: Returns False (no clarification needed) for MVP.
    P5 will implement LLM-based sufficiency check.

    Returns:
        True if clarification is needed, False otherwise.
    """
    return False


async def generate_step_output(state: WorkflowState) -> dict:
    """Generate step output using LLM.

    Stub: Returns placeholder output for MVP.
    P5 will implement LLM-based generation.

    Returns:
        Step output dictionary.
    """
    return {
        "placeholder": True,
        "step": state.current_step.value,
        "pass": state.current_pass.value,
    }


async def validate_output(step: StepName, output: dict) -> ValidationResult:
    """Validate step output against schema.

    Stub: Always passes for MVP.
    P5 will implement schema validation.

    Returns:
        ValidationResult with passed=True.
    """
    return ValidationResult(passed=True)


# =============================================================================
# Node Implementations
# =============================================================================


async def receive_node(state: WorkflowState) -> WorkflowState:
    """Initialize step execution.

    Sets phase to RECEIVED, status to IN_PROGRESS, and records start time.
    """
    state = coerce_state(state)
    state.step_state.phase = StepPhase.RECEIVED
    state.step_state.status = StepStatus.IN_PROGRESS
    state.step_state.started_at = datetime.utcnow()
    state.updated_at = datetime.utcnow()
    return state


async def analyze_node(state: WorkflowState) -> WorkflowState:
    """Analyze input and check sufficiency.

    Determines if clarification is needed before structuring.
    """
    state = coerce_state(state)
    state.step_state.phase = StepPhase.ANALYZING

    needs_clarification = await check_sufficiency(state)

    if needs_clarification:
        state.step_state.phase = StepPhase.ELICITING
        state.step_state.status = StepStatus.AWAITING_CLARIFICATION
    else:
        state.step_state.phase = StepPhase.STRUCTURING

    state.updated_at = datetime.utcnow()
    return state


async def elicit_node(state: WorkflowState) -> WorkflowState:
    """Raise interrupt for clarification.

    Pauses execution until clarification is provided.
    """
    state = coerce_state(state)
    interrupt({
        "gate_type": "clarification",
        "questions": [q.__dict__ for q in (state.step_state.clarification_request or [])],
        "step_name": state.current_step.value,
        "pass_type": state.current_pass.value,
    })

    # Resumed after clarification received
    state.step_state.phase = StepPhase.STRUCTURING
    state.step_state.status = StepStatus.IN_PROGRESS
    state.updated_at = datetime.utcnow()
    return state


async def structure_node(state: WorkflowState) -> WorkflowState:
    """Generate step output.

    Clears stale human_decision (reject path), generates output,
    and transitions to validation.
    """
    state = coerce_state(state)
    # Clear human_decision if present (handles reject branch re-entry)
    if state.human_decision is not None:
        _clear_human_decision(state)

    state.step_state.phase = StepPhase.STRUCTURING
    state.step_state.status = StepStatus.IN_PROGRESS

    # Generate output (stub for P5)
    output = await generate_step_output(state)
    state.step_state.output = output

    state.step_state.phase = StepPhase.VALIDATING
    state.updated_at = datetime.utcnow()
    return state


async def validate_node(state: WorkflowState) -> WorkflowState:
    """Validate output against rules.

    Clears stale human_decision (modify path), validates output,
    and transitions to review if passed.
    """
    state = coerce_state(state)
    # Clear human_decision if present (handles modify branch re-entry)
    if state.human_decision is not None:
        _clear_human_decision(state)

    state.step_state.phase = StepPhase.VALIDATING
    state.step_state.status = StepStatus.IN_PROGRESS

    # Validate output (stub for P5)
    result = await validate_output(state.current_step, state.step_state.output)
    state.step_state.validation_result = result

    if result.passed:
        state.step_state.phase = StepPhase.REVIEWING
        state.step_state.status = StepStatus.AWAITING_REVIEW
    else:
        state.step_state.phase = StepPhase.STRUCTURING

    state.updated_at = datetime.utcnow()
    return state


async def review_node(state: WorkflowState) -> WorkflowState:
    """Raise interrupt for human review.

    Gate policy enforcement:
    - Pass 1 + NONE: auto-approve
    - Pass 1 + END_OF_PASS + step < 10: auto-approve
    - Pass 2: always requires human approval
    """
    state = coerce_state(state)
    # Gate policy enforcement (Pass 1 only)
    if state.current_pass == PassType.DEFINITION:
        if state.gate_policy == GatePolicy.NONE:
            state.human_decision = HumanAction.APPROVE
            return state
        elif state.gate_policy == GatePolicy.END_OF_PASS:
            step_num = STEP_NUMBERS[state.current_step]
            if step_num < 10:
                state.human_decision = HumanAction.APPROVE
                return state

    # Pass 2 always requires human approval, or Pass 1 with PER_STEP policy
    interrupt({
        "gate_type": "review",
        "output": state.step_state.output,
        "validation": state.step_state.validation_result.__dict__ if state.step_state.validation_result else None,
        "step_name": state.current_step.value,
        "pass_type": state.current_pass.value,
    })

    return state


async def process_decision_node(state: WorkflowState) -> WorkflowState:
    """Process human decision.

    Updates state based on human action. Does NOT clear human_decision
    (routing depends on it; cleared in target nodes per DECISIONS.md P3.3).
    """
    state = coerce_state(state)
    if state.human_decision == HumanAction.APPROVE:
        state.step_state.status = StepStatus.APPROVED
        state.step_state.phase = StepPhase.COMPLETE
        state.step_state.completed_at = datetime.utcnow()

    elif state.human_decision == HumanAction.REJECT:
        state.step_state.status = StepStatus.REVISION_REQUESTED
        state.step_state.human_feedback = state.human_feedback
        state.step_state.phase = StepPhase.STRUCTURING

    elif state.human_decision == HumanAction.MODIFY:
        # Guard against None output
        if state.step_state.output is not None and state.human_modifications:
            state.step_state.output.update(state.human_modifications)
        state.step_state.phase = StepPhase.VALIDATING

    state.updated_at = datetime.utcnow()
    return state


async def advance_node(state: WorkflowState) -> WorkflowState:
    """Advance to next step.

    Clears human_decision (approve path), stores artifact,
    and transitions to next step.
    """
    state = coerce_state(state)
    # Clear human_decision (approve path cleanup)
    _clear_human_decision(state)

    # Store artifact
    step_key = state.current_step.value
    if state.current_pass == PassType.DEFINITION:
        state.methodology[step_key] = state.step_state.output
    else:
        state.artifacts[step_key] = state.step_state.output

    # Determine next position (MVP: Steps 1-3 only)
    current_num = STEP_NUMBERS[state.current_step]

    if current_num < 3:
        # Advance to next step within same pass
        next_step = [k for k, v in STEP_NUMBERS.items() if v == current_num + 1][0]
        state.current_step = next_step
    elif state.current_pass == PassType.DEFINITION:
        # End of Pass 1 Step 3 → Pass 2 Step 1
        state.current_pass = PassType.EXECUTION
        state.current_step = StepName.PROBLEM_DEFINITION
    # else: workflow complete (handled by graph edge)

    # Reset step state for new step
    state.step_state = StepState(
        step_name=state.current_step,
        step_number=STEP_NUMBERS[state.current_step],
        pass_type=state.current_pass,
    )

    state.updated_at = datetime.utcnow()
    return state
