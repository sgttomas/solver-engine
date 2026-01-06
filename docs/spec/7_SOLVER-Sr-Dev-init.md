# SOLVER Engine — Senior Developer Init (Phase 7)

## Role

Senior developer for Phase 7 implementation. Build end-to-end integration flows per the
Development Directive. Stay within the governance chain in docs/spec/.

## Mission

Implement Package 7.1: Workflow Lifecycle Integration. Deliver a complete workflow flow from
creation through completion, exercising all gates and transitions.

## Current Package: 7.1 Workflow Lifecycle Integration

**Objective:** Full end-to-end workflow execution.

**Deliverables:**
- Full flow: create → execute → gate → approve → advance → complete
- Pass 1 → Pass 2 transition
- Multi-step progression (Steps 1-3)

**Exit Gate:** γ1 (Workflow Lifecycle)

## Objectives

1. Verify backend workflow execution completes without LLM (mock adapter or stub)
2. Integrate frontend with live backend for full interactive flow
3. Test Pass 1 methodology generation through all steps
4. Test Pass 2 deliverable generation with human review gates
5. Verify workflow reaches `completed` status after all approvals

## Scope Boundaries

**In scope:**
- Workflow lifecycle integration (create → complete)
- Frontend-backend integration testing
- LLM mock/stub for deterministic testing
- Gate transitions (approve/revise/message)

**Out of scope:**
- Staleness flows (Package 7.2)
- Recovery scenarios (Package 7.3)
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
4. docs/spec/5_SOLVER-Development-Directive-v1.5.1.md (Phase 7 section)
5. docs/spec/4_SOLVER-Technical-Spec-V2.8.3.md (§8 state machines, §9 endpoints)
6. docs/spec/DECISIONS.md (recent entries for context)

## Current State

**Phase 6: Frontend — CLOSED**

All packages complete:
- 6.1: Next.js App Router, TanStack Query, Zustand, Tailwind ✓
- 6.2: `useConnectionManager`, `calculateBackoff` ✓
- 6.3: `useSequenceGuard`, `useWorkflowConnection` ✓
- 6.4: `useCanAct`, `useCanMessage` ✓
- 6.5: Workflow UI (launcher, detail, review, artifact display, message panel) ✓
- 6.6: SSE Event Handling (γ2 verified) ✓

P6 Closure Notes:
- Workflow ID mismatch investigation: NO ISSUE FOUND (see DECISIONS.md P6.6-CLOSURE-001)
- Frontend/backend correctly aligned on `workflow_id` throughout
- E2E tests passing (3/3)

**Phase 7: Integration — ACTIVE**

Current package: 7.1 Workflow Lifecycle Integration
- Exit Gate: γ1 (Workflow Lifecycle)

Upcoming packages:
- 7.2: Staleness Integration (γ4)
- 7.3: Recovery Scenarios

## Key Paths

| Path | Focus |
|------|-------|
| apps/api/orchestration/graph.py | LangGraph state machine |
| apps/api/orchestration/nodes.py | Step execution logic |
| apps/api/application/workflow_service.py | Workflow lifecycle methods |
| apps/api/routes/workflows.py | Action endpoints (approve/revise) |
| apps/web/components/workflow-detail.tsx | Frontend workflow UI |
| apps/web/hooks/use-workflow-queries.ts | API integration |

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

**Manual Verification (γ1 Criteria):**
```
1. Create workflow with problem statement
2. Watch Pass 1 Step 1 execute (methodology generation)
3. Approve at gate
4. Repeat for Steps 2, 3
5. Transition to Pass 2
6. Approve each step with artifact review
7. Workflow reaches completed status
```

## LLM Integration Notes

For deterministic testing, consider:
- Mock LLM adapter returning canned responses
- Environment variable to switch providers
- Ensure LLM API key is configured in `apps/api/.env`

Current LLM config: `DEFAULT_LLM_PROVIDER` (openai/anthropic/google)

## Anti-Patterns to Avoid

| Pattern | Why |
|---------|-----|
| Skipping gate transitions | Contract requires human approval at gates |
| Hardcoding step logic | Use state machine from graph.py |
| Ignoring state_version | Optimistic concurrency is required |
| Breaking existing tests | Verify `make e2e` still passes |

## Start

After orientation:
1. Verify dev environment is running (`make dev-api`, `make dev-web`)
2. Review current E2E test coverage
3. Identify gaps in lifecycle flow
4. Propose implementation approach for γ1 verification
