# Gemini Context: SOLVER

**Structured Reasoning Workflow Engine**
A deterministic supervisor for stochastic agents, optimizing for rigor, traceability, and human oversight.

## Project State
- **Phase:** Pre-Phase 6 (Backend Remediation Complete)
- **Current Focus:** Ready for Frontend Implementation
- **Latest Milestone:** Backend Contract Alignment (Fixes 1-7 complete)

## Authority Stack
| Document | Domain | Role |
|----------|--------|------|
| `docs/spec/3_SOLVER-Architectural-Contract-v3.4.md` | **CONTRACT** | Invariants, R1-R19 rules, Replay logic |
| `docs/spec/4_solver-technical-spec-V2.8.0.md` | **SPEC** | Schemas, Endpoints, Tables |
| `docs/spec/5_SOLVER-Development-Directive-v1.5.md` | **DIRECTIVE** | Build phases, Gate criteria |

**Rule:** Contract wins. If code conflicts with Contract, code is wrong.

## Backend Architecture (Contract-Aligned)
- **Event Sourcing:** `workflow_events` table is the authoritative log.
- **Atomicity:** Events persist in the *same transaction* as state changes; broadcast happens *after* commit.
- **Replay:** SSE stream uses "Subscribe Live -> Query DB -> Filter" pattern to guarantee gap-free, duplicate-free ordering.
- **Optimistic Concurrency:** Actions require `expected_state_version` and `expected_position`. Version increments on *any* state-eligibility change.
- **Staleness:** DB triggers propagate staleness on *INSERT* (new revision) to all downstream artifacts and traceability links.

## Key Invariants
1.  **Persist Before Broadcast:** No SSE event is emitted unless it is committed to DB.
2.  **Monotonic Sequences:** Every event has a unique, gap-free sequence number per workflow.
3.  **Strict Validation:** Missing request fields return 400 (not 422). Step names are validated.
4.  **Synthetic Events:** Artifact deltas are synthetic but persisted transactionally by the route.

## Verification
| Gate | Status | Verified By |
|------|--------|-------------|
| **Gate C** (Gating) | ✅ PASS | `apps/api/tests/e2e/test_gate_c.py` |
| **Gate D** (Restart) | ✅ PASS | `apps/api/tests/e2e/test_gate_d.py` |
| **Gate E** (SSE Flow) | ✅ PASS | `apps/api/tests/e2e/test_gate_e.py` |
| **SSE Replay** | ✅ PASS | `apps/api/tests/e2e/test_sse_replay.py` |

## Next Steps
1.  **Frontend Phase (Phase 6):** Implement React/Next.js frontend against this compliant backend.
2.  **Strictness:** Frontend must enforce R1-R19 reliability contracts (Sequence Guard, Connection Manager).
3.  **Dependencies:** Frontend relies on `GET /progress` and `GET /staleness` (canonical refetch bundle).

## Dev Context
- **Working Dir:** `projects/solver-engine/`
- **Backend:** FastAPI, SQLAlchemy (Async), LangGraph, Postgres+pgvector
- **Migrations:** Alembic (`003_remediation.py` is latest)
- **Tests:** `make test-gates`, `make e2e`
