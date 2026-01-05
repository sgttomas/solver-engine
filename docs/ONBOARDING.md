# SOLVER Engine — Senior Developer Onboarding

## What This Is

SOLVER is a **deterministic supervisor for stochastic agents** — a structured reasoning workflow engine that prioritizes rigor, traceability, and human oversight over speed and autonomy.

**Key invariant:** LLMs cannot advance workflow state. Only external API calls from authenticated actors can approve gates.

---

## Current State

**Backend (P1–P6):** ✅ Complete — All MVP gates pass

| Gate | Criterion | Status |
|------|-----------|--------|
| A | 36 methodology docs exist | ✅ |
| B | Packages validate + trace links | ✅ |
| C | Cannot advance without approve | ✅ |
| D | State survives restart | ✅ |
| E | API + SSE works | ✅ |
| F | Audit trail complete | ✅ |

**Frontend:** Scaffold only — integration phase begins now

---

## Before You Code

### 1. Read the Authority Stack

Documents in `docs/spec/` govern all work. Read in this order:

| # | Document | What You'll Learn |
|---|----------|-------------------|
| 0 | Document-Type-Specifications | Governance framework, binding precedence |
| 2 | Design-Intent | Why² — principles, tradeoffs, trust boundary |
| 3 | Architectural-Contract | Invariants R1–R19, backend/frontend contracts |
| 4 | Technical-Spec | Schemas, endpoints, error codes, event types |
| 5 | Development-Directive | Phases, packages, gates, deliverables |
| 6 | Change-Management | Deviation process, CR workflow |

**Authority rule:** Contract wins conflicts. Intent is tie-breaker among compliant options. Deviations require logging in `docs/DECISIONS.md`.

### 2. Verify the Backend

```bash
docker compose -f infra/docker/docker-compose.yml up -d
make migrate
make test-gates    # Gate C
make test-recovery # Gate D
make e2e           # Gate E + SSE replay
```

### 3. Review Orientation Files

- `README.md` — Project overview, architecture, quick start
- `CLAUDE.md` — AI development guide, key context, pitfalls
- `AGENTS.md` — Repo-level agent instructions
- `docs/DECISIONS.md` — Approved deviations (5 recorded)

---

## Your Focus: Frontend Integration

### Target Gates

| Gate | Name | What It Verifies |
|------|------|------------------|
| γ1 | Workflow Lifecycle | Create → execute → gate → approve → advance |
| γ2 | SSE Client Sync | Gaps, replay, reconnect handled correctly |
| γ3 | Action Gating | canAct/canMessage rules enforced (R3–R6, R14–R15) |
| γ4 | Staleness Flow | Upstream revision → downstream stale → re-execute |

### Frontend Reliability Rules (Contract §13–14)

The Architectural Contract defines 19 reliability rules (R1–R19) for the frontend. Key themes:

- **Sequence Guard:** Deduplicate by `lastContiguousSequence`, buffer out-of-order, detect gaps
- **Connection States:** `connecting` → `connected` → `reconnecting` → `resyncing` → `failed`
- **Action Gating:** `canAct` requires connected + awaiting_review + staleness known + can_complete
- **Optimistic Concurrency:** Actions must include `expected_state_version` + `expected_position`

Read Contract §13–14 for the complete rules. Do not guess — implement exactly as specified.

### Backend API Reference

All endpoints under `/api/v1`. Key endpoints for frontend:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/workflows` | Create workflow |
| GET | `/workflows/{id}` | Current state + position |
| GET | `/workflows/{id}/stream?from_sequence=N` | SSE events (replay from N) |
| POST | `/workflows/{id}/actions/approve` | Approve gate (requires OCC fields) |
| POST | `/workflows/{id}/actions/revise` | Request revision |
| POST | `/workflows/{id}/actions/message` | Comment (no state change) |

See Technical Spec §9 for full endpoint documentation.

---

## Patterns to Avoid

| Don't | Why | Do Instead |
|-------|-----|------------|
| Create `apps/api/src/` nesting | Project uses flat layout | Keep `apps/api/` structure |
| Use PostgresSaver directly | Schema incompatibility | Use `SolverCheckpointSaver` |
| Wire message action to graph | Gate C: no state change | DB-only persistence |
| Publish events inside transaction | Race conditions | Persist in txn, publish after commit |
| Assume state types after resume | LangGraph deserializes to dict | Use `coerce_state()` in nodes |
| Skip reading Contract | Invariants are non-negotiable | Read R1–R19 before implementing |
| Invent endpoint shapes | Spec is authoritative | Follow Tech Spec or log deviation |

---

## Work Protocol

### For Each Deliverable

1. **Plan:** Identify tasks, dependencies, acceptance criteria, applicable Contract rules
2. **Implement:** Small, testable increments
3. **Verify:** Check against acceptance criteria and Contract rules
4. **Report:** Files changed, commands run, gates satisfied

### Deviation Handling

If backend doesn't match Contract/Spec:

1. Check `docs/DECISIONS.md` for existing approved deviation
2. If new deviation needed: Log it with impact analysis
3. Options: DEFER (workaround) | IMPLEMENT (fix) | CHANGE REQUEST (spec wrong)

---

## Quick Reference

```bash
# Database
docker compose -f infra/docker/docker-compose.yml up -d
make migrate

# Development
make dev-api      # Start API server (localhost:8000)
make test         # Run tests
make lint         # Lint code

# Gate Verification
make test-gates   # Gate C
make test-recovery # Gate D
make e2e          # Gate E + SSE replay
```

**Key Files:**
- Backend routes: `apps/api/routes/workflows.py`
- Service layer: `apps/api/application/workflow_service.py`
- Graph definition: `apps/api/orchestration/graph.py`
- Event streaming: `apps/api/application/event_stream.py`
- Migrations: `infra/db/migrations/versions/`

**Database:** 3 migrations (001_initial_schema, 002_contract_alignment, 003_remediation)

---

## First Steps

1. Complete orientation reading (authority stack + orientation files)
2. Run gate verification commands to confirm backend health
3. Read Contract §13–14 (frontend reliability rules R1–R19)
4. Propose plan for Package 6.1 (Project Setup)
5. Wait for approval before implementing
