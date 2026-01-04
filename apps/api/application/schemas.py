"""
SOLVER API - JSON Schema Loader

Loads and provides access to artifact schemas per Doc 3 §5.1-5.3.
"""

import json
from pathlib import Path
from typing import Any

from domain.state import StepName


# Schema directory relative to this file
# apps/api/application/schemas.py -> packages/contracts/
SCHEMA_DIR = Path(__file__).parent.parent.parent.parent / "packages" / "contracts"


def _load_schema(filename: str) -> dict[str, Any]:
    """Load a JSON schema from the contracts directory.

    Args:
        filename: Schema filename (e.g., "problem_definition.schema.json").

    Returns:
        Parsed schema as dict.

    Raises:
        FileNotFoundError: If schema file doesn't exist.
        json.JSONDecodeError: If schema is not valid JSON.
    """
    path = SCHEMA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Schema not found: {path}. "
            f"Ensure packages/contracts/ contains schemas per Doc 3."
        )
    with open(path) as f:
        return json.load(f)


# Load schemas at module import time for fast access
PROBLEM_DEFINITION_SCHEMA = _load_schema("problem_definition.schema.json")
REQUIREMENTS_SCHEMA = _load_schema("requirements.schema.json")
OBJECTIVES_SCHEMA = _load_schema("objectives.schema.json")


# Step name to schema mapping
STEP_SCHEMAS: dict[StepName, dict[str, Any]] = {
    StepName.PROBLEM_DEFINITION: PROBLEM_DEFINITION_SCHEMA,
    StepName.REQUIREMENTS: REQUIREMENTS_SCHEMA,
    StepName.OBJECTIVES: OBJECTIVES_SCHEMA,
}


def get_schema_for_step(step: StepName) -> dict[str, Any]:
    """Get the schema for a given step.

    Args:
        step: Step name (PROBLEM_DEFINITION, REQUIREMENTS, OBJECTIVES).

    Returns:
        JSON Schema dict for the step's package.

    Raises:
        KeyError: If step has no associated schema (Steps 4-10).
    """
    schema = STEP_SCHEMAS.get(step)
    if schema is None:
        raise KeyError(f"No schema defined for step: {step}")
    return schema


def get_required_content_fields(step: StepName) -> list[str]:
    """Get required content fields (excluding metadata) for a step.

    Used for basic structural validation when full schema validation
    is not needed (e.g., Pass 1).

    Args:
        step: Step name.

    Returns:
        List of required content field names.
    """
    # Metadata fields injected by persistence layer
    METADATA_FIELDS = {
        "package_id",
        "workflow_id",
        "instance_id",
        "step_number",
        "version",
        "created_at",
    }

    schema = get_schema_for_step(step)
    all_required = set(schema.get("required", []))
    return list(all_required - METADATA_FIELDS)
