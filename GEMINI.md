# Gemini Context: SOLVER Engine

This document provides a comprehensive overview of the SOLVER Engine project. It is intended to guide future AI-driven development and analysis.

## Project Overview

SOLVER is a **Structured Reasoning Workflow Engine** designed to orchestrate agentic work with a focus on rigor, traceability, and human oversight. It functions as a deterministic supervisor for stochastic agents.

**Core Philosophy:**
- **Separate Method from Content:** Two-pass execution (Methodology Generation → Supervised Execution).
- **Human-in-the-loop:** Explicit approval gates before advancing steps.
- **Stateless & Traceable:** Persistent artifacts and audit logs; does not rely on LLM internal state.

**Workflow:**
The system enforces a 10-step workflow (Problem Definition → Requirements → Objectives → ... → Resolution).
The MVP scope focuses on Steps 1–3.

## Architecture & Technology Stack

The project is structured as a monorepo.

- **Backend (`apps/api`):**
    - **Framework:** FastAPI (Python 3.11+)
    - **Orchestration:** LangGraph 1.0+
    - **Database:** PostgreSQL + pgvector (for artifacts and embeddings)
    - **Migrations:** Alembic
    - **LLM Integration:** OpenAI, Anthropic, or Gemini APIs

- **Frontend (`apps/web`):**
    - **Framework:** Next.js 14 (Future/In-Progress)
    - **SDK:** Vercel AI SDK

- **Infrastructure:**
    - Docker & Docker Compose for local development (PostgreSQL).

## Development Conventions

### Coding Standards
- **Python:**
    - **Linting & Formatting:** `ruff` (configured in `pyproject.toml`)
    - **Type Checking:** `mypy` (Strict mode enabled)
- **TypeScript (Web):**
    - ESLint & Prettier

### Testing Strategy
Tests are categorized and runnable via `Makefile`:
- **Unit Tests:** `make test-unit` (`apps/api/tests/unit/`)
- **Integration Tests:** `make test-integration` (`apps/api/tests/integration/`)
- **End-to-End (Gate E):** `make e2e` (`apps/api/tests/e2e/`)
- **Gate Enforcement (Gate C):** `make test-gates`
- **Recovery/Persistence (Gate D):** `make test-recovery`

### Operational Commands (Makefile)
- **Setup:** `make install` (Installs dependencies for API and Web)
- **Development:**
    - `make dev`: Starts DB, API, and Web.
    - `make dev-api`: Starts API only (`localhost:8000`).
    - `make dev-db`: Starts PostgreSQL via Docker.
- **Database:**
    - `make migrate`: Apply Alembic migrations.
    - `make db-reset`: **WARNING** Destroys and recreates the DB.
- **Linting:** `make lint` (Runs ruff, mypy, and eslint).

## Project Structure

```
solver-engine/
├── apps/
│   ├── api/                    # FastAPI Backend
│   └── web/                    # Next.js Frontend
├── docs/                       # Specifications and Design Docs
├── infra/                      # Docker & Infrastructure config
├── packages/                   # Shared libraries
├── tests/                      # Testing root
└── tools/                      # Validation scripts
```

## Key Documentation References
- **`docs/spec/5_SOLVER-Development-Directive-v1.5.md`**: The authoritative manual for development slices.
- **`docs/spec/4_solver-technical-spec-V2.8.0.md`**: Technical specification for schemas and endpoints.
- **`AGENTS.md`**: Specific instructions for AI agents working in this repo.
