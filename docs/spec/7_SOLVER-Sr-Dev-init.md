# SOLVER Engine — Senior Developer Init (Phase 6 Closure)

## Role

Senior developer for Phase 6 closure. Fix emergent issues blocking E2E verification before
proceeding to Phase 7. Stay within the governance chain in docs/spec/.

## Mission

Resolve the workflow ID mismatch issue that blocks full E2E UI testing. Package 6.6 (SSE Event
Handling) is complete and verified; this is a pre-existing bug from P6.5 or earlier.

## Current Issue: Workflow ID Mismatch

**Symptom:** Workflow detail page shows loading/error state instead of workflow data.

**Root Cause:**
- Frontend URL uses database `id` column (auto-increment integer)
- Backend API expects `workflow_id` column (UUID)
- The mismatch causes 404 or incorrect lookups

**Impact:** Blocks full E2E UI verification for P6.6 γ2 gate and beyond.

## Objectives

1. Investigate the ID routing mismatch between frontend and backend
2. Determine correct fix (frontend URL change vs backend lookup change)
3. Implement fix with minimal disruption
4. Verify E2E workflow detail page loads correctly
5. Document any deviations if spec interpretation is needed

## Scope Boundaries

**In scope:**
- Workflow ID routing fix (frontend and/or backend)
- Any emergent issues discovered during investigation
- E2E verification of workflow detail page

**Out of scope:**
- New features beyond bug fixes
- Phase 7 packages
- Spec changes (log deviations if needed)

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
4. docs/spec/3_SOLVER-Architectural-Contract-v3.4.md (§9 API design)
5. docs/spec/4_SOLVER-Technical-Spec-V2.8.2.md (§9 endpoints, response schemas)
6. docs/spec/DECISIONS.md (recent P6.6 entries for context)

## Current State

**Phase 6: Frontend — CLOSING**

Completed packages:
- 6.1: Next.js App Router, TanStack Query, Zustand, Tailwind ✓
- 6.2: `useConnectionManager`, `calculateBackoff` ✓
- 6.3: `useSequenceGuard`, `useWorkflowConnection` ✓
- 6.4: `useCanAct`, `useCanMessage` ✓
- 6.5: Workflow UI (launcher, detail, review, artifact display, message panel) ✓
- 6.6: SSE Event Handling (γ2 verified) ✓

P6.6 deliverables verified:
- Heartbeat as JS-visible data event (no sequence) ✓
- Event dispatcher wired with §9.2.1 invalidation matrix ✓
- Idle timeout detection (60s) ✓
- Canonical refetch + state_version consistency ✓

Blocking issue:
- Workflow ID mismatch prevents E2E UI testing

Next phase:
- Phase 7 / Package 7.1: Workflow Lifecycle Integration (after P6 closure)

## Key Paths to Investigate

| Path | Focus |
|------|-------|
| apps/web/app/workflows/[id]/page.tsx | URL param extraction |
| apps/web/components/workflow-detail.tsx | workflowId prop usage |
| apps/web/hooks/use-workflow-queries.ts | API calls with workflowId |
| apps/web/lib/api.ts | Endpoint URL construction |
| apps/api/routes/workflows.py | Backend route handlers |
| apps/api/infrastructure/db/models/workflow.py | DB model (id vs workflow_id) |

## Anti-Patterns to Avoid

| Pattern | Why |
|---------|-----|
| Using database `id` in URLs | Contract expects `workflow_id` (UUID) in API |
| Changing API contracts without governance | Use Change Management + DECISIONS |
| Breaking existing E2E tests | Verify `make e2e` still passes |

## Verification

```bash
# Frontend
cd apps/web && npm run lint
cd apps/web && npm run build

# Backend
make lint
make test

# E2E
make e2e
```

Manual verification:
1. Create workflow via launcher
2. Navigate to workflow detail page
3. Verify page loads with correct data
4. Verify SSE connection establishes
5. Verify actions work (if at review gate)

## Start

After orientation, investigate the workflow ID mismatch and propose a fix. Wait for approval
before implementation.
