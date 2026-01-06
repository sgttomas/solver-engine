# SOLVER Engine — Senior Developer Init (Phase 7 — Package 7.3)

## Role

Senior developer for Phase 7 implementation. Build end-to-end integration/recovery flows per
the Development Directive. Stay within the governance chain in docs/spec/.

## Mission

Implement Package 7.3: Recovery Scenarios. Verify workflow recovery/resume after restart,
checkpoint integrity, and replay guarantees. Spec is UNFROZEN (working draft V2.8.4) and will
re-freeze at phase end.

## Current Package: 7.3 Recovery Scenarios

**Objective:** Workflow recovery, checkpoint persistence, and replay integrity.

**Deliverables (Directive §7.3):**
- Resume workflow after process restart without state loss
- Checkpoint saver produces/reads durable state (positions, artifacts, trace links)
- SSE/history replay remains consistent after recovery
- Gate C/D coverage: gating and recovery flows remain intact

**Exit Gate:** Recovery Gate (test-recovery) plus regression of γ1/γ4 as applicable

## Objectives

1. Validate checkpoint persistence and replay on restart/resume
2. Verify workflow position/state_version are coherent after recovery
3. Confirm SSE/history replay matches persisted sequence (no gaps/dupes)
4. Ensure approvals/revisions remain OCC-safe after recovery
5. Confirm staleness integration (γ4) does not regress under recovery flows

## Scope Boundaries

**In scope:**
- Recovery/resume flows (process restart, resume approvals/revisions)
- Checkpoint saver integrity (state, artifacts, trace links)
- SSE/history replay correctness post-restart
- Regression of staleness gating (γ4) under recovery scenarios

**Out of scope:**
- New feature work beyond recovery (keep Phase 7 scope)
- Spec changes beyond recovery alignment (log deviations if needed)

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
4. docs/spec/5_SOLVER-Development-Directive-v1.5.1.md (Phase 7, Package 7.3)
5. docs/spec/4_SOLVER-Technical-Spec-V2.8.4.md (recovery/checkpoint sections)
6. docs/spec/3_SOLVER-Architectural-Contract-v3.4.md (§11 recovery invariants)
7. docs/spec/DECISIONS.md (P7.1 deviations; Phase 7 deferrals)

## Current State

**Phase 6: Frontend — CLOSED**

All packages complete:
- 6.1: Next.js App Router, TanStack Query, Zustand, Tailwind ✓
- 6.2: `useConnectionManager`, `calculateBackoff` ✓
- 6.3: `useSequenceGuard`, `useWorkflowConnection` ✓
- 6.4: `useCanAct`, `useCanMessage` ✓
- 6.5: Workflow UI (launcher, detail, review, artifact display, message panel) ✓
- 6.6: SSE Event Handling (γ2 verified) ✓

**Phase 7: Integration — ACTIVE**

Completed packages:
- 7.1: Workflow Lifecycle Integration ✓ (γ1 PASSED)
  - DECISIONS.md: P7.1-DEV-001 (completed_at documented in V2.8.4), P7.1-DEV-002 (artifact availability), P7.1-DEF-001 (SSE replay coverage deferral)
  - E2E test: `test_gate_gamma1.py`

Current package: 7.3 Recovery Scenarios
- Exit Gate: Recovery Gate (test-recovery) + regression of γ1/γ4

Upcoming packages:
- 7.3: Recovery Scenarios

## Key Paths

| Path | Focus |
|------|-------|
| apps/api/orchestration/graph.py | Resume/restart behavior, checkpoint wiring |
| apps/api/application/workflow_service.py | Recovery-safe approvals/revisions (OCC) |
| apps/api/application/artifact_service.py | Revision persistence, supersedes integrity |
| apps/api/orchestration/checkpoint_saver.py | Custom checkpoint saver logic |
| apps/api/infrastructure/db/repositories/checkpoint.py | Checkpoint read/write |
| apps/api/routes/workflows.py | Resume endpoints, position/state coherence |
| apps/api/tests/e2e/ | Gate γ1/γ4 regression, recovery tests |

## Testing Strategy

**Unit/Integration (Backend):**
```bash
make test                    # All backend tests
make test-integration        # Integration tests only
make e2e                     # E2E API + SSE flow
make test-recovery           # Recovery gate
```

**Frontend:**
```bash
cd apps/web && npm run lint
cd apps/web && npm run build
```

**Manual Verification (Recovery Focus):**
```
1. Start workflow, advance into Pass 2
2. Persist checkpoints; stop/restart API process
3. Resume workflow; verify position/state_version and artifacts intact
4. Approve/revise after restart; verify OCC and staleness gating still enforce
5. Inspect SSE/history replay for gaps/dupes post-restart
```

## Staleness Architecture

Per Tech Spec §4/§9 and Contract §11:

| Concept | Description |
|---------|-------------|
| Checkpoint | Serialized workflow state (position, artifacts, links) for restart |
| Replay | SSE/history re-delivery after reconnect/restart |
| OCC | `state_version` prevents stale approvals after recovery |
| Staleness | γ4 behavior must persist across recovery flows |

## Anti-Patterns to Avoid

| Pattern | Why |
|---------|-----|
| Losing checkpoints on restart | Violates recovery objectives |
| Approving with stale state_version | Breaks OCC and Contract invariants |
| Ignoring SSE/history replay | Users need continuity after reconnect |
| Regressing γ1/γ4 flows | Prior packages are closed; prevent regression |
| Bypassing audit | Contract §12 requires visible audit trail |

## Start

After orientation:
1. Verify dev environment is running (`make dev-api`, `make dev-web`)
2. Review checkpoint saver and recovery code paths
3. Identify gaps in restart/resume and replay flows
4. Plan implementation for recovery gate and regression coverage (γ1/γ4)
