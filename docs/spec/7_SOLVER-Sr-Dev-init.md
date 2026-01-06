# SOLVER Engine — Senior Developer Init (Phase 6 / Package 6.6)

## Role

Senior developer for Package 6.6 (SSE Event Handling). Implement only after plan approval.
Stay within the governance chain in docs/spec/.

## Mission

Deliver SSE event handling, reconnection, and event-driven query updates while complying with
Architectural Contract and Technical Spec requirements.

## Objectives (Package 6.6)

- Wire SSE event dispatcher through `useSequenceGuard`
- Implement event-driven TanStack Query invalidation for relevant events
- Trigger staleness refetch on `artifact.stale` / `artifact.stale_cleared`
- Update message thread state on message events
- Canonical refetch bundle integration per Contract v3.4 §10.4 (workflow + progress + staleness)
- Enforce "connected" only after canonical refetch completes with consistent `state_version`

## Scope Boundaries

**In scope:**
- SSE event handling in frontend (sequence guard + connection manager)
- Event-driven query invalidation/refetch (per events and reconnects)
- Canonical refetch after reconnect/gap recovery
- Integration with existing hooks (`useWorkflowConnection`, `useSequenceGuard`, `useCanAct`, `useCanMessage`)

**Out of scope:**
- Backend endpoint/schema changes (log deviations via Change Management if needed)
- New UI features beyond event-driven updates
- Phase 7 integration packages

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
4. docs/spec/0_Document-Type-Specifications-v2.1.1.md
5. docs/spec/1_SOLVER-README-v1.0.md
6. docs/spec/2_SOLVER-Design-Intent-v1.1.md (focus §1.2 cost asymmetry)
7. docs/spec/3_SOLVER-Architectural-Contract-v3.4.md (focus §10.4, §12.4, §16.9)
8. docs/spec/4_SOLVER-Technical-Spec-V2.8.2.md (focus §16 endpoints + SSE event types)
9. docs/spec/5_SOLVER-Development-Directive-v1.5.1.md (Package 6.6)
10. docs/spec/6_SOLVER-Change-Management-v2.0.1.md (governance for spec/deviation changes)
11. docs/spec/DECISIONS.md
12. docs/spec/FREEZE-RECORD.md (only when auditing governed docs)

## Current State

**Phase 6: Frontend — Package 6.6: SSE Event Handling**

Completed:
- 6.1: Next.js App Router, TanStack Query, Zustand, Tailwind
- 6.2: `useConnectionManager`, `calculateBackoff`
- 6.3: `useSequenceGuard`, `useWorkflowConnection`
- 6.4: `useCanAct`, `useCanMessage`
- 6.5: Workflow UI (launcher, detail, review, artifact display, message panel)
- V2.8.2 schema alignment (message response, progress schema, staleness schema, can_complete logic)

P6.5 deliverables ready for P6.6 integration:
- `useWorkflowQueries` canonical bundle with R7/C2 state_version verification
- `onDispatch` callback in `useWorkflowConnection` (not yet wired)
- Artifact endpoint implemented (`GET /workflows/{id}/artifacts/{aid}`)

Deviations logged:
- R11 EventSource handler timing (best-effort compliance)
- Reconnect-on-disconnect verification deferred to 6.6 (resolve now)

Next package:
- Phase 7 / Package 7.1: Workflow Lifecycle Integration

## Governance Context

- docs/spec/6_SOLVER-Change-Management-v2.0.1.md — required process for spec changes
- docs/spec/DECISIONS.md — deviations and approvals
- docs/spec/FREEZE-RECORD.md — audit-only reference

## Key Paths

| Path | Purpose |
|------|---------|
| apps/web/hooks/useConnectionManager.ts | Connection lifecycle + status |
| apps/web/hooks/useSequenceGuard.ts | Sequencing + gap handling |
| apps/web/hooks/useWorkflowConnection.ts | SSE integration wrapper (wire onDispatch here) |
| apps/web/hooks/use-workflow-queries.ts | Canonical query bundle (workflow + progress + staleness) |
| apps/web/hooks/useCanAct.ts | Action gating (R3-R6) |
| apps/web/hooks/api/ | Individual query/mutation hooks |
| apps/web/lib/api.ts | REST client + error handling |
| apps/web/lib/types.ts | TypeScript types for API responses |
| apps/web/components/workflow-detail.tsx | Main UI component (integrates queries + SSE) |
| docs/spec/DECISIONS.md | Log deviations here |
| docs/spec/6_SOLVER-Change-Management-v2.0.1.md | Governance for spec changes |

## Anti-Patterns to Avoid

| Pattern | Why |
|---------|-----|
| Bypassing `useSequenceGuard` | Violates Contract v3.4 §16.9 sequencing rules |
| Using `maxSeen` as correctness cursor | Contract requires `lastContiguousSequence` |
| Marking `connected` before canonical refetch | Violates Contract v3.4 §10.4 / R7 |
| Invalidating unrelated queries | Event-driven invalidation must be scoped to events |
| Spec or API shape changes without governance | Use Change Management + DECISIONS |

## Verification

```bash
cd apps/web && npm run lint
cd apps/web && npm run build
```

Manual verification (Package 6.6):
1. Live UI updates when SSE events arrive (progress, artifacts, messages)
2. Gap triggers reconnect with `from_sequence = lastContiguousSequence`
3. Canonical refetch bundle completes before `connected`
4. state_version consistency verified before actions re-enable

## Start

After orientation, propose a plan for Package 6.6 and wait for approval before implementation.
