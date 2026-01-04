#!/usr/bin/env python3
"""
Gate B Schema Validation Tool

Validates that Pass 2 step packages exist and conform to their JSON schemas.
Gate B criterion (schema portion): Step 1-3 packages validate against schemas.

Usage:
    python tools/validate_schemas.py --workflow-id <workflow_id>
    python tools/validate_schemas.py --workflow-id wf-abc123 --verbose
    python tools/validate_schemas.py --workflow-id wf-abc123 --steps 1 2

Exit Codes:
    0 - PASS: All expected step packages found and schema-valid
    1 - FAIL: Missing, empty, or invalid packages
    2 - ERROR: Invalid arguments or database connection failed
    3 - ERROR: Specified workflow not found
"""

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import jsonschema

# Add apps/api to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "api"))

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Use domain.state.StepName for schema lookup (NOT infrastructure.db.models.StepName)
from domain.state import StepName as DomainStepName
from infrastructure.db.models import PassType
from infrastructure.db.repositories import ArtifactRepository, WorkflowRepository
from application.schemas import get_schema_for_step


# =============================================================================
# Constants
# =============================================================================

# Map step_number → domain.state.StepName for schema lookup
STEP_NUMBER_TO_DOMAIN_STEP: Dict[int, DomainStepName] = {
    1: DomainStepName.PROBLEM_DEFINITION,
    2: DomainStepName.REQUIREMENTS,
    3: DomainStepName.OBJECTIVES,
}

# Expected package_type per step (for structural validation)
EXPECTED_PACKAGE_TYPE: Dict[int, str] = {
    1: "ProblemDefinitionPackage",
    2: "RequirementsPackage",
    3: "ObjectivesPackage",
}

# Human-readable step names
STEP_NAMES: Dict[int, str] = {
    1: "problem_definition",
    2: "requirements",
    3: "objectives",
}

# Status values
STATUS_VALID = "VALID"
STATUS_INVALID = "INVALID"
STATUS_EMPTY = "EMPTY"
STATUS_MISSING = "MISSING"


# =============================================================================
# Result Data Structures
# =============================================================================


@dataclass
class ValidationError:
    """A single validation error."""

    path: List[Any]
    message: str
    validator: Optional[str] = None
    schema_path: Optional[List[Any]] = None


@dataclass
class PackageStatus:
    """Status of a single step package."""

    step_number: int
    status: str  # VALID, INVALID, EMPTY, MISSING
    package_type: Optional[str] = None
    revision: Optional[int] = None
    artifact_id: Optional[str] = None
    errors: List[ValidationError] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Overall validation result."""

    workflow_id: str
    steps: List[int]
    packages: Dict[int, PackageStatus] = field(default_factory=dict)

    @property
    def expected_count(self) -> int:
        return len(self.steps)

    @property
    def valid_count(self) -> int:
        return sum(1 for p in self.packages.values() if p.status == STATUS_VALID)

    @property
    def invalid_count(self) -> int:
        return sum(1 for p in self.packages.values() if p.status == STATUS_INVALID)

    @property
    def empty_count(self) -> int:
        return sum(1 for p in self.packages.values() if p.status == STATUS_EMPTY)

    @property
    def missing_count(self) -> int:
        return sum(1 for p in self.packages.values() if p.status == STATUS_MISSING)

    @property
    def passed(self) -> bool:
        return self.valid_count == self.expected_count


# =============================================================================
# Validation Logic
# =============================================================================


async def validate_schemas(
    database_url: str,
    workflow_id: str,
    steps: List[int],
    verbose: bool = False,
) -> Tuple[int, Optional[ValidationResult]]:
    """
    Validate step packages for a workflow against JSON schemas.

    Args:
        database_url: PostgreSQL connection URL
        workflow_id: Public workflow ID string
        steps: List of step numbers to validate
        verbose: Whether to print verbose output

    Returns:
        Tuple of (exit_code, result)
    """
    # Create engine
    try:
        engine = create_async_engine(database_url, echo=False)
    except Exception as e:
        print(f"ERROR: Failed to create database engine: {e}", file=sys.stderr)
        return 2, None

    try:
        async_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        async with async_session_factory() as session:
            # Resolve workflow ID to internal UUID
            workflow_repo = WorkflowRepository(session)
            workflow = await workflow_repo.get_by_workflow_id(workflow_id)

            if workflow is None:
                print(f"ERROR: Workflow '{workflow_id}' not found", file=sys.stderr)
                return 3, None

            # Fetch all artifacts for workflow (explicit filtering for transparency)
            artifact_repo = ArtifactRepository(session)
            all_artifacts = await artifact_repo.list_for_workflow(workflow.id)

            # Filter to Pass 2 step packages only
            step_packages = [
                a
                for a in all_artifacts
                if a.artifact_type == "step_package"
                and a.pass_type == PassType.EXECUTION
                and a.step_number in steps
            ]

            # Build result
            result = ValidationResult(workflow_id=workflow_id, steps=steps)

            for step_num in steps:
                # Find all packages for this step
                matches = [a for a in step_packages if a.step_number == step_num]

                if not matches:
                    result.packages[step_num] = PackageStatus(
                        step_number=step_num,
                        status=STATUS_MISSING,
                    )
                    continue

                # Get latest revision
                artifact = max(matches, key=lambda a: a.revision)

                # Check for empty content
                if artifact.content_jsonb is None:
                    result.packages[step_num] = PackageStatus(
                        step_number=step_num,
                        status=STATUS_EMPTY,
                        package_type=artifact.package_type,
                        revision=artifact.revision,
                        artifact_id=str(artifact.id),
                    )
                    continue

                # Check package_type matches expected
                expected_type = EXPECTED_PACKAGE_TYPE[step_num]
                if artifact.package_type != expected_type:
                    result.packages[step_num] = PackageStatus(
                        step_number=step_num,
                        status=STATUS_INVALID,
                        package_type=artifact.package_type,
                        revision=artifact.revision,
                        artifact_id=str(artifact.id),
                        errors=[
                            ValidationError(
                                path=["package_type"],
                                message=f"Expected '{expected_type}', got '{artifact.package_type}'",
                                validator="package_type_check",
                            )
                        ],
                    )
                    continue

                # Validate against JSON schema using domain.state.StepName
                domain_step = STEP_NUMBER_TO_DOMAIN_STEP[step_num]
                schema = get_schema_for_step(domain_step)
                validator = jsonschema.Draft7Validator(schema)
                schema_errors = list(validator.iter_errors(artifact.content_jsonb))

                if schema_errors:
                    result.packages[step_num] = PackageStatus(
                        step_number=step_num,
                        status=STATUS_INVALID,
                        package_type=artifact.package_type,
                        revision=artifact.revision,
                        artifact_id=str(artifact.id),
                        errors=[
                            ValidationError(
                                path=list(e.path),
                                message=e.message,
                                validator=e.validator,
                                schema_path=list(e.schema_path),
                            )
                            for e in schema_errors
                        ],
                    )
                else:
                    result.packages[step_num] = PackageStatus(
                        step_number=step_num,
                        status=STATUS_VALID,
                        package_type=artifact.package_type,
                        revision=artifact.revision,
                        artifact_id=str(artifact.id),
                    )

            # Determine exit code
            exit_code = 0 if result.passed else 1
            return exit_code, result

    except Exception as e:
        print(f"ERROR: Database query failed: {e}", file=sys.stderr)
        return 2, None
    finally:
        await engine.dispose()


# =============================================================================
# Output Formatting
# =============================================================================


def print_report(result: ValidationResult, verbose: bool = False) -> None:
    """Print the validation report."""
    print("=" * 60)
    print("Gate B Schema Validation Report")
    print("=" * 60)
    print(f"Workflow: {result.workflow_id}")
    print(f"Steps: {', '.join(map(str, result.steps))}")
    print()

    for step_num in result.steps:
        step_name = STEP_NAMES.get(step_num, f"step_{step_num}")
        print(f"Step {step_num}: {step_name}")
        print("-" * 40)

        pkg = result.packages.get(step_num)
        if pkg is None:
            print("  Status: UNKNOWN")
            print()
            continue

        if pkg.status == STATUS_MISSING:
            print("  Status: MISSING")
        else:
            print(f"  Package: {pkg.package_type}")
            print(f"  Revision: {pkg.revision}")
            print(f"  Status: {pkg.status}")

            if pkg.errors and verbose:
                print("  Errors:")
                for error in pkg.errors:
                    path_str = " -> ".join(str(p) for p in error.path) if error.path else "(root)"
                    print(f"    - path: {path_str}")
                    print(f"      message: {error.message}")

        print()

    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Expected:  {result.expected_count}")
    print(f"Valid:     {result.valid_count}")
    print(f"Invalid:   {result.invalid_count}")
    if result.empty_count > 0:
        print(f"Empty:     {result.empty_count}")
    if result.missing_count > 0:
        print(f"Missing:   {result.missing_count}")
    print()

    status = "PASS" if result.passed else "FAIL"
    print(f"Status: {status}")
    print()


# =============================================================================
# CLI Interface
# =============================================================================


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Gate B Schema Validation - Check step package schema conformance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python tools/validate_schemas.py --workflow-id wf-abc123
    python tools/validate_schemas.py --workflow-id wf-abc123 --verbose
    python tools/validate_schemas.py --workflow-id wf-abc123 --steps 1 2
        """,
    )

    parser.add_argument(
        "--workflow-id",
        type=str,
        required=True,
        help="Public workflow ID (e.g., wf-abc123)",
    )

    parser.add_argument(
        "--steps",
        type=int,
        nargs="+",
        default=[1, 2, 3],
        help="Step numbers to validate (default: 1 2 3)",
    )

    parser.add_argument(
        "--database-url",
        type=str,
        default=None,
        help="PostgreSQL connection URL (default: from settings)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed validation errors",
    )

    return parser.parse_args()


def main() -> None:
    """CLI entry point."""
    args = parse_args()

    # Get database URL
    if args.database_url:
        database_url = args.database_url
    else:
        try:
            from config import settings

            database_url = settings.postgres_url
        except ImportError as e:
            print(f"ERROR: Cannot import settings: {e}", file=sys.stderr)
            print("Use --database-url to specify connection string", file=sys.stderr)
            sys.exit(2)

    # Validate and deduplicate steps
    for step in args.steps:
        if step not in STEP_NUMBER_TO_DOMAIN_STEP:
            print(
                f"ERROR: Invalid step number {step}. Valid steps: {list(STEP_NUMBER_TO_DOMAIN_STEP.keys())}",
                file=sys.stderr,
            )
            sys.exit(2)

    # Deduplicate and sort steps to prevent false failures
    steps = sorted(set(args.steps))

    # Run validation
    exit_code, result = asyncio.run(
        validate_schemas(
            database_url=database_url,
            workflow_id=args.workflow_id,
            steps=steps,
            verbose=args.verbose,
        )
    )

    # Print report if we have results
    if result is not None:
        print_report(result, verbose=args.verbose)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
