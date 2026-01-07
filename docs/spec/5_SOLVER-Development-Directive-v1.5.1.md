# SOLVER Development Directive v1.5.1

**Purpose:** Phased implementation plan for building SOLVER MVP (Steps 1-3), derived from architectural contracts and technical specification.

**Target Audience:** AI coding agents and developers implementing the system.

**Entry Point:** For project orientation, start with `README.md` (or `SOLVER-README-v1.0.md`).

**Document Hierarchy:**
- **Design Intent (Why²):** `SOLVER-Design-Intent-v1.1.md` — Design rationale, first principles
- **Architectural Contract (Why):** `SOLVER-Architectural-Contract-v3.4.md` — What must be true
- **Technical Specification (What):** `4_SOLVER-Technical-Spec-V2.8.4.md` — Schemas, endpoints, code
- **This document (How):** Development Directive — Build phases, packages, execution order

---

## Gate Definitions

### Infrastructure Gates (α-series)

| Gate | Name | Criterion |
|------|------|-----------|
| **α1** | Environment Runs | `docker-compose up` succeeds; `/health` returns 200 with database connected |
| **α2** | Schema Applied | All migrations run; constraints and triggers verified |
| **α3** | LangGraph Operational | Graph compiles; mock node execution succeeds |

### Contract Gates (β-series)

| Gate | Name | Criterion |
|------|------|-----------|
| **β1** | Event Sequence Safety | Concurrent event emission produces gap-free sequences (load test) |
| **β2a** | Replay Query Correctness | `get_events_after(sequence)` returns correct ordered events from database |
| **β2** | SSE Replay Works | `from_sequence=N` returns correct ordered events via SSE; live follows replay without interleaving |
| **β3** | Optimistic Concurrency | Stale `expected_state_version` returns 409 with current state |
| **β4** | Runner Lease Works | Lease acquisition, renewal, expiry, recovery, AND exclusivity (concurrent runners cannot both advance same workflow) |
| **β5** | Audit Attribution Correct | Session-based actor ID correctly recorded in audit log; replay timeline can reconstruct actor for every event |
| **β6a** | Broadcast After Commit | Events exist in DB even if live SSE delivery fails; broadcast never inside transaction |

### Integration Gates (γ-series)

| Gate | Name | Criterion |
|------|------|-----------|
| **γ1** | Workflow Lifecycle | Create → execute → gate → approve → advance works end-to-end |
| **γ2** | SSE Client Sync | Frontend receives events, handles gaps, recovers via replay |
| **γ3** | Action Gating | UI correctly disables actions based on connection/staleness/position |
| **γ4** | Staleness Flow | Upstream revision → downstream stale → acknowledge/re-execute works |

### Acceptance Gates (A-F from spec)

| Gate | Name | Criterion |
|------|------|-----------|
| **A** | Methodology Exists | Steps 1-3 Pass 1 produces 36 methodology documents (3 steps × 4 types × 3 versions) |
| **B** | Packages with Traces | Steps 1-3 Pass 2 produces packages with correct schema and trace links |
| **C** | Gating Enforcement | Pass 2 cannot advance without `approve`; `revise` loops; `message` doesn't bypass |
| **D** | Restart/Resume | Mid-step and `awaiting_review` recovery with no lost artifacts |
| **E** | SSE Flow | Full interactive review flow via REST + SSE |
| **F** | Audit Trail | Complete timeline reconstructable; artifacts versioned deterministically |

---

## Phases and Packages Summary

**Phase 1: Foundation**
Package 1.1: Project Skeleton
Package 1.2: Domain Models
Package 1.3: Database Schema

**Phase 2: Persistence Contracts**
Package 2.1: Event Log with Concurrency-Safe Sequences
Package 2.2: Workflow State Management
Package 2.3: Audit Logging with Session Attribution
Package 2.4: Staleness Trigger

**Phase 3: Orchestration**
Package 3.1: Graph Definition
Package 3.2: Node Implementations (Steps 1-3)
Package 3.3: Interrupt Gates
Package 3.4: Checkpointing

**Phase 4: API Layer**
Package 4.1: Workflow CRUD and Progress Endpoints
Package 4.2: SSE Streaming with Replay
Package 4.3: Human Action Endpoints
Package 4.4: Staleness Endpoints

**Phase 5: Runner and Leases**
Package 5.1: Lease Management
Package 5.2: Runner Loop
Package 5.3: LLM Integration

**Phase 6: Frontend**
Package 6.1: Project Setup
Package 6.2: Connection Manager
Package 6.3: Sequence Guard
Package 6.4: Action Gating
Package 6.5: Workflow UI
Package 6.6: SSE Event Handling

**Phase 7: Integration**
Package 7.1: Workflow Lifecycle Integration
Package 7.2: Staleness Integration
Package 7.3: Recovery Scenarios

**Phase 8: Verification**
Package 8.1: Gate A — Methodology Exists
Package 8.2: Gate B — Packages with Traces
Package 8.3: Gate C — Gating Enforcement
Package 8.4: Gate D — Restart/Resume
Package 8.5: Gate E — SSE Flow
Package 8.6: Gate F — Audit Trail


## Phase 1: Foundation

**Objective:** Runnable backend skeleton with database connectivity.

**Exit Gate:** α1 (Environment Runs)

### Package 1.1: Project Skeleton

**Deliverables:**
- FastAPI application structure per tech spec §11
- Docker Compose configuration (Postgres, API, Web)
- Environment configuration (`.env.example`, config module)
- Health endpoint returning `{"status": "ok", "database": "connected"}`

**Verification:**
```bash
docker-compose up -d
curl http://localhost:8000/health
# Returns: {"status": "ok", "database": "connected"}
```

### Package 1.2: Domain Models

**Deliverables:**
- Pure domain models (no DB dependencies): `PassType`, `StepName`, `StepStatus`, `HumanAction`
- State dataclasses: `Position`, `StepState`, `WorkflowState`
- Pydantic schemas for API request/response

**Verification:**
- Unit tests for enum values and state transitions
- No import errors from infrastructure modules

### Package 1.3: Database Schema

**Deliverables:**
- Alembic migration setup
- Initial migration with all tables from tech spec §7:
  - `instances`, `workflows` (with `state_version`)
  - `step_executions` (with `pending` status support)
  - `artifacts` (insert-per-revision model with `supersedes`/`superseded_by`)
  - `latest_artifacts` view
  - `create_artifact_revision()` function
  - `traceability_links`, `messages`, `audit_log`
  - `workflow_events`, `workflow_execution_locks`
  - `checkpoints`, `checkpoint_writes`
- All enums (note: `step_status` includes `pending`, `workflow_status` excludes `paused`)
- All constraints and indexes
- Staleness propagation trigger (INSERT-based: fires on new revisions via `create_artifact_revision()`)

**Verification:**
```bash
alembic upgrade head
# All tables created, constraints active
```

**Exit Gate:** α2 (Schema Applied)

---

## Phase 2: Persistence Contracts

**Objective:** Implement durable persistence contracts from Architectural Contract §9.

**Exit Gates:** β1, β2a, β5, β6a

**Note:** β2 (SSE Replay Works) requires the SSE endpoint implemented in Phase 4. Phase 2 verifies the underlying replay query correctness via β2a.

### Package 2.1: Event Log with Concurrency-Safe Sequences

**Deliverables:**
- `emit_and_persist_event()` function with advisory lock per tech spec §16.2
- `get_events_after()` for replay queries
- Broadcast-after-commit pattern (not inside transaction)
- In-process pubsub for MVP (`_subscribers` dict with queues)

**Verification:**
```python
# Concurrent emission test
async def test_concurrent_sequences():
    """
    Verify concurrency-safe sequencing produces gap-free sequences.
    
    NOTE: We validate contiguity and uniqueness, NOT completion ordering.
    Tasks may complete out of order, but sequences must form a 
    gap-free contiguous range.
    """
    tasks = [emit_and_persist_event(wf_id, "test", {}) for _ in range(100)]
    sequences = await asyncio.gather(*tasks)
    
    # Validate contiguity: sorted sequences form [1..N] with no gaps
    assert sorted(sequences) == list(range(1, 101)), "Sequences must be contiguous"
    
    # Validate uniqueness: no duplicate sequences
    assert len(set(sequences)) == 100, "No duplicate sequences allowed"
    
    # Validate in database
    result = await db.fetchrow("""
        SELECT COUNT(*) as count, 
               MAX(sequence) - MIN(sequence) + 1 as expected_count
        FROM workflow_events 
        WHERE workflow_id = $1
    """, wf_id)
    assert result['count'] == result['expected_count'], "DB must have no gaps"

# Replay query correctness test (β2a)
async def test_replay_query_correctness():
    """
    Verify get_events_after() returns correctly ordered events.
    This tests the database query layer, not SSE delivery.
    """
    wf_id = create_test_workflow()
    
    # Emit events in sequence
    for i in range(10):
        await emit_and_persist_event(wf_id, f"event_{i}", {"index": i})
    
    # Query from middle
    events = await get_events_after(wf_id, sequence=5)
    
    # Should get events 6, 7, 8, 9, 10 in strict order
    assert len(events) == 5
    sequences = [e.sequence for e in events]
    assert sequences == [6, 7, 8, 9, 10], "Events must be strictly ordered"
    
    # Query from start
    all_events = await get_events_after(wf_id, sequence=0)
    assert len(all_events) == 10
    assert [e.sequence for e in all_events] == list(range(1, 11))

# Broadcast-after-commit test (β6a)
async def test_broadcast_after_commit():
    """
    Event must exist in DB even if live broadcast fails.
    Recovery via replay must work.
    
    This verifies the critical invariant: events are durable BEFORE
    broadcast is attempted. If broadcast fails, replay recovers.
    """
    # Simulate broadcast failure (disconnect all SSE clients)
    await disconnect_all_sse_clients()
    
    # Emit event (should commit to DB despite no live delivery)
    seq = await emit_and_persist_event(wf_id, "test", {"data": "important"})
    
    # Verify event exists in DB
    event = await db.fetchrow(
        "SELECT * FROM workflow_events WHERE workflow_id = $1 AND sequence = $2",
        wf_id, seq
    )
    assert event is not None, "Event must be persisted even if broadcast fails"
    
    # Verify replay recovers the event
    events = await get_events_after(wf_id, seq - 1)
    assert len(events) == 1
    assert events[0]["payload"]["data"] == "important"
```

**Exit Gates:** β1 (Event Sequence Safety), β2a (Replay Query Correctness), β6a (Broadcast After Commit)

### Package 2.2: Workflow State Management

**Deliverables:**
- `get_workflow()` returning full state with `state_version`
- `increment_state_version()` atomic increment
- Workflow CRUD operations
- Step execution state management

**Verification:**
- State version increments on position/status changes
- State version does NOT increment on timestamp-only updates

### Package 2.3: Audit Logging with Session Attribution

**Deliverables:**
- `get_current_actor()` PostgreSQL function
- `record_step_audit()` trigger using session variable
- `with_actor_context()` Python helper
- Audit log query functions
- `reconstruct_timeline_with_actors()` function for replay

**Actor Attribution in Replay:**
When reconstructing the event timeline, actor identity must be recoverable for every event:
- For user actions (approve, revise, message): `actor_id` stored in audit_log and event payload
- For system actions (step transitions, artifact creation): `actor_id = 'system'` or runner ID
- Join pattern: `workflow_events JOIN audit_log ON (workflow_id, timestamp range)` for full attribution

**Verification:**
```python
async def test_audit_attribution():
    async with db.transaction():
        await with_actor_context(db, "user-123")
        await update_step_status(...)
    
    audit = await get_latest_audit(workflow_id)
    assert audit.actor_id == "user-123"

async def test_replay_actor_reconstruction():
    """
    Verify that replayed timeline can reconstruct actor for every event.
    This is required for Gate F (Audit Trail).
    """
    # Create workflow with mixed user/system actions
    wf_id = await create_workflow(actor="user-123")
    await approve_step(wf_id, actor="user-456")  # User action
    # System advances to next step (system action)
    
    # Reconstruct timeline
    timeline = await reconstruct_timeline_with_actors(wf_id)
    
    # Every event must have actor attribution
    for event in timeline:
        assert event.actor_id is not None, f"Event {event.sequence} missing actor"
        assert event.actor_id in ["user-123", "user-456", "system", "runner"]
```

**Exit Gate:** β5 (Audit Attribution Correct)

### Package 2.4: Staleness Trigger

**Deliverables:**
- `propagate_staleness()` trigger function
- Trigger on artifacts INSERT when `revision > 1` (new revision via `create_artifact_revision()`)
- Downstream artifact and trace link staleness propagation

**NOTE:** With insert-per-revision model, staleness propagates on INSERT of new revision rows,
NOT on UPDATE. The `create_artifact_revision()` function creates the new row; the trigger
fires on that INSERT to propagate staleness downstream.

**Verification:**
```python
async def test_staleness_propagation():
    # Create revision using the proper function (triggers INSERT)
    new_artifact_id = await db.fetchval(
        "SELECT create_artifact_revision($1, NULL, $2)",
        step_1_artifact_id, new_content_jsonb
    )
    
    # Verify downstream is marked stale
    step_2_artifact = await get_artifact(step_2_id)
    assert step_2_artifact.stale == True
    assert "upstream_step_1" in step_2_artifact.stale_reason
```

---

## Phase 3: Orchestration

**Objective:** LangGraph state machine with interrupt gates and checkpointing.

**Exit Gate:** α3 (LangGraph Operational)

### Package 3.1: Graph Definition

**Deliverables:**
- `create_graph()` function per tech spec §8.2
- Node stubs for all steps (Steps 4-10 return immediately)
- Edge routing based on `HumanAction`
- Conditional edges for step advancement

**Verification:**
- Graph compiles without errors
- Node names and edges match state machine diagram

### Package 3.2: Node Implementations (Steps 1-3)

**Deliverables:**
- `problem_definition_node()` — Pass 1 methodology + Pass 2 package
- `requirements_node()` — Pass 1 methodology + Pass 2 package
- `objectives_node()` — Pass 1 methodology + Pass 2 package
- LLM adapter interface (mock for testing)

**Verification:**
- Each node produces expected artifact structure
- Mock LLM returns canned responses for deterministic testing

### Package 3.3: Interrupt Gates

**Deliverables:**
- `human_review_gate()` with `interrupt()` call
- Gate policy handling (per-step for Pass 1, mandatory for Pass 2)
- Review unit construction for UI

**Verification:**
```python
async def test_gate_pauses():
    state = await graph.ainvoke(initial_state)
    assert state.step_state.status == StepStatus.AWAITING_REVIEW
    # Graph execution paused
```

### Package 3.4: Checkpointing

**Deliverables:**
- PostgresSaver configuration
- Checkpoint storage and retrieval
- Resume from checkpoint after restart

**Verification:**
```python
async def test_resume_from_checkpoint():
    """
    Resume uses POST /workflows/{id}/resume which triggers graph continuation
    using persisted checkpoint, NOT direct graph.ainvoke with resume=True.
    """
    # Run to gate, stop
    await client.post(f"/workflows/{wf_id}/actions/start")
    workflow = await client.get(f"/workflows/{wf_id}")
    assert workflow.json()["position"]["status"] == "awaiting_review"
    
    # Simulate restart (checkpoint persisted in PostgresSaver)
    # ... restart server ...
    
    # Resume via API endpoint (triggers graph continuation internally)
    response = await client.post(f"/workflows/{wf_id}/resume")
    assert response.status_code == 200
    
    # Verify continues from same position
    workflow = await client.get(f"/workflows/{wf_id}")
    assert workflow.json()["position"]["status"] == "awaiting_review"
```

---

## Phase 4: API Layer

**Objective:** REST endpoints with SSE streaming and optimistic concurrency.

**Exit Gates:** β2, β3

### Package 4.1: Workflow CRUD and Progress Endpoints

**Deliverables:**
- `POST /workflows` — Create workflow
- `GET /workflows/{id}` — Get state (includes `state_version`)
- `GET /workflows/{id}/progress` — Get step completion status (canonical refetch)
- `GET /workflows` — List workflows
- Position wrapper on all responses

**Verification:**
```bash
curl -X POST http://localhost:8000/api/v1/workflows \
  -H "Content-Type: application/json" \
  -d '{"problem": "Test", "created_by": "test"}'
# Returns workflow with state_version

curl http://localhost:8000/api/v1/workflows/{id}/progress
# Returns step progress for all steps
```

### Package 4.2: SSE Streaming with Replay

**Deliverables:**
- `GET /workflows/{id}/stream` endpoint
- `from_sequence` query parameter support
- Replay-then-live pattern per tech spec §16.4
- `sse-starlette` integration with correct framing

**Verification:**
```python
async def test_sse_replay():
    """Basic replay test."""
    # Emit 5 events
    for i in range(5):
        await emit_and_persist_event(wf_id, "test", {"n": i})
    
    # Connect with from_sequence=2
    events = await collect_sse_events(f"/stream?from_sequence=2")
    assert len(events) == 3  # Events 3, 4, 5
    assert events[0]["sequence"] == 3

async def test_sse_replay_monotonicity_during_emit():
    """
    Critical test: verify strict monotonicity when new events are
    emitted DURING replay. Client must see replay events followed
    by live events, strictly increasing, no gaps.
    """
    # Pre-emit events 1..K
    K = 5
    for i in range(1, K + 1):
        await emit_and_persist_event(wf_id, "test", {"n": i})
    
    # Connect with from_sequence=2 (should replay 3, 4, 5)
    N = 2
    client_events = []
    
    async def collect_with_concurrent_emit():
        async with sse_client(f"/stream?from_sequence={N}") as stream:
            event_count = 0
            async for event in stream:
                client_events.append(event)
                event_count += 1
                
                # After receiving first replay event, emit new live events
                if event_count == 1:
                    for j in range(K + 1, K + 4):  # Emit K+1, K+2, K+3
                        await emit_and_persist_event(wf_id, "test", {"n": j})
                
                # Stop after receiving all expected events
                if event_count >= (K - N) + 3:  # replay + live
                    break
    
    await collect_with_concurrent_emit()
    
    # Extract sequences
    sequences = [e["sequence"] for e in client_events]
    
    # Assert strict monotonicity (no interleaving, no duplicates)
    for i in range(1, len(sequences)):
        assert sequences[i] > sequences[i-1], f"Monotonicity violated: {sequences}"
    
    # Assert we got replay (3,4,5) then live (6,7,8)
    assert sequences == [3, 4, 5, 6, 7, 8], f"Expected replay-then-live, got: {sequences}"
```

**Exit Gate:** β2 (SSE Replay Works)

### Package 4.3: Human Action Endpoints

**Deliverables:**
- `POST /workflows/{id}/actions/approve` — with optimistic concurrency
- `POST /workflows/{id}/actions/revise` — with optimistic concurrency
- `POST /workflows/{id}/actions/message` — NOT state-mutating
- 409 response with `current_position` and `current_state_version`

**Verification:**
```python
async def test_409_conflict():
    workflow = await get_workflow(wf_id)
    
    # Modify state externally
    await increment_state_version(wf_id)
    
    # Attempt approve with stale version
    response = await client.post(
        f"/workflows/{wf_id}/actions/approve",
        json={"expected_state_version": workflow.state_version, ...}
    )
    assert response.status_code == 409
    assert response.json()["current_state_version"] > workflow.state_version
```

**Exit Gate:** β3 (Optimistic Concurrency)

### Package 4.4: Staleness Endpoints

**Deliverables:**
- `GET /workflows/{id}/staleness` — staleness report
- `POST /workflows/{id}/artifacts/{aid}/acknowledge-stale` — state-mutating
- `POST /workflows/{id}/steps/{n}/re-execute` — state-mutating
- Both emit events and bump `state_version`

**Verification:**
- Acknowledge requires `expected_state_version`
- Re-execute triggers runner and emits `step.reexecute_started`

---

## Phase 5: Runner and Leases

**Objective:** Workflow advancement with exclusive execution.

**Exit Gates:** β4

### Package 5.1: Lease Management

**Deliverables:**
- `acquire_workflow_lease()` — with time-bounded expiry
- `renew_workflow_lease()` — extend lease if held
- `release_workflow_lease()` — explicit release
- Expired lease recovery

**Verification:**
```python
async def test_lease_expiry():
    assert await acquire_workflow_lease(wf_id, "runner-1") == True
    assert await acquire_workflow_lease(wf_id, "runner-2") == False
    
    # Wait for expiry
    await asyncio.sleep(LEASE_DURATION + 1)
    
    # Now runner-2 can acquire
    assert await acquire_workflow_lease(wf_id, "runner-2") == True

async def test_lease_exclusivity_under_contention():
    """
    Two runners racing to advance must not both succeed.
    Only one advances; no double-emit of step transitions.
    
    This is part of β4 (Runner Lease Works) - verifies exclusivity guarantee.
    """
    events_before = await count_events(wf_id, "step.status_changed")
    
    # Start workflow at a gate
    await run_to_gate(wf_id)
    await client.post(f"/workflows/{wf_id}/actions/approve", json={...})
    
    # Race two runners trying to advance
    async def runner_advance(runner_id: str):
        if await acquire_workflow_lease(wf_id, runner_id):
            await advance_workflow(wf_id)
            await release_workflow_lease(wf_id, runner_id)
            return True
        return False
    
    results = await asyncio.gather(
        runner_advance("runner-1"),
        runner_advance("runner-2"),
        return_exceptions=True
    )
    
    # Exactly one runner should have advanced
    successes = [r for r in results if r is True]
    assert len(successes) == 1, "Only one runner should advance"
    
    # No duplicate step transition events
    events_after = await count_events(wf_id, "step.status_changed")
    assert events_after == events_before + 1, "Should emit exactly one step transition"
```

**Exit Gate:** β4 (Runner Lease Works)

### Package 5.2: Runner Loop

**Deliverables:**
- Runner loop that processes pending workflows
- Lease acquisition before advancement
- Graph resumption after human action
- Event emission on state changes

**Verification:**
- Runner advances workflow after approve
- Runner respects lease boundaries

### Package 5.3: LLM Integration

**Deliverables:**
- Claude API adapter
- Prompt templates for each step
- Streaming response handling
- Token counting and limits

**Verification:**
- Real LLM calls produce valid artifacts
- Streaming events emitted correctly

---

## Phase 6: Frontend

**Objective:** React frontend with reliability invariants from Architectural Contract §13-14.

**Exit Gates:** γ2, γ3

### Package 6.1: Project Setup

**Deliverables:**
- Next.js 14+ with App Router
- TanStack Query configuration
- Zustand stores for connection state
- Tailwind + shadcn/ui setup

**Verification:**
- `npm run dev` succeeds
- Basic page renders

### Package 6.2: Connection Manager

**Deliverables:**
- `useConnectionManager` hook
- EventSource lifecycle management
- Status states: `connecting`, `connected`, `reconnecting`, `resyncing`, `failed`
- Reconnection with backoff (R19 reentrancy guard)

**Verification:**
- Connects on mount
- Reconnects on disconnect
- Transitions through correct status states

### Package 6.3: Sequence Guard

**Deliverables:**
- `useSequenceGuard` hook
- `useWorkflowConnection` provider hook (wires sequence guard + connection manager for 6.5/6.6)
- `lastContiguousSequence` tracking (not `maxSeen`)
- Gap detection and buffering
- Overflow handling (R12 bounded pending)

**Verification:**
```typescript
// Out-of-order event
guard.process({sequence: 5, ...});  // Gap: missing 3, 4
expect(guard.pending.size).toBe(1);
expect(guard.lastContiguous).toBe(2);

// Fill gap
guard.process({sequence: 3, ...});
guard.process({sequence: 4, ...});
expect(guard.lastContiguous).toBe(5);  // Drained
```

### Package 6.4: Action Gating

**Deliverables:**
- `useCanAct` hook implementing R3-R6, R14-R15
- `useCanMessage` hook per Architectural Contract V3.4 §14.3 and Technical Specification V2.8.2 §16.7
- Disabled state with user-visible reasons
- Background refetch detection via `isFetching` on ALL canonical queries

**NOTE:** Per R14 and Architectural Contract v3.4 §13.4, `canAct` must be false when ANY
of the canonical queries (workflow, progress, staleness) are fetching. This prevents
actions during canonical refetch after reconnect.

**Verification:**
```typescript
// canAct must check ALL canonical queries
const workflowQuery = useWorkflow(workflowId);
const progressQuery = useProgress(workflowId);
const stalenessQuery = useStaleness(workflowId);

const isAnyCanonicalFetching = 
  workflowQuery.isFetching || 
  progressQuery.isFetching || 
  stalenessQuery.isFetching;

// Button disabled when ANY canonical query is fetching
expect(canAct).toBe(false) when isAnyCanonicalFetching;
```

- Button disabled when `connectionStatus !== 'connected'`
- Button disabled when staleness unknown
- Button disabled when ANY canonical query is fetching (R14)
- Button disabled when `can_complete === false`
- Tooltip shows reason

**Exit Gate:** γ3 (Action Gating)

### Package 6.5: Workflow UI

**Deliverables:**
- Workflow list page
- Workflow detail page with step progress
- Review panel for `awaiting_review` state
- Streaming artifact display

**Verification:**
- Can create workflow
- Can view progress
- Can approve/revise at gates

### Package 6.6: SSE Event Handling

**Deliverables:**
- Event dispatcher integrated with sequence guard
- TanStack Query invalidation on relevant events
- Staleness refetch on `artifact.stale` / `artifact.stale_cleared`
- Message thread updates
- Canonical refetch bundle integration per Architectural Contract v3.4 §10.4

**Canonical Refetch Integration:**
After reconnect/gap recovery, the canonical refetch bundle must be fetched:
```typescript
// After EventSource reconnect completes
await Promise.all([
  queryClient.invalidateQueries(['workflow', workflowId]),
  queryClient.invalidateQueries(['progress', workflowId]),
  queryClient.invalidateQueries(['staleness', workflowId])
]);

// Only transition to 'connected' after all complete successfully
// and state_versions are consistent
```

**Verification:**
- UI updates when events arrive
- Gap triggers reconnect with replay
- Canonical refetch after reconnect includes {workflow, progress, staleness}
- state_version consistency verified before entering 'connected' state

**Exit Gate:** γ2 (SSE Client Sync)

---

## Phase 7: Integration

**Objective:** End-to-end flows working correctly.

**Exit Gate:** γ1, γ4

### Package 7.1: Workflow Lifecycle Integration

**Deliverables:**
- Full flow: create → execute → gate → approve → advance → complete
- Pass 1 → Pass 2 transition
- Multi-step progression

**Verification:**
```
1. Create workflow with problem statement
2. Watch Pass 1 Step 1 execute (methodology generation)
3. Approve at gate
4. Repeat for Steps 2, 3
5. Transition to Pass 2
6. Approve each step with artifact review
7. Workflow reaches completed status
```

**Exit Gate:** γ1 (Workflow Lifecycle)

### Package 7.2: Staleness Integration

**Deliverables:**
- Revise at Step 1 → Step 2, 3 marked stale
- Acknowledge stale workflow
- Re-execute step workflow
- `can_complete` blocks completion when stale

**Verification:**
```
1. Complete Steps 1-3
2. Revise Step 1
3. Verify Steps 2, 3 show stale indicator
4. Verify "Complete" button disabled
5. Acknowledge or re-execute
6. Verify completion unblocked
```

**Exit Gate:** γ4 (Staleness Flow)

### Package 7.3: Recovery Scenarios

**Deliverables:**
- Network disconnect → reconnect → replay recovery
- Server restart → client resync
- Concurrent action → 409 handling
- Runner crash → lease expiry → recovery

**Verification:**
- Kill network, restore, verify no lost state
- Restart server, verify client recovers
- Race two approves, verify one wins cleanly

---

## Phase 8: Verification

**Objective:** All acceptance gates pass.

**Exit Gates:** A, B, C, D, E, F

### Package 8.1: Gate A — Methodology Exists

**Deliverables:**
- Test script that runs complete Pass 1
- Verification query for 36 documents

**Verification:**
```sql
SELECT step_name, document_type, document_version, COUNT(*)
FROM artifacts
WHERE workflow_id = $1 
  AND pass_type = 'definition'
  AND artifact_type = 'methodology_doc'
  AND step_number <= 3
GROUP BY step_name, document_type, document_version
HAVING COUNT(*) = 1;
-- Should return 36 rows
```

### Package 8.2: Gate B — Packages with Traces

**Deliverables:**
- Test script that runs complete Pass 2
- Schema validation for packages
- Trace link verification with coverage assertions

**Verification:**
```python
async def test_gate_b_packages_with_traces():
    packages = await get_step_packages(workflow_id)
    for pkg in packages:
        assert validate_schema(pkg.content_jsonb, pkg.package_type)
    
    # Verify trace links exist and have valid references
    traces = await get_trace_links(workflow_id)
    
    # Step 2 requirements must reference Step 1 elements
    step2_traces = [t for t in traces if t.to_step == 2]
    step1_ids = await get_all_element_ids(workflow_id, step=1)
    for trace in step2_traces:
        assert trace.from_id in step1_ids, f"Trace {trace.id} references invalid Step 1 ID"
    
    # Step 3 objectives must link to Step 2 requirements  
    step3_traces = [t for t in traces if t.to_step == 3]
    step2_req_ids = await get_requirement_ids(workflow_id)
    for trace in step3_traces:
        assert trace.from_id in step2_req_ids, f"Trace {trace.id} references invalid requirement"
    
    # Coverage maps exist
    step2_pkg = await get_package(workflow_id, step=2)
    assert "coverage_map" in step2_pkg.content_jsonb
    assert len(step2_pkg.content_jsonb["coverage_map"]) > 0
    
    step3_pkg = await get_package(workflow_id, step=3)
    assert "trace_map" in step3_pkg.content_jsonb
    assert len(step3_pkg.content_jsonb["trace_map"]) > 0
    
    # Verify all must-priority sources are covered (optional threshold)
    coverage = await compute_trace_coverage(workflow_id)
    assert coverage["must_priority_coverage"] == 1.0, "All must-priority items must be traced"
```

### Package 8.3: Gate C — Gating Enforcement

**Deliverables:**
- Test: attempt advance without approve → blocked
- Test: revise → loops back correctly
- Test: message during review → no state change

**Verification:**
```python
# Cannot advance without approve
with pytest.raises(GatingError):
    await advance_step(workflow_id)

# Revise loops
await revise_step(workflow_id, "needs work")
assert workflow.step_state.status == StepStatus.REVISION_REQUESTED

# Message doesn't advance
version_before = workflow.state_version
await send_message(workflow_id, "question?")
assert workflow.state_version == version_before
```

### Package 8.4: Gate D — Restart/Resume

**Deliverables:**
- Test: kill server mid-step → restart → resumes
- Test: kill at `awaiting_review` → restart → review UI works
- Artifact integrity verification

**Verification:**
```python
async def test_mid_step_restart():
    """
    Resume uses POST /workflows/{id}/resume endpoint which triggers
    graph continuation using persisted PostgresSaver checkpoint.
    """
    # Start step execution
    await client.post(f"/workflows/{wf_id}/actions/start")
    
    # Verify in progress
    workflow = await client.get(f"/workflows/{wf_id}")
    assert workflow.json()["position"]["status"] == "in_progress"
    
    # Kill server (checkpoint persisted)
    await restart_server()
    
    # Resume via API endpoint
    response = await client.post(f"/workflows/{wf_id}/resume")
    assert response.status_code == 200
    
    # Wait for completion and verify
    workflow = await wait_for_gate(wf_id)
    assert workflow["position"]["status"] == "awaiting_review"

async def test_gate_restart():
    """Review UI works after restart at awaiting_review."""
    # Run to gate
    await run_to_gate(wf_id)
    workflow = await client.get(f"/workflows/{wf_id}")
    assert workflow.json()["position"]["status"] == "awaiting_review"
    
    # Restart server
    await restart_server()
    
    # Review UI loads correctly (no resume needed - already at gate)
    workflow = await client.get(f"/workflows/{wf_id}")
    assert workflow.json()["position"]["status"] == "awaiting_review"
    
    # Can approve
    response = await client.post(
        f"/workflows/{wf_id}/actions/approve",
        json={"expected_state_version": workflow.json()["state_version"]}
    )
    assert response.status_code == 200
```

### Package 8.5: Gate E — SSE Flow

**Deliverables:**
- Test: full interactive flow via SSE
- Event sequence verification
- Reconnection scenario

**Verification:**
```python
async with sse_client(workflow_id) as client:
    await trigger_step_execution(workflow_id)
    
    events = []
    async for event in client:
        events.append(event)
        if event.type == "step.awaiting_review":
            break
    
    assert_monotonic_sequences(events)
    assert any(e.type == "artifact.delta" for e in events)
```

### Package 8.6: Gate F — Audit Trail

**Deliverables:**
- Replay function implementation
- Trace hash computation
- Timeline reconstruction test

**Verification:**
```python
trace = await replay_workflow(workflow_id)

# Deterministic
trace2 = await replay_workflow(workflow_id)
assert trace.trace_hash == trace2.trace_hash

# Complete
assert len(trace.events) >= expected_events
assert all(e.actor_id is not None for e in trace.events)
```

---

## Dependency Graph

```
Phase 1 ─────────────────────────────────────────────────────────────────────►
    │
    ├── 1.1 Skeleton ──► 1.2 Domain Models ──► 1.3 Schema
    │                                              │
Phase 2 ◄──────────────────────────────────────────┘
    │
    ├── 2.1 Event Log ──► 2.2 State Mgmt ──► 2.3 Audit ──► 2.4 Staleness
    │         │
Phase 3 ◄─────┘
    │
    ├── 3.1 Graph Def ──► 3.2 Nodes ──► 3.3 Gates ──► 3.4 Checkpoints
    │                                       │
Phase 4 ◄───────────────────────────────────┘
    │
    ├── 4.1 CRUD ──► 4.2 SSE ──► 4.3 Actions ──► 4.4 Staleness
    │                   │            │
Phase 5 ◄───────────────┘            │
    │                                │
    ├── 5.1 Leases ──► 5.2 Runner ──►┘──► 5.3 LLM
    │
Phase 6 ◄── (parallel with 4, 5 once 2 complete)
    │
    ├── 6.1 Setup ──► 6.2 Connection ──► 6.3 Sequence ──► 6.4 Gating
    │                                                         │
    └── 6.5 UI ◄───────────────────────────────────────────────┘
         │
         └──► 6.6 Events
                  │
Phase 7 ◄─────────┘
    │
    ├── 7.1 Lifecycle ──► 7.2 Staleness ──► 7.3 Recovery
    │
Phase 8 ◄────────────────────────────────────────────────────────────────────►
    │
    └── 8.1-8.6 (Gate verification, can run in parallel)
```

---

## Critical Path

The minimum path to a working system:

```
1.1 → 1.2 → 1.3 → 2.1 → 2.2 → 3.1 → 3.2 → 3.3 → 4.1 → 4.2 → 4.3 → 7.1
```

This path delivers:
- Database with core schema
- Event log for SSE
- LangGraph with gates
- API endpoints
- End-to-end workflow

Frontend (Phase 6) can proceed in parallel once Phase 2 is complete, using the API.

---

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| LLM output variance | Mock LLM adapter for deterministic testing |
| SSE reconnection complexity | Extensive unit tests for sequence guard |
| Concurrency bugs in sequences | Load tests in Package 2.1 |
| State version drift | Integration tests with concurrent clients |
| Audit attribution errors | Session-based attribution per Package 2.3 |

---

## Definition of Done (Per Package)

Each package is complete when:

1. **Code complete** — All deliverables implemented
2. **Tests pass** — Unit and integration tests green
3. **Verification script runs** — Listed verification steps succeed
4. **Documentation updated** — Code comments, README if applicable
5. **No regressions** — All prior package tests still pass

---

## Timeline Estimates

| Phase | Packages | Estimated Effort |
|-------|----------|------------------|
| 1. Foundation | 3 | 1-2 days |
| 2. Persistence | 4 | 2-3 days |
| 3. Orchestration | 4 | 3-4 days |
| 4. API | 4 | 2-3 days |
| 5. Runner | 3 | 2-3 days |
| 6. Frontend | 6 | 4-5 days |
| 7. Integration | 3 | 2-3 days |
| 8. Verification | 6 | 2-3 days |

**Total:** ~20-26 days for experienced developer/agent

**Parallel execution:** Phases 4-5 and 6 can run in parallel after Phase 2, reducing wall-clock time to ~15-18 days.

---

## Appendix: Golden Path Transcript

> **This is the canonical "did we build the same system?" reference.** One deterministic trace through Steps 1-3, Pass 1 (definition), showing expected events, state versions, and artifacts.

### Scenario: Complete Pass 1 Definition (Steps 1-3)

**Initial State:**
- No workflow exists
- User: `user-alice`

### Step-by-Step Transcript

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ACTION: Create Workflow                                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ Request:                                                                    │
│   POST /workflows                                                           │
│   { "problem": "Design a recommendation system", "created_by": "user-alice"}│
│                                                                             │
│ Response:                                                                   │
│   workflow_id: wf-001                                                       │
│   state_version: 1                                                          │
│   position: { step: 1, status: "not_started", pass: "definition" }          │
│                                                                             │
│ Events emitted:                                                             │
│   seq=1: workflow.started (actor: user-alice)                               │
│                                                                             │
│ Artifacts created: (none)                                                   │
│ Audit rows: 1 (workflow.started)                                            │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ ACTION: Runner advances Step 1                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│ Trigger: Runner picks up workflow with status not_started                   │
│                                                                             │
│ State changes:                                                              │
│   state_version: 1 → 2                                                      │
│   position: { step: 1, status: "in_progress", phase: "processing" }         │
│                                                                             │
│ Events emitted:                                                             │
│   seq=2: step.started (step=1, actor: system)                               │
│   seq=3: artifact.delta (streaming...)                                      │
│   seq=4: artifact.delta (streaming...)                                      │
│   seq=5: artifact.final (artifact_id: art-001)                              │
│                                                                             │
│ State changes:                                                              │
│   state_version: 2 → 3                                                      │
│   position: { step: 1, status: "awaiting_review", phase: "complete" }       │
│                                                                             │
│ Events emitted:                                                             │
│   seq=6: step.awaiting_review (step=1, actor: system)                       │
│                                                                             │
│ Artifacts created:                                                          │
│   art-001: problem_definition, revision=1, stale=false                      │
│                                                                             │
│ Audit rows: 3 (step.started, artifact.final, step.awaiting_review)          │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ ACTION: User approves Step 1                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│ Request:                                                                    │
│   POST /workflows/wf-001/actions/approve                                    │
│   { expected_state_version: 3, feedback: "Looks good" }                     │
│                                                                             │
│ Response:                                                                   │
│   state_version: 4                                                          │
│   position: { step: 1, status: "approved" }                                 │
│                                                                             │
│ Events emitted:                                                             │
│   seq=7: step.approved (step=1, actor: user-alice)                          │
│                                                                             │
│ Audit rows: 1 (step.approved, actor=user-alice)                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ ACTION: Runner advances to Step 2                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ State changes:                                                              │
│   state_version: 4 → 5                                                      │
│   position: { step: 2, status: "in_progress", phase: "processing" }         │
│                                                                             │
│ Events emitted:                                                             │
│   seq=8: step.started (step=2, actor: system)                               │
│   seq=9-12: artifact.delta (streaming...)                                   │
│   seq=13: artifact.final (artifact_id: art-002)                             │
│                                                                             │
│ State changes:                                                              │
│   state_version: 5 → 6                                                      │
│   position: { step: 2, status: "awaiting_review" }                          │
│                                                                             │
│ Events emitted:                                                             │
│   seq=14: step.awaiting_review (step=2, actor: system)                      │
│                                                                             │
│ Artifacts created:                                                          │
│   art-002: requirements, revision=1, stale=false                            │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ ACTION: User requests revision on Step 2                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ Request:                                                                    │
│   POST /workflows/wf-001/actions/revise                                     │
│   { expected_state_version: 6, feedback: "Add more NFRs" }                  │
│                                                                             │
│ Response:                                                                   │
│   state_version: 7                                                          │
│   position: { step: 2, status: "revising" }                                 │
│                                                                             │
│ Events emitted:                                                             │
│   seq=15: step.revision_requested (step=2, actor: user-alice)               │
│                                                                             │
│ Audit rows: 1 (step.revision_requested, actor=user-alice)                   │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ ACTION: Runner re-executes Step 2                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ State changes:                                                              │
│   state_version: 7 → 8                                                      │
│   position: { step: 2, status: "in_progress", phase: "processing" }         │
│                                                                             │
│ Events emitted:                                                             │
│   seq=16: step.started (step=2, actor: system)                              │
│   seq=17-20: artifact.delta (streaming...)                                  │
│   seq=21: artifact.final (artifact_id: art-003)                             │
│                                                                             │
│ State changes:                                                              │
│   state_version: 8 → 9                                                      │
│   position: { step: 2, status: "awaiting_review" }                          │
│                                                                             │
│ Events emitted:                                                             │
│   seq=22: step.awaiting_review (step=2, actor: system)                      │
│                                                                             │
│ Artifacts created:                                                          │
│   art-003: requirements, revision=2, supersedes=art-002, stale=false        │
│                                                                             │
│ Artifact updates:                                                           │
│   art-002: superseded_by=art-003                                            │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ ACTION: User approves Step 2                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│ Request:                                                                    │
│   POST /workflows/wf-001/actions/approve                                    │
│   { expected_state_version: 9, feedback: "Much better" }                    │
│                                                                             │
│ Response:                                                                   │
│   state_version: 10                                                         │
│   position: { step: 2, status: "approved" }                                 │
│                                                                             │
│ Events emitted:                                                             │
│   seq=23: step.approved (step=2, actor: user-alice)                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ ACTION: Runner advances to Step 3, completes, user approves                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ (Similar pattern to Steps 1-2)                                              │
│                                                                             │
│ Final state after Step 3 approval:                                          │
│   state_version: 14                                                         │
│   position: { step: 3, status: "approved", pass: "definition" }             │
│   last_sequence: 31                                                         │
│                                                                             │
│ Artifacts (latest revisions only):                                          │
│   art-001: problem_definition, revision=1                                   │
│   art-003: requirements, revision=2                                         │
│   art-004: objectives, revision=1                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Summary Table

| Checkpoint | state_version | last_sequence | Artifacts (latest) |
|------------|---------------|---------------|-------------------|
| After create | 1 | 1 | (none) |
| After Step 1 awaiting_review | 3 | 6 | art-001 (problem_definition r1) |
| After Step 1 approved | 4 | 7 | art-001 |
| After Step 2 awaiting_review | 6 | 14 | art-001, art-002 (requirements r1) |
| After Step 2 revision_requested | 7 | 15 | art-001, art-002 |
| After Step 2 re-executed, awaiting | 9 | 22 | art-001, art-003 (requirements r2) |
| After Step 2 approved | 10 | 23 | art-001, art-003 |
| After Step 3 approved | 14 | 31 | art-001, art-003, art-004 (objectives r1) |

### Verification Queries

```sql
-- Verify state_version at end
SELECT state_version FROM workflows WHERE id = 'wf-001';
-- Expected: 14

-- Verify sequence contiguity
SELECT COUNT(*), MAX(sequence) FROM workflow_events WHERE workflow_id = 'wf-001';
-- Expected: count=31, max=31 (no gaps)

-- Verify latest artifacts
SELECT step_name, revision FROM artifacts 
WHERE workflow_id = 'wf-001' AND superseded_by IS NULL
ORDER BY step_number;
-- Expected: problem_definition r1, requirements r2, objectives r1

-- Verify audit trail completeness
SELECT COUNT(*) FROM audit_log WHERE workflow_id = 'wf-001';
-- Expected: at least 10 (major state transitions)

-- Verify no stale artifacts
SELECT COUNT(*) FROM artifacts 
WHERE workflow_id = 'wf-001' AND stale = true AND superseded_by IS NULL;
-- Expected: 0
```

### Using This Transcript

1. **Implementation validation:** Run this scenario manually or automated; compare actual values to expected
2. **Gate verification:** Each checkpoint corresponds to a testable state
3. **Debugging:** When something fails, compare actual event sequence to expected
4. **Onboarding:** Walk through this transcript to understand system behavior

---

## Version History

| Version | Changes |
|---------|---------|
| V1.0 | Initial development directive derived from Frontend Contract v2.2, MVP Architecture Contract v1.1, Tech Spec V2.5 |
| V1.1 | Updated for Tech Spec V2.6: insert-per-revision artifacts, progress endpoint, enum alignment |
| V1.2 | Aligned with Tech Spec V2.7 and unified Architectural Contract v3.1: fixed staleness trigger to INSERT-based; fixed sequence tests for contiguity/uniqueness; added replay-during-emit monotonicity test; fixed Gate B trace coverage assertions; fixed resume pseudocode to use POST /resume; added β6 gate for broadcast/lease correctness; expanded isFetching to all canonical queries; added canonical refetch bundle reference; references restructured unified contract |
| V1.3 | Fixed Phase 2 exit gates (β2→β2a); added β2a gate for replay query correctness; enhanced β5 with explicit actor attribution for replay; added `reconstruct_timeline_with_actors()` test; updated document references to v1.1/v3.3 |
| V1.4 | Split β6 into β6a (Broadcast After Commit); β6a assigned to Phase 2, lease exclusivity folded into β4; removed Package 5.1.1; restructured Package 5.2 |
| V1.5 | Added Golden Path Transcript appendix — deterministic trace through Steps 1-3 Pass 1 with expected events, state versions, and artifacts |
| V1.5.1 | Clarified Package 6.3 deliverables to include `useWorkflowConnection` provider hook |

---

*SOLVER Development Directive v1.5.1*
*Phased implementation plan with lettered gates and deliverable packages*
