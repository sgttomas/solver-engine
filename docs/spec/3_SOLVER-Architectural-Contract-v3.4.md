# SOLVER Architectural Contract

**Purpose:** Unified specification for implementing a reliable human-in-the-loop workflow engine. This document contains both architectural descriptions (how the system is structured) and contracts (what must be true for correctness).

**Audience:** A future implementer (human or AI) with access to the actual codebase.

**Scope:** Single-instance MVP with future-safe seams for multi-instance scaling.

**Entry Point:** For project orientation, start with `README.md` (or `SOLVER-Project-Orientation-v1.0.md`).

**Document Hierarchy:**
- **Design Intent (Why²):** `SOLVER-Design-Intent-v1.1.md` — Design rationale, first principles, rejected alternatives
- **This document (Why):** Architectural Contract — What must be true for correctness
- **Technical Specification (What):** `4_solver-technical-spec-V2.8.0.md` — Schemas, endpoints, implementation details
- **Development Directive (How):** `SOLVER-Development-Directive-v1.5.md` — Build phases, packages, execution order

**Document Structure:**
- **Part I: Architecture** — Descriptive. How the system is structured, why it exists, what components it has.
- **Part II: Contracts** — Prescriptive. Invariants that MUST hold. Uses normative language (MUST, SHALL, REQUIRED).
- **Part III: Verification** — Checklists for confirming contract compliance.
- **Part IV: Reference** — Glossary and version history.

---

# Part I: Architecture

*This section describes the system structure. It explains what SOLVER is, how components relate, and where seams exist for future scaling. This section is descriptive, not prescriptive.*

---

## 1. System Context

### 1.1 What SOLVER Is

SOLVER is a **structured workflow generator**. Given a problem statement for knowledge work, it produces detailed specifications for solving that problem — breaking complex tasks into smaller, gated steps that integrate into a coherent solution.

**What it produces:** Workflow orchestration documents with sufficient detail that humans and AI agents can use them to structure and execute complex work in their domains.

**The meta-property:** SOLVER itself is a structured workflow. The first instance can be used to build domain-specific instances that solve particular types of problems. The system is recursive: it generates the kind of structured guidance it itself follows.

**Who uses it:** Both humans and AI agents, working together on complex knowledge work that benefits from methodical decomposition and human oversight at key decision points.

### 1.2 Why Human Review Gates Exist

The system generates specifications that others will follow. Errors in early steps propagate into all downstream work. Human review gates exist to:
- Validate that generated specifications correctly capture intent
- Catch errors before they become foundations for further generation
- Ensure domain expertise shapes the output at critical junctures

### 1.3 Workflow Structure

A SOLVER workflow has two passes:
- **Definition pass:** Establishes the methodology — what needs to be done, in what order, with what constraints
- **Execution pass:** Applies the methodology to produce detailed specifications

Each pass has multiple steps, each potentially producing artifacts (methodology documents, structured packages). Review gates can be configured per-step or at pass boundaries.

**Staleness:** When an upstream artifact is revised, downstream artifacts that depend on it become "stale" and may need regeneration. The system surfaces staleness clearly and prevents completion when stale artifacts would corrupt the output.

---

## 2. Components

### 2.1 Component Overview

| Component | Responsibility |
|-----------|----------------|
| **Frontend** | Human-in-the-loop interface: displays progress, presents review gates, handles clarification exchanges, tracks staleness, enforces action safety |
| **API Layer** | REST endpoints for state queries and actions; SSE streaming for real-time updates |
| **Orchestration** | LangGraph-based workflow engine with interrupt gates and checkpointing |
| **Persistence** | PostgreSQL for workflow state, event log, artifacts, and audit trail |
| **Runner** | Background process that advances workflows through automated steps |

### 2.2 Frontend Role

The frontend provides the human-in-the-loop interface:
- Displays real-time generation progress via SSE
- Presents review gates where humans approve or request revision
- Supports clarification exchanges when the system needs more information
- Tracks staleness when upstream changes invalidate downstream artifacts
- Enforces action safety through client-side gating

### 2.3 Backend Role

The backend provides:
- Durable persistence of workflow state and history
- SSE streaming with replay support for client resynchronization
- Optimistic concurrency control via state versioning
- Exclusive execution guarantees for workflow advancement

### 2.4 Runner Role

The runner is a distinct concern from API request handling:
- Advances workflows through automated steps
- Holds exclusive leases to prevent concurrent advancement
- Operates idempotently (safe to retry)

This separation creates a clean seam for future multi-agent operation.

---

## 3. Data Model

### 3.1 Core Entities

| Entity | Purpose |
|--------|---------|
| **Workflow** | Master record with position, status, and state version |
| **Step Execution** | Per-step state within a workflow |
| **Artifact** | Output of a step (methodology doc or package); versioned with insert-per-revision |
| **Event** | Append-only record of state transitions; supports SSE replay |
| **Message** | Conversation thread entries for clarification exchanges |
| **Audit Log** | Immutable record of all actions for compliance |

### 3.2 Workflow Status vs Position Status

The system distinguishes between:

- **Workflow status** (`active`, `completed`, `abandoned`) — Lifecycle state. Is the workflow still in progress?
- **Position status** (`not_started`, `pending`, `in_progress`, `awaiting_review`, `approved`, etc.) — Execution state. What is the workflow currently doing?

The concept of "paused" or "not advancing" is derived from position status:
- `awaiting_review` → blocked on human approval
- `awaiting_clarification` → blocked on human input
- `revision_requested` → blocked until re-execution starts

A workflow with `workflow_status = active` and `position.status = awaiting_review` is active but not advancing.

### 3.3 Artifact Versioning Model

Artifacts use an **insert-per-revision** model:
- Each revision creates a new row with a new artifact ID
- The `supersedes` field links to the previous revision
- The `superseded_by` field links to the next revision (NULL if current)
- A view (`latest_artifacts`) provides the current version for each step

**Lineage keys** define what constitutes a single logical artifact:
- For methodology_doc: `(workflow_id, pass_type, step_number, document_type, document_version)`
- For step_package: `(workflow_id, pass_type, step_number, package_type)`

---

## 4. Data Flow

### 4.1 Request Flow

```
User Action → Frontend → REST API → Orchestration → Persistence
                                  ↓
                              LLM (Claude)
                                  ↓
                            SSE Events → Frontend → User Display
```

### 4.2 SSE Event Flow

```
State Change → Event Persisted → Broadcast Attempted → Client Receives
                    ↓                                        ↓
              (always durable)                    (best-effort delivery)
                                                            ↓
                                              Gap Detected → Replay Request
                                                            ↓
                                              Replay from Event Log → Client Catches Up
```

### 4.3 Action Flow

```
User Clicks Approve
       ↓
Frontend checks canAct (all prerequisites)
       ↓
Request with expected_state_version + expected_position
       ↓
Server validates expected state matches current
       ↓
[Match] → Atomic: append event + update snapshot + bump version → Success
[Mismatch] → 409 Conflict with current state → Client refetches
```

---

## 5. Technology Stack

### 5.1 MVP Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14+, TanStack Query, Zustand, Tailwind, shadcn/ui |
| API | FastAPI (Python 3.11+) |
| Streaming | SSE via sse-starlette |
| Orchestration | LangGraph 1.0+ with PostgresSaver |
| Database | PostgreSQL with pgvector |
| LLM | Claude API |
| Observability | LangSmith / Langfuse |

### 5.2 Key Libraries

- **TanStack Query**: Manages REST queries with caching, invalidation, and `isFetching` state
- **Zustand**: Manages connection state (status, sequence guard)
- **LangGraph**: Provides state machine, interrupts, and checkpointing
- **PostgresSaver**: LangGraph's PostgreSQL-backed checkpoint persistence

---

## 6. Seams & Scaling Path

### 6.1 What is a Seam?

A **seam** is a boundary designed for future replacement without rewrite. MVP implementation is simple, but the interface is stable.

### 6.2 Identified Seams

| Seam | MVP Implementation | Future Implementation |
|------|-------------------|----------------------|
| Event broadcast | In-process pubsub | Redis pubsub / NATS |
| Runner coordination | DB advisory lock | Distributed queue + locks |
| API instances | Single | N (load balanced) |
| Authentication | Deferred | SSO / multi-tenant |

### 6.3 Correctness Anchor

All correctness relies on **event log + snapshot**, not on in-memory connection state. This is why scaling from 1 → N instances is a transport/routing change, not a correctness change.

---

## 7. MVP Scope

### 7.1 What MVP Includes

- Single API instance
- Single runner/agent process
- PostgreSQL for all persistence
- In-process event broadcasting
- DB-backed execution locking
- Steps 1-3 of the 10-step workflow

### 7.2 What MVP Excludes

To avoid premature complexity:
- Distributed pub/sub (Kafka/NATS/Redis)
- Multiple API instances
- Multiple concurrent agents or worker fleets
- Complex scheduling/queuing infrastructure
- Multi-tenant authentication
- Steps 4-10 (scaffolded as stubs)

**Constraint:** MVP design does not block these; it preserves the seams.

---

# Part II: Contracts

*This section defines invariants that MUST hold for correctness. It uses normative language: MUST, SHALL, REQUIRED. Violations of these contracts indicate bugs.*

---

## 8. Core Principles (Normative)

### 8.1 Durable Truth + Replayable History

The system MUST treat the database as the source of truth for:
1. **Current workflow state** — a materialized snapshot
2. **Transition history** — an append-only event log

Every externally visible state change MUST be representable as an event that can be replayed to reconstruct state after failure or support client resynchronization.

### 8.2 Defense in Depth

Action safety MUST be enforced at two layers:
1. **Client-side gating** — block actions during uncertain states
2. **Server-side validation** — reject actions if state has changed

Neither layer alone is sufficient. Both MUST be implemented.

### 8.3 Canonical Convergence

After any disruption (gap, reconnect, error), the UI MUST converge to server truth via canonical refetch. SSE is a real-time optimization; it is NEVER authoritative. The server's REST responses define truth.

---

## 9. Persistence Contracts

### 9.1 Workflow Snapshot Contract

| Property | Requirement |
|----------|-------------|
| `workflow_id` | MUST be unique and stable |
| `position` | MUST include pass type, step number, step name, status |
| `workflow_status` | MUST be one of: `active`, `completed`, `abandoned` |
| `state_version` | MUST be a monotonically increasing integer |
| `state_version` increment | MUST occur on every accepted state transition |

### 9.2 Event Log Contract

| Property | Requirement |
|----------|-------------|
| `sequence` | MUST be monotonic and gap-free per workflow |
| Uniqueness | `(workflow_id, sequence)` MUST be unique (DB-enforced) |
| Durability | Events MUST be durable before considered committed |
| Stability | Sequences MUST survive server restarts |
| Queryability | MUST support "events with sequence > N" queries |
| Retention | MUST retain events for expected reconnection window (~5 minutes minimum) |

**Invariant:** The event log is the authoritative history. The snapshot is a materialized view reconstructable from events.

### 9.3 Artifact Contract

| Property | Requirement |
|----------|-------------|
| Identity | Each artifact MUST have a unique ID |
| Versioning | MUST use insert-per-revision model with `supersedes` links |
| Lineage uniqueness | Exactly one "latest" (superseded_by IS NULL) per logical lineage |
| Revision increment | New revision MUST equal previous revision + 1 (enforced by function) |
| Staleness | MUST track stale flag, reason, and timestamp |

### 9.4 Staleness Contract

The system MUST:
- Track which artifacts are stale
- Record why they are stale (which upstream change)
- Expose whether stale artifacts block completion (`can_complete`)
- Propagate staleness when new revisions are created (INSERT-triggered)

---

## 10. API Contracts

### 10.1 Required Endpoints

| Endpoint | Requirement |
|----------|-------------|
| `GET /workflows/{id}` | MUST return `state_version`, `position`, `workflow_status` |
| `GET /workflows/{id}/progress` | MUST return `state_version` matching workflow |
| `GET /workflows/{id}/staleness` | MUST return `can_complete` boolean |
| `GET /workflows/{id}/stream` | MUST support `from_sequence` parameter |
| `POST /workflows/{id}/actions/approve` | MUST validate expected state |
| `POST /workflows/{id}/actions/revise` | MUST validate expected state |
| `POST /workflows/{id}/actions/message` | MUST NOT require expected state (not state-mutating) |

### 10.2 Workflow Response Contract

Every workflow response MUST include:
- Workflow identifier
- Position (pass type, step number, step name, status)
- Workflow status
- State version
- Current gate (when `awaiting_review`)

### 10.3 Progress Response Contract

The progress response MUST include:
- `workflow_id`
- `state_version` (MUST match workflow.state_version)
- `current_pass`
- `current_step`
- `steps` array with per-step: `pass_type`, `step_number`, `step_name`, `status`, `phase`, `latest_artifact_id`, `latest_artifact_revision`, `artifact_stale`, `updated_at`

### 10.4 Canonical Refetch Bundle Contract

The canonical refetch bundle is: `{workflow, progress, staleness}`

Requirements:
1. Client MUST fetch all three after any disruption
2. Client MUST NOT enter `connected` state until all three succeed
3. `workflow.state_version` and `progress.state_version` MUST match
4. If versions mismatch, client MUST refetch (bounded retries)

### 10.5 Conflict Response Contract

On state mismatch, server MUST return HTTP 409 with:
```json
{
  "error_code": "STATE_CONFLICT",
  "message": "string",
  "current_position": { "pass_type": "...", "step_number": 0, "step_name": "...", "status": "..." },
  "current_state_version": 0
}
```

---

## 11. Action Safety Contracts

### 11.1 Optimistic Concurrency Contract

All state-mutating action endpoints MUST include:
- `expected_state_version`
- `expected_position`

**State-mutating** means: can change `position`, `status`, `current_gate`, or any field affecting action safety.

The `/actions/message` endpoint is NOT state-mutating (appends to thread only).

### 11.2 Server Validation Contract

If expected state does not match current state:
- Server MUST reject with HTTP 409
- Response MUST include current position and state_version

### 11.3 Transactional Transition Contract

When an action is accepted, the server MUST atomically:
1. Append the corresponding event(s) to the event log
2. Update the workflow snapshot
3. Increment `state_version`

**Invariant:** There MUST NOT be a state where event is logged but snapshot is stale, or vice versa.

### 11.4 Broadcast After Commit Contract

Events MUST be persisted to the database BEFORE live broadcast is attempted.

**Invariant:** If broadcast fails, the event still exists in the database and can be recovered via replay.

---

## 12. Streaming Contracts

### 12.1 Replay Contract

The SSE endpoint MUST accept `from_sequence` parameter:
```
GET /workflows/{id}/stream?from_sequence=N
```

Behavior requirements:
1. MUST replay all events with `sequence > N` in strict increasing order
2. MUST then stream live events
3. Live events MUST have sequence greater than last replayed (strict prefix)
4. Replay MUST NOT interleave with live events in a way that breaks monotonicity
5. If replay ordering cannot be guaranteed, server MUST fail the request

### 12.2 Delivery Contract

SSE delivery is **best-effort**. Events may be lost due to network issues.

**Replay is the correctness path.** Clients MUST NOT rely on receiving every live event.

### 12.3 Event Structure Contract

All sequenced events MUST include:
- `event_type` (discriminator)
- `sequence` (monotonic per workflow)
- `timestamp`
- `workflow_id`

### 12.4 Reconnection Window Contract

Server MUST support replay for connections within 5 minutes of disconnection.

**The Reconnection Cursor Invariant:**

> Client cursor = `lastContiguousSequence`. Server replay starts at `from_sequence=cursor`. No other values are correct.

This single rule prevents the most common SSE correctness bugs:

```
CORRECT:
  Client disconnects with lastContiguousSequence = 42
  Client reconnects with from_sequence=42
  Server replays events 43, 44, 45, ... in order
  Client receives exactly the events it missed, no duplicates, no gaps

WRONG (using maxSeen):
  Client disconnects with lastContiguousSequence = 42, maxSeen = 47
  Client reconnects with from_sequence=47  ← WRONG
  Events 43, 44, 45, 46 are never delivered ← DATA LOSS

WRONG (using sequence of last processed):
  Client processes event 42, has pending 44, 45
  Client reconnects with from_sequence=42  ← Would duplicate 42
  Server replays 43, 44, 45, ... but 44, 45 already in buffer ← COMPLEX

CORRECT SIMPLE RULE:
  Always use lastContiguousSequence as the cursor
  Always request from_sequence=lastContiguousSequence
  Server returns sequence > from_sequence
  Deduplication handles any overlap
```

**Implementation:**

```typescript
// Client reconnection
function reconnect() {
  const cursor = sequenceGuard.lastContiguousSequence;
  eventSource = new EventSource(`/stream?from_sequence=${cursor}`);
}

// Server replay (returns events with sequence > from_sequence)
async def stream_events(from_sequence: int):
    events = await get_events_after(workflow_id, from_sequence)
    for event in events:
        yield event  # sequence > from_sequence guaranteed
```

---

## 13. Frontend Reliability Contracts (R1-R19)

### 13.1 Sequence & Deduplication

| # | Contract |
|---|----------|
| R1 | Events with `sequence ≤ lastContiguous` MUST be dropped (no duplicate processing) |
| R2 | Sequence guard MUST NOT reset on reconnect (only on workflow change) |
| R10 | Deduplication MUST be based on `lastContiguous`, not `maxSeen` |

### 13.2 Connection & Sync

| # | Contract |
|---|----------|
| R7 | `connected` status ONLY after reconnect succeeds AND canonical refetch completes |
| R8 | Gap MUST trigger stream reconnect with `from_sequence` (refetch alone insufficient) |
| R9 | Events for wrong workflow ID MUST be dropped |
| R11 | Event handlers MUST be registered BEFORE connect is called |
| R13 | Failed refetch MUST result in `failed` status (not silent inconsistency) |
| R16 | Gap reconnect MUST NOT flicker through `connecting` state |
| R19 | Multiple rapid gaps MUST NOT cause reconnect storms (reentrancy guard) |

### 13.3 Buffering & Ordering

| # | Contract |
|---|----------|
| R12 | Pending set MUST be bounded (~100 max); overflow triggers recovery |
| R17 | Out-of-order events MUST be buffered, NOT dispatched until contiguous |

### 13.4 Action Gating

| # | Contract |
|---|----------|
| R3 | `canAct = false` until staleness query completes successfully |
| R4 | `canAct = false` while resyncing |
| R5 | `canAct = false` while reconnecting |
| R6 | `canAct = false` if `staleness.can_complete === false` |
| R14 | `canAct = false` if ANY canonical query is fetching (workflow, progress, staleness) |
| R15 | `canAct = false` unless `connectionStatus === 'connected'` |

### 13.5 Server Validation

| # | Contract |
|---|----------|
| R18 | Approve/revise requests MUST include expected position and state version |

---

## 14. Frontend State Machine Contracts

### 14.1 Connection Status Contract

Valid statuses: `disconnected | connecting | connected | reconnecting | resyncing | failed`

| ID | Contract |
|----|----------|
| C1 | When client cannot assert stream continuity and canonical freshness, it MUST NOT report `connected` |
| C2 | Client MUST enter `connected` only after: (1) stream established AND (2) canonical refetch completed |
| C3 | On gap detection: MUST transition to `resyncing` and initiate replay-capable reconnect without `connecting` flicker |
| C4 | Recovery attempts MUST be bounded; unrecoverable state MUST transition to `failed` |
| C5 | Status semantics: `reconnecting` = transport recovery; `resyncing` = correctness recovery; `failed` = user intervention required |

### 14.2 Sequence Guard Contract

State: `maxSeen`, `lastContiguous`, `pending` (set), `buffer` (map)

| Condition | Required Action |
|-----------|-----------------|
| First event | Initialize both `maxSeen` and `lastContiguous` to sequence |
| `sequence ≤ lastContiguous` | Drop (duplicate) |
| `sequence == lastContiguous + 1` | Advance `lastContiguous`, drain contiguous pending |
| `sequence > lastContiguous + 1` | Add to pending, buffer payload, update `maxSeen` |
| `pending.size > MAX` | Trigger overflow recovery |

**Clarification: `lastContiguous` vs `maxSeen`**

These two values serve different purposes:

| Value | Purpose | Used For |
|-------|---------|----------|
| `lastContiguous` | **Correctness cursor** — highest sequence where all prior sequences received | Deduplication (R1), replay requests (`from_sequence`), gap detection |
| `maxSeen` | **Telemetry only** — highest sequence ever observed | UI hints (e.g., "X events pending"), debugging, overflow detection |

**Critical:** Deduplication and replay MUST use `lastContiguous`, never `maxSeen`. Using `maxSeen` for deduplication would cause events to be incorrectly dropped during gap recovery.

**Implementation note:** `maxSeen` MAY be omitted entirely if no telemetry is needed. `lastContiguous` is REQUIRED.

### 14.3 Action Eligibility Contract

**canAct** MUST be true if and only if ALL of:
1. `connectionStatus === 'connected'`
2. `position.status === 'awaiting_review'`
3. Staleness state is known (not undefined, not errored)
4. All canonical queries are idle (none fetching)
5. `staleness.can_complete === true`

**canMessage** MUST be true if and only if:
1. `position.status` ∈ `{'awaiting_review', 'awaiting_clarification'}`
2. `connectionStatus` ∈ `{'connected', 'reconnecting', 'resyncing'}`

When `canAct` is false, UI MUST show reason.

---

## 15. Backend Execution Contracts

### 15.1 Runner Boundary Contract

Workflow advancement MUST be treated as "runner work" — a distinct concern from API request handling.

### 15.2 Exclusive Execution Contract

Requirements:
- Only one runner MUST advance a workflow at a time
- Exclusivity is per `workflow_id`
- Lease/lock MUST be time-bounded (renewable)
- Expired leases MUST be recoverable by another runner

### 15.3 Idempotency Contract

Runner operations MUST be safe to retry without corrupting state:
- MUST check `state_version` before advancing
- MUST reject if state has moved
- Event log prevents duplicate transitions

---

# Part III: Verification

*This section provides checklists for confirming contract compliance.*

---

## 16. Conformance Checklists

### 16.1 Persistence Checklist

- [ ] Workflow snapshot includes monotonic `state_version`
- [ ] `state_version` increments on every accepted transition
- [ ] Event log has per-workflow monotonic `sequence`
- [ ] `(workflow_id, sequence)` uniqueness is DB-enforced
- [ ] Event log supports "events after sequence N" queries
- [ ] Events are durable before acknowledged
- [ ] Sequences survive server restart
- [ ] Artifacts use insert-per-revision model with `supersedes` links
- [ ] Exactly one "latest" artifact per logical lineage (unique index enforced)
- [ ] Artifacts track staleness with reason
- [ ] Staleness propagates on new revision INSERT

### 16.2 Action Safety Checklist

- [ ] Approve endpoint requires `expected_state_version` and `expected_position`
- [ ] Revise endpoint requires `expected_state_version` and `expected_position`
- [ ] Mismatched expected state returns 409 with current state
- [ ] Accepted actions atomically: append event + update snapshot + bump version
- [ ] Message endpoint does NOT require expected state
- [ ] Events persisted before broadcast attempted

### 16.3 Streaming Checklist

- [ ] SSE endpoint accepts `from_sequence` parameter
- [ ] Replay delivers events with `sequence > from_sequence` in order
- [ ] Live events follow replay without interleaving
- [ ] All sequenced events include `event_type`, `sequence`, `timestamp`, `workflow_id`
- [ ] Replay supported for 5+ minute reconnection window

### 16.4 Execution Checklist

- [ ] Runner boundary is explicit (separate from request handlers)
- [ ] Exclusive execution is enforced (DB lock or equivalent)
- [ ] Leases are time-bounded with expiry
- [ ] Expired leases are recoverable
- [ ] Runner checks `state_version` before advancing
- [ ] Runner operations are safe to retry

### 16.5 Frontend: Sequence Guard Checklist

- [ ] First event initializes both `maxSeen` and `lastContiguous`
- [ ] Events with `sequence ≤ lastContiguous` are dropped (R1)
- [ ] Events with `sequence == lastContiguous + 1` advance and drain pending
- [ ] Events with `sequence > lastContiguous + 1` are buffered, NOT dispatched (R17)
- [ ] Pending set has maximum size; overflow triggers recovery (R12)
- [ ] Method exists to clear pending/buffer while preserving `lastContiguous`
- [ ] Guard is NOT reset on reconnect, only on workflow change (R2)

### 16.6 Frontend: Connection Manager Checklist

- [ ] Handlers registered BEFORE connect is called (R11)
- [ ] Events with non-matching workflow ID are dropped (R9)
- [ ] On gap: status becomes `resyncing` BEFORE reconnect (R16)
- [ ] Gap reconnect uses `from_sequence = lastContiguous` (R8)
- [ ] Gap reconnect does NOT transition through `connecting` (R16)
- [ ] Reentrancy guard prevents reconnect storms (R19)
- [ ] Overflow triggers recovery with preserved dedupe boundary (R12)
- [ ] `connected` set ONLY after canonical refetch completes (R7)
- [ ] Refetch failure results in `failed` status (R13)
- [ ] Remaining buffer discarded after successful refetch

### 16.7 Frontend: Action Gating Checklist

- [ ] `canAct` false when `connectionStatus != 'connected'` (R15)
- [ ] `canAct` false when `position.status != 'awaiting_review'`
- [ ] `canAct` false when staleness undefined or errored (R3)
- [ ] `canAct` false when ANY canonical query is fetching (R14)
- [ ] `canAct` false when `staleness.can_complete === false` (R6)
- [ ] `canMessage` true for `awaiting_review` OR `awaiting_clarification`
- [ ] `canMessage` true for `connected`, `reconnecting`, or `resyncing`
- [ ] `canMessage` false for `disconnected`, `connecting`, or `failed`
- [ ] UI shows reason when action is disabled

### 16.8 Frontend: API Request Checklist

- [ ] Approve includes expected position (pass type, step number, status)
- [ ] Approve includes expected state version
- [ ] Revise includes same expected state fields plus feedback
- [ ] 409 STATE_CONFLICT triggers query invalidation and user message

### 16.9 Frontend: SSE Event Checklist

- [ ] Events without sequence bypass ordering logic
- [ ] Sequenced events with `sequence ≤ lastContiguous` are dropped (R1)
- [ ] Out-of-order events are buffered, not dispatched (R17)
- [ ] Buffered events dispatched in order once contiguous
- [ ] Remaining buffer discarded after canonical refetch
- [ ] `message.delta`/`message.final` only apply if `reply_to_message_id` matches
- [ ] Domain error events do NOT change connection status
- [ ] Transport failures drive connection status toward `failed`

### 16.10 Frontend: UI Behavior Checklist

- [ ] Connection status is visible to user
- [ ] `resyncing` shows syncing indicator (spinner)
- [ ] `reconnecting` shows reconnecting indicator (spinner)
- [ ] `failed` shows failure indicator (static)
- [ ] `disconnected` shows disconnected indicator (static)
- [ ] Disabled actions show explanatory tooltip/reason

---

# Part IV: Reference

---

## 17. Glossary

### Architecture Terms

| Term | Definition |
|------|------------|
| **Snapshot** | Materialized current state of a workflow |
| **Event log** | Append-only history of state transitions |
| **Runner** | Process/agent that advances workflow through automated steps |
| **Seam** | Boundary designed for future replacement without rewrite |
| **Advisory lock** | DB-level lock that coordinates without blocking reads |
| **Pass** | Major workflow phase: definition (methodology) or execution (artifacts) |
| **Gate** | Human review checkpoint requiring explicit approval |

### Contract Terms

| Term | Definition |
|------|------------|
| **state_version** | Monotonic version number for optimistic concurrency |
| **sequence** | Monotonic event order within a workflow |
| **lastContiguous** | Highest sequence where all prior sequences received. **Correctness cursor** — used for deduplication and replay. |
| **maxSeen** | Highest sequence ever received (may have gaps). **Telemetry only** — never used for correctness decisions. Optional. |
| **pending** | Set of sequences received but not yet contiguous |
| **buffer** | Event payloads held for pending sequences |
| **gap** | Received sequence N+k without N+1 through N+k-1 |
| **canonical refetch** | REST query set for authoritative state: `{workflow, progress, staleness}` |
| **canAct** | Computed boolean: safe to approve/revise? Requires all prerequisites. |
| **canMessage** | Computed boolean: safe to send message? |
| **defense in depth** | Both client gating and server validation prevent invalid actions |

---

## 18. Version History

### Frontend Contract Lineage

| Version | Changes |
|---------|---------|
| V1.0–V1.3 | Initial spec, SSE standardization, guard fixes |
| V1.4 | Awaited refetch, action gating during resync |
| V1.5 | Sequence guard dedupe fix (lastContiguous not maxSeen) |
| V1.6 | Gap triggers reconnect, dispatch order fix |
| V1.7 | Buffering, reentrancy guard, server validation |
| V1.8 | Distilled to architectural contract |
| V1.9 | Strengthened from_sequence to MUST; expanded canMessage |
| V2.0 | Added substantive context: what SOLVER is, why gates exist |
| V2.1 | Aligned with tech spec V2.4: explicit 409 response schema |
| V2.2 | Aligned with tech spec V2.5: new SSE event types |
| V2.3 | Added Progress Response contract |
| V2.4 | Added Canonical Refetch Bundle; strengthened R14 |

### MVP Contract Lineage

| Version | Changes |
|---------|---------|
| V1.0 | Initial MVP architecture contract |
| V1.1 | Clarified SSE delivery; time-bounded runner lease |

### Unified Contract

| Version | Changes |
|---------|---------|
| V3.0 | Merged Frontend Contract v2.4 + MVP Architecture Contract v1.1 |
| V3.1 | Restructured into Part I (Architecture) + Part II (Contracts) + Part III (Verification) + Part IV (Reference) for clearer separation of descriptive vs prescriptive content |
| V3.2 | Added document hierarchy reference to Design Intent (Why²); positioned in four-document taxonomy |
| V3.3 | Added explicit clarification of `lastContiguous` vs `maxSeen` roles (§14.2); enhanced glossary definitions |
| V3.4 | Strengthened §12.4 Reconnection Window Contract with explicit cursor invariant: client cursor = lastContiguousSequence, server replay from from_sequence=cursor |

---

*SOLVER Architectural Contract v3.4*
*Unified specification with clear Architecture / Contracts separation*
