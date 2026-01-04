#!/usr/bin/env python3
"""
Complete Workflow Tool for Gate F Testing

Creates a fully-approved workflow (Pass 1 + Pass 2, Steps 1-3) deterministically
without LLM calls. Uses httpx + ASGITransport to run FastAPI in-process.

Usage:
    python tools/complete_workflow.py
    # Outputs: <workflow_id>

Exit Codes:
    0 - SUCCESS: Workflow created and fully approved
    1 - ERROR: Workflow creation or approval failed
"""

import asyncio
import os
import sys
import time
from typing import Any, Dict

# Add apps/api to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "api"))

import httpx
from httpx import ASGITransport

from main import app
from domain.state import PassType, StepName, ValidationResult, WorkflowState
import orchestration.nodes as nodes


# =============================================================================
# Stub Payloads (Schema-Valid with Trace Links)
# =============================================================================


def methodology_payload() -> Dict[str, Any]:
    """Pass 1 methodology payload (v1, v2, v3 structure)."""
    base = {
        "data_sheet": "# Data Sheet\n\nInput/output contracts and validation rules.",
        "todo_list": "# To Do List\n\n1. Task one\n2. Task two",
        "guidance": "# Guidance\n\nContext, principles, and anti-patterns.",
        "detailed_procedure": "# Detailed Procedure\n\nState machine and decision logic.",
    }
    return {"v1": base, "v2": base, "v3": base}


def step1_content() -> Dict[str, Any]:
    """Pass 2 Step 1: ProblemDefinitionPackage with stakeholders and success_criteria."""
    return {
        "title": "Gate F Test Problem",
        "canonical_problem_definition": {
            "statement": "Verify audit trail completeness for Gate F compliance"
        },
        "stakeholders": [
            {
                "id": "SH-001",
                "name_or_group": "System Auditor",
                "role": "Verifier",
                "needs": ["Complete audit trail", "Reconstructable timeline"],
                "concerns": ["Missing entries", "Incomplete actor tracking"],
                "impact": "High",
            }
        ],
        "constraints": {
            "hard": [
                {
                    "id": "HC-001",
                    "statement": "All state transitions must be logged",
                    "rationale": "Gate F requirement",
                }
            ],
            "soft": [
                {
                    "id": "SC-001",
                    "statement": "Logs should be queryable by step",
                    "rationale": "Usability",
                }
            ],
        },
        "scope": {
            "in": [{"id": "IN-001", "item": "Audit log verification"}],
            "out": [
                {
                    "id": "OUT-001",
                    "item": "Real-time monitoring",
                    "rationale": "Out of MVP scope",
                }
            ],
        },
        "success_criteria": [
            {
                "id": "CRT-001",
                "metric_or_signal": "Audit entries exist for all transitions",
                "target": "12+ entries for 3 steps",
                "how_verified": "tools/verify_audit.py",
            }
        ],
    }


def step2_content() -> Dict[str, Any]:
    """Pass 2 Step 2: RequirementsPackage with coverage_map tracing to SH-001."""
    return {
        "overview": {
            "summary": "Requirements for audit trail verification",
            "boundaries": ["Gate F scope"],
            "total_requirements": 1,
            "priority_distribution": {"must": 1, "should": 0, "could": 0},
        },
        "requirements": [
            {
                "id": "FR-001",
                "category": "FR",
                "priority": "must",
                "statement": "System shall log all state transitions with actor and timestamp",
                "rationale": "Gate F auditability requirement",
                "source": {"type": "stakeholder", "id": "SH-001", "aspect": "need"},
                "component": ["audit"],
                "testability": {
                    "method": "test",
                    "description": "Verify via tools/verify_audit.py",
                },
                "trace": {"stakeholders": ["SH-001"]},
            }
        ],
        "coverage_map": [
            {
                "source_type": "stakeholder",
                "source_id": "SH-001",
                "requirement_ids": ["FR-001"],
                "coverage_note": "Stakeholder need for audit trail covered by FR-001",
            }
        ],
    }


def step3_content() -> Dict[str, Any]:
    """Pass 2 Step 3: ObjectivesPackage with trace_map and acceptance_criteria."""
    return {
        "overview": {
            "intent": "Define objectives for audit trail verification",
            "measurement_principles": ["Completeness", "Traceability"],
            "boundaries": ["Gate F"],
            "total_objectives": 1,
            "consolidation_ratio": 1.0,
        },
        "objectives": [
            {
                "id": "CAP-001",
                "category": "CAP",
                "tier": "primary",
                "statement": "Achieve complete audit trail coverage",
                "rationale": "Gate F compliance requirement",
                "owner_type": "system",
                "linked_requirements": ["FR-001"],
                "consolidated": False,
                "success_criteria": {
                    "definition": "All transitions logged with actors",
                    "verification": {
                        "method": "test",
                        "description": "Run tools/verify_audit.py",
                        "evidence_artifacts": ["audit_log entries"],
                    },
                    "metric": None,
                    "threshold": None,
                },
                "component": ["audit"],
                "acceptance_criteria": ["CRT-001"],
            }
        ],
        "success_framework": {
            "minimum_viable": {
                "description": "Basic audit trail exists",
                "objectives": ["CAP-001"],
                "requirement_coverage": ["FR-001"],
            },
            "target": {
                "description": "Complete audit trail with all transitions",
                "objectives": ["CAP-001"],
                "requirement_coverage": ["FR-001"],
            },
            "aspirational": {
                "description": "Full audit trail with rich metadata",
                "objectives": ["CAP-001"],
                "requirement_coverage": ["FR-001"],
            },
        },
        "trace_map": [
            {
                "objective_id": "CAP-001",
                "requirement_ids": ["FR-001"],
                "consolidated": False,
            }
        ],
    }


# =============================================================================
# Monkeypatched LLM Functions
# =============================================================================


async def fake_generate_step_output(state: WorkflowState) -> Dict[str, Any]:
    """Return deterministic output based on step and pass type."""
    if state.current_pass == PassType.DEFINITION:
        return methodology_payload()

    # Pass 2 (EXECUTION)
    if state.current_step == StepName.PROBLEM_DEFINITION:
        return step1_content()
    if state.current_step == StepName.REQUIREMENTS:
        return step2_content()
    if state.current_step == StepName.OBJECTIVES:
        return step3_content()

    # Fallback (shouldn't reach here for Steps 1-3)
    return {}


async def fake_validate_output(*_args, **_kwargs) -> ValidationResult:
    """Return passing validation without LLM."""
    return ValidationResult(passed=True, errors=[], warnings=[])


# =============================================================================
# Workflow Driver
# =============================================================================


async def wait_for_review(
    client: httpx.AsyncClient,
    workflow_id: str,
    step_num: int,
    pass_type: str,
    timeout: float = 30.0,
) -> None:
    """Poll until workflow reaches awaiting_review for given step/pass."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = await client.get(f"/api/v1/workflows/{workflow_id}")
        if resp.status_code == 200:
            data = resp.json()
            if (
                data["current_step_number"] == step_num
                and data["current_pass"] == pass_type
                and data["step_state"]["status"] == "awaiting_review"
            ):
                return
        await asyncio.sleep(0.3)
    raise RuntimeError(
        f"Timeout waiting for {pass_type} step {step_num} awaiting_review"
    )


async def run_complete_workflow() -> str:
    """Create and fully approve a workflow through Pass 1 + Pass 2, Steps 1-3."""
    # Monkeypatch before importing app modules
    nodes.generate_step_output = fake_generate_step_output
    nodes.validate_output = fake_validate_output

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        timeout=60.0,
    ) as client:
        # Create workflow
        resp = await client.post(
            "/api/v1/workflows",
            json={
                "problem": "Gate F audit trail seed workflow",
                "created_by": "gate-f-tool",
            },
        )
        if resp.status_code != 201:
            raise RuntimeError(f"Failed to create workflow: {resp.status_code} {resp.text}")

        workflow_id = resp.json()["workflow_id"]

        # Pass 1 (definition) approvals for Steps 1-3
        for step_num in (1, 2, 3):
            await wait_for_review(client, workflow_id, step_num, "definition")
            approve_resp = await client.post(
                f"/api/v1/workflows/{workflow_id}/actions/approve",
                json={"actor_id": "gate-f-tool"},
            )
            if approve_resp.status_code != 200:
                raise RuntimeError(
                    f"Pass 1 Step {step_num} approve failed: {approve_resp.status_code} {approve_resp.text}"
                )

        # Pass 2 (execution) approvals for Steps 1-3
        for step_num in (1, 2, 3):
            await wait_for_review(client, workflow_id, step_num, "execution")
            approve_resp = await client.post(
                f"/api/v1/workflows/{workflow_id}/actions/approve",
                json={"actor_id": "gate-f-tool"},
            )
            if approve_resp.status_code != 200:
                raise RuntimeError(
                    f"Pass 2 Step {step_num} approve failed: {approve_resp.status_code} {approve_resp.text}"
                )

        return workflow_id


# =============================================================================
# CLI Entry Point
# =============================================================================


def main() -> None:
    """CLI entry point."""
    try:
        workflow_id = asyncio.run(run_complete_workflow())
        print(workflow_id)
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
