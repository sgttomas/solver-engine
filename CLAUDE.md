# CLAUDE.md — AI Development Guide for SOLVER

## What Is This Project?

**SOLVER** is a Structured Reasoning Workflow Engine — a deterministic supervisor for stochastic agents. It prioritizes **rigor, traceability, and human oversight** over speed and autonomy.

**Key Constraint:** LLMs cannot advance workflow state. Only external API calls from authenticated actors can approve gates.

---

## Authority Stack (CRITICAL)

When documents conflict, higher priority wins:

| Priority | Document | Governs |
|----------|----------|---------|
| 1st | `docs/spec/1_meta-prompt-structured-reasoning.md` | **Why** — Logic, gates |
| 2nd | `docs/spec/2_structured-reasoning-architecture.md` | **Where** — Components |
| 3rd | `docs/spec/3_solver-technical-spec.md` | **What** — Tables, schemas |
| 4th | `docs/spec/0_SOLVER-Development-Directive.md` | **How** — Slices, workflow |

Deviations require approval and entry in `docs/DECISIONS.md`.

---

## Current Status

**P1 Foundation:** Complete
**P2 Persistence:** In Progress

| Slice | Deliverable | Exit Criterion |
|-------|-------------|----------------|
| P2.1 | SQLAlchemy Models | Models import without error |
| P2.2 | Repository Layer | Unit tests pass (mocked DB) |
| P2.3 | Checkpoint Adapter | LangGraph saver round-trips |

### Key Context for P2

- **Schema is authoritative:** `infra/db/migrations/versions/001_initial_schema.py` defines the database. Models must match exactly.
- **Config location:** `apps/api/config.py` (not `apps/api/config/settings.py` — that was deleted)
- **Flat layout:** `apps/api/infrastructure/db/` (not `apps/api/src/solver_api/`)

---

## Project Structure

```
apps/api/
├── domain/           # Pure domain models
├── application/      # Use cases, orchestration
├── infrastructure/   # DB, LLM adapters
│   └── db/
│       ├── models/   # SQLAlchemy models (P2.1)
│       └── repositories/  # Repository pattern (P2.2)
├── api/              # REST routes
└── config.py         # Settings (pydantic-settings)

infra/db/migrations/  # Alembic migrations
docs/spec/            # Authority documents
```

---

## Development Pattern

### Before Starting

1. Read `docs/spec/0_SOLVER-Development-Directive.md` for your slice
2. Read relevant sections of Doc 3 (Technical Spec)
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
```

---

## Common Pitfalls

| Don't | Do |
|-------|-----|
| Skip reading specs | Read authority docs first |
| Create `apps/api/src/` nesting | Use flat `apps/api/` layout |
| Let LLM control state | Only API calls advance gates |
| Assume schema fields | Check migration file |
| Create new migrations for P2 | Map to existing tables |

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

- **Database tables:** 9 tables defined in `001_initial_schema.py`
- **Instance 0:** Already seeded (Universal Methodology)
- **Async DB:** Use `asyncpg` driver, `AsyncSession`
- **ENUMs exist:** Use `create_type=False` in SQLAlchemy

For full details, see `README.md` and the spec documents.
