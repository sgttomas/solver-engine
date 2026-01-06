# SOLVER Engine — Senior Developer Init (Phase 7 — Package 7.2)

## Role

Senior developer for Phase 7 implementation. Build end-to-end integration flows per the
Development Directive. Stay within the governance chain in docs/spec/.

## Mission

Implement Package 7.2: Staleness Integration. Verify staleness propagation when upstream
artifacts are revised, and deliver acknowledge/re-execute workflows. Spec is UNFROZEN
(working draft V2.8.4) and will re-freeze at phase end.

## Current Package: 7.2 Staleness Integration

**Objective:** Staleness propagation and resolution flows.

**Deliverables (Directive §7.2):**
- Revise at Step 1 → downstream steps marked stale (progress + staleness)
- `/staleness` endpoint returns stale artifacts and stale trace links
- Acknowledge stale workflow flow
- Re-execute step flow clears staleness and allows progression

**Exit Gate:** γ4 (Staleness Flow, Gate E alignment for SSE as needed)

## Objectives

1. Verify revise action propagates staleness to downstream steps
2. Verify `/staleness` endpoint returns accurate stale artifacts/links
3. Verify `is_stale` flag in `/progress` response
4. Test acknowledge stale workflow
5. Test re-execute step after revision clears staleness and trace blocks
6. Ensure `can_complete` blocks completion when stale items remain

## Scope Boundaries

**In scope:**
- Staleness propagation (revise → downstream marked stale)
- `/staleness` endpoint verification
- `is_stale` flags in `/progress` response
- Acknowledge and re-execute flows
- Trace link staleness

**Out of scope:**
- Recovery scenarios (Package 7.3)
- Artifact count/trace validation (Gate A/B; already covered)
- Spec changes beyond staleness alignment (log deviations if needed)

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
4. docs/spec/5_SOLVER-Development-Directive-v1.5.1.md (Phase 7, Package 7.2)
5. docs/spec/4_SOLVER-Technical-Spec-V2.8.4.md (§9.4 staleness, Appendix C.5)
6. docs/spec/3_SOLVER-Architectural-Contract-v3.4.md (§11.3-11.4 staleness)
7. docs/spec/DECISIONS.md (P7.1-DEV-001, P7.1-DEV-002, P7.1-DEF-001)

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

Current package: 7.2 Staleness Integration
- Exit Gate: γ4 (Staleness Flow)

Upcoming packages:
- 7.3: Recovery Scenarios

## Key Paths

| Path | Focus |
|------|-------|
| apps/api/routes/workflows.py | Staleness endpoint, revise action |
| apps/api/application/workflow_service.py | Revise logic, staleness propagation |
| apps/api/application/traceability_service.py | Trace link management |
| apps/api/infrastructure/db/repositories/traceability.py | Trace queries |
| apps/api/infrastructure/db/models/traceability.py | Trace link model |
| apps/api/infrastructure/db/models/artifact.py | Artifact staleness flags |
| apps/web/hooks/use-workflow-queries.ts | Frontend staleness queries |
| apps/web/lib/sse-events.ts | SSE event list (ensure staleness events mapped) |

## Testing Strategy

**Unit/Integration (Backend):**
```bash
make test                    # All backend tests
make test-integration        # Integration tests only
make e2e                     # E2E API + SSE flow
```

**Frontend:**
```bash
cd apps/web && npm run lint
cd apps/web && npm run build
```

**Manual Verification (γ4 Criteria):**
```
1. Create workflow, advance through Pass 1 to Step 2 or 3
2. Revise Step 1 with feedback
3. Verify Step 2, 3 show is_stale=true in /progress; can_complete=false
4. Query /staleness endpoint — verify stale_artifacts and stale_trace_links
5. Acknowledge or re-execute downstream steps
6. Verify staleness cleared after resolution; can_complete flips true
7. Workflow can proceed to completion; SSE/history record staleness events
```

## Staleness Architecture

Per Tech Spec §9.4 and Contract §11.3-11.4:

| Concept | Description |
|---------|-------------|
| `is_stale` | Step flag in /progress when upstream revised |
| `stale_artifacts` | Artifacts with outdated upstream dependencies |
| `stale_trace_links` | Trace links invalidated by revision |
| `can_complete` | False if blocking stale items exist |
| `acknowledge` | Accept stale state without re-execution |
| `reexecute` | Clears stale state and re-runs generation |

## Anti-Patterns to Avoid

| Pattern | Why |
|---------|-----|
| Skipping staleness propagation | Contract §11.3 requires downstream marking |
| Ignoring trace links | Trace staleness blocks completion |
| Breaking existing tests | Verify `make e2e` still passes |
| Modifying γ1 test behavior | 7.1 is closed; add new tests for 7.2 |
| Bypassing SSE/audit | Contract §12/§11.3 require visible audit trail |

## Start

After orientation:
1. Verify dev environment is running (`make dev-api`, `make dev-web`)
2. Review existing staleness-related code in traceability_service.py
3. Identify gaps in staleness propagation flow
4. Plan implementation for γ4 verification and test coverage (progress, staleness endpoint, SSE/audit)
