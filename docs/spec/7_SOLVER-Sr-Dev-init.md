# SOLVER Engine — Senior Developer Init (Phase 6 / Package 6.5)

## Role

Senior developer for Package 6.5 (Workflow UI). Implement only after plan approval. Stay
within the governance chain in docs/spec/.

## Mission

Deliver workflow UI that lets users create workflows, view progress, and take actions at review
gates while complying with Contract/Spec requirements.

## Objectives (Package 6.5)

- Workflow list page (display all workflows)
- Workflow detail page with step progress
- Review panel for `awaiting_review` state
- Artifact display that can render streaming content from local state (SSE wiring is 6.6)
- Action buttons use `useCanAct` / `useCanMessage` and surface reasons when disabled
- Approve/revise requests include `expected_position` and `expected_state_version`
- Message action does NOT require `expected_state_version` (Tech Spec V2.8.0 §16.7)

## Scope Boundaries

**In scope:**
- UI components and App Router routes
- TanStack Query hooks for REST endpoints
- Form state and submission
- Integration with existing hooks (`useWorkflowConnection`, `useCanAct`, `useCanMessage`)

**Out of scope:**
- SSE event handling and query invalidation (Package 6.6)
- API type definitions (spec is authoritative)
- Proxy rewrites or devtools

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
7. docs/spec/3_SOLVER-Architectural-Contract-v3.4.md (focus §13-14, §14.3, §16.7, §16.10)
8. docs/spec/4_SOLVER-Technical-Spec-V2.8.0.md (focus §16 endpoints; §16.7 message action)
9. docs/spec/5_SOLVER-Development-Directive-v1.5.1.md (Package 6.5)
10. docs/spec/6_SOLVER-Change-Management-v2.0.1.md (only if proposing doc changes)
11. docs/spec/DECISIONS.md
12. docs/spec/FREEZE-RECORD.md (only when auditing governed docs)

## Current State

**Phase 6: Frontend — Package 6.5: Workflow UI**

Completed:
- 6.1: Next.js App Router, TanStack Query, Zustand, Tailwind
- 6.2: `useConnectionManager`, `calculateBackoff`
- 6.3: `useSequenceGuard`, `useWorkflowConnection`
- 6.4: `useCanAct`, `useCanMessage`

Deviations logged:
- R11 EventSource handler timing (best-effort compliance)
- Reconnect-on-disconnect verification deferred to 6.6

## Key Paths

| Path | Purpose |
|------|---------|
| apps/web/app/ | App Router pages |
| apps/web/components/ | UI components |
| apps/web/hooks/ | Existing hooks to consume |
| apps/web/lib/ | REST helpers and utilities |
| docs/spec/DECISIONS.md | Log deviations here |

## Anti-Patterns to Avoid

| Pattern | Why |
|---------|-----|
| Inventing endpoint shapes | Tech Spec V2.8.0 §16 is authoritative |
| Implementing SSE event handling | Belongs to Package 6.6 |
| Silent disabled buttons | Contract V3.4 §14.3 requires user-visible reasons |
| Missing `expected_state_version` on approve/revise | Contract V3.4 §13.5 (R18) |
| Requiring `expected_state_version` for message | Tech Spec V2.8.0 §16.7 |
| Duplicating gating logic | Use `useCanAct` / `useCanMessage` |

## Verification

```bash
cd apps/web && npm run lint
cd apps/web && npm run build
```

Manual verification:
1. Create workflow via UI
2. View workflow list
3. View workflow detail with progress
4. Approve/revise at gate (gating enforced; reasons visible)

## Start

After orientation, propose a plan for Package 6.5 and wait for approval before implementation.
