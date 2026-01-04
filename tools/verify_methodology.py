#!/usr/bin/env python3
"""
Gate A Verification Tool

Verifies that methodology documents exist in the database with valid content.
Gate A criterion: 36 methodology docs (3 steps x 4 doc types x 3 versions)

Usage:
    python tools/verify_methodology.py --workflow-id <workflow_id>
    python tools/verify_methodology.py --workflow-id wf-abc123 --verbose
    python tools/verify_methodology.py --workflow-id wf-abc123 --steps 1 2

Exit Codes:
    0 - PASS: All expected methodology documents found with valid content
    1 - FAIL: Missing or empty methodology documents
    2 - ERROR: Database connection failed
    3 - ERROR: Specified workflow not found
"""

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# Add apps/api to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "api"))

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from infrastructure.db.models import (
    DocumentType,
    DocumentVersion,
    PassType,
    StepName,
)
from infrastructure.db.repositories import ArtifactRepository, WorkflowRepository


# =============================================================================
# Constants
# =============================================================================

STEP_NUMBER_TO_NAME: Dict[int, StepName] = {
    1: StepName.PROBLEM_DEFINITION,
    2: StepName.REQUIREMENTS,
    3: StepName.OBJECTIVES,
}

DOCUMENT_TYPES: List[DocumentType] = list(DocumentType)
DOCUMENT_VERSIONS: List[DocumentVersion] = list(DocumentVersion)

# Status values for each doc
STATUS_OK = "OK"
STATUS_MISSING = "MISSING"
STATUS_EMPTY = "EMPTY"
STATUS_DUPLICATE = "DUPLICATE"


# =============================================================================
# Result Data Structures
# =============================================================================


@dataclass
class DocStatus:
    """Status of a single methodology document."""

    step_number: int
    document_type: DocumentType
    document_version: DocumentVersion
    status: str  # OK, MISSING, EMPTY, DUPLICATE
    artifact_id: Optional[str] = None
    created_at: Optional[str] = None
    count: int = 0  # Number of artifacts found (for duplicate detection)


@dataclass
class VerificationResult:
    """Overall verification result."""

    workflow_id: str
    steps: List[int]
    docs: Dict[Tuple[int, DocumentType, DocumentVersion], DocStatus] = field(
        default_factory=dict
    )

    @property
    def expected_count(self) -> int:
        return len(self.steps) * len(DOCUMENT_TYPES) * len(DOCUMENT_VERSIONS)

    @property
    def ok_count(self) -> int:
        return sum(1 for d in self.docs.values() if d.status == STATUS_OK)

    @property
    def missing_count(self) -> int:
        return sum(1 for d in self.docs.values() if d.status == STATUS_MISSING)

    @property
    def empty_count(self) -> int:
        return sum(1 for d in self.docs.values() if d.status == STATUS_EMPTY)

    @property
    def duplicate_count(self) -> int:
        return sum(1 for d in self.docs.values() if d.status == STATUS_DUPLICATE)

    @property
    def passed(self) -> bool:
        return self.ok_count == self.expected_count


# =============================================================================
# Verification Logic
# =============================================================================


async def verify_methodology(
    database_url: str,
    workflow_id: str,
    steps: List[int],
    verbose: bool = False,
) -> Tuple[int, Optional[VerificationResult]]:
    """
    Verify methodology documents for a workflow.

    Args:
        database_url: PostgreSQL connection URL
        workflow_id: Public workflow ID string
        steps: List of step numbers to verify
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

            # Fetch all artifacts for workflow
            artifact_repo = ArtifactRepository(session)
            all_artifacts = await artifact_repo.list_for_workflow(workflow.id)

            # Filter to methodology docs for requested steps
            methodology_docs = [
                a
                for a in all_artifacts
                if a.artifact_type == "methodology_doc"
                and a.pass_type == PassType.DEFINITION
                and a.step_number in steps
            ]

            # Build result
            result = VerificationResult(workflow_id=workflow_id, steps=steps)

            for step_num in steps:
                for doc_type in DOCUMENT_TYPES:
                    for doc_version in DOCUMENT_VERSIONS:
                        # Find matching artifacts
                        matches = [
                            a
                            for a in methodology_docs
                            if a.step_number == step_num
                            and a.document_type == doc_type
                            and a.document_version == doc_version
                        ]

                        key = (step_num, doc_type, doc_version)

                        if len(matches) == 0:
                            result.docs[key] = DocStatus(
                                step_number=step_num,
                                document_type=doc_type,
                                document_version=doc_version,
                                status=STATUS_MISSING,
                                count=0,
                            )
                        elif len(matches) > 1:
                            # Multiple artifacts found - anomaly
                            result.docs[key] = DocStatus(
                                step_number=step_num,
                                document_type=doc_type,
                                document_version=doc_version,
                                status=STATUS_DUPLICATE,
                                artifact_id=str(matches[0].id),
                                created_at=(
                                    matches[0].created_at.isoformat()
                                    if matches[0].created_at
                                    else None
                                ),
                                count=len(matches),
                            )
                        else:
                            # Exactly one artifact - check content
                            artifact = matches[0]
                            content = artifact.content_markdown

                            if content is None or content.strip() == "":
                                status = STATUS_EMPTY
                            else:
                                status = STATUS_OK

                            result.docs[key] = DocStatus(
                                step_number=step_num,
                                document_type=doc_type,
                                document_version=doc_version,
                                status=status,
                                artifact_id=str(artifact.id),
                                created_at=(
                                    artifact.created_at.isoformat()
                                    if artifact.created_at
                                    else None
                                ),
                                count=1,
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


def print_report(result: VerificationResult, verbose: bool = False) -> None:
    """Print the verification report."""
    print("=" * 60)
    print("Gate A Verification Report")
    print("=" * 60)
    print(f"Workflow: {result.workflow_id}")
    print(f"Steps: {', '.join(map(str, result.steps))}")
    print()

    for step_num in result.steps:
        step_name = STEP_NUMBER_TO_NAME.get(step_num, f"step_{step_num}")
        step_name_str = step_name.value if hasattr(step_name, "value") else str(step_name)
        print(f"Step {step_num}: {step_name_str}")
        print("-" * 40)

        if verbose:
            # Detailed per-document listing
            for doc_type in DOCUMENT_TYPES:
                for doc_version in DOCUMENT_VERSIONS:
                    key = (step_num, doc_type, doc_version)
                    doc = result.docs.get(key)
                    if doc:
                        status_str = doc.status
                        if doc.status == STATUS_DUPLICATE:
                            status_str = f"{doc.status} ({doc.count})"
                        detail = ""
                        if doc.artifact_id and doc.status == STATUS_OK:
                            detail = f" [{doc.artifact_id[:8]}...]"
                        print(
                            f"  {doc_type.value:20} {doc_version.value}: {status_str}{detail}"
                        )
        else:
            # Summary table
            header = f"{'Document Type':<20} {'v1':>8} {'v2':>8} {'v3':>8}"
            print(header)

            for doc_type in DOCUMENT_TYPES:
                row = [doc_type.value]
                for doc_version in DOCUMENT_VERSIONS:
                    key = (step_num, doc_type, doc_version)
                    doc = result.docs.get(key)
                    status = doc.status if doc else STATUS_MISSING
                    row.append(status)
                print(f"{row[0]:<20} {row[1]:>8} {row[2]:>8} {row[3]:>8}")

        print()

    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Expected:  {result.expected_count}")
    print(f"OK:        {result.ok_count}")
    print(f"Missing:   {result.missing_count}")
    print(f"Empty:     {result.empty_count}")
    if result.duplicate_count > 0:
        print(f"Duplicate: {result.duplicate_count}")
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
        description="Gate A Verification - Check methodology document completeness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python tools/verify_methodology.py --workflow-id wf-abc123
    python tools/verify_methodology.py --workflow-id wf-abc123 --verbose
    python tools/verify_methodology.py --workflow-id wf-abc123 --steps 1 2
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
        help="Step numbers to verify (default: 1 2 3)",
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
        help="Show detailed per-document listing",
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
        if step not in STEP_NUMBER_TO_NAME:
            print(
                f"ERROR: Invalid step number {step}. Valid steps: {list(STEP_NUMBER_TO_NAME.keys())}",
                file=sys.stderr,
            )
            sys.exit(2)

    # Deduplicate and sort steps to prevent false failures
    steps = sorted(set(args.steps))

    # Run verification
    exit_code, result = asyncio.run(
        verify_methodology(
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
