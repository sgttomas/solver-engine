# CLAUDE.md — AI Development Guide for SOLVER

## Project Overview

**SOLVER** is a Structured Reasoning Workflow Engine that acts as a deterministic supervisor for stochastic agents. This is NOT a typical agent framework—it optimizes for **rigor, traceability, and human oversight** rather than speed and autonomy.

### Core Principles

1. **Method and Content are Separate** — Two-pass execution model
2. **Human Gates are Mandatory** — LLMs cannot advance workflow states
3. **Everything is Traceable** — Persistent artifacts, audit logs, version tracking
4. **Schema Conformance** — All outputs must validate against defined schemas
5. **Stateless LLM Design** — All state lives in PostgreSQL, not conversation history

### Trust Boundary

**What LLMs CAN Influence:**
- Artifact content (methodology documents, deliverables)
- Reasoning text and explanations
- Clarification questions
- Revision attempts

**What LLMs CANNOT Influence:**
- State transitions between steps
- Gate approvals (approve/revise/message)
- Step advancement
- Workflow completion status

Even if an LLM outputs "I approve this" or "ready to advance," the system ignores it. Only external API calls from authenticated actors can advance the workflow.

---

## Authority Stack (CRITICAL)

When working on this codebase, you MUST follow the document hierarchy:

| Priority | Document | Governs | Location |
|----------|----------|---------|----------|
| **1st** | Meta-Prompt | **Why** — Logic, reasoning rules, gates | `docs/spec/1_meta-prompt-structured-reasoning.md` |
| **2nd** | Architecture | **Where** — Components, layers, boundaries | `docs/spec/2_structured-reasoning-architecture.md` |
| **3rd** | Technical Spec | **What** — Tables, endpoints, schemas | `docs/spec/3_solver-technical-spec.md` |
| **4th** | Development Directive | **How** — AI agent instructions, slices | `docs/spec/0_SOLVER-Development-Directive.md` |

### Authority Rules

- If documents conflict, **higher priority wins**
- All deviations require approval and entry in `docs/DECISIONS.md`
- Before implementing ANY feature, read relevant spec sections
- When in doubt, ask for clarification rather than making assumptions

---

## Two-Pass Execution Model

Every step in the 10-step workflow executes in two passes:

### Pass 1: Methodology Generation

Generate and refine four methodology documents through V1 → V2 → V3:

| Document | Purpose |
|----------|---------|
| **Data Sheet** | Input/output contracts, schemas, validation rules |
| **To Do List** | Task decomposition, checkpoints, validation hooks |
| **Guidance** | Context, principles, anti-patterns, quality criteria |
| **Detailed Procedure** | State machine, algorithms, decision logic, gates |

### Pass 2: Supervised Execution

Apply the V3 methodology to produce the deliverable artifact, then **interrupt** for human review:

- **Approve**: Advance to next step
- **Revise**: Re-run step with feedback
- **Message**: Record commentary without state change

---

## MVP Scope

**Current Focus:** Steps 1–3 only (Definition Phase)

| Step | Output | Description |
|------|--------|-------------|
| **Step 1** | `ProblemDefinitionPackage` | Canonical problem statement, stakeholders, constraints, scope, success criteria |
| **Step 2** | `RequirementsPackage` | FR, NFR, CR, IR requirements with traceability and verification methods |
| **Step 3** | `ObjectivesPackage` | CAP, QUAL, COMP, INTF objectives with success criteria and key results |

**Out of scope for MVP:** Steps 4–10 (Verification and Execution phases)

---

## Acceptance Gates

MVP completion requires ALL gates to pass:

| Gate | Criterion | Verification Method |
|------|-----------|---------------------|
| **A** | Methodology exists | 36 docs (3 steps × 4 types × 3 versions) present |
| **B** | Packages with traces | Schema validation + trace link verification |
| **C** | Gating enforced | Cannot advance without approve; message doesn't bypass |
| **D** | Restart works | State survives process kill and resumes correctly |
| **E** | API + SSE works | Full interactive flow (UI optional) |
| **F** | Audit complete | Timeline reconstructable from audit_log table |

When implementing features, always consider which gate(s) your work satisfies.

---

## Project Structure

```
solver-engine/
├── docs/
│   └── spec/                           # Authority documents (READ THESE FIRST)
│       ├── 0_SOLVER-Development-Directive.md
│       ├── 1_meta-prompt-structured-reasoning.md
│       ├── 2_structured-reasoning-architecture.md
│       └── 3_solver-technical-spec.md
├── apps/
│   ├── api/                            # FastAPI backend
│   │   ├── domain/                     # Pure domain models (no external deps)
│   │   ├── application/                # Use cases / services
│   │   ├── infrastructure/             # DB adapters, LLM clients
│   │   └── api/                        # REST routes, SSE handlers
│   └── web/                            # Next.js frontend (future)
├── packages/
│   ├── contracts/                      # Shared schemas (Pydantic/TypeScript)
│   └── instance_packs/
│       └── instance_0/                 # Seed methodology pack
├── infra/
│   ├── docker-compose.yml
│   └── db/migrations/                  # SQL migration files
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/                            # Gate verification tests
└── tools/                              # Validation scripts
```

---

## Architecture Layers

### 1. Frontend Layer
- **Tech:** Next.js 14+, Vercel AI SDK, assistant-ui
- **Role:** User interface, SSE client for streaming
- **Status:** Future work (MVP uses API directly)

### 2. API Layer
- **Tech:** FastAPI, Python 3.11+
- **Role:** REST endpoints, SSE streaming, request validation
- **Location:** `apps/api/api/`

### 3. Orchestration Layer
- **Tech:** LangGraph 1.0+
- **Role:** State machine, interrupts, checkpointing, workflow control
- **Location:** `apps/api/application/`
- **Critical:** This layer enforces gates—LLM cannot bypass

### 4. Persistence Layer
- **Tech:** PostgreSQL + pgvector
- **Role:** Artifacts, audit logs, embeddings, checkpoints
- **Location:** `apps/api/infrastructure/db/`
- **Tables:** workflows, workflow_state, artifacts, audit_log, methodology_docs

### 5. LLM Layer
- **Tech:** Claude API (Anthropic) or OpenAI API
- **Role:** Generate methodology docs and deliverable artifacts
- **Location:** `apps/api/infrastructure/llm/`
- **Constraint:** Cannot influence state transitions

### 6. Observability Layer
- **Tech:** LangSmith / Langfuse
- **Role:** Tracing, debugging, cost tracking
- **Status:** To be implemented

---

## Development Workflow

### Before Starting Work

1. **Read the specs** in `docs/spec/` relevant to your task
2. **Check existing structure** before creating new files
3. **Follow the authority stack** when making decisions
4. **Verify which gate(s)** your work will satisfy

### Implementation Approach

Work in **small slices**. Each slice should:

1. Have a clear, testable outcome
2. Reference which spec section it implements
3. Satisfy or progress toward a specific gate
4. Include verification commands and results

### After Completing Work

Each slice should produce:

1. **Changed files list** with brief description
2. **Commands run** + their results (tests, lints, etc.)
3. **Which gate(s) satisfied** or progressed
4. **Next slice plan** (what comes next)

---

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
| GET | `/workflows/{id}/history` | Artifacts + audit trail |
| GET | `/workflows/{id}/staleness` | Staleness report |

### SSE Stream Events

`GET /workflows/{id}/stream` emits:

```
workflow.started
step.started
artifact.delta              # Streaming chunk during generation
artifact.final              # Complete artifact ready
step.awaiting_review        # Human gate triggered
step.approved
step.revision_requested
artifact.stale
workflow.completed
error
```

---

## Key Design Decisions

### 1. Why Two-Pass Execution?

Separating methodology from content prevents:
- Inconsistent application of reasoning steps
- Hidden assumptions in deliverables
- Difficulty auditing "how we got here"

### 2. Why Human Gates?

LLMs cannot reliably self-assess quality. External approval ensures:
- Human oversight of critical decisions
- Ability to course-correct before compounding errors
- Audit trail of who approved what and when

### 3. Why Stateless LLM Design?

Conversation history is not durable or queryable. Persistent artifacts enable:
- Process restart without loss
- Parallel workflow execution
- Historical analysis and learning
- Regulatory compliance

### 4. Why Schema Enforcement?

Freeform outputs resist automation. Schemas enable:
- Automated validation and quality checks
- Reliable trace link extraction
- Integration with downstream tools
- Consistent audit log format

---

## Common Pitfalls (AVOID THESE)

### ❌ DON'T

1. **Skip reading the specs** — "I'll just look at the code"
2. **Let LLM control state** — "Just let Claude/OpenAI decide when to advance"
3. **Make assumptions about schemas** — "This field probably means..."
4. **Hardcode workflow logic** — "Step 3 always comes after Step 2"
5. **Ignore trace links** — "We don't need full traceability yet"
6. **Skip gate tests** — "We'll add approval enforcement later"
7. **Mix concerns across layers** — "Let's put LLM calls in the API route"
8. **Optimize for speed** — "Let's auto-approve trivial steps"

### ✅ DO

1. **Read authority docs first** — Start with specs, not code
2. **Enforce gates strictly** — Only API calls can advance state
3. **Validate against schemas** — Every artifact, every time
4. **Make workflow data-driven** — Read step definitions from DB/config
5. **Track everything** — Audit log for all state changes
6. **Test gate enforcement** — Verify LLM cannot bypass approvals
7. **Respect layer boundaries** — Domain → Application → Infrastructure → API
8. **Prioritize correctness** — Slow and right beats fast and wrong

---

## Testing Strategy

### Unit Tests
```bash
cd apps/api
make test
```

Test domain logic in isolation. No external dependencies.

### Integration Tests
```bash
make test-integration
```

Test layer interactions (e.g., LangGraph → DB, API → LLM).

### Gate Tests
```bash
make test-gates
```

**Critical:** Verify that:
- LLM output claiming "approved" doesn't advance state
- Only `/actions/approve` endpoint advances workflow
- `/actions/message` doesn't change state

### End-to-End Tests
```bash
make e2e
```

Run full workflow through Steps 1–3, verifying:
- All 36 methodology docs generated
- Schema validation passes
- Trace links present
- Audit log complete

### Recovery Tests
```bash
make test-recovery
```

Verify state survives:
- Process kill and restart
- Database connection loss and reconnection
- Checkpoint restore

---

## Environment Setup

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Anthropic API key

### Quick Start

```bash
# Clone and configure
cd /Users/ryan/ai-env/projects/solver-engine
cp .env.example .env
# Add ANTHROPIC_API_KEY to .env

# Start services
docker-compose up -d

# Run migrations
make migrate

# Verify
curl http://localhost:8000/health
# Expected: {"status": "ok", "database": "connected"}
```

### Development Commands

```bash
make dev              # Start dev server with hot reload
make test             # Run unit tests
make lint             # Run linting (ruff, mypy)
make format           # Auto-format code
make migrate          # Run DB migrations
make test-gates       # Test gate enforcement
make e2e              # End-to-end tests
python tools/validate_schemas.py   # Validate artifact schemas
```

---

## Working with Specs

### Reading Order for New Features

1. **Development Directive** (`0_SOLVER-Development-Directive.md`) — Understand slice-based workflow
2. **Meta-Prompt** (`1_meta-prompt-structured-reasoning.md`) — Understand reasoning rules and gates
3. **Architecture** (`2_structured-reasoning-architecture.md`) — Understand system components
4. **Technical Spec** (`3_solver-technical-spec.md`) — Understand implementation details

### When to Update Specs

If you discover:
- Ambiguity or contradiction between specs
- Missing critical information
- Implementation decision not covered by specs

**Process:**
1. Note the issue in your response
2. Propose a resolution aligned with SOLVER principles
3. Wait for human approval
4. Add entry to `docs/DECISIONS.md`
5. Update relevant spec if needed

---

## Design Tradeoffs

SOLVER makes deliberate tradeoffs favoring **correctness over speed**:

| Dimension | SOLVER Choice | Consequence |
|-----------|---------------|-------------|
| Speed vs Correctness | **Correctness** | 10-step process is slow |
| Flexibility vs Rigor | **Rigor** | Cannot skip steps |
| Autonomy vs Control | **Control** | Human gates required |
| Simplicity vs Auditability | **Auditability** | More persistence overhead |

### Good Fit
- High-stakes decisions
- Regulated domains (healthcare, finance, legal)
- Complex multi-step reasoning
- Audit requirements
- Research and analysis

### Poor Fit
- Quick questions or simple lookups
- Time-critical responses
- Low-stakes decisions
- Simple CRUD operations

---

## Instance Hierarchy

| Instance | Name | Role |
|----------|------|------|
| **Instance 0** | Universal Methodology | Defines 10-step process + schemas + "4 Documents" scaffold |
| **Instance 1** | SOLVER Software | Implements Instance 0 as executable runtime (this repo) |
| **Instance N** | Domain Specialization | Adds domain schemas/templates without changing core |

**Current Work:** Implementing Instance 1 (the software runtime)

**Future Work:** Enable Instance N creation (e.g., "Instance 2: Medical Diagnosis Solver")

---

## Contribution Guidelines

### Code Style
- Follow PEP 8 for Python
- Use type hints throughout
- Prefer explicit over implicit
- Document "why" not "what" in comments

### Commit Messages
```
feat(domain): add ProblemDefinitionPackage schema
test(gates): verify approve-only advancement
fix(api): correct SSE event serialization
docs(spec): clarify trace link requirements
```

### Pull Request Template
1. **Spec Reference:** Which spec section(s) does this implement?
2. **Gate Progress:** Which gate(s) does this satisfy/advance?
3. **Changed Files:** List with brief purpose
4. **Testing:** Commands run + results
5. **Next Steps:** What comes after this is merged?

---

## Current Status

**Phase:** Implementation in progress
**Focus:** MVP (Steps 1–3 with two-pass execution, gates, persistence, streaming)
**Next Milestones:**
1. Gate A: Generate all 36 methodology documents
2. Gate B: Schema validation + trace links working
3. Gate C: Gate enforcement verified (approve-only advancement)
4. Gate D: Checkpoint/restart working
5. Gate E: Full API + SSE flow working
6. Gate F: Complete audit trail

---

## Questions to Ask Before Implementing

1. **Which spec covers this?** Have I read the relevant sections?
2. **Which gate does this advance?** How will I verify it works?
3. **What's the authority?** If specs conflict, which takes precedence?
4. **Where does this live?** Which layer/directory is correct?
5. **How is this traced?** What goes in the audit log?
6. **Can LLM bypass this?** If it's a gate, how do I enforce it?
7. **What's the schema?** Is this artifact validated?
8. **Is this testable?** Can I verify this works in isolation?

## Summary for AI Coding Agents

You are working on **SOLVER**, a structured reasoning engine that prioritizes rigor over speed. Key points:

1. **Read specs first** (`docs/spec/`) before implementing anything
2. **Follow authority stack** (Meta-Prompt > Architecture > Technical Spec)
3. **Enforce gates strictly** — LLMs cannot advance workflow state
4. **Validate everything** — All artifacts must conform to schemas
5. **Work in small slices** — Testable increments that satisfy gates
6. **Audit all changes** — State transitions go to audit_log
7. **Test gate enforcement** — Critical that LLM cannot bypass approvals
8. **Respect layer boundaries** — Domain → Application → Infrastructure → API
9. **Prioritize correctness** — Slow and auditable beats fast and opaque
10. **Ask when unsure** — Better to clarify than assume

**Remember:** This is not a typical agent framework. SOLVER is designed for high-stakes reasoning where trustworthiness and traceability matter more than speed or autonomy.

---

*Generated for SOLVER — Structured Reasoning Workflow Engine*
*Last Updated: 2026-01-02*
