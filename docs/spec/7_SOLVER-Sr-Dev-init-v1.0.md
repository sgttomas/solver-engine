# SOLVER Engine — Senior Developer Init (Phase 6 / Package 6.3)

## Role

Senior developer for Package 6.3 (Sequence Guard). Implement only after plan approval and stay within
the governance chain.

## Mission

Deliver a Sequence Guard that enforces ordered SSE processing with gap detection, buffering, and
recovery, aligned to the Architectural Contract and Technical Spec.

## Objectives

- Implement `useSequenceGuard` for `lastContiguousSequence` tracking (not `maxSeen`).
- Buffer out-of-order events; drain contiguous sequences when gaps fill.
- Drop events with `sequence <= lastContiguousSequence` (deduplication).
- Enforce bounded pending set (~100 max); overflow triggers recovery (R12).
- Integrate with `useConnectionManager` via `getLastContiguousSequence()` and gap-triggered resync.
- Maintain scope boundaries (no Action Gating 6.4, no UI 6.5, no SSE event handling/query hooks 6.6,
  no API types, no proxy rewrites, no devtools).

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
- docs/spec/3_SOLVER-Architectural-Contract-v3.4.md (especially §12.4, §14.2, §16.6)
- docs/spec/4_SOLVER-Technical-Spec-V2.8.0.md (relevant sections only)
- docs/spec/5_SOLVER-Development-Directive-v1.5.md
- docs/spec/6_SOLVER-Change-Management-v2.0.1.md
- docs/spec/DECISIONS.md

## Current State
Current Phase 6: Frontend
Current Package 6.3: Sequence Guard
- Package 6.1 complete: Next.js App Router, TanStack Query provider, Zustand store, Tailwind.
- Package 6.2 complete: `useConnectionManager`, `calculateBackoff`, connection retry tracking.
- Approved deviations: R11 EventSource handler timing; reconnect-on-disconnect verification deferred to 6.6.
- `useConnectionManager` expects `getLastContiguousSequence` (currently returns 0).


## Key Contract Requirements

| Requirement | Description |
|-------------|-------------|
| R1 | Drop events with `sequence <= lastContiguousSequence` |
| R10 | Deduplication must use `lastContiguousSequence` (not `maxSeen`) |
| R12 | Pending set must be bounded (~100 max); overflow triggers recovery |
| R17 | Out-of-order events buffered, not dispatched until contiguous |
| C3 | Gap detection triggers resyncing (no connecting flicker) |

## Key Paths

- apps/web/hooks/useConnectionManager.ts
- apps/web/hooks/useSequenceGuard.ts (new)
- apps/web/stores/connection.ts
- apps/web/lib/sse.ts
- apps/api/application/event_stream.py (context)

## Verification Commands (frontend)

- cd apps/web && npm run lint
- cd apps/web && npm run build
- make lint-web
- make format-web

## Working Protocol

- Propose a plan for Package 6.3; wait for approval before implementation.
- Log deviations in docs/spec/DECISIONS.md.
- Do not edit applied migrations.

## Start

After orientation, propose the Package 6.3 plan and wait for approval.
