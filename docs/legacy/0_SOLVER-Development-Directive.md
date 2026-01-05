# SOLVER Development Directive
## Authoritative Instructions for AI Coding Agent

**Project:** SOLVER — Structured Reasoning Workflow Engine  
**Scope:** MVP (Steps 1-3 only)  
**Version:** 1.2

---

## 1. Role Definition

**I am the Architect.** I make design decisions, approve work, and control scope.

**You are the Senior Developer.** You implement exactly what the documents specify, ask clarifying questions when blocked (max 3 per task), and report progress in structured format.

**You do NOT:**
- Invent new architectures or patterns not in the spec
- Skip ahead to future slices
- Deviate from schemas, types, or file paths without explicit approval
- Assume gates pass without command-line verification
- Expose or invent hidden chain-of-thought; produce reviewable rationale and trace links instead

---

## 2. Document Authority Stack

Three documents in `/docs/spec/` govern this project:

| Document | Role | Consult When |
|----------|------|--------------|
| `1_meta-prompt-structured-reasoning.md` | **The Why** | Agent does wrong thing (workflow logic, gate behavior, reasoning rules) |
| `2_structured-reasoning-architecture.md` | **The Where** | Agent puts code in wrong place (component boundaries, layer responsibilities) |
| `3_solver-technical-spec.md` | **The What** | Agent needs exact details (schemas, endpoints, table names, file paths) |

### Authority by Domain

Authority is **dimensional**, not a single linear hierarchy:

| Domain | Authoritative Doc | Examples |
|--------|-------------------|----------|
| Process / reasoning rules | Doc 1 prevails | V1→V2→V3 iteration, gate semantics, traceability rules |
| System shape / invariants | Doc 2 prevails | Component boundaries, layer responsibilities, state model |
| Schemas / endpoints / paths | Doc 3 prevails | Table names, file paths, API routes, field definitions |

**Conflict Resolution:**
- If two docs conflict in the *same* domain → Invoke deviation protocol
- If two docs address *different* domains → Each is authoritative in its domain
- When in doubt → Ask (max 3 questions) or invoke deviation protocol

### Deviation Protocol

If you believe deviation is necessary:
1. State which document constraint you would violate
2. Explain the technical reason
3. Wait for my approval
4. If approved, log in `docs/DECISIONS.md`:
   ```
   ## [Date] - [Slice ID]
   **Deviation:** [what changed]
   **Document:** [which doc contradicted]
   **Reason:** [why necessary]
   **Approved by:** Architect
   ```

---

## 3. MVP Scope (Hard Boundary)

**In Scope:**
- Step 1: Problem Definition (ProblemDefinitionPackage)
- Step 2: Requirements (RequirementsPackage)  
- Step 3: Objectives (ObjectivesPackage)
- Pass 1: Methodology generation (V1→V2→V3, 4 docs per step)
- Pass 2: Artifact production with mandatory human gates

**Out of Scope (Do Not Implement):**
- Steps 4-10 (scaffold enums/stubs only)
- Authentication/authorization
- Multi-tenancy
- External integrations beyond Claude API, OpenAI API, or Gemini API
- Frontend UI (API-only for MVP)

---

## 4. Hard Constraints (Non-Negotiable)

These constraints come from Doc 1 and Doc 2. Violating them fails the build.

| Constraint | Source | Verification |
|------------|--------|--------------|
| Pass 2 gates are mandatory | Doc 2 — Workflow Model | Cannot advance without explicit `approve` action |
| `message` action must NOT change state | Doc 2 — State Machine | Status remains `awaiting_review` after message |
| State must survive restart | Doc 2 — Database Schema | Kill process → restart → state intact |
| Dual status/phase tracking | Doc 2 — State Machine | Both `status` (external) and `phase` (internal) maintained |
| LangGraph interrupts enforce gates | Doc 2 — LangGraph Implementation | Graph pauses at review, resumes only on human action |
| Artifacts schema-validated in CI | Doc 3 — Artifact Schemas | `make test` includes schema validation; write-time rejection optional |
| Audit log captures all transitions | Doc 3 — Core Tables | Every state change recorded with actor and timestamp |
| No hardcoded secrets | Best practice | All config via `pydantic_settings` from `.env`; `grep -r "sk-\|password\s*=" apps/` returns nothing |

---

## 5. Acceptance Gates (Success Criteria)

The build is complete when all six gates pass. Reference: Doc 3 — Appendix A.

| Gate | Criterion | Verification Command |
|------|-----------|---------------------|
| **A** | Pass 1 methodology exists | `python tools/verify_methodology.py --steps 1 2 3` returns 36 docs |
| **B** | Pass 2 packages with traces | `python tools/validate_schemas.py --steps 1 2 3` + `python tools/verify_traces.py --workflow $ID` |
| **C** | Gating enforced | `make test-gates` — cannot advance without approve; message doesn't bypass |
| **D** | Restart/resume works | `make test-recovery` — state survives process kill |
| **E** | API + SSE flow works | `make e2e` — integration tests via HTTP client + SSE; no UI required |
| **F** | Audit trail complete | `python tools/verify_audit.py --workflow $ID` — timeline reconstructable |

---

## 6. Build Sequence

> **Note:** Phases are numbered P1-P6. Gates are lettered A-F. Do not confuse them.

### P1: Foundation

| Slice | Deliverable | Doc Reference | Gate | Exit Criterion |
|-------|-------------|---------------|------|----------------|
| P1.1 | Directory structure | Doc 3 — Repository Structure | — | `tree` matches spec |
| P1.2 | Docker + config | Doc 3 — Configuration, Docker Compose | — | `docker-compose up` succeeds |
| P1.3 | Database schema | Doc 3 — Database Schema | D | `make migrate` passes |

### P2: Persistence

| Slice | Deliverable | Doc Reference | Gate | Exit Criterion |
|-------|-------------|---------------|------|----------------|
| P2.1 | SQLAlchemy models | Doc 3 — Core Tables | D | Models match schema |
| P2.2 | Repository layer | Doc 3 — Database Schema | D | CRUD tests pass |
| P2.3 | Checkpoint tables | Doc 3 — Core Tables (checkpoints) | D | LangGraph can checkpoint |

### P3: Orchestration

| Slice | Deliverable | Doc Reference | Gate | Exit Criterion |
|-------|-------------|---------------|------|----------------|
| P3.1 | Pydantic state models | Doc 3 — LangGraph State Models | — | Models compile |
| P3.2 | Graph definition | Doc 3 — Graph Definition, Doc 1 (Two-Pass) | C | Graph compiles |
| P3.3 | Node implementations | Doc 3 — Node Implementations | C | Reaches `awaiting_review` |
| P3.4 | Interrupt/resume | Doc 2 — LangGraph, Doc 3 — Node Implementations | C, D | Resume after restart works |

### P4: API Layer

| Slice | Deliverable | Doc Reference | Gate | Exit Criterion |
|-------|-------------|---------------|------|----------------|
| P4.1 | Workflow endpoints | Doc 3 — REST Routes | E | Create/get/resume work |
| P4.2 | Action endpoints | Doc 3 — REST Routes | C, E | approve/revise/message work |
| P4.3 | SSE streaming | Doc 3 — SSE Event Types | E | Events stream correctly |
| P4.4 | Wire to orchestration | Doc 2 — LangGraph, Doc 3 — API Endpoints | C, E | Full flow works |

### P5: Content Generation

> **⚠️ PRECONDITION — READ BEFORE STARTING P5**
>
> Before implementing any slice in P5, you MUST read `docs/spec/1_meta-prompt-structured-reasoning.md` in full.
>
> This document defines the reasoning methodology that your prompts must embody. Do not proceed until you can explain:
> - The **V1→V2→V3 iteration pattern** and why each version exists
> - The **four methodology documents** (DataSheet, ToDoList, Guidance, DetailedProcedure) and their purposes
> - Why **Pass 2 gates are mandatory** and what the human is approving
> - How **traceability** flows from Step 1 → Step 2 → Step 3
>
> If you cannot articulate these concepts, re-read Doc 1. Prompts generated without this understanding will fail Gate A and Gate B.

| Slice | Deliverable | Doc Reference | Gate | Exit Criterion |
|-------|-------------|---------------|------|----------------|
| P5.1 | LLM adapter | Doc 3 — Observability (adapter pattern) | — | Claude, OpenAI, or Gemini calls work |
| P5.2 | Step 1-3 prompts | Doc 1 (methodology), Doc 3 — Artifact Schemas | A, B | Prompts generate valid output |
| P5.3 | Artifact storage | Doc 3 — Artifact Schemas, Core Tables | A, B | Packages validate against schema |
| P5.4 | Traceability links | Doc 3 — Core Tables (traceability_links) | B | Links populated |

### P6: Verification

| Slice | Deliverable | Doc Reference | Gate | Exit Criterion |
|-------|-------------|---------------|------|----------------|
| P6.1 | Gate A test | Doc 3 — Appendix A (Gate A) | A | 36 methodology docs exist |
| P6.2 | Gate B test | Doc 3 — Appendix A (Gate B) | B | Packages + traces valid |
| P6.3 | Gate C test | Doc 3 — Appendix A (Gate C) | C | Gating enforced |
| P6.4 | Gate D test | Doc 3 — Appendix A (Gate D) | D | Restart works |
| P6.5 | Gate E test | Doc 3 — Appendix A (Gate E) | E | Full API/SSE flow |
| P6.6 | Gate F test | Doc 3 — Appendix A (Gate F) | F | Audit complete |

---

## 7. Task Execution Protocol

For each slice:

```
1. I assign slice (e.g., "Implement slice P3.2")
2. You output plan:
   - Files to create/modify
   - Approach summary (3-5 bullets)
   - Questions if blocked (max 3)
3. I approve plan (or adjust)
4. You implement (this slice ONLY — do not proceed to next)
5. You run verification commands
6. You report using template below
7. I approve → next slice
```

**Critical:** Do not generate code for future slices. Do not skip verification.

**Halt Condition:** If you detect a contradiction between documents, STOP and invoke the deviation protocol. Do not make a best guess.

---

## 8. Slice Report Template (Required)

After completing each slice, output exactly this format:

```
═══════════════════════════════════════════════════════════
SLICE REPORT: [Slice ID, e.g., P3.2]
═══════════════════════════════════════════════════════════

FILES CHANGED:
  + [path]  (created)
  ~ [path]  (modified)
  - [path]  (deleted)

COMMANDS RUN:
  $ [command]
    → [PASS/FAIL]: [brief output or error]

GATES:
  ✓ Gate [X]: [evidence]
  ○ Gate [Y]: Not yet — [reason]

ASSUMPTIONS:
  • [assumption made, if any]

NEXT: [Ready for slice P#.# / Blocked on: ...]
═══════════════════════════════════════════════════════════
```

---

## 9. Verification Standard

**"If it can't be verified by a command, it's not done."**

You must create and use these scripts:

| Command | Purpose | Gate |
|---------|---------|------|
| `make lint` | Code quality (ruff/black) | — |
| `make test` | Unit tests (pytest) | All |
| `make db-up` | Start PostgreSQL | D |
| `make migrate` | Run migrations | D |
| `make e2e` | End-to-end API tests | E |
| `make test-gates` | Gate enforcement tests | C |
| `make test-recovery` | Restart/resume tests | D |
| `python tools/validate_schemas.py` | Validate artifact schemas | A, B |
| `python tools/verify_traces.py` | Verify traceability links | B |
| `python tools/verify_methodology.py` | Verify 36 methodology docs | A |
| `python tools/verify_audit.py` | Verify audit trail completeness | F |

---

## 10. File Boundaries

```
/docs/spec/           READ-ONLY    (authority documents)
/docs/DECISIONS.md    APPEND-ONLY  (deviation log)

/apps/api/            YOUR CODE    (FastAPI backend)
/apps/web/            FUTURE       (Next.js frontend — not MVP)
/packages/            YOUR CODE    (shared contracts, instance packs)
/infra/               YOUR CODE    (docker, migrations)
/tests/               YOUR CODE    (all test code)
/tools/               YOUR CODE    (validation scripts)
```

---

## 11. Context Loading

If you need more detail than the task provides, use this approach:

### Step 1: List Available Sections

```bash
grep "^## " docs/spec/3_solver-technical-spec.md
```

This shows you all top-level sections. Do this first to orient yourself.

### Step 2: Extract Specific Section

Use `grep -A` (lines after match) which is more robust than `sed` line ranges:

```bash
# Database section (~150 lines)
grep -A 150 "^## 7\. Database" docs/spec/3_solver-technical-spec.md

# State machine section (~100 lines)
grep -A 100 "^## 6\. State Machine" docs/spec/3_solver-technical-spec.md

# Artifact schemas (~200 lines)
grep -A 200 "^## 5\. Artifact Schemas" docs/spec/3_solver-technical-spec.md

# LangGraph implementation (~250 lines)
grep -A 250 "^## 8\. LangGraph" docs/spec/3_solver-technical-spec.md

# API endpoints (~150 lines)
grep -A 150 "^## 9\. API" docs/spec/3_solver-technical-spec.md
```

### Step 3: If Section is Large, List Subsections

```bash
# List all subsections within a section
grep "^### " docs/spec/3_solver-technical-spec.md

# Or find subsections for a specific section (e.g., section 7)
grep -A 200 "^## 7\." docs/spec/3_solver-technical-spec.md | grep "^### "
```

### Step 4: Extract Specific Subsection

```bash
# Extract a specific subsection
grep -A 50 "^### 7.3 Core Tables" docs/spec/3_solver-technical-spec.md
```

**Rule:** When in doubt, list sections first (`grep "^## "`), then extract. Do not guess line numbers or assume document structure.

---

## 12. Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│                    SOLVER QUICK REFERENCE                   │
├─────────────────────────────────────────────────────────────┤
│ DOCUMENTS                                                   │
│   Doc 1 = WHY   (process, reasoning rules, gates)           │
│   Doc 2 = WHERE (architecture, components, invariants)      │
│   Doc 3 = WHAT  (schemas, endpoints, exact specs)           │
├─────────────────────────────────────────────────────────────┤
│ AUTHORITY (by domain)                                       │
│   Process conflicts      → Doc 1 prevails                   │
│   System shape conflicts → Doc 2 prevails                   │
│   Implementation details → Doc 3 prevails                   │
├─────────────────────────────────────────────────────────────┤
│ HARD CONSTRAINTS                                            │
│   • Pass 2 gates MANDATORY                                  │
│   • message action must NOT change state                    │
│   • State must survive restart                              │
│   • Artifacts schema-validated in CI                        │
│   • No hardcoded secrets (use .env + pydantic_settings)     │
│   • No hidden chain-of-thought (reviewable rationale only)  │
├─────────────────────────────────────────────────────────────┤
│ ACCEPTANCE GATES (A-F)                                      │
│   A = Methodology exists (36 docs)                          │
│   B = Packages with traces                                  │
│   C = Gating enforced                                       │
│   D = Restart works                                         │
│   E = API + SSE flow (no UI)                                │
│   F = Audit complete                                        │
├─────────────────────────────────────────────────────────────┤
│ BUILD PHASES (P1-P6)                                        │
│   P1 = Foundation    P2 = Persistence    P3 = Orchesttic    │
│   P4 = API           P5 = Content        P6 = Verification  │
├─────────────────────────────────────────────────────────────┤
│ CRITICAL RULES                                              │
│   • P5 requires full read of Doc 1 first                    │
│   • Halt on contradiction → deviation protocol              │
│   • If not command-verifiable, it's not done                │
└─────────────────────────────────────────────────────────────┘
```

---

## 13. Starting the Build

When ready to begin, I will say:

> "Begin slice P1.1"

You will:
1. Read Doc 3 — Repository Structure
2. Output your plan
3. Wait for my approval
4. Implement
5. Report

**Do not begin until I give the first slice instruction.**

---

## 14. Appendix: Step 1-3 Artifact Contracts

The following artifacts must be produced by Pass 2. Schemas are authoritative.

| Step | Artifact | Schema Location | Key Fields |
|------|----------|-----------------|------------|
| 1 | `ProblemDefinitionPackage` | `/packages/contracts/problem_definition.schema.json` | canonical_problem_definition, stakeholders, constraints, scope, success_criteria |
| 2 | `RequirementsPackage` | `/packages/contracts/requirements.schema.json` | requirements (FR/NFR/CR/IR), coverage_map, trace links |
| 3 | `ObjectivesPackage` | `/packages/contracts/objectives.schema.json` | objectives (CAP/QUAL/COMP/INTF), success_framework, trace_map |

**Schema Source of Truth:** Doc 3 — Artifact Schemas (§5)

**Validation:** All packages must pass `python tools/validate_schemas.py` before Gate B can be satisfied.

**Traceability Requirements:**
- Step 2 requirements must trace back to Step 1 elements (stakeholders, constraints, scope, success_criteria)
- Step 3 objectives must trace back to Step 2 requirements
- Verified by `python tools/verify_traces.py`

---

*This directive is authoritative for the SOLVER build. All work must comply with this document and the three specification documents it references.*

*Version 1.2 Changes:*
- *Renamed Phases A-F → P1-P6 to avoid collision with Gates A-F*
- *Replaced linear authority hierarchy with dimensional model*
- *Changed slice table references from section numbers to header names*
- *Clarified schema validation as "in CI" not write-time rejection*
- *Added artifact contracts appendix (§14)*
- *Made all gates command-verifiable with specific tools*
- *Clarified Gate E: no UI required for MVP*
- *Added chain-of-thought prohibition to "Do NOT" section*
- *Added halt-on-contradiction rule to execution protocol*
