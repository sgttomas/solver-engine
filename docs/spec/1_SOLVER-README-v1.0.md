# SOLVER Project

**Structured Workflow Generator for Human-AI Collaborative Knowledge Work**

**Document Status:** Governed as of 2025-01-04. See `SOLVER-Change-Management-v2.0.md` for change control rules.

---

## What is SOLVER?

SOLVER is a workflow engine that orchestrates Claude (or other LLMs) through a rigorous, gated reasoning process. Given a complex problem, it produces detailed specifications by breaking work into steps with mandatory human approval gates.

**The core value proposition:** Errors caught early don't propagate. Human expertise shapes AI output at critical junctures. Every approval is recorded against verified state.

---

## Project Documentation Structure

This project uses a four-document taxonomy that separates concerns by the question each document answers:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         WHY² (Design Intent)                        │
│         "Why must the architecture be this way?"                    │
│                                                                     │
│   • First principles and design rationale                          │
│   • Rejected alternatives and why                                  │
│   • Failure modes we're protecting against                         │
│   • Assumptions that would trigger rethinking                      │
│                                                                     │
│   Stability: MOST STABLE — changes when problem space changes      │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      WHY (Architectural Contract)                   │
│              "What must be true for correctness?"                   │
│                                                                     │
│   • Invariants and contracts (MUST/SHALL language)                 │
│   • Persistence, API, streaming, safety contracts                  │
│   • Frontend reliability rules (R1-R19)                            │
│   • Conformance checklists                                         │
│                                                                     │
│   Stability: VERY STABLE — changes when correctness changes        │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      WHAT (Technical Specification)                 │
│                   "What are we building?"                           │
│                                                                     │
│   • Database schemas and migrations                                │
│   • API endpoints and response formats                             │
│   • State machines and transitions                                 │
│   • Code structure and patterns                                    │
│                                                                     │
│   Stability: MODERATELY STABLE — changes as implementation evolves │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      HOW (Development Directive)                    │
│                    "How do we build it?"                            │
│                                                                     │
│   • Phases and gates                                               │
│   • Packages and deliverables                                      │
│   • Verification steps                                             │
│   • Dependency graph and critical path                             │
│                                                                     │
│   Stability: LEAST STABLE — changes every sprint/iteration         │
└─────────────────────────────────────────────────────────────────────┘
```

### The Document Index

| Document | Question | File |
|----------|----------|------|
| **Document-Type Specifications** | Governance model | `0_Document-Type-Specifications-v2.1.1.md` |
| **Change Management** | Governance | `SOLVER-Change-Management-v2.0.md` |
| **Design Intent** | Why² | `SOLVER-Design-Intent-v1.1.md` |
| **Architectural Contract** | Why | `SOLVER-Architectural-Contract-v3.4.md` |
| **Technical Specification** | What | `4_SOLVER-Technical-Spec-V2.8.0.md` |
| **Development Directive** | How | `SOLVER-Development-Directive-v1.5.md` |

### When to Consult Each Document

| If you need to... | Consult |
|-------------------|---------|
| Understand why a decision was made | Design Intent (Why²) |
| Know what invariants must hold | Architectural Contract (Why) |
| Find a schema, endpoint, or code pattern | Technical Specification (What) |
| Know what to build next | Development Directive (How) |
| Challenge an architectural decision | Design Intent first, then Contract |
| Verify implementation correctness | Contract checklists, then Directive gates |

### The Cascade Property

Changes flow downward through the hierarchy:

```
Why² changes → revisit Why → update What → revise How
```

But changes should NOT flow upward without deliberation:

```
How changes → What probably unchanged
What changes → Why should be unchanged
Why changes → Why² should be unchanged (or you're redefining the problem)
```

**The implication:** If you find yourself wanting to change a contract (Why) to accommodate an implementation detail (How), stop. Either the implementation is wrong, or you've discovered a flaw in the contract that needs explicit discussion.

---

## Project Execution Structure

The Development Directive organizes work into a hierarchy:

```
PROJECT
   │
   ├── PHASE 1: Foundation
   │      │
   │      ├── Package 1.1: Project Skeleton
   │      │      ├── Deliverable: FastAPI application structure
   │      │      ├── Deliverable: Docker Compose configuration
   │      │      ├── Deliverable: Health endpoint
   │      │      └── Verification: docker-compose up succeeds
   │      │
   │      ├── Package 1.2: Domain Models
   │      │      ├── Deliverable: Enums (PassType, StepStatus, ...)
   │      │      ├── Deliverable: State dataclasses
   │      │      └── Verification: Unit tests pass
   │      │
   │      └── Package 1.3: Database Schema
   │             ├── Deliverable: Alembic migrations
   │             ├── Deliverable: All tables and constraints
   │             └── Verification: alembic upgrade head succeeds
   │      
   │      ════════════════════════════════════════════
   │                    GATE α1, α2
   │      ════════════════════════════════════════════
   │
   ├── PHASE 2: Persistence Contracts
   │      │
   │      ├── Package 2.1: Event Log
   │      ├── Package 2.2: Workflow State
   │      ├── Package 2.3: Audit Logging
   │      └── Package 2.4: Staleness Trigger
   │      
   │      ════════════════════════════════════════════
   │                    GATE β1, β2a, β5, β6a
   │      ════════════════════════════════════════════
   │
   └── ... (Phases 3-8)
```

### Hierarchy Definitions

| Level | Definition | Example |
|-------|------------|---------|
| **Phase** | Major milestone with coherent objective | "Phase 2: Persistence Contracts" |
| **Gate** | Exit criteria that must pass to proceed | "β1: Event Sequence Safety" |
| **Package** | Cohesive unit of work with clear scope | "Package 2.1: Event Log" |
| **Deliverable** | Concrete artifact produced | "emit_and_persist_event() function" |
| **Task** | Atomic unit of work by one developer | "Implement advisory lock pattern" |

### Gate Types

| Series | Name | Purpose |
|--------|------|---------|
| **α** | Infrastructure | Environment runs, schema applied, graph operational |
| **β** | Contract | Persistence, concurrency, streaming contracts verified |
| **γ** | Integration | End-to-end flows, client-server sync, UI gating |
| **A-F** | Acceptance | Final MVP criteria from specification |

### The Gate Contract

Gates are binary: **PASS** or **FAIL**. There is no "mostly passing."

Each gate has:
- **Criterion:** Precise definition of what must be true
- **Verification:** How to test it (script, query, manual check)
- **Blocking:** What cannot proceed until this passes

**Example:**

```
Gate β1: Event Sequence Safety

Criterion: Concurrent event emission produces gap-free sequences

Verification:
    async def test_concurrent_sequences():
        tasks = [emit_event(wf_id, "test", {}) for _ in range(100)]
        sequences = await asyncio.gather(*tasks)
        assert sorted(sequences) == list(range(1, 101))
        assert len(set(sequences)) == 100

Blocking: Phase 3 cannot start until β1 passes
```

---

## How Documentation Supports Execution

The four-document structure is not arbitrary — it directly supports the development process:

### 1. Design Intent Enables Decision-Making

When a developer encounters an ambiguous situation:

```
"Should I optimize this query or keep it simple?"
```

The Design Intent provides the answer:

```
§8.3: "MVP favors simplicity over optimization."
§8.4: "Explicit code is debuggable. Magic fails mysteriously."
→ Keep it simple.
```

Without Why², developers either guess (inconsistent decisions) or ask (slow).

### 2. Contracts Define Gate Criteria

Gates test whether contracts are satisfied:

| Gate | Tests Contract |
|------|----------------|
| β1 (Event Sequence Safety) | §9.2 Event Log Contract: sequences MUST be gap-free |
| β3 (Optimistic Concurrency) | §11.1: actions MUST include expected_state_version |
| γ3 (Action Gating) | §13.4: canAct rules R3-R6, R14-R15 |

**The relationship:** Contracts define correctness. Gates verify correctness. If a gate fails, a contract is violated.

### 3. Specification Defines Deliverables

Each package's deliverables map to specification sections:

| Package | Deliverable | Specification Section |
|---------|-------------|----------------------|
| 1.3 | artifacts table | §7.3 Database Schema |
| 4.1 | GET /workflows/{id}/progress | §9.1 REST Routes |
| 6.3 | Sequence guard | Contract §14.2 |

**The relationship:** Specification says *what* to build. Packages organize *when* to build it.

### 4. Directive Sequences Work Correctly

The Development Directive's dependency graph ensures:

```
Package 2.1 (Event Log) 
    → Package 4.2 (SSE Streaming) 
        → Package 6.6 (Frontend Event Handling)
```

You can't build SSE streaming without the event log. You can't build frontend event handling without SSE streaming. The Directive encodes this.

### 5. Verification Closes the Loop

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   Design Intent ──defines──► Architectural Contract             │
│        │                            │                           │
│        │                            │ defines                   │
│        │                            ▼                           │
│        │                     Gate Criteria                      │
│        │                            │                           │
│        │                            │ verified by               │
│        │                            ▼                           │
│        │                     Conformance Tests                  │
│        │                            │                           │
│        │                            │ run against               │
│        │                            ▼                           │
│        └──informs──► Technical Spec ──built by──► Code          │
│                            │                        │           │
│                            │ organized by           │           │
│                            ▼                        │           │
│                     Development Directive           │           │
│                            │                        │           │
│                            └────────────────────────┘           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## For Different Audiences

### For New Team Members

1. Read **Design Intent** §1-2 (Core Problem, Trust Model) — 10 minutes
2. Skim **Architectural Contract** Part I (Architecture) — 15 minutes
3. Read **Development Directive** Gate Definitions — 5 minutes
4. Find your assigned Package in the Directive
5. Read the relevant Specification sections for your Package

### For Architects / Tech Leads

1. Read **Design Intent** fully — understand the reasoning
2. Read **Architectural Contract** Part II (Contracts) — know the invariants
3. Use Contract checklists (Part III) for code review
4. Update Design Intent when assumptions change

### For AI Coding Agents

1. Always check **Directive** for current Package and gate requirements
2. Consult **Specification** for schemas, endpoints, code patterns
3. Verify work against **Contract** checklists before marking complete
4. If blocked by ambiguity, consult **Design Intent** for principles

### For Project Managers

1. Track progress by **Gate** completion (binary: pass/fail)
2. **Phases** map to milestones
3. **Packages** map to sprint work items
4. Use Directive dependency graph for scheduling

---

## Document Maintenance

### Change Frequency

| Document | Expected Change Frequency |
|----------|---------------------------|
| Design Intent | Rarely (major pivots only) |
| Architectural Contract | Occasionally (new invariants, refined contracts) |
| Technical Specification | Regularly (new features, schema changes) |
| Development Directive | Frequently (every planning cycle) |

### Change Process

| Change Type | Process |
|-------------|---------|
| Fix typo/clarification | Direct commit |
| Add new contract/invariant | Review against Design Intent, update Contract + Spec + Directive |
| Change existing contract | Review Design Intent assumptions, explicit team discussion |
| Challenge Design Intent | Requires evidence that assumptions have changed |

### Version Alignment

Documents reference each other by version. When updating:

1. Update the source document
2. Update references in downstream documents
3. Bump version numbers
4. Update Document Index in this README

---

## Quick Reference

### Current Document Versions

| Document | Version | Last Updated |
|----------|---------|--------------|
| Design Intent | v1.1 | 2025-01-04 |
| Architectural Contract | v3.4 | 2025-01-04 |
| Technical Specification | v2.8.0 | 2025-01-04 |
| Development Directive | v1.5 | 2025-01-04 |

### Key Concepts

| Concept | Definition | Where Defined |
|---------|------------|---------------|
| state_version | Monotonic version for optimistic concurrency | Contract §9.1 |
| sequence | Monotonic event order per workflow | Contract §9.2 |
| canAct | Computed eligibility for approve/revise | Contract §14.3 |
| canonical refetch | Three-endpoint bundle for authoritative state | Contract §10.4 |
| defense in depth | Client gating + server validation | Design Intent §4.3 |

### Critical Invariants

| Invariant | Consequence if Violated |
|-----------|------------------------|
| state_version monotonicity | Optimistic concurrency breaks, corruption possible |
| Event sequence contiguity | Replay incomplete, audit trail has holes |
| Atomic transitions | Inconsistent state between event log and snapshot |
| Broadcast after commit | Clients see state that doesn't exist |
| Exclusive execution | Duplicate events, race conditions |

---

## Getting Started

> **Note:** This documentation set defines the architecture and contracts for SOLVER. The codebase is built following the Development Directive phases. The commands below represent the *target* development environment, not a currently running system.

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Node.js 18+
- PostgreSQL client tools (psql, pg_dump)

### First Steps 

```bash
# Clone the repository
git clone <repository-url>
cd solver

# Read the orientation (this document)
# Then read Design Intent §1-2 for context

# Start the development environment
docker-compose up -d

# Verify health (Gate α1 criterion)
curl http://localhost:8000/health
# Expected: {"status": "healthy", "database": "connected"}

# Apply database migrations (Gate α2)
alembic upgrade head

# Run the test suite
pytest

# Check current gate status
./scripts/check-gates.sh
```

### Before the Codebase Exists

If you're reading this before implementation begins:

1. **Understand the problem:** Read Design Intent §1-2
2. **Know the rules:** Read Architectural Contract Part II
3. **Find your work:** Check Development Directive for your assigned Phase/Package
4. **Reference details:** Use Technical Specification for schemas and code patterns

### Development Workflow

1. Check **Directive** for your assigned Package
2. Read Package deliverables and verification steps
3. Consult **Specification** for implementation details
4. Implement deliverables
5. Run verification steps
6. Submit for review with checklist items marked

---

## Contributing

### Before Making Changes

1. Identify which document governs your change
2. If changing behavior, check if contracts are affected
3. If contracts change, verify Design Intent still supports them
4. Update all affected documents, not just code

### Pull Request Checklist

- [ ] Code implements Specification correctly
- [ ] Relevant Contract checklist items pass
- [ ] Gate verification steps succeed
- [ ] No regression in prior gates
- [ ] Document versions updated if specs changed

---

*SOLVER Project — Structured Workflow Generator*
*SOLVER-README v1.0*
