# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SOLVER (Structured Reasoning Workflow Engine) is a deterministic supervisor for stochastic agents—an orchestration layer for agentic work that executes a structured, human-in-the-loop reasoning workflow. It converts unstructured problem statements into versioned, traceable, verifiable artifacts.

**MVP Scope:** Steps 1–3 (Problem Definition → Requirements → Objectives) with two-pass execution, persistence, gates, audit, and streaming.

## Common Commands

```bash
# Setup
docker compose -f infra/docker/docker-compose.yml up -d   # Start PostgreSQL
make migrate                                               # Run migrations
make install-api                                           # Install API deps
make install-web                                           # Install Web deps

# Development
make dev-api                    # Start API server (localhost:8000)
make dev-web                    # Start Next.js dev server (localhost:3000)

# Testing
make test                       # Run API tests
make test-unit                  # Unit tests only
make test-integration           # Integration tests only
make test-gates                 # Gate C (gating enforcement)
make test-recovery              # Gate D (restart/recovery)
make e2e                        # Gate E (API + SSE flow)

# Single test file
PYTHONPATH=apps/api .venv/bin/pytest apps/api/tests/unit/test_artifact_service.py -v

# Code quality
make lint                       # ruff + mypy
make format                     # ruff format + fix
make lint-web                   # ESLint for frontend
make format-web                 # Prettier for frontend
```

## Architecture

### Directory Structure

```
apps/api/
├── domain/           # Pure domain models (no external deps)
├── application/      # Use cases / services
├── infrastructure/   # DB models, repositories, LLM adapter
├── orchestration/    # LangGraph state machine, nodes, prompts
├── routes/           # REST API endpoints
└── tests/            # unit/, integration/, e2e/

apps/web/
├── app/              # Next.js App Router pages
├── components/       # React components
├── hooks/            # React hooks (connection manager)
├── lib/              # Utilities (api, backoff, SSE)
└── stores/           # Zustand state stores
```

### Core Execution Model

**Two-Pass Execution:** Every step executes in two passes:
- Pass 1: Generate methodology (4 docs × 3 versions = V1→V2→V3)
- Pass 2: Apply V3 methodology to produce deliverable, then interrupt for human review

**Human Actions at Gates:**
- `approve` — Advance to next step
- `revise` — Re-run step with feedback
- `message` — Record commentary without state change

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| WorkflowService | `application/workflow_service.py` | Orchestrates workflow lifecycle |
| ArtifactService | `application/artifact_service.py` | Creates/manages artifact revisions |
| Graph | `orchestration/graph.py` | LangGraph state machine with interrupt gates |
| Nodes | `orchestration/nodes.py` | Step execution logic |
| DB Models | `infrastructure/db/models/` | SQLAlchemy ORM (10 tables) |
| LLM Adapter | `infrastructure/llm.py` | Multi-provider (Claude, OpenAI, Gemini) |


## Specification Documents

Authoritative docs in `docs/spec/` (read in order for full context):

| # | Document | Purpose |
|---|----------|---------|
| 0 | [Document-Type-Specifications](docs/spec/0_Document-Type-Specifications-v2.1.1.md) | Governance framework |
| 1 | [SOLVER-README](docs/spec/1_SOLVER-README-v1.0.md) | Project orientation |
| 2 | [Design-Intent](docs/spec/2_SOLVER-Design-Intent-v1.1.md) | Why² — design rationale |
| 3 | [Architectural-Contract](docs/spec/3_SOLVER-Architectural-Contract-v3.4.md) | Why — invariants, constraints |
| 4 | [Technical-Spec](docs/spec/4_SOLVER-Technical-Spec-V2.8.0.md) | What — schemas, endpoints |
| 5 | [Development-Directive](docs/spec/5_SOLVER-Development-Directive-v1.5.1.md) | How — phases, gates |
| 6 | [Change-Management](docs/spec/6_SOLVER-Change-Management-v2.0.1.md) | Process — change control |
| 7 | [Sr-Dev-init](docs/spec/7_SOLVER-Sr-Dev-init.md) | Senior developer initialization |
| 8 | [Co-Dev-init](docs/spec/8_SOLVER-Co-Dev-init.md) | Co-developer initialization |
| 9 | [Decision-Heuristic](docs/spec/9_SOLVER-Decision-Heuristic-v.1.0.md) | Decision criteria |
| - | [DECISIONS](docs/spec/DECISIONS.md) | Approved deviations and notes |
| - | [FREEZE-RECORD](docs/spec/FREEZE-RECORD.md) | Release freeze history |

**Authority order:** Specs (docs/spec/) → DECISIONS.md → README.md

Approved deviations from specs are recorded in `docs/spec/DECISIONS.md`.


## Key Patterns

- **Insert-per-revision model:** Each artifact revision creates a new row with `supersedes`/`superseded_by` links
- **Optimistic concurrency:** `state_version` field for conflict detection (409 on mismatch)
- **Custom checkpoint saver:** `SolverCheckpointSaver` instead of upstream PostgresSaver (see `docs/spec/DECISIONS.md`)
- **State transitions are code-controlled:** LLM cannot influence gate approvals or step advancement

## Environment

Required in `apps/api/.env` (at least one provider key):
```
DEFAULT_LLM_PROVIDER=openai   # optional; defaults to openai
ANTHROPIC_API_KEY=...   # OR OPENAI_API_KEY or GOOGLE_API_KEY
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=solver
POSTGRES_PASSWORD=solver
POSTGRES_DB=solver
```
