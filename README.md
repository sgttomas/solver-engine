# SOLVER

**Structured Reasoning Workflow Engine**

> *A deterministic supervisor for stochastic agents.*

SOLVER is an orchestration layer for agentic work. It executes a structured, human-in-the-loop reasoning workflow that converts an **unstructured problem statement** into **versioned, traceable, verifiable artifacts**.

Unlike standard agent frameworks that optimize for speed and autonomy, SOLVER optimizes for **rigor, traceability, and human oversight**.

> **MVP Scope:** Steps 1–3 (Problem Definition → Requirements → Objectives) with two-pass execution, persistence, gates, audit, and streaming.

---

## Why SOLVER Exists

Most agent frameworks optimize for tool-calling and autonomy. SOLVER optimizes for **reliable knowledge production**:

| Other Frameworks | SOLVER |
|------------------|--------|
| Method and content interleaved | **Separate method from content** (two-pass execution) |
| Agent self-validates | **Human approval gates** before advancing |
| State in conversation | **Persistent artifacts** (stateless LLM; durable DB) |
| Freeform outputs | **Schema-conformant** and audit-friendly |
| Implicit reasoning | **Full traceability** across steps and revisions |

### The Trust Problem

LLMs can generate convincing text claiming "I've verified this" or "This is ready for the next step." SOLVER creates a **Trust Boundary**:

| LLM Can Influence | LLM Cannot Influence |
|-------------------|----------------------|
| Artifact content | State transitions |
| Reasoning text | Gate approvals |
| Clarification questions | Step advancement |
| Revision attempts | Workflow completion |

Even if the LLM outputs "I approve this," the system ignores it. Only external API calls from authenticated actors advance the workflow.

---

## Core Concepts

### Instance Hierarchy

| Instance | Name | Role |
|----------|------|------|
| **0** | Universal Methodology | Defines the 10-step process + schemas + "4 Documents" scaffold |
| **1** | SOLVER Software | Implements Instance 0 as executable runtime (this repo) |
| **N** | Domain Specialization | Adds domain schemas/templates without changing core |

### Two-Pass Execution Model

Every step executes in two passes:

**Pass 1 — Methodology Generation**

For each step, SOLVER generates four methodology documents and refines them through V1 → V2 → V3:

| Document | Purpose |
|----------|---------|
| **Data Sheet** | Input/output contracts, schemas, validation rules |
| **To Do List** | Task decomposition, checkpoints, validation hooks |
| **Guidance** | Context, principles, anti-patterns, quality criteria |
| **Detailed Procedure** | State machine, algorithms, decision logic, gates |

**Pass 2 — Supervised Execution**

SOLVER applies the step's V3 methodology to produce the deliverable artifact, then **interrupts** for human review:

| Action | Effect |
|--------|--------|
| **Approve** | Advance to next step |
| **Revise** | Re-run step with feedback |
| **Message** | Record commentary without changing state |

### Ten-Step Workflow

```
╔═══════════════════════════════════════════════════════════════════╗
║  DEFINITION PHASE — "What are we solving?"                        ║
╠═══════════════════════════════════════════════════════════════════╣
║  Step 1: Problem Definition    → Scope, constraints, success      ║
║  Step 2: Requirements          → What the solution must do        ║
║  Step 3: Objectives            → What success looks like          ║
╠═══════════════════════════════════════════════════════════════════╣
║  VERIFICATION PHASE — "How will we know it works?"                ║
╠═══════════════════════════════════════════════════════════════════╣
║  Step 4: Verification Design   → Correctness checks               ║
║  Step 5: Validation Design     → Fitness checks                   ║
║  Step 6: Evaluation Criteria   → Success metrics                  ║
║  Step 7: Assessment Protocol   → Measurement process              ║
╠═══════════════════════════════════════════════════════════════════╣
║  EXECUTION PHASE — "Build and learn"                              ║
╠═══════════════════════════════════════════════════════════════════╣
║  Step 8: Implementation        → Build the solution               ║
║  Step 9: Reflection            → Assess results                   ║
║  Step 10: Resolution           → Conclude with findings           ║
╚═══════════════════════════════════════════════════════════════════╝
```

---

## MVP Scope (Steps 1–3)

### Step 1 Output: `ProblemDefinitionPackage`
Canonical problem statement, stakeholders, constraints (hard/soft), scope (in/out), success criteria, assumptions, and handoff to requirements.

### Step 2 Output: `RequirementsPackage`
Functional (FR), non-functional (NFR), constraint (CR), and interface (IR) requirements with traceability to Step 1, coverage analysis, and verification methods.

### Step 3 Output: `ObjectivesPackage`
Capability (CAP), quality (QUAL), compliance (COMP), and interface (INTF) objectives with success criteria, key results, trace map to requirements, and success framework (minimum viable / target / aspirational).

---

## Reasoning Visibility

SOLVER does **not** depend on hidden model internals. "Visibility" means:

- Outputs are stored and reviewable
- Governing methodology is linked to each artifact
- Trace links connect artifacts across steps
- Verification hooks and evidence pointers are explicit
- Approvals/revisions are recorded in audit logs

The system is designed for **stateless LLM interaction**; reasoning is made auditable through persistent, reviewable artifacts rather than model introspection.

---

## Architecture

```mermaid
graph TD
    User((User)) <--> FE[Frontend Layer<br/>Next.js 14 + Vercel AI SDK]
    FE <--> API[API Layer<br/>FastAPI + SSE Streaming]
    API <--> ORCH[Orchestration Layer<br/>LangGraph State Machine]
    ORCH <--> LLM[LLM Layer<br/>Claude API, OpenAI API, or Gemini API]
    ORCH <--> DB[(Persistence Layer<br/>PostgreSQL + pgvector)]
    ORCH -.-> OBS[Observability<br/>LangSmith / Langfuse]
```

| Layer | Technology | Role |
|-------|------------|------|
| Frontend | Next.js 14+, Vercel AI SDK, assistant-ui | User interface, SSE client |
| API | FastAPI, Python 3.11+ | REST endpoints, SSE streaming |
| Orchestration | LangGraph 1.0+ | State machine, interrupts, checkpointing |
| Persistence | PostgreSQL + pgvector | Artifacts, audit logs, embeddings |
| LLM | Claude API, OpenAI API, or Gemini API | Agent reasoning and generation |
| Observability | LangSmith / Langfuse | Tracing, debugging, cost tracking |

---

## Project Structure

```
solver-engine/
├── docs/
│   └── spec/
│       ├── 0_Document-Type-Specifications-v2.1.md  # Governance framework
│       ├── 1_SOLVER-README.md                      # Project orientation
│       ├── 2_SOLVER-Design-Intent-v1.1.md          # Why² — Design rationale
│       ├── 3_SOLVER-Architectural-Contract-v3.4.md # Why — Invariants
│       ├── 4_solver-technical-spec-V2.7.3.md       # What — Schemas, endpoints
│       ├── 5_SOLVER-Development-Directive-v1.5.md  # How — Phases, gates
│       └── 6_SOLVER-Change-Management-v1.2.md      # Process — Change control
├── apps/
│   ├── api/                    # FastAPI backend
│   │   ├── domain/             # Pure domain models
│   │   ├── application/        # Use cases / services
│   │   ├── infrastructure/     # DB, LLM adapters
│   │   ├── tests/              # API tests (pytest)
│   │   └── routes/             # REST routes
│   └── web/                    # Next.js frontend (future)
├── packages/
│   ├── contracts/              # Shared schemas
│   └── instance_packs/
│       └── instance_0/         # Seed methodology pack
├── infra/
│   ├── docker/
│   │   └── docker-compose.yml
│   └── db/
│       └── migrations/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── tools/                      # Validation scripts
```

---

Checkpoint persistence uses a custom saver aligned to the current schema; see `docs/DECISIONS.md` (Decision #5).

## API Overview

All endpoints under `/api/v1`.

### REST Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/workflows` | Create workflow (problem + instance) |
| GET | `/workflows/{id}` | Current state + position |
| POST | `/workflows/{id}/resume` | Resume from checkpoint |
| POST | `/workflows/{id}/actions/approve` | Approve gate |
| POST | `/workflows/{id}/actions/revise` | Request revision with feedback |
| POST | `/workflows/{id}/actions/message` | Comment without state change |
| POST | `/workflows/{id}/actions/clarify` | Submit clarification answers |
| GET | `/workflows/{id}/progress` | Progress snapshot (canonical refetch bundle) |
| GET | `/workflows/{id}/staleness` | Staleness snapshot (canonical refetch bundle) |
| POST | `/workflows/{id}/actions/acknowledge-stale` | Acknowledge stale items |
| POST | `/workflows/{id}/actions/re-execute` | Re-execute stale step (stub) |

Endpoints listed here are currently implemented. See `docs/spec/4_solver-technical-spec-V2.7.3.md` for additional planned endpoints (history, traceability).

### SSE Stream

`GET /workflows/{id}/stream?from_sequence=N` — Structured events during execution:

```
workflow.started        Workflow execution began
step.started           Step execution began
step.awaiting_clarification Needs user input
step.awaiting_review   Ready for human approval
artifact.delta         Streaming output chunk
artifact.final         Final artifact ready
step.approved          Step approved
step.revision_requested Revision requested
workflow.completed     Workflow finished
error                  Error occurred
```

Events are persisted to the database with monotonic sequence numbers. The `from_sequence` parameter enables reliable reconnection by replaying only events with `sequence > N`. Late-connecting clients receive the full event history.

---

## Acceptance Gates

MVP is complete when all gates pass:

| Gate | Criterion | Verification |
|------|-----------|--------------|
| **A** | Methodology exists | 36 docs (3 steps × 4 types × 3 versions) |
| **B** | Packages with traces | Schema validation + trace link verification |
| **C** | Gating enforced | Cannot advance without approve; message doesn't bypass |
| **D** | Restart works | State survives process kill |
| **E** | API + SSE works | Full interactive flow (UI optional) |
| **F** | Audit complete | Timeline reconstructable from audit_log |

Approved deviations from gate scenarios (if any) are recorded in `docs/DECISIONS.md`.

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Anthropic API key, OpenAI API key, or Google GenAI API key

### Setup

```bash
# Clone and configure
git clone <repo-url> && cd solver-engine
cp apps/api/.env.example apps/api/.env
# Add ANTHROPIC_API_KEY, OPENAI_API_KEY, or GOOGLE_API_KEY to apps/api/.env

# Start database
docker compose -f infra/docker/docker-compose.yml up -d

# Run migrations
make migrate

# Verify database
docker exec solver-db psql -U solver -d solver -c "\dt"
# → 10 tables (9 schema + alembic_version)

# Start API server
make dev-api
# → API available at http://localhost:8000
```

---

## Development

Authority order and change-control are defined in:
- `docs/spec/0_Document-Type-Specifications-v2.1.md`
- `AGENTS.md`

### With AI Coding Agent

The [Development Directive](docs/spec/5_SOLVER-Development-Directive-v1.5.md) provides complete instructions:

```
"Read docs/spec/5_SOLVER-Development-Directive-v1.5.md in full.
This is your authoritative operating manual."

"Begin slice P1.1"
```

Work proceeds in **small slices**, each ending with:
1. Changed files list
2. Commands run + results
3. Which gate(s) satisfied
4. Next slice plan

### Manual Development

```bash
cd apps/api
pip install -e ".[dev]"
make test    # Run tests
make lint    # Run linting
make dev     # Start dev server
```

### Verification

```bash
make test              # Unit tests
make e2e               # End-to-end gate checks (starts local SSE server; requires database running)
make test-gates        # Gate enforcement tests
make test-recovery     # Restart/resume tests
python tools/validate_schemas.py   # Schema validation
```

---

## Design Tradeoffs

SOLVER prioritizes **correctness over speed**:

| Tradeoff | SOLVER Choice | Consequence |
|----------|---------------|-------------|
| Speed vs Correctness | Correctness | 10-step process is slow |
| Flexibility vs Rigor | Rigor | Cannot skip steps |
| Autonomy vs Control | Control | Human gates required |

**Good fit:** High-stakes decisions, regulated domains, audit requirements, complex multi-step reasoning

**Poor fit:** Quick questions, simple lookups, time-critical responses, low-stakes decisions

---

## Documentation

| Document | Purpose |
|----------|---------|
| [ONBOARDING.md](docs/ONBOARDING.md) | Senior developer onboarding guide |
| [CO-DEV-ONBOARDING.md](docs/CO-DEV-ONBOARDING.md) | Co-developer (reviewer) onboarding guide |
| [CLAUDE.md](CLAUDE.md) | Claude Code development guide |
| [AGENTS.md](AGENTS.md) | Repo-level instructions for AI coding agents |
| [SOLVER README](docs/spec/1_SOLVER-README.md) | Project orientation |
| [Design Intent](docs/spec/2_SOLVER-Design-Intent-v1.1.md) | Why² — Design rationale |
| [Architectural Contract](docs/spec/3_SOLVER-Architectural-Contract-v3.4.md) | Why — Invariants, constraints |
| [Technical Spec](docs/spec/4_solver-technical-spec-V2.7.3.md) | What — Schemas, endpoints |
| [Development Directive](docs/spec/5_SOLVER-Development-Directive-v1.5.md) | How — Phases, packages, gates |

---

## Status

**Phase:** P6 Verification complete (MVP gates satisfied)

| Phase | Status | Description |
|-------|--------|-------------|
| P1 Foundation | ✅ Complete | Directory structure, Docker, database schema |
| P2 Persistence | ✅ Complete | SQLAlchemy models, repositories, checkpoint adapter |
| P3 Orchestration | ✅ Complete | LangGraph state machine, interrupt/resume |
| P4 API | ✅ Complete | REST endpoints, SSE streaming, graph wiring |
| P5 Content | ✅ Complete | Artifact storage, schema validation, traceability |
| P6 Verification | ✅ Complete | Gate C ✓, Gate D ✓, Gate E ✓, Gate F ✓ |

**MVP Focus:** Steps 1–3 with two-pass workflow, persistence, gates, streaming, and auditability

Deferred items are tracked in `docs/DECISIONS.md`.

---

## License

TBD

---

*SOLVER: Because some problems are too important for "trust me, I'm an AI."*
