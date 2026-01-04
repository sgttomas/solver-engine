#!/usr/bin/env python3
"""
Gate F Verification Tool

Verifies audit trail completeness - timeline must be reconstructable from audit_log.
Gate F criterion: Full timeline with state transitions, human actions, and actors.

Usage:
    python tools/verify_audit.py --workflow-id <workflow_id>
    python tools/verify_audit.py --workflow <workflow_id>
    python tools/verify_audit.py --workflow-id <id> --verbose
    python tools/verify_audit.py --workflow-id <id> --steps 1 2 3

Exit Codes:
    0 - PASS: Audit trail complete
    1 - FAIL: Audit trail incomplete
    2 - ERROR: Database connection failed
    3 - ERROR: Specified workflow not found
"""

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

# Add apps/api to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "api"))

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from infrastructure.db.models import PassType, StepName
from infrastructure.db.repositories import AuditLogRepository, WorkflowRepository


# =============================================================================
# Constants
# =============================================================================

STEP_NUMBER_TO_NAME: Dict[int, StepName] = {
    1: StepName.PROBLEM_DEFINITION,
    2: StepName.REQUIREMENTS,
    3: StepName.OBJECTIVES,
}

# Status values
STATUS_OK = "OK"
STATUS_INCOMPLETE = "INCOMPLETE"
STATUS_MISSING = "MISSING"

# Required to_status values for each step (per Appendix A)
REQUIRED_TO_STATUSES = {"in_progress", "awaiting_review", "approved"}

# Required human action event type
REQUIRED_HUMAN_ACTION = "step_approved"


# =============================================================================
# Result Data Structures
# =============================================================================


@dataclass
class StepAuditStatus:
    """Audit status for a single step."""

    step_number: int
    step_name: str
    status: str = STATUS_OK
    transition_count: int = 0
    statuses_found: Set[str] = field(default_factory=set)
    missing_statuses: Set[str] = field(default_factory=set)
    has_human_action: bool = False
    transitions: List[Tuple[str, str, datetime, str]] = field(
        default_factory=list
    )  # (from, to, timestamp, actor)


@dataclass
class AuditResult:
    """Overall audit verification result."""

    workflow_id: str
    steps: List[int]
    step_audits: Dict[int, StepAuditStatus] = field(default_factory=dict)
    total_entries: int = 0
    pass2_entries: int = 0
    timestamps_ordered: bool = True
    all_actors_present: bool = True
    missing_actors: List[str] = field(default_factory=list)

    @property
    def expected_min_entries(self) -> int:
        """Minimum entries expected (4 transitions x number of steps)."""
        return len(self.steps) * 4

    @property
    def passed(self) -> bool:
        """Gate F passes if all checks pass."""
        # Primary: per-step status coverage + human action
        steps_ok = all(s.status == STATUS_OK for s in self.step_audits.values())

        # Secondary checks (including minimum entry count per spec)
        return (
            steps_ok
            and self.timestamps_ordered
            and self.all_actors_present
            and len(self.step_audits) == len(self.steps)
            and self.pass2_entries >= self.expected_min_entries
        )


# =============================================================================
# Verification Logic
# =============================================================================


async def verify_audit(
    database_url: str,
    workflow_id: str,
    steps: List[int],
    verbose: bool = False,
) -> Tuple[int, Optional[AuditResult]]:
    """
    Verify audit trail completeness for a workflow.

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

            # Fetch all audit entries for workflow (ordered by created_at)
            audit_repo = AuditLogRepository(session)
            all_entries = await audit_repo.list_for_workflow(workflow.id)

            # Build result
            result = AuditResult(
                workflow_id=workflow_id,
                steps=steps,
                total_entries=len(all_entries),
            )

            # Filter to Pass 2 (execution) entries for requested steps
            pass2_entries = [
                e
                for e in all_entries
                if e.pass_type == PassType.EXECUTION and e.step_number in steps
            ]
            result.pass2_entries = len(pass2_entries)

            # Check timestamp ordering (non-decreasing)
            timestamps = [e.created_at for e in pass2_entries if e.created_at]
            if timestamps:
                result.timestamps_ordered = all(
                    timestamps[i] <= timestamps[i + 1]
                    for i in range(len(timestamps) - 1)
                )

            # Check all actors present
            missing_actors = []
            for e in pass2_entries:
                if not e.actor_id or e.actor_id.strip() == "":
                    missing_actors.append(f"entry {e.id}")
            result.all_actors_present = len(missing_actors) == 0
            result.missing_actors = missing_actors

            # Analyze each step
            for step_num in steps:
                step_entries = [e for e in pass2_entries if e.step_number == step_num]
                step_name = STEP_NUMBER_TO_NAME.get(step_num, f"step_{step_num}")
                step_name_str = (
                    step_name.value if hasattr(step_name, "value") else str(step_name)
                )

                # Extract to_status values found
                statuses_found: Set[str] = set()
                transitions = []
                has_human_action = False

                for entry in step_entries:
                    # Check to_status
                    if entry.to_status:
                        status_val = (
                            entry.to_status.value
                            if hasattr(entry.to_status, "value")
                            else str(entry.to_status)
                        )
                        statuses_found.add(status_val)

                    # Check for human action (step_approved event)
                    if entry.event_type == REQUIRED_HUMAN_ACTION:
                        has_human_action = True

                    # Record transition for verbose output
                    from_status = (
                        entry.from_status.value
                        if entry.from_status and hasattr(entry.from_status, "value")
                        else str(entry.from_status) if entry.from_status else "None"
                    )
                    to_status = (
                        entry.to_status.value
                        if entry.to_status and hasattr(entry.to_status, "value")
                        else str(entry.to_status) if entry.to_status else "None"
                    )
                    transitions.append(
                        (
                            from_status,
                            to_status,
                            entry.created_at,
                            entry.actor_id or "unknown",
                        )
                    )

                # Determine missing statuses
                missing_statuses = REQUIRED_TO_STATUSES - statuses_found

                # Determine step status
                if len(step_entries) == 0:
                    status = STATUS_MISSING
                elif missing_statuses or not has_human_action:
                    status = STATUS_INCOMPLETE
                else:
                    status = STATUS_OK

                result.step_audits[step_num] = StepAuditStatus(
                    step_number=step_num,
                    step_name=step_name_str,
                    status=status,
                    transition_count=len(step_entries),
                    statuses_found=statuses_found,
                    missing_statuses=missing_statuses,
                    has_human_action=has_human_action,
                    transitions=transitions,
                )

            # Determine exit code
            exit_code = 0 if result.passed else 1
            return exit_code, result

    except Exception as e:
        print(f"ERROR: Database query failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 2, None
    finally:
        await engine.dispose()


# =============================================================================
# Output Formatting
# =============================================================================


def print_report(result: AuditResult, verbose: bool = False) -> None:
    """Print the verification report."""
    print("=" * 60)
    print("Gate F Audit Verification Report")
    print("=" * 60)
    print(f"Workflow: {result.workflow_id}")
    print(f"Steps: {', '.join(map(str, result.steps))}")
    print()

    for step_num in result.steps:
        step_audit = result.step_audits.get(step_num)
        if not step_audit:
            print(f"Step {step_num}: NO DATA")
            print()
            continue

        print(f"Step {step_num}: {step_audit.step_name}")
        print("-" * 40)
        print(f"  Status: {step_audit.status}")
        print(f"  Pass 2 entries: {step_audit.transition_count}")
        print(f"  Statuses found: {', '.join(sorted(step_audit.statuses_found)) or 'none'}")
        print(f"  Human action (step_approved): {'Yes' if step_audit.has_human_action else 'No'}")

        if step_audit.missing_statuses:
            print(f"  Missing statuses: {', '.join(sorted(step_audit.missing_statuses))}")

        if verbose and step_audit.transitions:
            print(f"  Timeline:")
            for from_s, to_s, ts, actor in step_audit.transitions:
                ts_str = ts.isoformat() if ts else "unknown"
                print(f"    {ts_str}: {from_s} -> {to_s} (by {actor})")

        print()

    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Total audit entries: {result.total_entries}")
    print(f"Pass 2 entries: {result.pass2_entries}")
    print(f"Expected min (Pass 2): {result.expected_min_entries}")
    print(f"Timestamps ordered: {'Yes' if result.timestamps_ordered else 'No'}")
    print(f"All actors present: {'Yes' if result.all_actors_present else 'No'}")

    if result.missing_actors:
        print(f"Missing actors in: {', '.join(result.missing_actors[:5])}")
        if len(result.missing_actors) > 5:
            print(f"  ... and {len(result.missing_actors) - 5} more")

    print()

    # Per-step summary
    steps_ok = sum(1 for s in result.step_audits.values() if s.status == STATUS_OK)
    steps_incomplete = sum(
        1 for s in result.step_audits.values() if s.status == STATUS_INCOMPLETE
    )
    steps_missing = sum(
        1 for s in result.step_audits.values() if s.status == STATUS_MISSING
    )
    print(f"Steps OK: {steps_ok}")
    print(f"Steps incomplete: {steps_incomplete}")
    print(f"Steps missing: {steps_missing}")
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
        description="Gate F Verification - Check audit trail completeness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python tools/verify_audit.py --workflow-id wf-abc123
    python tools/verify_audit.py --workflow wf-abc123
    python tools/verify_audit.py --workflow-id wf-abc123 --verbose
    python tools/verify_audit.py --workflow-id wf-abc123 --steps 1 2 3
        """,
    )

    # Primary arg with alias for Doc 0 compatibility
    parser.add_argument(
        "--workflow-id",
        "--workflow",
        type=str,
        required=True,
        dest="workflow_id",
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
        help="Show detailed timeline per step",
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
        verify_audit(
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
