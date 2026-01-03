# Gemini Context: SOLVER

This document provides a persistent overview of the SOLVER project for AI-driven development. It summarizes the authoritative instructions from `docs/spec/0_SOLVER-Development-Directive.md`.

## Project Overview
**SOLVER** is a Structured Reasoning Workflow Engine designed to transform problems into structured solutions through a two-pass methodology (V1→V2→V3 iteration and artifact production).

## Role Definition
- **Architect (User):** Makes design decisions, approves work, and controls scope.
- **Senior Developer (AI Agent):** Implements exactly what the documents specify. Does NOT invent new architectures, skip slices, or deviate without approval.

## Document Authority Stack
| Document | Domain | Role |
|----------|--------|------|
| `docs/spec/1_meta-prompt-structured-reasoning.md` | **The Why** | Process, reasoning rules, gate semantics |
| `docs/spec/2_structured-reasoning-architecture.md` | **The Where** | Component boundaries, layer responsibilities |
| `docs/spec/3_solver-technical-spec.md` | **The What** | Schemas, endpoints, tables, file paths |

## Hard Constraints
- **Pass 2 Gates are mandatory:** Cannot advance without explicit human `approve` action.
- **State must survive restart:** All state persisted in DB; LangGraph interrupts enforce gates.
- **No hardcoded secrets:** Use `.env` and `pydantic_settings`.
- **Audit log:** All transitions must be recorded.
- **Traceability:** Mandatory links from Step 1 → Step 2 → Step 3.
- **Architecture:** Strict flat layout at `apps/api/`. Do NOT use `src/` directory.

## Current Session Context (Phase 2 Focus)
- **Phase 1 (Foundation):** Complete.
    - Directory structure is flat (`apps/api/`).
    - Docker running with `pgvector` and `api`.
    - Database schema applied via Alembic (Raw SQL).
- **Phase 2 (Persistence):** In Progress.
    - Goal: Satisfy Gate D (Restart/Resume).
    - Focus: SQLAlchemy models, Repository layer, Checkpoint adapter.
    - Constraint: Models must map to existing Raw SQL schema (no new migrations).

## Acceptance Gates (Success Criteria)
- **Gate A:** Methodology exists (36 docs for Steps 1-3).
- **Gate B:** Packages with valid schemas and traceability traces.
- **Gate C:** Gating enforced (cannot bypass via message).
- **Gate D:** Restart/resume works (state survives kill).
- **Gate E:** API + SSE flow works (no UI required for MVP).
- **Gate F:** Audit trail complete.

## Build Sequence (P1-P6)
1. **P1: Foundation** (Structure, Docker, DB Schema) ✅
2. **P2: Persistence** (SQLAlchemy models, Repositories, Checkpoints) 🚧
3. **P3: Orchestration** (Pydantic state, Graph definition, Interrupts)
4. **P4: API Layer** (FastAPI endpoints, SSE, Wiring)
5. **P5: Content Generation** (LLM adapter, Prompts, Traceability)
6. **P6: Verification** (Gate tests)

## Verification Standard
| Command | Purpose |
|---------|---------|
| `make test` | Unit tests |
| `make test-gates` | Gate enforcement |
| `make test-recovery` | Restart/resume tests |
| `make migrate` | Run DB migrations (via Alembic) |
| `python tools/validate_schemas.py` | Artifact validation |

## File Boundaries
- `/apps/api/`: FastAPI backend (flat structure).
- `/packages/`: Shared contracts and logic.
- `/infra/`: Docker and migrations.
- `/tests/` & `/tools/`: Verification code.
- `/docs/spec/`: READ-ONLY authority.