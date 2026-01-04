"""
SOLVER API - Prompt Helpers

Shared utilities for prompt building and response parsing.
"""

import json
import re
from typing import Any

from domain.state import WorkflowState, StepName, PassType


# =============================================================================
# Step Ordering
# =============================================================================


STEP_ORDER = [
    StepName.PROBLEM_DEFINITION,
    StepName.REQUIREMENTS,
    StepName.OBJECTIVES,
]


def prev_step(step: StepName) -> StepName | None:
    """Get the previous step in the workflow.

    Args:
        step: Current step name.

    Returns:
        Previous step name, or None if at first step.
    """
    try:
        idx = STEP_ORDER.index(step)
        return STEP_ORDER[idx - 1] if idx > 0 else None
    except ValueError:
        return None


def prev_version(version: str) -> str | None:
    """Get the previous version in V1→V2→V3 sequence.

    Args:
        version: Current version (v1, v2, v3).

    Returns:
        Previous version, or None if at v1.
    """
    versions = ["v1", "v2", "v3"]
    try:
        idx = versions.index(version)
        return versions[idx - 1] if idx > 0 else None
    except ValueError:
        return None


# =============================================================================
# Document Type Constants
# =============================================================================


DOC_TYPES = ["data_sheet", "todo_list", "guidance", "detailed_procedure"]

DOC_TYPE_NAMES = {
    "data_sheet": "Data Sheet",
    "todo_list": "To Do List",
    "guidance": "Guidance Document",
    "detailed_procedure": "Detailed Procedure",
}


# =============================================================================
# Context Building
# =============================================================================


def build_context(
    state: WorkflowState,
    prior_version_docs: dict[str, str],
    current_version_docs: dict[str, str],
    version: str | None = None,
    doc_type: str | None = None,
) -> dict[str, Any]:
    """Build context dict for prompt formatting.

    Args:
        state: Current workflow state.
        prior_version_docs: Documents from prior version (e.g., v1 docs when building v2).
        current_version_docs: Documents from current version built so far.
        version: Version being generated (v1, v2, v3) for considering header.
        doc_type: Document type being generated for considering header.

    Returns:
        Context dict with all available information for prompt formatting.
    """
    # Get prior step output if exists
    prior_step_name = prev_step(state.current_step)
    prior_step_output = None
    if prior_step_name and state.current_pass == PassType.EXECUTION:
        prior_step_output = state.artifacts.get(prior_step_name.value)

    # Get V3 methodology for Pass 2 execution
    v3_methodology = None
    if state.current_pass == PassType.EXECUTION:
        step_methodology = state.methodology.get(state.current_step.value, {})
        if isinstance(step_methodology, dict):
            v3_methodology = step_methodology.get("v3", {})

    # Build considering header if version and doc_type provided
    considering = ""
    if version and doc_type:
        refs = get_considering_refs(version, doc_type)
        considering = considering_header(refs)

    # Build clarification section for execution prompts
    clarification_section = ""
    if state.step_state and state.step_state.clarification_response:
        clarification_section = f"""## Clarifications Received
{state.step_state.clarification_response}
"""

    # Build feedback section for revision prompts
    feedback_section = ""
    if state.step_state and state.step_state.human_feedback:
        feedback_section = f"""## Revision Feedback
{state.step_state.human_feedback}
"""

    return {
        # Workflow context
        "instance_number": state.instance_number,
        "step_name": state.current_step.value,
        "step_number": _step_number(state.current_step),
        "pass_type": state.current_pass.value,

        # Problem input
        "original_problem": state.original_problem,
        "domain": state.domain or "Universal (Domain-Agnostic)",

        # Prior step (for Steps 2-3)
        "prior_step_output": prior_step_output,
        "prior_step_name": prior_step_name.value if prior_step_name else None,

        # Prior version docs (for V2, V3 iterations)
        "prior_data_sheet": prior_version_docs.get("data_sheet", ""),
        "prior_todo_list": prior_version_docs.get("todo_list", ""),
        "prior_guidance": prior_version_docs.get("guidance", ""),
        "prior_detailed_procedure": prior_version_docs.get("detailed_procedure", ""),

        # Current version docs built so far
        "current_data_sheet": current_version_docs.get("data_sheet", ""),
        "current_todo_list": current_version_docs.get("todo_list", ""),
        "current_guidance": current_version_docs.get("guidance", ""),
        "current_detailed_procedure": current_version_docs.get("detailed_procedure", ""),

        # V3 methodology for Pass 2
        "v3_methodology": v3_methodology,
        "v3_data_sheet": v3_methodology.get("data_sheet", "") if v3_methodology else "",
        "v3_todo_list": v3_methodology.get("todo_list", "") if v3_methodology else "",
        "v3_guidance": v3_methodology.get("guidance", "") if v3_methodology else "",
        "v3_detailed_procedure": v3_methodology.get("detailed_procedure", "") if v3_methodology else "",

        # Human feedback (for revisions)
        "human_feedback": state.step_state.human_feedback if state.step_state else None,

        # Clarification responses
        "clarification_response": (
            state.step_state.clarification_response if state.step_state else None
        ),

        # Prompt-specific fields
        "considering": considering,
        "clarification_section": clarification_section,
        "feedback_section": feedback_section,
    }


def _step_number(step: StepName) -> int:
    """Get step number from step name."""
    step_numbers = {
        StepName.PROBLEM_DEFINITION: 1,
        StepName.REQUIREMENTS: 2,
        StepName.OBJECTIVES: 3,
    }
    return step_numbers.get(step, 0)


# =============================================================================
# Considering Header
# =============================================================================


def considering_header(references: list[str]) -> str:
    """Generate 'Considering: X + Y + Z' header line.

    Args:
        references: List of document references (e.g., ["Data Sheet V1", "To Do List V1"]).

    Returns:
        Formatted considering header.
    """
    if not references:
        return ""
    return f"Considering: {' + '.join(references)}"


def get_considering_refs(version: str, doc_type: str) -> list[str]:
    """Get the documents to consider for a given version and doc type.

    Based on the V1→V2→V3 iteration pattern from Doc 1.

    Args:
        version: Current version (v1, v2, v3).
        doc_type: Document type being generated.

    Returns:
        List of document references to consider.
    """
    # V1 considers: seed or prior docs in V1
    if version == "v1":
        if doc_type == "data_sheet":
            return ["Seed Problem"]
        elif doc_type == "todo_list":
            return ["Data Sheet V1"]
        elif doc_type == "guidance":
            return ["Seed Problem", "Data Sheet V1", "To Do List V1"]
        elif doc_type == "detailed_procedure":
            return ["Data Sheet V1", "To Do List V1", "Guidance Document V1"]

    # V2 considers: full V1 set + prior docs in V2
    elif version == "v2":
        if doc_type == "data_sheet":
            return ["Detailed Procedure V1", "Guidance Document V1", "To Do List V1"]
        elif doc_type == "todo_list":
            return ["Data Sheet V2", "Guidance Document V1", "Detailed Procedure V1"]
        elif doc_type == "guidance":
            return ["Data Sheet V2", "To Do List V2", "Detailed Procedure V1"]
        elif doc_type == "detailed_procedure":
            return ["Data Sheet V2", "To Do List V2", "Guidance Document V2"]

    # V3 considers: full V2 set + prior docs in V3
    elif version == "v3":
        if doc_type == "data_sheet":
            return ["Detailed Procedure V2", "Guidance Document V2", "To Do List V2"]
        elif doc_type == "todo_list":
            return ["Data Sheet V3", "Guidance Document V2", "Detailed Procedure V2"]
        elif doc_type == "guidance":
            return ["Data Sheet V3", "To Do List V3", "Detailed Procedure V2"]
        elif doc_type == "detailed_procedure":
            return ["Data Sheet V3", "To Do List V3", "Guidance Document V3"]

    return []


# =============================================================================
# JSON Parsing
# =============================================================================


class JSONParseError(Exception):
    """Error parsing JSON from LLM response."""

    def __init__(self, message: str, raw_content: str):
        super().__init__(message)
        self.raw_content = raw_content


def parse_json_output(content: str) -> dict:
    """Parse JSON from LLM response with basic error handling.

    Handles common LLM output patterns:
    - Markdown code fences (```json ... ```)
    - Leading/trailing whitespace
    - Multiple JSON blocks (takes first valid one)

    Args:
        content: Raw LLM response content.

    Returns:
        Parsed JSON as dict.

    Raises:
        JSONParseError: If no valid JSON can be extracted.
    """
    if not content or not content.strip():
        raise JSONParseError("Empty response content", content or "")

    # Try direct parse first
    try:
        return json.loads(content.strip())
    except json.JSONDecodeError:
        pass

    # Strip markdown code fences
    cleaned = _strip_code_fences(content)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object in content
    json_match = re.search(r'\{[\s\S]*\}', content)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    raise JSONParseError(
        f"Could not parse JSON from response. Content starts with: {content[:100]}...",
        content,
    )


def _strip_code_fences(content: str) -> str:
    """Strip markdown code fences from content.

    Handles:
    - ```json ... ```
    - ``` ... ```
    - ```yaml ... ``` (sometimes LLMs use yaml for JSON)
    """
    # Pattern: ```[language]\n content \n```
    pattern = r'```(?:json|yaml|JSON|YAML)?\s*\n?([\s\S]*?)\n?```'
    match = re.search(pattern, content)
    if match:
        return match.group(1).strip()
    return content.strip()


# =============================================================================
# Package Field Constants (Doc 3 Aligned)
# =============================================================================


# Metadata fields injected by persistence layer (P5.3), not LLM
INJECTED_METADATA_FIELDS = [
    "package_id",
    "workflow_id",
    "instance_id",
    "step_number",
    "version",
    "created_at",
]


# Required top-level keys for basic validation (P5.2 scope)
STEP_1_REQUIRED_KEYS = [
    "title",
    "canonical_problem_definition",
    "stakeholders",
    "constraints",
    "scope",
    "success_criteria",
]

STEP_2_REQUIRED_KEYS = [
    "overview",
    "requirements",
    "coverage_map",
]

STEP_3_REQUIRED_KEYS = [
    "overview",
    "objectives",
    "success_framework",
    "trace_map",
]


def get_required_keys(step: StepName) -> list[str]:
    """Get required top-level keys for a step's package.

    Used for basic structural validation in P5.2.
    Full schema validation deferred to P5.3.
    """
    if step == StepName.PROBLEM_DEFINITION:
        return STEP_1_REQUIRED_KEYS
    elif step == StepName.REQUIREMENTS:
        return STEP_2_REQUIRED_KEYS
    elif step == StepName.OBJECTIVES:
        return STEP_3_REQUIRED_KEYS
    return []
