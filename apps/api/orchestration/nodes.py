"""
SOLVER API - LangGraph Node Implementations

Node implementations per Doc 3 Section 8.4.
Deviation: human_decision clearing moved from process_decision_node to
branch-specific nodes (see docs/spec/DECISIONS.md P3.3).
"""

import logging
from datetime import datetime
from typing import Any

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
from infrastructure.llm import get_default_adapter, LLMAdapter, LLMError
from orchestration.prompts import (
    get_prompt,
    get_execution_prompt,
    build_context,
    parse_json_output,
    get_required_keys,
    prev_version,
    DOC_TYPES,
    JSONParseError,
)


logger = logging.getLogger(__name__)


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
# LLM Generation Functions
# =============================================================================


async def check_sufficiency(state: WorkflowState) -> bool:
    """Check if input is sufficient or needs clarification.

    Policy:
    - Pass 1: Always False (autonomous methodology generation).
    - Steps 2-3 Pass 2: Always False (have prior step output as input).
    - Step 1 Pass 2: Could check problem statement sufficiency, but
      for MVP returns False (no clarification workflow yet).

    Returns:
        True if clarification is needed, False otherwise.
    """
    # Pass 1 is fully autonomous
    if state.current_pass == PassType.DEFINITION:
        return False

    # Steps 2-3 have prior step output - no clarification needed
    if state.current_step != StepName.PROBLEM_DEFINITION:
        return False

    # Step 1 Pass 2: MVP returns False
    # Future: could use LLM to check if problem statement needs clarification
    return False


async def generate_step_output(state: WorkflowState) -> dict[str, Any]:
    """Generate step output using LLM.

    Pass 1 (DEFINITION): Generates 12 methodology documents in V1→V2→V3 sequence.
    Pass 2 (EXECUTION): Executes V3 methodology to produce step package as JSON.

    Returns:
        Pass 1: {"v1": {...}, "v2": {...}, "v3": {...}} methodology dict.
        Pass 2: Content-only dict conforming to Doc 3 schema (no metadata fields).
            Example for Step 1: {"title": "...", "canonical_problem_definition": {...},
                "stakeholders": [...], "constraints": {...}, "scope": {...}, ...}
            Metadata fields (package_id, workflow_id, created_at) are injected
            by the persistence layer in P5.3.

    Raises:
        LLMError: If LLM calls fail.
        JSONParseError: If Pass 2 JSON parsing fails.
    """
    adapter = get_default_adapter()

    if state.current_pass == PassType.DEFINITION:
        return await _generate_methodology(state, adapter)
    else:
        return await _execute_methodology(state, adapter)


async def _generate_methodology(
    state: WorkflowState,
    adapter: LLMAdapter,
) -> dict[str, dict[str, str]]:
    """Generate 12 methodology documents in V1→V2→V3 sequence.

    Each version builds on prior versions:
    - V1: Starts from seed problem
    - V2: Considers V1 documents
    - V3: Considers V2 documents

    Returns:
        {"v1": {"data_sheet": "...", "todo_list": "...", ...},
         "v2": {...},
         "v3": {...}}
    """
    results: dict[str, dict[str, str]] = {"v1": {}, "v2": {}, "v3": {}}

    for version in ["v1", "v2", "v3"]:
        # Get prior version docs (empty for v1)
        prior_ver = prev_version(version)
        prior_version_docs = results.get(prior_ver, {}) if prior_ver else {}

        for doc_type in DOC_TYPES:
            # Build context with prior and current version docs
            context = build_context(
                state=state,
                prior_version_docs=prior_version_docs,
                current_version_docs=results[version],
                version=version,
                doc_type=doc_type,
            )

            # Get and format prompt
            prompt = get_prompt(state.current_step, version, doc_type)
            messages = [
                {"role": "system", "content": prompt["system"].format(**context)},
                {"role": "user", "content": prompt["user"].format(**context)},
            ]

            logger.debug(
                "Generating %s %s %s",
                state.current_step.value,
                version,
                doc_type,
            )

            try:
                response = await adapter.generate(messages)
                results[version][doc_type] = response.content
            except LLMError as e:
                logger.error(
                    "LLM error generating %s %s %s: %s",
                    state.current_step.value,
                    version,
                    doc_type,
                    str(e),
                )
                raise

    return results


async def _execute_methodology(
    state: WorkflowState,
    adapter: LLMAdapter,
) -> dict[str, Any]:
    """Execute V3 methodology to produce step package as JSON.

    Uses the V3 methodology from Pass 1 to generate the step output.

    Returns:
        Step package dict conforming to Doc 3 schema.

    Raises:
        JSONParseError: If response cannot be parsed as JSON.
    """
    # Build context with V3 methodology
    context = build_context(
        state=state,
        prior_version_docs={},
        current_version_docs={},
    )

    # Get and format execution prompt
    prompt = get_execution_prompt(state.current_step)
    messages = [
        {"role": "system", "content": prompt["system"].format(**context)},
        {"role": "user", "content": prompt["user"].format(**context)},
    ]

    logger.debug(
        "Executing %s Pass 2",
        state.current_step.value,
    )

    try:
        response = await adapter.generate(messages)
    except LLMError as e:
        logger.error(
            "LLM error executing %s: %s",
            state.current_step.value,
            str(e),
        )
        raise

    # Parse JSON output
    try:
        return parse_json_output(response.content)
    except JSONParseError as e:
        logger.error(
            "JSON parse error for %s: %s",
            state.current_step.value,
            str(e),
        )
        raise


async def validate_output(
    step: StepName,
    output: dict,
    pass_type: PassType | None = None,
) -> ValidationResult:
    """Validate step output against schema.

    Pass 1: Basic structural validation (required keys exist).
    Pass 2: Full JSON schema validation with temporary metadata injection.

    Args:
        step: Step name for schema lookup.
        output: Step output dict to validate.
        pass_type: Pass type (DEFINITION or EXECUTION). If None, uses basic validation.

    Returns:
        ValidationResult with passed=True/False and errors list.
    """
    if output is None:
        return ValidationResult(
            passed=False,
            errors=[{"message": "Output is None"}],
        )

    # Pass 1 (DEFINITION): Validate methodology structure (v1, v2, v3 keys)
    if pass_type == PassType.DEFINITION:
        methodology_keys = ["v1", "v2", "v3"]
        missing_keys = [k for k in methodology_keys if k not in output]

        if missing_keys:
            return ValidationResult(
                passed=False,
                errors=[{"message": f"Missing methodology versions: {', '.join(missing_keys)}"}],
            )
        return ValidationResult(passed=True)

    # No pass_type specified: Basic key validation (legacy behavior)
    if pass_type is None:
        required_keys = get_required_keys(step)
        missing_keys = [k for k in required_keys if k not in output]

        if missing_keys:
            return ValidationResult(
                passed=False,
                errors=[{"message": f"Missing required keys: {', '.join(missing_keys)}"}],
            )
        return ValidationResult(passed=True)

    # Pass 2 (EXECUTION): Full JSON schema validation
    from application.artifact_service import ArtifactService

    # Create a temporary service instance for validation only (no DB needed)
    service = ArtifactService.__new__(ArtifactService)
    errors = service.validate_package_content(step, output)

    if errors:
        return ValidationResult(
            passed=False,
            errors=errors,
        )

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

    # Validate output - P5.3: Full schema validation for Pass 2
    result = await validate_output(
        step=state.current_step,
        output=state.step_state.output,
        pass_type=state.current_pass,
    )
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

    # Check if workflow complete (Step 3 Pass 2 approved)
    workflow_complete = (
        current_num == 3
        and state.current_pass == PassType.EXECUTION
    )

    if workflow_complete:
        # Keep step_state as-is with APPROVED status for is_workflow_complete check
        # Don't reset - this signals workflow completion to the graph
        pass
    elif current_num < 3:
        # Advance to next step within same pass
        next_step = [k for k, v in STEP_NUMBERS.items() if v == current_num + 1][0]
        state.current_step = next_step
        # Reset step state for new step
        state.step_state = StepState(
            step_name=state.current_step,
            step_number=STEP_NUMBERS[state.current_step],
            pass_type=state.current_pass,
        )
    else:
        # End of Pass 1 Step 3 → Pass 2 Step 1
        state.current_pass = PassType.EXECUTION
        state.current_step = StepName.PROBLEM_DEFINITION
        # Reset step state for new step
        state.step_state = StepState(
            step_name=state.current_step,
            step_number=STEP_NUMBERS[state.current_step],
            pass_type=state.current_pass,
        )

    state.updated_at = datetime.utcnow()
    return state
