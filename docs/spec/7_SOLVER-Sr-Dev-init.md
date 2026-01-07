# SOLVER Engine — Senior Developer Init (Phase 7R — Remediation)

## Role

Senior developer for Phase 7R remediation. Resolve or reclassify open DECISIONS entries and
deferrals, then prepare for re-freeze. Stay within the governance chain in docs/spec/.

## Mission

Implement Phase 7R: Intermediary Remediation. Resolve outstanding deferrals from prior packages,
implement deferred functionality where feasible, or reclassify with clear rationale. Prepare
codebase and governance docs for next freeze cycle.

## Phase 7R Scope

**Objective:** Resolve or reclassify open DECISIONS entries/deferrals, then re-freeze.

**Workstreams:**

| # | Workstream | DECISIONS Entry | Spec Reference |
|---|------------|-----------------|----------------|
| 1 | Lease/Exclusive Execution | P7.3-DEF-001 | Contract §15.2, Design Intent §4.8 |
| 2 | SSE Replay Coverage | P7.1-DEF-001 | Contract §12 |
| 3 | Messages List/Query | P6.6-DEFER-001 | Tech Spec §8.x |
| 4 | Streaming Delta / Mid-step Recovery | P6.5/P6.4 synthetic deltas | Tech Spec §9 |

**Exit Gate:** All workstreams resolved (implemented or reclassified) + F0–F4 freeze checks pass

## Workstream Details

### 1. Lease/Exclusive Execution (P7.3-DEF-001)

**Goal:** Implement exclusive execution via leases per Contract §15.2 and Design Intent §4.8.

**Deliverables:**
- `workflow_execution_locks` table (schema + migration)
- `acquire_workflow_lease()`, `renew_workflow_lease()`, `release_workflow_lease()` functions
- Lease expiry and reacquisition logic
- β4 gate tests (acquire, renew, expire/reacquire, crash recovery)
- DECISIONS resolution entry removing P7.3-DEF-001 deferral

**Verification:** `make test-recovery` includes β4 lease tests; no regression of γ1/γ4

### 2. SSE Replay Coverage (P7.1-DEF-001)

**Goal:** Complete SSE replay coverage for `workflow.completed` events.

**Deliverables:**
- Replay test for `workflow.completed` via `/stream?from_sequence`
- Ensure Contract §12 monotonic/gap-free replay coverage for completion events
- DECISIONS resolution entry removing P7.1-DEF-001 deferral

**Verification:** Gate E includes completion event replay test

### 3. Messages List/Query (P6.6-DEFER-001)

**Goal:** Decide implementation vs permanent deferral for messages list endpoint.

**Options:**
- A: Implement list endpoint + hook + tests; update Tech Spec if shape changes
- B: Reclassify as permanent deferral with rationale (e.g., history endpoint sufficient)

**Deliverables:**
- Implementation OR reclassification rationale
- Tech Spec update if behavior changes
- DECISIONS resolution or reclassification entry

### 4. Streaming Delta / Mid-step Recovery (P6.5/P6.4)

**Goal:** Decide implementation vs permanent deferral for synthetic deltas and mid-step recovery.

**Context:**
- P6.5 synthetic deltas: SSE delta events during step execution
- P6.4 mid-step recovery: Resume from mid-generation (limited by LangGraph checkpoint semantics)

**Options:**
- A: Implement with tests
- B: Keep deferred with updated rationale and timeline

**Deliverables:**
- Implementation OR updated deferral rationale
- DECISIONS resolution or updated deferral entry

## Objectives

1. Close all Phase 6/7 deferrals via implementation or reclassification
2. Maintain governance integrity (every change logged in DECISIONS)
3. Update Tech Spec for any behavior changes
4. Pass F0–F4 freeze checks for next baseline
5. No regression of existing gates (γ1, γ4, Gate D, Gate E)

## Scope Boundaries

**In scope:**
- Implementing deferred functionality (leases, SSE replay, messages, deltas)
- Reclassifying deferrals with clear rationale
- Updating Tech Spec for implemented features
- Adding/adjusting tests for each workstream
- Preparing FREEZE-RECORD for next baseline

**Out of scope:**
- New features beyond resolving deferrals
- Phase 8+ work
- Spec changes unrelated to deferral resolution

## Orientation

Run:
```bash
pwd
git status -sb
```

Read in order:
1. README.md
2. AGENTS.md
3. CLAUDE.md
4. docs/spec/DECISIONS.md (focus on P7.3-DEF-001, P7.1-DEF-001, P6.6-DEFER-001, P6.5/P6.4 entries)
5. docs/spec/5_SOLVER-Development-Directive-v1.5.1.md (Phase 5.1 for lease requirements)
6. docs/spec/3_SOLVER-Architectural-Contract-v3.4.md (§15.2 Exclusive Execution, §12 Replay)
7. docs/spec/2_SOLVER-Design-Intent-v1.1.md (§4.8 Exclusive Execution via Leases)
8. docs/spec/4_SOLVER-Technical-Spec-V2.8.4.md (current schema baseline)

## Current State

**Phase 7: Integration — CLOSED (spec-freeze-v2.8.4)**

All packages complete:
- 7.1: Workflow Lifecycle Integration ✓ (γ1 PASSED)
- 7.3: Recovery Scenarios ✓ (Recovery Gate PASSED, 21 tests; Gate C/E/γ1/γ4 passing)
- Baseline frozen at `spec-freeze-v2.8.4` (see FREEZE-RECORD.md)

Open deferrals from prior phases:
- P7.3-DEF-001: Lease recovery (Phase 5 infrastructure absent)
- P7.1-DEF-001: SSE replay coverage for workflow.completed
- P6.6-DEFER-001: Messages list/query endpoint
- P6.5/P6.4: Synthetic deltas, mid-step recovery

**Phase 7R: Remediation — NEXT**

- Unfreeze per Change Management §3.5 before semantic changes
- Resolve/reclassify deferrals above, then re-freeze (new baseline post-Phase 7R)

**Spec Status:** FROZEN at spec-freeze-v2.8.4 until unfreeze for Phase 7R work

## Key Paths

| Path | Focus |
|------|-------|
| infra/db/migrations/ | New migration for workflow_execution_locks |
| apps/api/infrastructure/db/models/ | Lease model |
| apps/api/application/workflow_service.py | Lease acquire/renew/release |
| apps/api/routes/workflows.py | SSE replay, messages endpoint |
| apps/api/tests/integration/test_beta4.py | Lease gate tests (new) |
| apps/api/tests/e2e/ | SSE replay tests, messages tests |
| docs/spec/DECISIONS.md | Resolution entries |
| docs/spec/FREEZE-RECORD.md | Next freeze record |

## Testing Strategy

**Per Workstream:**
```bash
# Workstream 1: Leases
PYTHONPATH=apps/api .venv/bin/pytest apps/api/tests/integration/test_beta4.py -v

# Workstream 2: SSE Replay
make e2e  # Gate E includes completion replay

# Workstream 3: Messages (if implemented)
PYTHONPATH=apps/api .venv/bin/pytest apps/api/tests/e2e/test_messages.py -v

# Regression
make test-recovery   # Gate D + recovery scenarios
make e2e             # Gate E
make test-gates      # Gate C
PYTHONPATH=apps/api .venv/bin/pytest apps/api/tests/e2e/test_gate_gamma1.py apps/api/tests/e2e/test_gate_gamma4.py -v
```

**Freeze Verification:**
```bash
# F0–F4 checks before freeze
python tools/validate_schemas.py
make test
make e2e
make test-recovery
# Verify DECISIONS entries complete
# Update FREEZE-RECORD.md and tag new baseline
```

## Anti-Patterns to Avoid

| Pattern | Why |
|---------|-----|
| Implementing without DECISIONS resolution | Governance requires closure |
| Deferring without rationale | Change Management requires justification |
| Skipping regression tests | Prior gates must remain green |
| Changing spec without logging | Violates change control |
| Partial implementation | Each workstream should be complete or clearly deferred |

## Start

After orientation develop a comprehensive plan to do the following:
1. Verify dev environment is running (`make dev-api`)
2. Review DECISIONS.md for all open deferrals
3. Prioritize workstreams (recommend: leases first as foundational)
4. For each workstream: implement or reclassify, add tests, log resolution
5. Prepare for re-freeze (F0–F4, FREEZE-RECORD update)
