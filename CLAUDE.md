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

# Development
make dev-api                    # Start API server (localhost:8000)

# Testing
make test                       # Run all tests
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
| DB Models | `infrastructure/db/models.py` | SQLAlchemy ORM (10 tables) |
| LLM Adapter | `infrastructure/llm/adapter.py` | Multi-provider (Claude, OpenAI, Gemini) |


## Specification Documents

Authoritative docs in `docs/spec/` (read in order for full context):

| # | Document | Purpose |
|---|----------|---------|
| 0 | Document-Type-Specifications | Governance framework |
| 1 | SOLVER-README | Project orientation |
| 2 | Design-Intent | Why² — design rationale |
| 3 | Architectural-Contract | Why — invariants, constraints |
| 4 | Technical-Spec | What — schemas, endpoints |
| 5 | Development-Directive | How — phases, gates |
| 6 | Change-Management | Process — change control |

**Authority order:** Specs (docs/spec/) → DECISIONS.md → README.md

Approved deviations from specs are recorded in `docs/DECISIONS.md`.


## Key Patterns

- **Insert-per-revision model:** Each artifact revision creates a new row with `supersedes`/`superseded_by` links
- **Optimistic concurrency:** `state_version` field for conflict detection (409 on mismatch)
- **Custom checkpoint saver:** `SolverCheckpointSaver` instead of upstream PostgresSaver (see DECISIONS.md #5)
- **State transitions are code-controlled:** LLM cannot influence gate approvals or step advancement

## Environment

Required in `apps/api/.env`:
```
ANTHROPIC_API_KEY=...   # OR OPENAI_API_KEY or GOOGLE_API_KEY
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=solver
POSTGRES_PASSWORD=solver
POSTGRES_DB=solver
```
