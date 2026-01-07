# Solver Engine

## Project Overview
**Solver Engine** is an orchestration layer for agentic work that prioritizes rigor, traceability, and human oversight over pure autonomy. It implements a structured, human-in-the-loop reasoning workflow ("The Solver Protocol") to convert unstructured problem statements into versioned, verifiable artifacts.

The system is a **monorepo** containing a Python/FastAPI backend and a Next.js frontend.

### Core Concepts
*   **Two-Pass Execution:** Every step runs in two passes:
    1.  **Methodology Generation:** Creates the "how-to" (Data Sheet, To-Do List, Guidance, Procedure).
    2.  **Supervised Execution:** Executes the procedure to create the deliverable.
*   **Trust Boundary:** LLMs generate content, but cannot change state. Only authenticated API calls advance the workflow.
*   **Statelessness:** The LLM interaction is designed to be stateless; context is maintained via persistent artifacts and database state.

## Tech Stack

### Backend (`apps/api`)
*   **Language:** Python 3.11+
*   **Framework:** FastAPI
*   **Orchestration:** LangGraph 1.0+
*   **Database:** PostgreSQL + pgvector (for artifacts, audit logs, and embeddings)
*   **Testing:** Pytest
*   **Linting/Formatting:** Ruff, Mypy

### Frontend (`apps/web`)
*   **Framework:** Next.js 14+
*   **State Management:** Zustand, TanStack Query
*   **Styling:** Tailwind CSS
*   **Communication:** SSE (Server-Sent Events) for streaming updates

### Infrastructure
*   **Containerization:** Docker & Docker Compose

## Key Commands

The project uses a root `Makefile` to manage all tasks.

### Setup & Installation
*   `make install`: Install all dependencies (API + Web).
*   `make migrate`: Apply database migrations (requires DB running).
*   `make db-seed`: Seed the database with test data.

### Development
*   `make dev`: Start all services (Postgres, API, Web) in development mode.
*   `make dev-api`: Start only the API server (available at `http://localhost:8000`).
*   `make dev-web`: Start only the Next.js dev server.
*   `make dev-db`: Start only the PostgreSQL container.

### Testing
*   `make test`: Run all tests.
*   `make test-api`: Run API tests (unit + integration).
*   `make e2e`: Run Gate E tests (End-to-End API + SSE flow).
*   `make test-gates`: Run Gate C tests (gating enforcement).
*   `make test-recovery`: Run Gate D tests (restart/recovery scenarios).

### Code Quality
*   `make lint`: Run all linters (Ruff, Mypy, ESLint).
*   `make format`: Auto-format code (Ruff, Prettier).
*   `make typecheck`: Run static type checking.

## Directory Structure

*   `apps/api/`: Backend application code.
    *   `domain/`: Pure domain models and logic.
    *   `application/`: Service layer and use cases.
    *   `orchestration/`: LangGraph state machine definitions.
    *   `infrastructure/`: DB and LLM adapters.
    *   `routes/`: FastAPI endpoints.
*   `apps/web/`: Frontend application code.
*   `docs/spec/`: **Authoritative Specifications.** Contains the "Source of Truth" for the project (Architecture, Tech Spec, Dev Directive).
*   `infra/`: Docker and Database configuration.
*   `packages/`: Shared resources (contracts/schemas).

## Development Conventions

*   **Documentation First:** The `docs/spec/` directory is the authority. Consult `5_SOLVER-Development-Directive-v1.5.1.md` for the development process.
*   **Schema Strictness:** Inputs and outputs are strictly validated against schemas defined in `packages/contracts`.
*   **Gated Workflow:** Development proceeds in "Gates" (Gate A through Gate E), verified by specific test suites (e.g., `make test-gate-b`).
