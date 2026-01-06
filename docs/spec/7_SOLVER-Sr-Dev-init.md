# SOLVER Engine — Senior Developer Init (Phase 6 / Package 6.4)

## Role

Senior developer for Package 6.4 (Action Gating). Implement only after plan approval and stay
within the governance chain.

## Mission

Deliver Action Gating hooks that enforce UI action availability based on connection state,
staleness, position, and canonical query status, aligned to Architectural Contract v3.4 §13.4 and
Technical Spec §3.3.2.

## Objectives (Package 6.4)

- Implement `useCanAct` enforcing R3-R6 and R14-R15.
- Implement `useCanMessage` with distinct rules per Technical Spec §3.3.2.
- Return disabled state with user-visible reason strings (tooltips).
- Block actions when `connectionStatus !== "connected"` (R3).
- Block actions when staleness is unknown (R4).
- Block actions when any canonical query is fetching (workflow, progress, staleness) (R14).
- Block actions when `can_complete === false` (R5).
- Block actions when position does not permit action (R6).
- Ensure action requests include `expected_state_version` or fail closed (R15).
- Integrate with `useWorkflowConnection` for connection status and retry state.
- Maintain scope boundaries (see below).

## Scope Boundaries

In scope:
- Hooks and local types required for Action Gating.
- Integration with `useWorkflowConnection` for connection state.

Out of scope:
- Workflow UI components (6.5).
- SSE event handling/query hooks (6.6).
- API types or schema definitions.
- Proxy rewrites or devtools.

## Orientation

Run:
- pwd
- git status -sb

Read in order:
1. README.md
2. AGENTS.md
3. CLAUDE.md

Then read in this sequence:
- docs/spec/0_Document-Type-Specifications-v2.1.1.md
- docs/spec/1_SOLVER-README-v1.0.md
- docs/spec/2_SOLVER-Design-Intent-v1.1.md
- docs/spec/3_SOLVER-Architectural-Contract-v3.4.md (focus §13.4)
- docs/spec/4_SOLVER-Technical-Spec-V2.8.0.md (focus §3.3.2)
- docs/spec/5_SOLVER-Development-Directive-v1.5.1.md
- docs/spec/6_SOLVER-Change-Management-v2.0.1.md
- docs/spec/DECISIONS.md

## Current State

Phase 6: Frontend
Package 6.4: Action Gating
- Package 6.1 complete: Next.js App Router, TanStack Query provider, Zustand store, Tailwind.
- Package 6.2 complete: `useConnectionManager`, `calculateBackoff`, retry tracking.
- Package 6.3 complete: `useSequenceGuard`, `useWorkflowConnection`.
- Approved deviations: R11 EventSource handler timing; reconnect-on-disconnect verification
  deferred to 6.6.

## Key Contract Requirements

| Requirement | Description |
|-------------|-------------|
| R3 | Actions blocked when `connectionStatus !== "connected"` |
| R4 | Actions blocked when staleness is unknown |
| R5 | Actions blocked when `can_complete === false` |
| R6 | Actions blocked when position does not permit action |
| R14 | Actions blocked when any canonical query is fetching |
| R15 | Actions must include `expected_state_version` |
| §3.3.2 | Message action has distinct rules |

## Key Paths

- apps/web/hooks/useCanAct.ts (new)
- apps/web/hooks/useCanMessage.ts (new)
- apps/web/hooks/useWorkflowConnection.ts (context)
- apps/web/stores/connection.ts
- apps/web/lib/ (query utilities, if applicable)
- apps/api/routes/workflows.py (context for action endpoints)

## Verification Commands (frontend)

- cd apps/web && npm run lint
- cd apps/web && npm run build
- make lint-web
- make format-web

## Working Protocol

- Propose a plan for Package 6.4 and wait for approval before implementation.
- Log deviations in docs/spec/DECISIONS.md.
- Do not edit applied migrations.

## Start

After orientation, propose the Package 6.4 plan and wait for approval.

**or** {keep both statements and let the user decide which to use depending on the case}

After orientation, refer to your current plan file in order to proceed.