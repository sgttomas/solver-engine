"""
SOLVER API - Prompt Templates

Entry points for methodology generation (Pass 1) and execution (Pass 2) prompts.
"""

from typing import Any

from domain.state import StepName

from . import step_1, step_2, step_3
from .common import (
    build_context,
    parse_json_output,
    considering_header,
    get_considering_refs,
    get_required_keys,
    prev_step,
    prev_version,
    DOC_TYPES,
    DOC_TYPE_NAMES,
    JSONParseError,
)


__all__ = [
    # Main API
    "get_prompt",
    "get_execution_prompt",
    "format_prompt",
    # Helpers
    "build_context",
    "parse_json_output",
    "considering_header",
    "get_considering_refs",
    "get_required_keys",
    "prev_step",
    "prev_version",
    # Constants
    "DOC_TYPES",
    "DOC_TYPE_NAMES",
    # Exceptions
    "JSONParseError",
]


# =============================================================================
# Step Module Routing
# =============================================================================


_STEP_MODULES = {
    StepName.PROBLEM_DEFINITION: step_1,
    StepName.REQUIREMENTS: step_2,
    StepName.OBJECTIVES: step_3,
}


def get_prompt(step: StepName, version: str, doc_type: str) -> dict[str, str]:
    """Get Pass 1 methodology prompt for a specific step, version, and document type.

    Args:
        step: Step name (PROBLEM_DEFINITION, REQUIREMENTS, OBJECTIVES).
        version: Version (v1, v2, v3).
        doc_type: Document type (data_sheet, todo_list, guidance, detailed_procedure).

    Returns:
        Dict with 'system' and 'user' prompt templates.

    Raises:
        KeyError: If step, version, or doc_type is invalid.
    """
    module = _STEP_MODULES.get(step)
    if module is None:
        raise KeyError(f"Unknown step: {step}")

    prompts = module.PROMPTS.get(version)
    if prompts is None:
        raise KeyError(f"Unknown version: {version}")

    prompt = prompts.get(doc_type)
    if prompt is None:
        raise KeyError(f"Unknown doc_type: {doc_type}")

    return prompt


def get_execution_prompt(step: StepName) -> dict[str, str]:
    """Get Pass 2 execution prompt for a specific step.

    Args:
        step: Step name (PROBLEM_DEFINITION, REQUIREMENTS, OBJECTIVES).

    Returns:
        Dict with 'system' and 'user' prompt templates.

    Raises:
        KeyError: If step is invalid.
    """
    module = _STEP_MODULES.get(step)
    if module is None:
        raise KeyError(f"Unknown step: {step}")

    return module.PASS_2_EXECUTION_PROMPT


def format_prompt(
    step: StepName,
    version: str,
    doc_type: str,
    context: dict[str, Any],
) -> dict[str, str]:
    """Get and format a Pass 1 methodology prompt with context.

    Convenience function combining get_prompt() with .format().

    Args:
        step: Step name.
        version: Version (v1, v2, v3).
        doc_type: Document type.
        context: Context dict for formatting (from build_context()).

    Returns:
        Dict with formatted 'system' and 'user' prompts.
    """
    prompt = get_prompt(step, version, doc_type)
    return {
        "system": prompt["system"].format(**context),
        "user": prompt["user"].format(**context),
    }


def format_execution_prompt(
    step: StepName,
    context: dict[str, Any],
) -> dict[str, str]:
    """Get and format a Pass 2 execution prompt with context.

    Convenience function combining get_execution_prompt() with .format().

    Args:
        step: Step name.
        context: Context dict for formatting (from build_context()).

    Returns:
        Dict with formatted 'system' and 'user' prompts.
    """
    prompt = get_execution_prompt(step)
    return {
        "system": prompt["system"].format(**context),
        "user": prompt["user"].format(**context),
    }
