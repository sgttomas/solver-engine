# CLAUDE.md — AI Development Guide for SOLVER

## What Is This Project?

**SOLVER** is a Structured Reasoning Workflow Engine — a deterministic supervisor for stochastic agents. It prioritizes **rigor, traceability, and human oversight** over speed and autonomy.

**Key Constraint:** LLMs cannot advance workflow state. Only external API calls from authenticated actors can approve gates.

---

## Authority Stack (CRITICAL)

Two hierarchies govern (from Document-Type-Specifications v2.1):

| Hierarchy | Order | Use When |
|-----------|-------|----------|
| **Purpose Priority** | Intent > Contract > Spec > Directive | Choosing between compliant options |
| **Binding Precedence** | Contract > Spec > Directive > Intent | Resolving conflicts about what must be true |

**Documents (in docs/spec/):**

| # | Document | Role |
|---|----------|------|
| 0 | `0_Document-Type-Specifications-v2.1.md` | Governance framework |
| 2 | `2_SOLVER-Design-Intent-v1.1.md` | Why² — Design rationale |
| 3 | `3_SOLVER-Architectural-Contract-v3.4.md` | Why — Invariants, R1–R19 |
| 4 | `4_solver-technical-spec-V2.7.3.md` | What — Schemas, endpoints |
| 5 | `5_SOLVER-Development-Directive-v1.5.md` | How — Phases, packages, gates |
| 6 | `6_SOLVER-Change-Management-v1.2.md` | Process — Change control |

**Rule:** Contract wins conflicts. Intent is tie-breaker only among compliant solutions.

Deviations require approval and entry in `docs/DECISIONS.md` per Change Management process.

---

## Current Status

**P1 Foundation:** ✅ Complete
**P2 Persistence:** ✅ Complete
**P3 Orchestration:** ✅ Complete
**P4 API:** ✅ Complete
**P5 Content:** ✅ Complete
**P6 Verification:** ✅ Complete (Gate C ✓, Gate D ✓, Gate E ✓, Gate F ✓)

### Key Context

- **Schema is authoritative:** `infra/db/migrations/versions/` defines the database (001, 002, 003). Models must match exactly.
- **Config location:** `apps/api/config.py` (not `apps/api/config/settings.py` — that was deleted)
- **Flat layout:** `apps/api/infrastructure/db/` (not `apps/api/src/solver_api/`)
- **Custom checkpoint saver:** Uses `SolverCheckpointSaver` instead of `langgraph-checkpoint-postgres.PostgresSaver` due to schema incompatibility (see `docs/DECISIONS.md`)
- **State coercion:** Use `coerce_state(state)` at start of nodes to handle dict/string deserialization from checkpoints
- **Resume from interrupt:** Use `as_node="review"` or `as_node="elicit"` in `aupdate_state()` to tell LangGraph which node completed
- **Graph singleton:** Module-level graph in `routes/workflows.py`; checkpointer manages sessions, `thread_id` provides isolation
- **Event persistence:** `sync_db_from_state()` persists events in correct order (step.started → artifact.* → step.awaiting_review). Routes publish events AFTER transaction commits.
- **SSE replay:** Stream endpoint uses `from_sequence` parameter for reliable reconnection. Events replayed from DB, then live events from broker.

---

## Project Structure

```
apps/api/
├── domain/           # Pure domain models (state.py)
├── application/      # Use cases (workflow_service.py)
├── orchestration/    # LangGraph graph + nodes
├── infrastructure/   # DB, LLM adapters
│   └── db/
│       ├── models/   # SQLAlchemy models
│       └── repositories/  # Repository pattern
├── routes/           # FastAPI routes (workflows.py)
└── config.py         # Settings (pydantic-settings)

infra/db/migrations/  # Alembic migrations
docs/spec/            # Authority documents
```

---

## Development Pattern

### Before Starting

1. Read `docs/spec/5_SOLVER-Development-Directive-v1.5.md` for your package/slice
2. Read relevant sections of Technical Spec (`docs/spec/4_solver-technical-spec-V2.7.3.md`)
3. Check existing code before creating new files

### Working on a Slice

1. Create a plan file or use TodoWrite to track tasks
2. Implement in small, testable increments
3. Verify against exit criterion
4. Document which gate(s) your work advances

### After Completing

Report: files changed, commands run, gates satisfied, next slice.

---

## Key Commands

```bash
# Database
docker compose -f infra/docker/docker-compose.yml up -d   # Start DB
make migrate                                               # Run migrations

# Development
make dev-api          # Start API server
make test             # Run tests
make lint             # Run linting
make format           # Format code

# Gate Verification
make test-gates       # Gate C (gating enforced)
make test-recovery    # Gate D (restart/resume)
make e2e              # Gate E (API + SSE)

# Gate F Audit Verification
python tools/complete_workflow.py                    # Create fully-approved workflow
python tools/verify_audit.py --workflow-id $ID      # Verify audit trail
```

---

## Common Pitfalls

| Don't | Do |
|-------|-----|
| Skip reading specs | Read authority docs first |
| Create `apps/api/src/` nesting | Use flat `apps/api/` layout |
| Let LLM control state | Only API calls advance gates |
| Assume schema fields | Check migration files (001, 002, 003) |
| Use PostgresSaver directly | Use `SolverCheckpointSaver` (schema mismatch) |
| Call `aupdate_state` without `as_node` | Use `as_node="review"` or `as_node="elicit"` |
| Assume state has proper types after resume | Use `coerce_state(state)` in nodes |
| Wire `message` action to graph | Keep DB-only (Gate C: no state change) |
| Publish events inside transaction | Persist in transaction, publish AFTER commit |

---

## Acceptance Gates

| Gate | Criterion |
|------|-----------|
| A | 36 methodology docs exist |
| B | Packages validate + trace links work |
| C | Cannot advance without approve |
| D | State survives restart |
| E | API + SSE works |
| F | Audit log complete |

---

## Quick Reference

- **Database:** 3 migrations (001_initial_schema, 002_contract_alignment, 003_remediation)
- **Instance 0:** Already seeded (Universal Methodology)
- **Async DB:** Use `asyncpg` driver, `AsyncSession`
- **ENUMs exist:** Use `create_type=False` in SQLAlchemy
- **Tests:** `make test-gates` (C), `make test-recovery` (D), `make e2e` (E + SSE replay)

For full details, see `README.md` and the spec documents.
