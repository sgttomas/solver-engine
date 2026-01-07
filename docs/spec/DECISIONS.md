# Architecture Decisions Log

This log records approved deviations from specification documents per
`docs/spec/6_SOLVER-Change-Management-v2.0.1.md`.

Note: filenames in this log reflect the names at the time of each decision.
Current canonical filenames may differ; see `docs/spec/` for the latest names.

---

## 2026-01-04 - Governance Transition: Unified Specification Set

**Context:** Backend (Phases 1–5) was built against partial specification set (Docs 0–3).
A comprehensive unified specification set (Docs 0–6) has been issued covering both
backend and frontend as one system.

**Action Taken:**
- Legacy docs moved to `docs/legacy/` (retained for reference)
- Unified docs installed to `docs/spec/` (now authoritative)
- Repository references updated (AGENTS.md, CLAUDE.md, README.md)

**Authority:** Unified docs in `docs/spec/` are now the single source of truth.
Legacy docs in `docs/legacy/` are not authoritative.

**Document Mapping:**

| Old (Legacy) | New (Authoritative) |
|--------------|---------------------|
| `0_SOLVER-Development-Directive.md` | `5_SOLVER-Development-Directive-v1.5.md` |
| `1_meta-prompt-structured-reasoning.md` | (retained in legacy; methodology source) |
| `2_structured-reasoning-architecture.md` | `3_SOLVER-Architectural-Contract-v3.4.md` |
| `3_solver-technical-spec.md` | `4_solver-technical-spec-V2.8.0.md` |

**New Documents:**
- `0_Document-Type-Specifications-v2.1.md` — Governance framework
- `1_SOLVER-README.md` — Project orientation
- `2_SOLVER-Design-Intent-v1.1.md` — Design rationale
- `6_SOLVER-Change-Management-v1.2.md` — Change control process

**Backend Contract Alignment:** The backend implementation is being updated to align
with the unified Architectural Contract (§9–12). Progress/staleness endpoints, state_version,
workflow_events table, and SSE from_sequence replay are being implemented.

---

## 2026-01-02 - P2.3
**Deviation:** Use custom SolverCheckpointSaver instead of langgraph.checkpoint.postgres.PostgresSaver
**Document:** docs/spec/3_solver-technical-spec.md
**Reason:** Installed langgraph-checkpoint-postgres v3.0.2 expects columns/tables absent from 001_initial_schema.py (checkpoint_ns, checkpoint_blobs, checkpoint_writes.type, checkpoint_writes.task_path, BYTEA storage); migrations are out of scope for P2.
**Approved by:** Architect
**Incorporated into spec:** docs/spec/3_solver-technical-spec.md updated to reference SolverCheckpointSaver and Gate D test changes.

## 2026-01-03 - P3.3
**Deviation:** Clear human_decision after routing instead of in process_decision_node
**Document:** docs/spec/3_solver-technical-spec.md §8.4
**Reason:** Doc 3 §8.4 clears human_decision in process_decision_node, but §8.2 route_after_decision reads it AFTER that node runs. Clearing before routing causes graph to default to "end" instead of correct branch. Resolution: clear in advance_node (approve path), structure_node (reject path), and validate_node (modify path).
**Approved by:** Co-Developer review + plan approval
**Incorporated into spec:** Updated docs/spec/3_solver-technical-spec.md §8.4 process_decision_node and advance_node.

## 2026-01-03 - P5.4 (RESOLVED 2026-01-05)
**Original Deviation:** Defer `/workflows/{id}/traceability` endpoint and `tools/verify_traces.py` (Gate B verification tool) beyond MVP; traceability_links persistence is implemented, but read/verification utilities are postponed.
**Document:** docs/spec/4_solver-technical-spec-V2.8.0.md §9 API Endpoints; Appendix A (Gate B)
**Resolution:** `/traceability` endpoint implemented with full filtering (from_step, to_step, stale_only). Gate B tests (7/7) passing. `verify_traces.py` tool remains deferred.
**Approved by:** Architect

## 2026-01-04 - P6.4
**Deviation:** Gate D mid-step recovery is not tested; restart/resume verification only covers awaiting_review checkpoints.
**Document:** docs/spec/3_solver-technical-spec.md Appendix A (Gate D)
**Reason:** LangGraph checkpoints at interrupt boundaries; deterministic mid-step recovery tests are brittle and non-deterministic in current harness.
**Approved by:** Architect

## 2026-01-04 - P6.5
**Deviation:** SSE `artifact.delta` events are emitted post-execution with synthetic chunks rather than true real-time streaming during generation.
**Document:** docs/spec/3_solver-technical-spec.md §9.2 SSE Event Types; Appendix A (Gate E)
**Reason:** MVP implements deterministic SSE sequence at API boundaries; true streaming during LLM generation is deferred.
**Approved by:** Architect

## 2026-01-05 - P6.2 R11 EventSource Handler Timing
**Deviation:** R11 requires handlers registered BEFORE connect; EventSource connects immediately on construction.
**Document:** docs/spec/3_SOLVER-Architectural-Contract-v3.4.md §14.1 (R11)
**Reason:** Native browser EventSource API initiates connection synchronously during `new EventSource(url)` constructor call. There is no pre-connect hook to register handlers beforehand. The implementation attaches handlers synchronously in the same JavaScript tick after construction, which is functionally equivalent since no events can fire until the current synchronous execution completes.
**Mitigation:** Handlers defined as functions before construction, attached immediately after in same tick. Guards check `internals.eventSource !== eventSource` to reject stale callbacks.
**Status:** Best-effort compliance accepted.
**Approved by:** Architect (Ryan Tufts)

## 2026-01-06 - P6.2 Verification: Reconnect-on-disconnect Evidence Deferred
**Deviation:** Package 6.2 verification criterion "Reconnects on disconnect" could not be reliably verified without a page reload.
**Document:** docs/spec/5_SOLVER-Development-Directive-v1.5.md §Package 6.2 Verification
**Reason:** EventSource did not consistently emit an error on idle stream disconnects; the client remained "connected" when the API was stopped or the network was set Offline, and the required automatic `connected → reconnecting → connected` transition could not be captured without a reload (which invalidates the test).
**Mitigation:** Re-verify after Package 6.6 adds SSE heartbeats/idle-timeout handling; capture the automatic reconnect transition without reload.
**Status:** Verification deferred; implementation unchanged.
**Approved by:** Architect (Ryan Tufts)

## 2026-01-06 - P6.5 Artifact Content Endpoint Gap (RESOLVED)
**Original Deviation:** Backend `GET /workflows/{id}/artifacts/{aid}` endpoint documented in Tech Spec Appendix C.4 but not implemented. Artifact display component shows placeholder when no content provided.
**Document:** docs/spec/4_SOLVER-Technical-Spec-V2.8.0.md Appendix C.4
**Resolution:** Endpoint implemented per Appendix C.4 spec. Migration 005 adds `updated_at` (with DB trigger) and `trace_id` columns. Response shape matches C.4 exactly with `artifact_type` = `step_name` and methodology markdown wrapped in `content_jsonb`.
**Status:** Endpoint implemented; deviation resolved.
**Approved by:** Architect (Ryan Tufts)

## 2026-01-06 - Tech Spec V2.8.1: API Schema Alignment
**Change Type:** Spec Amendment + Implementation Alignment
**Document:** docs/spec/4_SOLVER-Technical-Spec-V2.8.1.md
**Note:** The Technical Spec file was later renamed to `docs/spec/4_SOLVER-Technical-Spec-V2.8.2.md` (2026-01-06) to reflect subsequent amendments; this entry preserves the original V2.8.1 reference for historical accuracy.

**Background:** Co-Developer-1 identified three spec divergences during Package 6.5 implementation review:
1. Message endpoint returned `WorkflowResponse` but spec §16.7 defines `{message_id, status}`
2. Progress response had internal inconsistency between §9.1 and Appendix C.3
3. Staleness response missing fields from Appendix C.5

**Governance Decision:**

| Endpoint | Action | Rationale |
|----------|--------|-----------|
| Message | Align impl to spec | Minimal `{message_id, status}` is correct per §16.7 (non-state-mutating action) |
| Progress | Amend spec | §9.1 and C.3 had inconsistent field names; unified to single canonical schema |
| Staleness | Align impl to spec | Add missing fields per C.5: `has_stale_artifacts`, `position`, `blocking_reasons`; rename `stale_links` → `stale_trace_links` |

**Changes Made:**
- Tech Spec bumped V2.8.0 → V2.8.1
- Backend: MessageResponse, StepProgressEntry (+ timestamps), StaleArtifactEntry (+ artifact_type, blocking), StalenessResponse (+ has_stale_artifacts, stale_trace_links)
- Frontend: types.ts, api.ts, use-message.ts updated to match
- Contract tests: 10 tests added (test_api_contracts.py) to verify model shapes

**Verification:** All contract tests pass (10/10), frontend build passes, backend lint passes.
**Approved by:** Architect (Ryan Tufts)

## 2026-01-06 - Tech Spec V2.8.2: Schema Remediation Pass 2
**Change Type:** Spec Amendment + Bug Fix
**Document:** docs/spec/4_SOLVER-Technical-Spec-V2.8.2.md

**Background:** Code review identified issues with V2.8.1 alignment:
1. Message endpoint returned random UUID instead of actual persisted message ID
2. §9.3 claimed all responses include position, contradicting §16.7 minimal message response
3. §9.4 still used old field names (stale_links) and lacked V2.8.1 schema fields
4. C.3 showed numeric current_step but code uses string + current_step_number
5. C.5 can_complete semantics didn't document trace link blocking

**Issues Resolved:**

| # | Issue | Resolution |
|---|-------|------------|
| 1 | Message ID bug | Backend returns actual `message.id` from persisted Message record |
| 2 | §9.3 contradiction | Added exception clause for message endpoint minimal response |
| 3 | §9.4 outdated | Aligned with C.5: `stale_trace_links`, `has_stale_artifacts`, `blocking` |
| 4 | C.3 schema | `current_step` is string, `current_step_number` is integer |
| 5 | C.5 semantics | Documented trace links as blocking (not just artifacts with `blocking=true`) |

**Changes Made:**
- Tech Spec renamed V2.8.1 → V2.8.2
- Backend: `workflow_service.send_message()` returns message; `routes/workflows.py` uses `message.id`
- Cross-references updated in CLAUDE.md, AGENTS.md, README.md, and spec docs

**Verification:** Backend syntax verified, contract tests pass, frontend build passes.
**Approved by:** Architect (Ryan Tufts)

## 2026-01-06 - P6.5 Workflow List + Streaming Display Adjustment
**Change Type:** Implementation Deviation (Directive)
**Document:** docs/spec/5_SOLVER-Development-Directive-v1.5.1.md §Package 6.5 Deliverables ("Workflow list page", "Streaming artifact display")

**Background:** Package 6.5 implementation proceeded without a backend list endpoint and with SSE streaming reserved for Package 6.6. The UI shipped a workflow launcher (create + navigate by ID) instead of a list view, and the artifact display renders provided content but does not stream live updates.

**Decision:** Accept launcher-only UI and non-streaming artifact display for Package 6.5; defer list endpoint and live artifact streaming to later packages.

**Mitigation:** Provide create + navigate-by-ID flow; artifact display remains ready to render streamed content once SSE wiring lands in Package 6.6.

**Status:** Approved for Package 6.5; revisit in Package 6.6/7.x as needed.
**Approved by:** Architect (Ryan Tufts)

## 2026-01-06 - P6.6-SCOPE-001: Backend Heartbeat Change (DEVIATION)

**Type:** DEVIATION from Development Directive v1.5.1, Package 6.6

**Directive text:** "Out of scope: Backend endpoint/schema changes"

**Deviation:** Backend must emit `event: heartbeat` as JS-visible data events (not SSE comments) per Tech Spec §16.4.1.

**Rationale:** Without this change, frontend cannot comply with Tech Spec §16.4.1 (idle timer reset on heartbeat). Native SSE comments (`: keep-alive`) are not visible to JavaScript's `EventSource.onmessage` handler. A specification deviation (claiming heartbeat detection without actual heartbeat events) would be more severe than a directive scope deviation.

**Changes Made:**
- `apps/api/application/event_stream.py`: HEARTBEAT_EVENT sentinel renamed from `__heartbeat__` to `heartbeat`
- `apps/api/routes/workflows.py`: Replace `format_sse_comment("keep-alive")` with `format_sse_event("heartbeat", {...})`

**Critical Heartbeat Invariants:**
- Unsequenced: NO `sequence` field in payload (per §16.4.1)
- Not persisted: NOT written to `workflow_events` table (no DB logging)
- No position: Exempt from Appendix C.1 envelope (per §16.4.1/§16.9 interpretation)
- JS-visible: Uses `format_sse_event`, NOT `format_sse_comment`

**Approval:** Architect (Ryan Tufts)
**Date:** 2026-01-06

## 2026-01-06 - P6.6-DEFER-001: Messages List Query Deferred (DEFERRAL)

**Type:** DEFERRAL

**Deliverable:** "Message updates wired to SSE events" per Directive v1.5.1 Package 6.6

**Implemented:**
- `messageKeys` factory created in `apps/web/hooks/api/use-message.ts` for invalidation
- `message.created`/`message.final` events wired in dispatcher to invalidate messages queries
- `reply_to_message_id` correlation enforced per §16.9

**Deferred:**
- `useMessages` query hook (no GET endpoint exists per Tech Spec V2.8.2)
- Messages list UI component

**Rationale:** Tech Spec V2.8.2 does not define a messages list GET endpoint. Creating a stub hook would risk spec drift. Query key factory and invalidation wiring are ready for when the endpoint exists.

**Resolution:** Phase 7 or later when messages list API is defined.
**Approved by:** Architect (Ryan Tufts)
**Date:** 2026-01-06

## 2026-01-06 - P6.2-RECONNECT-001: Reconnect-on-disconnect Verified (RESOLUTION)

**Type:** RESOLUTION of prior deferral (P6.2 Verification: Reconnect-on-disconnect Evidence Deferred, 2026-01-06)

**Original deferral:** Package 6.2 verification criterion "Reconnects on disconnect" could not be reliably verified without a page reload. EventSource did not consistently emit an error on idle stream disconnects.

**Resolution:** Package 6.6 implements idle timeout detection per Tech Spec §16.4.1:
- `useConnectionManager.ts` now resets idle timer on every message (including heartbeats)
- Idle timeout (60s no messages) triggers resync via `scheduleReconnect()`
- Bounded retries (maxRetries=5) lead to `failed` status if recovery fails
- Backend heartbeats are now JS-visible data events (not SSE comments)

**Evidence:**
- `useConnectionManager.ts:303-317`: Idle timer reset on handleMessage
- `useConnectionManager.ts:308-316`: Idle timeout triggers reconnect
- `apps/api/routes/workflows.py:2577-2587`: Heartbeat as data event

**Status:** RESOLVED
**Verified by:** Senior Developer
**Date:** 2026-01-06

## 2026-01-06 - P6.6-INTERP-001: Appendix C.1 Envelope for Sequenced Events Only (CLARIFICATION)

**Type:** CLARIFICATION NOTE (not a spec change or deviation)

**Spec tension:** Appendix C.1 states "all SSE events include sequence/position". Tech Spec §16.4.1 states "heartbeats carry no sequence".

**Interpretation:** C.1 envelope requirements apply to sequenced events only. Heartbeats are explicitly unsequenced per §16.4.1 and Contract §16.9, exempt from C.1 envelope requirements.

**Heartbeat payload:**
```json
{
  "event_type": "heartbeat",
  "workflow_id": "...",
  "timestamp": "..."
}
```

**Implementation:**
- `apps/web/lib/sse-events.ts`: Discriminated union with `SequencedSSEEvent` (requires sequence) and `HeartbeatEvent` (no sequence)
- Type guards `isSequencedEvent()` and `isHeartbeat()` for safe discrimination

**Status:** Clarification accepted; no spec change required.
**Noted by:** Senior Developer
**Accepted by:** Architect (Ryan Tufts)
**Date:** 2026-01-06

## 2026-01-06 - P6.6-CLOSURE-001: Workflow ID Mismatch Investigation (NO ISSUE FOUND)

**Type:** INVESTIGATION RESULT

**Reported Issue:** Workflow detail page shows loading/error state. Claimed root cause: frontend URL uses database `id` (auto-increment integer); backend expects `workflow_id` (UUID).

**Investigation Findings:**

| Claim | Actual |
|-------|--------|
| Database `id` is auto-increment integer | `id` is UUID PRIMARY KEY |
| Frontend uses database `id` | Frontend correctly uses `workflow_id` from API response |
| Mismatch between frontend/backend | Both consistently use `workflow_id` |

**Code Flow Verified:**
1. `POST /workflows` → returns `WorkflowResponse { workflow_id: string, ... }`
2. Frontend stores `result.workflow_id` (`workflow-launcher.tsx:65`)
3. Navigation: `/workflow/${workflow_id}` (`workflow-launcher.tsx:74`)
4. Page extracts `params.id`, passes to `WorkflowDetail` (`page.tsx:26`)
5. API call: `GET /workflows/${workflowId}` (`api.ts:131`)
6. Backend: queries `WHERE workflow_id = ?` (`workflow.py:275`)

**Verification:**
- `make e2e` passes (3/3 tests)
- `GET /api/v1/workflows/{workflow_id}` returns correct workflow
- `GET /api/v1/workflows/{internal_id}` correctly returns 404

**Conclusion:** The reported issue does not exist in the current codebase. The frontend and backend are correctly aligned on using `workflow_id` throughout. The 500 error observed during manual testing was caused by LLM API authentication failure (`OpenAI API error: 401`), not a routing mismatch.

**Status:** NO ISSUE FOUND - Investigation closed
**Verified by:** Senior Developer
**Date:** 2026-01-06

## 2026-01-07 - P7.1-DEV-001: completed_at Field in WorkflowResponse (DEVIATION)

**Type:** DEVIATION from Tech Spec V2.8.3 Appendix C.2 (resolved via V2.8.4 update)

**Spec text:** "C.2 reserved fields removed — Removed pass_1_gate_policy, created_by, last_actor_id, completed_at (not implemented in MVP)"

**Deviation:** `completed_at` field is exposed in `WorkflowResponse` API schema.

**Rationale:**
- Additive change (backward-compatible)
- Essential for γ1 verification (workflow completion timestamp)
- User explicitly approved during Round 4 implementation

**Files Modified:**
- `apps/api/routes/workflows.py:474-476` (WorkflowResponse schema)
- `apps/api/routes/workflows.py:662` (build_workflow_response)

**Resolution:** Field remains exposed. Spec amended in V2.8.4 to document `completed_at`.
**Approved by:** Architect (Ryan Tufts)
**Date:** 2026-01-07

## 2026-01-07 - P7.1-DEV-002: Artifact Availability at Gates (DEVIATION)

**Type:** DEVIATION from Development Directive v1.5.1 §7.1

**Directive text:** Implies "approve with artifact review" at each gate.

**Deviation:** Artifacts are not available via `/progress` endpoint's `has_artifact` field at `awaiting_review` state.

**Root Cause:**
- Pass 1 methodology docs tracked via `state.methodology` dict, not `latest_artifact_id`
- Pass 2 step packages persisted only after approval (`workflow_service.py:1258`)
- `/progress` endpoint derives `has_artifact` from `step_execution.latest_artifact_id`

**Impact:** γ1 test verifies lifecycle flow only; artifact presence not asserted at gates.

**Mitigation:**
- Artifacts ARE available via `/history?type=artifact` (audit log)
- Artifact counts remain Gate A scope (Phase 8)
- Manual verification can use `/history` endpoint

**Resolution:** Defer artifact persistence timing change to future package. γ1 scope is lifecycle verification.
**Approved by:** Architect (Ryan Tufts)
**Date:** 2026-01-07

## 2026-01-07 - P7.1-DEF-001: SSE Replay Coverage Deferral (DEFERRAL)

**Type:** DEFERRAL (Test coverage)

**Context:** Contract §12 / Tech Spec §16 define SSE as canonical event delivery. The γ1 package verifies `workflow.completed` via `/history?type=event` (audit) but does not explicitly assert replay via `/stream?from_sequence=0`.

**Decision:** Defer explicit SSE replay verification for `workflow.completed` to Gate E / Phase 8. Current γ1 scope is satisfied via audit history checks.

**Rationale:**
- Behavior is correct (event emitted and audited); missing only replay-path test coverage.
- Gate E already covers SSE infrastructure; defer to avoid scope creep in 7.1.

**Impact:** No functional deviation; coverage gap noted for future package.
**Resolution Target:** Phase 8 (Gate E enhancements) or earlier if convenient.
**Approved by:** Architect (Ryan Tufts)
**Date:** 2026-01-07

## 2026-01-07 - P7.3-DEF-001: Lease Recovery Deferral (DEFERRAL)

**Type:** DEFERRAL

**Deliverable:** "Runner crash → lease expiry → recovery" per Directive v1.5.1 §7.3 (deliverable #4)

**Specification References:**
- Development Directive v1.5.1 §7.3 deliverable #4
- Architectural Contract v3.4 §15.2 (Exclusive Execution Contract)
- Design Intent v1.1 §4.8 (Exclusive Execution via Leases)

**Context:** Phase 5 Package 5.1 (Lease Management) was not implemented during backend phases.
The following artifacts are absent:
- `workflow_execution_locks` table (Directive §Phase 2)
- `acquire_workflow_lease()`, `renew_workflow_lease()`, `release_workflow_lease()` functions (Directive §5.1)
- β4 gate tests (Directive §5.1)

P7.3 deliverable #4 requires lease infrastructure to test; cannot proceed without it.

**Decision:** Defer P7.3 deliverable #4 until Phase 5 Package 5.1 is implemented.

**Impact:**
- Recovery Gate (P7.3 exit gate) covers deliverables #1–#3 only
- β4 gate remains unverified
- Exclusive execution per Contract §15.2 / Design Intent §4.8 is not tested
- Concurrent runner exclusivity (Design Intent §3.5 scenario) is not exercised

**Resolution Target:** Future package when lease infrastructure is added (recommend Phase 8 or dedicated backlog item).
**Approved by:** Architect (Ryan Tufts)
**Date:** 2026-01-07
