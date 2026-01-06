# SOLVER Design Intent

**Purpose:** Design rationale and first principles for SOLVER's architecture. This document explains *why* the architectural contracts must be the way they are — the reasoning, rejected alternatives, and assumptions that would require rethinking.

**Audience:** Architects, senior developers, and AI agents who need to understand not just the rules, but when the rules might be wrong.

**Entry Point:** For project orientation, start with `README.md` and then `SOLVER-README-v1.0.md`.

**Relationship to Other Documents:**
- **This document (Why²):** Design rationale, first principles, rejected alternatives
- **Architectural Contract (Why):** What must be true for correctness
- **Technical Specification (What):** Schemas, endpoints, implementation details
- **Development Directive (How):** Build phases, packages, execution order

**Key Principle:** When challenging a decision, consult this document first. The answer to "why do we need X?" lives here, not in the contracts themselves.

---

## 1. The Core Problem

### 1.1 What We're Protecting Against

SOLVER generates specifications that become foundations for further work. The critical failure mode is:

> **An approval recorded against stale or incorrect state corrupts workflow integrity.**

This corruption is:
- **Silent** — the system doesn't know it happened
- **Persistent** — the bad state is now the source of truth
- **Propagating** — downstream work builds on the corrupted foundation

### 1.2 The Cost Asymmetry

| Outcome | Cost |
|---------|------|
| Bad approval (approved stale/wrong state) | **Catastrophic** — corrupted workflow, downstream rework, trust loss |
| Blocked approval (couldn't approve due to safety checks) | **Minor** — user waits, refetches, tries again |
| False conflict (rejected valid approval) | **Low** — user refetches, succeeds on retry |

**Design implication:** We should be conservative. Err toward blocking actions rather than allowing potentially invalid ones. A frustrated user who has to retry is vastly preferable to corrupted workflow state.

### 1.3 The Propagation Problem

Errors in early steps compound:

```
Step 1 error (bad problem definition)
    → Step 2 builds on wrong foundation (requirements miss the point)
        → Step 3 compounds the error (objectives misaligned)
            → All downstream work is waste
```

**Design implication:** Human review gates exist to catch errors before they become foundations. The gates must be trustworthy — if a human approves, the system must guarantee that approval was recorded against the state the human actually reviewed.

---

## 2. The Trust Model

### 2.1 What We Cannot Trust

| Component | Why We Can't Trust It |
|-----------|----------------------|
| **The network** | Delays, drops, reordering, partial failures, split-brain |
| **The client alone** | Stale cache, race conditions, browser bugs, malicious tampering |
| **The server alone** | User needs responsive UI; can't wait for round-trip on every state check |
| **In-memory state** | Process restarts, crashes, multiple instances |
| **Clocks** | Drift, skew, NTP issues — ordering by timestamp is unreliable |

### 2.2 What We Can Trust

| Component | Why We Can Trust It |
|-----------|---------------------|
| **Durable database state** | ACID guarantees, survives restarts, single source of truth |
| **Explicit versioning** | `state_version` provides total ordering without relying on clocks |
| **Monotonic sequences** | `sequence` per workflow provides event ordering |
| **Constraints enforced by DB** | Uniqueness, foreign keys, check constraints — can't be bypassed |

### 2.3 The Trust Hierarchy

```
                    ┌─────────────────────────┐
                    │   Database (Authority)   │
                    │   - Event log            │
                    │   - Workflow snapshot    │
                    │   - Constraints          │
                    └───────────┬─────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
              ▼                 ▼                 ▼
        ┌───────────┐    ┌───────────┐    ┌───────────┐
        │  Server   │    │  Server   │    │  Server   │
        │ Instance  │    │ Instance  │    │ Instance  │
        └─────┬─────┘    └─────┬─────┘    └─────┬─────┘
              │                │                │
              ▼                ▼                ▼
        ┌───────────┐    ┌───────────┐    ┌───────────┐
        │  Client   │    │  Client   │    │  Client   │
        │ (Browser) │    │ (Browser) │    │ (Browser) │
        └───────────┘    └───────────┘    └───────────┘
```

**Trust flows down, not up.** The database is authoritative. Servers read from and write to the database. Clients read from servers and must prove they have current state before writing.

---

## 3. The Failure Mode Catalog

These are the specific failures we're designing against.

### 3.1 Stale Read → Bad Action

```
Timeline:
T1: Client reads workflow state (version 5)
T2: Another client approves, state advances (version 6)
T3: First client approves based on stale version 5 state
    → Approval recorded against wrong state
```

**Mitigation:** Optimistic concurrency. Client must include `expected_state_version` in action requests. Server rejects if version doesn't match.

### 3.2 Network Partition → Split Brain

```
Timeline:
T1: Client A connected to Server 1
T2: Client B connected to Server 2
T3: Network partition between servers
T4: Both clients approve "simultaneously"
    → Which approval wins? Data corruption?
```

**Mitigation:** Database as single source of truth. Both servers write to same database. Database constraints (state_version check) ensure only one succeeds.

### 3.3 SSE Drop → Missed State Change

```
Timeline:
T1: Client connected via SSE, sees state at version 5
T2: Network hiccup, SSE events dropped
T3: State advances to version 7 (events 6, 7 lost)
T4: Client thinks it's at version 5, acts accordingly
    → Action based on stale understanding
```

**Mitigation:** 
1. Sequence numbers detect gaps (client knows it missed something)
2. Replay via `from_sequence` recovers missed events
3. Canonical refetch establishes ground truth
4. Client blocks actions until synchronized

### 3.4 Server Restart → Lost In-Memory State

```
Timeline:
T1: Workflow at review gate, client waiting
T2: Server crashes and restarts
T3: In-memory state lost — what was the workflow doing?
```

**Mitigation:** All state durable in database. Server reconstructs from event log + snapshot. Client reconnects and replays. No in-memory-only state that matters for correctness.

### 3.5 Concurrent Runners → Double Advancement

```
Timeline:
T1: Human approves step
T2: Runner A picks up workflow to advance
T3: Runner B also picks up same workflow (race condition)
T4: Both runners try to advance
    → Duplicate events? Corrupted state?
```

**Mitigation:** Exclusive execution via time-bounded leases. Only lease holder can advance. Lease in database, not in memory. Expired leases recoverable.

### 3.6 Approval During Generation → Premature Lock-In

```
Timeline:
T1: LLM generating artifact (streaming)
T2: User sees partial output, clicks Approve
T3: Final output differs from what user saw
    → Approved something user didn't actually review
```

**Mitigation:** Approval only valid in `awaiting_review` status, which only occurs after generation complete. `canAct` gating enforces this client-side. Server validates status server-side.

---

## 4. Key Design Decisions

### 4.1 Event Log + Snapshot (not just snapshot)

**Problem:** How do we recover from failures, support client resync, and maintain audit trail?

**Alternatives considered:**

| Approach | Pros | Cons |
|----------|------|------|
| Snapshot only | Simple, fast reads | No history, no replay, no audit, no debugging |
| Event sourcing only | Complete history, replay | Expensive reconstruction, complex queries |
| Event log + snapshot | History + fast reads | Two things to keep in sync |

**Decision:** Event log as authoritative history + snapshot as materialized view.

**Rationale:**
- Snapshot provides fast reads for API responses
- Event log provides replay for SSE recovery
- Event log provides audit trail for compliance (Gate F)
- Event log enables debugging ("what happened?")
- Atomic transaction keeps them in sync (event + snapshot in same commit)

**The invariant:** Snapshot is always reconstructable from event log. If they diverge, event log wins.

### 4.2 Optimistic Concurrency (not pessimistic locking)

**Problem:** How do we prevent actions against stale state?

**Alternatives considered:**

| Approach | Pros | Cons |
|----------|------|------|
| Pessimistic locking | Strong guarantee | Blocks UI, deadlock risk, bad UX, doesn't scale |
| No concurrency control | Simple | Data corruption on races |
| Optimistic concurrency | Non-blocking, good UX | Conflicts require retry |

**Decision:** Optimistic concurrency via `state_version`.

**Rationale:**
- Conflicts are rare in practice (single user per workflow typically)
- When conflicts occur, the cost is low (refetch and retry)
- Non-blocking means responsive UI
- Scales to multiple servers without coordination
- Database enforces the check atomically

**The pattern:**
```
Client: "I want to approve. I believe state_version is 5."
Server: "Current state_version is 5. Approved. New version is 6."
   -or-
Server: "Current state_version is 7. Rejected. Here's current state."
```

### 4.3 Defense in Depth (client AND server validation)

**Problem:** Where should we enforce action safety?

**Alternatives considered:**

| Approach | Pros | Cons |
|----------|------|------|
| Client only | Fast feedback, no round-trip | Client can be wrong, malicious, or buggy |
| Server only | Authoritative | Bad UX (user clicks, waits, gets rejected) |
| Both layers | Best UX + safety net | More code, must stay in sync |

**Decision:** Both client gating AND server validation.

**Rationale:**
- Client gating (`canAct`) prevents most invalid attempts before they happen
- Server validation catches what client misses (race conditions, bugs, tampering)
- Neither layer is sufficient alone
- The cost of implementing both is low compared to the cost of corruption

**The principle:** Client gating is a UX optimization. Server validation is the safety guarantee. If they disagree, server wins.

### 4.4 Insert-per-Revision (not update-in-place)

**Problem:** How do we version artifacts?

**Alternatives considered:**

| Approach | Pros | Cons |
|----------|------|------|
| Update in place | Simple, single row | Loses history, no diff, no rollback |
| Soft delete + new row | Preserves history | Complex queries, no clear lineage |
| Insert per revision with chain | Full history, clear lineage | More rows, slightly more complex |

**Decision:** Each revision creates a new row with `supersedes` link to previous.

**Rationale:**
- Enables Gate F (audit trail with deterministic versioning)
- Enables `/diff` endpoint (compare any two versions)
- Enables replay (reconstruct state at any point)
- Enables rollback (if ever needed)
- `latest_artifacts` view makes queries simple
- `create_artifact_revision()` function enforces invariants

**The invariant:** Exactly one "latest" (superseded_by IS NULL) per logical artifact lineage.

### 4.5 SSE with Replay (not WebSockets, not polling)

**Problem:** How do we deliver real-time updates to clients?

**Alternatives considered:**

| Approach | Pros | Cons |
|----------|------|------|
| Polling | Simple, HTTP-native | Latency, server load, battery drain |
| WebSockets | Bidirectional, efficient | Complex, binary, harder to debug, proxy issues |
| SSE | HTTP-native, text, simple | Unidirectional only (fine for our use case) |

**Decision:** Server-Sent Events with `from_sequence` replay.

**Rationale:**
- HTTP-native means works through proxies, load balancers
- Text-based means easy to debug, log, inspect
- Unidirectional is sufficient (actions go via REST)
- Replay via `from_sequence` is natural fit with event log
- Browser has built-in EventSource API
- Reconnection is built into the protocol

**The contract:** 
- SSE delivery is best-effort (events may be lost)
- Replay is the correctness path (client reconnects with `from_sequence`)
- Canonical refetch is the ground truth (REST endpoints authoritative)

### 4.6 Sequence Numbers (not timestamps)

**Problem:** How do we order events?

**Alternatives considered:**

| Approach | Pros | Cons |
|----------|------|------|
| Timestamps | Human-readable, familiar | Clock skew, drift, unreliable ordering |
| UUIDs | Globally unique | No ordering |
| Monotonic sequences | Reliable ordering, gap detection | Must be allocated carefully |

**Decision:** Per-workflow monotonic sequence numbers.

**Rationale:**
- Sequences provide total ordering within a workflow
- Gap detection is trivial (`received 5, expected 4` → gap)
- No clock synchronization needed
- Database enforces uniqueness (`workflow_id, sequence`)
- Advisory lock prevents allocation races

**The invariant:** For any workflow, sequences are contiguous at the source. Delivery may have gaps, but replay recovers them.

### 4.7 Canonical Refetch Bundle (not single-endpoint truth)

**Problem:** How does a client establish authoritative state after disruption?

**Alternatives considered:**

| Approach | Pros | Cons |
|----------|------|------|
| Single mega-endpoint | One call | Expensive, tightly coupled, hard to cache |
| Individual endpoints, no coordination | Simple | Inconsistent views possible |
| Bundle with version alignment | Consistent, cacheable | Must verify consistency |

**Decision:** Three-endpoint bundle `{workflow, progress, staleness}` with `state_version` alignment.

**Rationale:**
- Each endpoint is independently useful and cacheable
- `state_version` in both workflow and progress enables consistency check
- If versions mismatch, client knows to refetch
- Bundle defines "what does it mean to be synchronized"

**The contract:** Client enters `connected` state only after all three succeed and versions align.

### 4.8 Exclusive Execution via Leases (not queues, not free-for-all)

**Problem:** How do we prevent concurrent runners from corrupting state?

**Alternatives considered:**

| Approach | Pros | Cons |
|----------|------|------|
| Free-for-all | Simple | Race conditions, duplicate work, corruption |
| Global queue | Ordered processing | Single point of failure, head-of-line blocking |
| Per-workflow locks (permanent) | Exclusive access | Deadlock on crash |
| Per-workflow leases (time-bounded) | Exclusive + recoverable | Must handle expiry |

**Decision:** Time-bounded leases per workflow, stored in database.

**Rationale:**
- Only one runner advances a workflow at a time (exclusive)
- If runner crashes, lease expires and another runner can take over (recoverable)
- Database-backed means survives runner restarts
- Per-workflow means workflows are independent (no head-of-line blocking)
- `state_version` check before advancing means idempotent retry

**The invariant:** A workflow can only be advanced by the current lease holder. Lease expiry is the recovery path.

### 4.9 Runner Boundary (separate from API handlers)

**Problem:** Where does "advance workflow" code live?

**Alternatives considered:**

| Approach | Pros | Cons |
|----------|------|------|
| Inline in API handlers | Simple, synchronous | Blocks request, no retry, couples concerns |
| Background in same process | Async, retryable | Still coupled, hard to scale |
| Explicit runner boundary | Clean separation, scalable | More moving parts |

**Decision:** Runner is a distinct concern from API request handling.

**Rationale:**
- "Handle user action" and "advance workflow" are different responsibilities
- Separation enables future multi-runner deployment
- Separation enables different scaling strategies (API vs compute)
- Separation enables different retry/error handling strategies
- Clean seam for testing (mock runner, test API; mock API, test runner)

**The principle:** API handlers accept actions and persist them. Runners read pending work and execute it. They communicate through the database.

### 4.10 Methodology Foundation (Instance 0)

SOLVER implements the Instance 0 methodology — the abstract structured reasoning process that drives the two-pass workflow. The normative definition is in **Technical Specification V2.8.2 §Appendix D**.

Key implications:
- Methodology is defined before execution (Pass 1 precedes Pass 2).
- V1 -> V2 -> V3 iteration exists to refine and correct the methodology.
- Pass 2 gates are mandatory because early errors propagate.
- Four document types separate contract, tasks, guidance, and procedure.

---

## 5. The Scaling Anchor

### 5.1 The Core Insight

> **All correctness MUST be anchored in database contracts, not process topology.**

This means:
- 1 API instance or N API instances: same correctness properties
- 1 runner or N runners: same correctness properties
- In-process pubsub or distributed pubsub: same correctness properties

### 5.2 What This Enables

| Scaling Change | Required Work | Correctness Impact |
|----------------|---------------|-------------------|
| Add API instances | Load balancer, session affinity for SSE | None (DB is authority) |
| Add runner instances | Distributed lease coordination | None (DB is authority) |
| Replace in-process pubsub with Redis | Config change, adapter implementation | None (DB is authority) |
| Geographic distribution | Read replicas, latency considerations | None for writes (DB is authority) |

### 5.3 What This Forbids

| Anti-Pattern | Why It's Forbidden |
|--------------|-------------------|
| In-memory-only state that matters | Lost on restart, inconsistent across instances |
| Correctness dependent on message delivery | Messages are best-effort, not guaranteed |
| Ordering dependent on wall-clock time | Clocks drift, skew, lie |
| Single-instance assumptions in contracts | Blocks scaling without rewrite |

### 5.4 The Seams

Seams are boundaries designed for replacement without rewrite:

| Seam | MVP | Future | Interface Stability |
|------|-----|--------|---------------------|
| Event broadcast | In-process dict | Redis pubsub | Stable (publish/subscribe) |
| Runner coordination | DB advisory lock | Distributed queue | Stable (acquire/release/expire) |
| SSE delivery | Direct from API | Through CDN/proxy | Stable (EventSource protocol) |

**The rule:** Implementations behind seams can change. Interfaces at seams must not.

---

## 6. The Invariants That Matter Most

These are the invariants that, if violated, cause the most damage:

### 6.1 State Version Monotonicity

> `state_version` MUST increase on every accepted state transition.

**If violated:** Optimistic concurrency breaks. Stale-state actions succeed. Corruption.

### 6.2 Event Sequence Contiguity

> Event sequences MUST be gap-free at the source.

**If violated:** Replay produces incomplete history. Client can't detect all gaps. Audit trail has holes.

### 6.3 Atomic Transition

> Event append + snapshot update + version bump MUST be atomic.

**If violated:** Event without snapshot update = stale reads. Snapshot without event = lost history. Version without either = phantom conflicts.

### 6.4 Broadcast After Commit

> Events MUST be durable before broadcast is attempted.

**If violated:** Broadcast succeeds, commit fails = clients see state that doesn't exist. Commit succeeds, broadcast fails = fine (replay recovers).

### 6.5 Exclusive Execution

> Only one runner MUST advance a workflow at a time.

**If violated:** Duplicate events, race conditions, corrupted state, non-deterministic outcomes.

### 6.6 Latest Artifact Uniqueness

> Exactly one artifact with `superseded_by IS NULL` per logical lineage.

**If violated:** Which version is "current"? Ambiguous state, incorrect staleness propagation.

---

## 7. Assumptions and Triggers for Rethinking

### 7.1 Conflict Rate

**Assumption:** Optimistic concurrency conflicts are rare (<5% of actions).

**If violated:** 
- Symptom: Users frequently see "state changed" errors
- Trigger: Conflict rate exceeds 10%
- Rethink: Consider pessimistic locking for specific high-contention operations, or workflow-level mutex

### 7.2 Reconnection Window

**Assumption:** 5-minute replay window is sufficient for reconnection.

**If violated:**
- Symptom: Users on flaky connections can't recover
- Trigger: Significant user complaints about lost state
- Rethink: Extend retention, add event compaction with checkpoints

### 7.3 Event Log Growth

**Assumption:** Event log growth is manageable without compaction.

**If violated:**
- Symptom: Database storage growing unboundedly, queries slowing
- Trigger: Event table exceeds reasonable size threshold
- Rethink: Add compaction (snapshot + truncate old events), archive to cold storage

### 7.4 Single Workflow Focus

**Assumption:** Users typically work on one workflow at a time.

**If violated:**
- Symptom: Users need multiple workflows open simultaneously
- Trigger: Feature request for multi-workflow dashboard
- Rethink: SSE multiplexing, cross-workflow state management

### 7.5 Trust in Human Approval

**Assumption:** Human approval is meaningful and informed.

**If violated:**
- Symptom: Users approve without reviewing, rubber-stamp everything
- Trigger: Quality issues in downstream work despite "approved" artifacts
- Rethink: Approval friction (confirm dialogs, review checklists), approval audit

### 7.6 LLM Determinism

**Assumption:** LLM outputs are acceptable for the use case despite non-determinism.

**If violated:**
- Symptom: Inconsistent quality, users frequently request revision
- Trigger: Revision rate exceeds acceptable threshold
- Rethink: Prompt engineering, model selection, structured output constraints

### 7.7 Single-Tenant Operation

**Assumption:** MVP is single-tenant; multi-tenant is future work.

**If violated:**
- Symptom: Need to support multiple organizations
- Trigger: Multi-tenant requirement becomes real
- Rethink: Tenant isolation throughout (DB, API, runner), authentication, authorization, data segregation

---

## 8. Trade-offs Acknowledged

### 8.1 Consistency vs Availability

**Trade-off:** We favor consistency over availability.

**Consequence:** If database is unreachable, system is unavailable. We don't serve stale data.

**Justification:** Stale data leads to corrupt approvals. Unavailability is recoverable; corruption may not be.

### 8.2 Safety vs Speed

**Trade-off:** We favor safety over speed.

**Consequence:** Extra round-trips for validation. Blocked actions during resync.

**Justification:** The cost asymmetry (§1.2) — bad approval is catastrophic, blocked approval is minor.

### 8.3 Simplicity vs Optimization

**Trade-off:** MVP favors simplicity over optimization.

**Consequence:** Some operations are less efficient than they could be (e.g., full refetch vs incremental sync).

**Justification:** Correctness first. Optimize when we have data on what's slow.

### 8.4 Explicitness vs Convenience

**Trade-off:** We favor explicit state management over magic.

**Consequence:** More code, more explicit checks, less "it just works."

**Justification:** Explicit code is debuggable. Magic fails mysteriously. In a system where corruption is catastrophic, we need to understand every state transition.

---

## 9. What This Document Is NOT

### 9.1 Not Implementation Guidance

This document explains *why* decisions were made, not *how* to implement them. For implementation, see:
- Technical Specification (schemas, code structure)
- Development Directive (build phases, packages)

### 9.2 Not Immutable

If the problem space changes, these decisions should be revisited. This document should be updated when:
- Core assumptions are invalidated (§7)
- New failure modes are discovered (§3)
- Trade-offs need rebalancing (§8)

### 9.3 Not Complete

This document captures the *known* rationale. Some decisions may have been made for reasons not captured here. When discovered, add them.

---

## 10. Terminology Mapping

To ensure consistency across the document set, the following canonical terms are used:

### Workflow Structure

| Canonical Term | Aliases (avoid) | Definition |
|---------------|-----------------|------------|
| **definition pass** | Pass 1, methodology pass | First workflow pass; produces methodology documents |
| **execution pass** | Pass 2, artifact pass | Second workflow pass; applies methodology to produce packages |
| **step** | stage, phase (in this context) | Numbered unit within a pass (Steps 1-10) |
| **gate** | checkpoint, review point | Human approval point before workflow advances |

### State Management

| Canonical Term | Aliases (avoid) | Definition |
|---------------|-----------------|------------|
| **state_version** | version, optimistic lock | Monotonic integer for concurrency control |
| **sequence** | event_id, event_number | Monotonic integer for event ordering |
| **lastContiguous** | lastProcessed, cursor | Correctness cursor for deduplication/replay |
| **maxSeen** | highWaterMark | Telemetry only; never for correctness |

### Artifacts

| Canonical Term | Aliases (avoid) | Definition |
|---------------|-----------------|------------|
| **revision** | version (in artifact context) | Integer incrementing per artifact update |
| **supersedes** | replaces, parent | Link to previous revision |
| **latest** | current, active | Artifact with `superseded_by IS NULL` |
| **stale** | outdated, invalidated | Artifact needing regeneration |

### System Components

| Canonical Term | Aliases (avoid) | Definition |
|---------------|-----------------|------------|
| **runner** | worker, agent, executor | Process that advances workflows |
| **lease** | lock (when time-bounded) | Time-bounded exclusive execution right |
| **seam** | boundary, interface | Point designed for future replacement |

**Usage:** When writing documentation or code, use the canonical term. When reading legacy content, map aliases to canonical terms.

---

## 11. Summary: The Design Philosophy

### 11.1 In One Sentence

> SOLVER's architecture is designed to make corruption impossible, recovery automatic, and scaling a configuration change.

### 11.2 The Three Pillars

1. **Database as Authority:** All correctness anchored in durable, transactional database state.

2. **Defense in Depth:** Multiple layers of protection, each assuming others might fail.

3. **Explicit Over Magic:** Every state transition is visible, auditable, and reversible.

### 11.3 The Guiding Questions

When making architectural decisions, ask:

1. **What can go wrong?** (Failure modes)
2. **How do we detect it?** (Observability)
3. **How do we recover?** (Resilience)
4. **Does this scale?** (Future-proofing)
5. **Can we debug it?** (Operability)

---

## 12. Version History

| Version | Changes |
|---------|---------|
| V1.0 | Initial design intent document derived from SOLVER Architectural Contract v3.1 rationale |
| V1.1 | Added §10 Terminology Mapping for consistent language across document set |

---

*SOLVER Design Intent v1.1*
*The Why² — Design rationale and first principles*
