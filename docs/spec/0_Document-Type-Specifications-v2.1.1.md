# Project Documentation System Specification

**Purpose:** Abstract specification for a documentation taxonomy suitable for complex systems with non-obvious design decisions, multi-phase implementation, and governance requirements.

**Usage:** Instantiate each document type for a specific project by following the structure and including the required sections.

**Version:** 2.1.1

---

## 0. Goals of This Documentation System

- Create a shared, durable understanding of *why* we're building something, *what* must be true, *how* it works, and *how* we ship it safely
- Provide clear "sources of truth" and an explicit conflict-resolution mechanism
- Enable controlled evolution via Change Management and Document Freeze
- Scale appropriately (not every project needs all documents)

---

## 1. Document Set

A complete documentation system includes these document types:

| # | Document Type | Question Answered | Normative Status |
|---|---------------|-------------------|------------------|
| 1 | **Design Intent** | Why must it be this way? | Non-normative (directional) |
| 2 | **Architectural Contract** | What must be true? | **Normative** |
| 3 | **Technical Specification** | What are we building? | **Normative** |
| 4 | **Development Directive** | How do we build it? | **Normative** (gates) |
| 5 | **Project Orientation (README)** | Where do I start? | Non-normative (index) |
| 6 | **Change Management** | How does truth evolve? | **Normative** |

**Normative** = contains binding requirements (MUST/SHALL language)
**Non-normative** = provides guidance, rationale, or navigation but cannot override normative documents

---

## 2. Authority Model

### 2.1 Purpose Priority (North Star)

Use this order when interpreting *what we are trying to accomplish* and evaluating options:

```
1. Design Intent      — why, goals, non-goals, principles, value thesis
2. Architectural Contract — invariants that protect correctness/safety
3. Technical Specification — mechanisms that satisfy contract
4. Development Directive  — sequencing to deliver the system
5. README               — orientation and navigation
```

Design Intent is the north star. When choosing between Contract-compliant solutions, Intent guides the choice.

### 2.2 Binding Precedence (Conflict Resolution)

Use this order when documents *disagree about what must be true*:

```
1. Architectural Contract — wins conflicts; non-negotiable invariants
2. Technical Specification — must satisfy contract
3. Development Directive   — must satisfy contract and spec
4. Design Intent          — tie-breaker among compliant solutions only
5. README                 — never normative; cannot win conflicts
```

Contract wins because it contains the invariants that protect correctness. You cannot bypass a Contract requirement by appealing to Intent.

### 2.3 Override Rule

**If Design Intent and Contract/Spec are misaligned:**

1. Do NOT override Contract/Spec by appeal to Intent
2. Treat as a governance mismatch
3. Open a Change Request to bring Contract/Spec into alignment with Intent
4. If frozen, use the freeze change path (see §8)

This preserves Intent as the north star while preventing it from becoming a backdoor around binding requirements.

### 2.4 Visual Summary

```
                    PURPOSE PRIORITY              BINDING PRECEDENCE
                    (what we want)                (what must be true)
                    
                         Intent ←─────────────────────┐
                           ↓                          │
                       Contract ──────────────────→ Contract
                           ↓                          ↓
                         Spec ────────────────────→ Spec
                           ↓                          ↓
                      Directive ──────────────────→ Directive
                           ↓                          ↓
                        README                     Intent (tie-break only)
                                                      ↓
                                                   README (never)
```

### 2.5 Meta-Governance (Change Management Authority)

Change Management is not part of the content precedence hierarchy. It governs *how changes occur*, not *what is true*.

| Authority Type | What It Governs | Documents |
|----------------|-----------------|-----------|
| **Content Authority** | What the system must do | Intent, Contract, Spec, Directive, README |
| **Process Authority** | How documents change | Change Management (including Freeze) |

**Implication:** Change Management cannot override a Contract requirement, but it can block a proposed change to Contract until proper review occurs. It is orthogonal to content precedence—it controls the process of change, not the substance.

---

## 3. Normative Language Standard

All normative documents must use consistent vocabulary:

| Term | Meaning | Example |
|------|---------|---------|
| **MUST** | Absolute requirement | "Events MUST be gap-free" |
| **MUST NOT** | Absolute prohibition | "Server MUST NOT broadcast inside transaction" |
| **SHALL** | Equivalent to MUST | "Client SHALL include state_version" |
| **SHOULD** | Strong default, exceptions must be documented | "Errors SHOULD include trace ID" |
| **SHOULD NOT** | Strong discouragement | "Clients SHOULD NOT cache beyond TTL" |
| **MAY** | Optional | "Server MAY include retry hint" |
| **NOTE** | Non-normative commentary | "NOTE: This simplifies debugging" |

**Rule:** Each document must state its normative status in its header.

---

## 4. Cross-Reference Rules

These rules ensure the document set remains internally consistent:

| Rule | Verification |
|------|--------------|
| Every MUST in Contract → satisfiable by Spec | Contract checklist maps to Spec sections |
| Every gate in Directive → maps to Contract/Spec clause | Directive gates cite verification source |
| README → links to current versions of all docs | Version table in README matches actual files |
| Terminology → defined once, used consistently | Single glossary, no conflicting definitions |
| Version references → match actual versions | No doc references a version that doesn't exist |

**Maintenance rule:** Any change that affects cross-references must update all affected documents atomically.

**Cross-Reference Format:** Cross-references MUST include document name, version, and section anchor:

```
Format: {Document Name} V{X.Y} §{Section}
Examples:
  - Architectural Contract V3.4 §9.2
  - Technical Specification V2.8.0 §7.3
  - Design Intent V1.1 §4.1 (Key Decisions)
```

When a referenced document is updated, all cross-references to changed sections must be verified or updated. Version pinning prevents silent drift.

---

## 5. Document Type Specifications

### 5.1 Design Intent (Why²)

#### Purpose

Explains the reasoning behind architectural decisions: why the system exists, what goals it serves, what alternatives were rejected, and what assumptions would trigger reconsideration.

#### Normative Status

**Non-normative (directional).** Design Intent explains *why* but does not contain MUST-level requirements. All binding constraints live in Contract.

**Must-Consult Rule:** Non-normative does not mean optional or ignorable. Design Intent is mandatory to consult whenever multiple Contract-compliant options exist. It is the tie-breaker among compliant solutions and the guide for interpreting ambiguous requirements.

#### Scope Boundaries

| Belongs in Design Intent | Does NOT Belong (goes in Contract/Spec) |
|--------------------------|----------------------------------------|
| "We value reliability over speed" | "Timeout MUST be < 100ms" |
| "We chose X because Y" | "System MUST use X" |
| "Failure mode Z concerns us" | "System MUST handle failure mode Z by..." |
| "We assume single-region deployment" | "System MUST operate in single region" |

#### Required Sections

| Section | Purpose |
|---------|---------|
| **Core Problem** | What failure/risk/need drives the design |
| **Design Inputs** | Trust model, failure modes, constraints (reasoning, not requirements) |
| **Key Decisions** | Major choices with alternatives and rationale |
| **Assumptions** | Conditions that would trigger rethinking |
| **Trade-offs** | Explicit compromises and their justifications |
| **Terminology** | Canonical terms to prevent drift |

#### Structure Template

```markdown
# {Project} Design Intent

**Purpose:** Design rationale and first principles.

**Normative Status:** Non-normative (directional). This document explains 
*why* but does not contain binding requirements. See Architectural Contract 
for MUST-level constraints.

---

## 1. The Core Problem

### 1.1 What We're Protecting Against

{The central failure mode or risk. Frame as a design input, not a requirement.}

> **{Problem statement}**

### 1.2 The Cost Asymmetry

| Outcome | Cost | Implication |
|---------|------|-------------|
| {Bad outcome} | {Severity} | {How this shapes our choices} |

---

## 2. Design Inputs

### 2.1 Trust Model

{What we assume we can and cannot trust. These are design inputs that 
lead to Contract requirements, not requirements themselves.}

| We assume we can trust | Because |
|------------------------|---------|

| We assume we cannot trust | Because |
|---------------------------|---------|

### 2.2 Failure Modes Under Consideration

{Failures we're designing against. The Contract will specify how we 
handle them; here we explain why they matter.}

#### {Failure Name}

**Scenario:** {How it happens}
**Why it matters:** {Consequence}
**Design direction:** {How we'll address it — Contract specifies the MUST}

---

## 3. Key Decisions

### 3.1 {Decision Name}

**Problem:** {What needed to be solved}

**Alternatives considered:**

| Approach | Pros | Cons |
|----------|------|------|

**Decision:** {What was chosen}

**Rationale:** {Why — this guides interpretation of Contract}

---

## 4. Assumptions

If any of these become false, revisit the design:

| Assumption | If Violated |
|------------|-------------|

---

## 5. Trade-offs

### 5.1 {Trade-off Name}

**Trade-off:** {X vs Y}
**We chose:** {X}
**Consequence:** {What we gave up}
**Justification:** {Why acceptable}

---

## 6. Terminology

| Canonical Term | Aliases (avoid) | Definition |
|----------------|-----------------|------------|
```

#### Quality Criteria

- [ ] Core problem stated in one clear sentence
- [ ] Design inputs framed as reasoning, not requirements
- [ ] Every major decision has documented alternatives
- [ ] Assumptions are falsifiable
- [ ] No MUST/SHALL language (those belong in Contract)
- [ ] Cross-references to Contract where decisions lead to requirements

---

### 5.2 Architectural Contract (Why — Invariants)

#### Purpose

Defines what must be true for the system to be correct. Uses normative language (MUST, SHALL). Provides the invariants that implementation must satisfy and that tests must verify.

#### Normative Status

**Normative.** This document contains binding requirements. It wins conflicts with all other documents.

#### Scope Boundaries

| Belongs in Contract | Does NOT Belong (goes elsewhere) |
|---------------------|----------------------------------|
| "Events MUST be gap-free" | "Use PostgreSQL sequences" (Spec) |
| "Client MUST NOT act on stale state" | "Why staleness matters" (Intent) |
| Invariants, guarantees, prohibitions | Implementation mechanisms |

#### Required Sections

| Section | Purpose |
|---------|---------|
| **System Context** | What the system is and why contracts exist |
| **Contracts by Domain** | Grouped MUST statements (persistence, API, safety, etc.) |
| **Verification Checklists** | How to confirm compliance |
| **Glossary** | Precise definitions of contract terms |

#### Structure Template

```markdown
# {Project} Architectural Contract

**Purpose:** What must be true for correctness.

**Normative Status:** Normative. This document contains binding requirements.
Per the Authority Model (§2), Contract wins conflicts with Spec, Directive, 
and Intent.

**Document Structure:**
- Part I: Architecture (descriptive context)
- Part II: Contracts (normative MUST/SHALL)
- Part III: Verification (checklists)
- Part IV: Reference (glossary)

---

# Part I: Architecture

## 1. System Context

### 1.1 What {Project} Is
{Clear description — frames the contracts}

### 1.2 Why Contracts Exist
{Reference to Design Intent failure modes these contracts address}

---

# Part II: Contracts

## {N}. {Domain} Contracts

### {N}.1 {Contract Name}

| Property | Requirement |
|----------|-------------|
| {Property} | MUST {requirement} |
| {Property} | MUST NOT {prohibition} |

**Invariant:** {Statement that must always be true}

**Rationale:** See Design Intent §{X} — {brief reference to why}

**Verified by:** {Gate ID or test name}

---

# Part III: Verification

## {M}. Conformance Checklists

### {M}.1 {Domain} Checklist

- [ ] {Checkable item derived from contract}

---

# Part IV: Reference

## Glossary

| Term | Definition |
|------|------------|
```

#### Quality Criteria

- [ ] Every MUST has a corresponding verification check
- [ ] Every MUST is testable (could write a failing test)
- [ ] No ambiguous requirements
- [ ] Cross-references to Intent rationale
- [ ] Cross-references to Spec implementation
- [ ] Glossary defines every term used in contracts

---

### 5.3 Technical Specification (What)

#### Purpose

Implementation-ready details: schemas, APIs, code patterns, configurations. Everything an implementer needs to build the system without inventing approaches.

#### Normative Status

**Normative.** This document contains binding implementation requirements. Must satisfy Contract; wins conflicts with Directive.

#### Scope Boundaries

| Belongs in Spec | Does NOT Belong (goes elsewhere) |
|-----------------|----------------------------------|
| Schema definitions | Why this schema (Intent) |
| API endpoints and formats | What invariants API must satisfy (Contract) |
| Code patterns | Build sequence (Directive) |
| Error response shapes | When to build error handling (Directive) |

#### Required Sections

| Section | Purpose |
|---------|---------|
| **Data Model** | Schemas, constraints, migrations |
| **API Specification** | Endpoints, request/response, errors |
| **State Machines** | Status transitions, valid sequences |
| **Code Patterns** | Reference implementations |
| **Configuration** | Environment variables, settings |

#### Structure Template

```markdown
# {Project} Technical Specification V{X.Y.Z}

**Purpose:** Implementation-ready specification.

**Normative Status:** Normative. Must satisfy Architectural Contract.

**Satisfies Contracts:** {List of Contract sections this Spec implements}

---

## 0. Version Changes

### V{X.Y.Z} Changes
{What changed, with Contract/Spec section references}

---

## 1. Data Model

### 1.1 {Table/Entity Name}

```sql
CREATE TABLE {name} ( ... );
```

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|

**Satisfies:** Contract §{X} ({invariant name})

---

## 2. API Specification

### 2.1 {Endpoint Group}

#### {METHOD} {path}

**Request:**
```json
{schema}
```

**Response:**
```json
{schema}
```

**Errors:**

| Code | Condition | Response Shape |
|------|-----------|----------------|

**Satisfies:** Contract §{X}

---

## 3. State Machines

### 3.1 {Entity} States

| From | To | Trigger | Side Effects |
|------|----|---------|--------------|

**Satisfies:** Contract §{X}

---

## 4. Code Patterns

### 4.1 {Pattern Name}

**Implements:** Contract §{X} requirement for {invariant}

```python
{reference implementation}
```

---

## 5. Configuration

| Variable | Type | Default | Purpose |
|----------|------|---------|---------|
```

#### Quality Criteria

- [ ] Every Contract MUST has implementing section
- [ ] Schemas include all constraints
- [ ] Every API has request/response schemas
- [ ] Code patterns are copy-pasteable and correct
- [ ] Cross-references to Contract requirements (Satisfies: §X)

---

### 5.4 Development Directive (How)

#### Purpose

Execution plan: phases, packages, gates, dependencies. Tells implementers what to build in what order and how to verify each step.

#### Normative Status

**Normative (gates only).** Gate definitions are binding. Package structure and sequencing are strong guidance but may be adjusted without CR if gates still pass.

#### Scope Boundaries

| Belongs in Directive | Does NOT Belong (goes elsewhere) |
|----------------------|----------------------------------|
| Phase sequence | Why this sequence (Intent) |
| Package deliverables | How to implement deliverables (Spec) |
| Gate criteria | What invariants gates verify (Contract) |
| Dependencies | Schema details (Spec) |

#### Required Sections

| Section | Purpose |
|---------|---------|
| **Gate Definitions** | All verification gates with criteria |
| **Phase Overview** | Major milestones and objectives |
| **Packages** | Units of work with deliverables |
| **Dependency Graph** | What blocks what |

#### Structure Template

```markdown
# {Project} Development Directive V{X.Y}

**Purpose:** Phased implementation plan with gates.

**Normative Status:** Normative for gate definitions. Package sequencing 
is guidance.

---

## Gate Definitions

### {Series} Gates

| Gate | Name | Criterion | Verifies Contract §{X} |
|------|------|-----------|------------------------|

---

## Phase {N}: {Name}

**Objective:** {What this phase accomplishes}

**Exit Gates:** {Gate IDs}

### Package {N.M}: {Name}

**Deliverables:**

| # | Deliverable | Acceptance | Spec Reference |
|---|-------------|------------|----------------|

**Dependencies:** {What must be complete first}

**Verification:**
```bash
{test command}
```

---

## Dependency Graph

```
{diagram}
```
```

#### Quality Criteria

- [ ] Every gate has binary pass/fail criterion
- [ ] Every gate maps to Contract clause it verifies
- [ ] Every package has concrete deliverables
- [ ] Dependencies are explicit
- [ ] Spec references point to exact sections

---

### 5.5 Project Orientation (SOLVER-README)

#### Purpose

Entry point for all audiences. Navigation to other documents, quick-start paths, just enough context to understand what the project is.

#### Normative Status

**Non-normative (index).** Cannot contain requirements; cannot win conflicts.

#### Required Sections

| Section | Purpose |
|---------|---------|
| **What This Is** | One paragraph on purpose |
| **Document Index** | Table mapping docs to questions |
| **Audience Paths** | Reading orders by role |
| **Quick Reference** | Key concepts, versions |
| **Getting Started** | First steps |

#### Structure Template

```markdown
# {Project}

**One-sentence description**

**Document Status:** {Governed | Draft}. See Change Management for rules.

**Normative Status:** Non-normative (index). This document provides 
navigation only.

---

## What is {Project}?

{2-3 paragraphs}

---

## Document Index

| Document | Question | File | Normative? |
|----------|----------|------|------------|
| Design Intent | Why? | `{file}` | No (directional) |
| Contract | What must be true? | `{file}` | **Yes** |
| Spec | What are we building? | `{file}` | **Yes** |
| Directive | How do we build? | `{file}` | **Yes** (gates) |
| Change Management | How does it evolve? | `{file}` | **Yes** |

---

## For Different Audiences

### For New Team Members
{Reading list}

### For Implementers
{Daily workflow}

---

## Quick Reference

### Current Versions
| Document | Version |
|----------|---------|

### Key Concepts
| Concept | Definition | Defined In |
|---------|------------|------------|
```

#### Quality Criteria

- [ ] Every doc referenced with correct filename and version
- [ ] No requirements (no MUST/SHALL language)
- [ ] Audience paths actually help those audiences
- [ ] Version table matches actual files

---

### 5.6 Change Management

#### Purpose

Governance policy for how specification documents evolve. Defines change categories, approval requirements, freeze procedures, and commitments.

#### Normative Status

**Normative.** This document governs changes to all other documents.

**Meta-Governance Role:** Change Management exercises *process authority*, not *content authority*. It governs how documents change, not what is true. It cannot override a Contract requirement, but it can require review before a Contract change is accepted. See §2.5 for the distinction.

#### Required Sections

| Section | Purpose |
|---------|---------|
| **Authority Model** | Document hierarchy, conflict resolution |
| **Governed Documents** | What's controlled (policy, not snapshot) |
| **Freeze Procedure** | How to lock specifications |
| **Change Control** | Categories, approvals, process |
| **Self-Governance** | How to change this document |

#### Structure Template

```markdown
# {Project} Change Management V{X.Y}

**Purpose:** Governance of specification documents.

**Normative Status:** Normative. This document governs all changes.

---

## 1. Authority Model

### 1.1 Purpose Priority
{Intent > Contract > Spec > Directive > README}

### 1.2 Binding Precedence  
{Contract > Spec > Directive > Intent > README}

### 1.3 Override Rule
{Intent-Contract conflicts require CR, not override}

---

## 2. Governed Documents

### 2.1 Document Types (Policy)

| Type | Role | Normative? |
|------|------|------------|

### 2.2 Baseline Requirements

{What a freeze baseline must contain — not the baseline itself}

### 2.3 Self-Governance

{Special rules for changing this document}

---

## 3. Freeze Procedure

### 3.1 What Freeze Means

{Allowed vs prohibited changes during freeze}

### 3.2 Freeze Gates

| Gate | Criterion | Evidence Required |
|------|-----------|-------------------|

### 3.3 Entering/Exiting Freeze

{Procedures}

### 3.4 Current State

| Property | Value |
|----------|-------|
| State | {FROZEN/UNFROZEN/PENDING} |
| Baseline ID | {tag/SHA or "none"} |

---

## 4. Change Control

### 4.1 Categories

| Category | Version Impact | Approval |
|----------|----------------|----------|

### 4.2 CR Requirements

{What a change request must contain}

### 4.3 Breaking Changes

{What counts, what's required}
```

#### Quality Criteria

- [ ] Authority model explicitly defines both hierarchies
- [ ] Override rule prevents Intent from bypassing Contract
- [ ] Freeze gates have objective evidence requirements
- [ ] Self-governance is addressed
- [ ] Baseline is an output artifact, not embedded in policy

---

## 6. Instantiation Guide

When applying this system to a new project:

1. **Start with README** — Forces you to name and locate documents
2. **Write Design Intent** — Forces you to articulate the core problem
3. **Define Contract** — Forces you to state invariants
4. **Write Spec** — Forces you to get concrete about implementation
5. **Create Directive** — Forces you to sequence the work
6. **Establish Change Management** — Forces you to define stability

---

## 7. Anti-Patterns

| Anti-Pattern | Problem | Fix |
|--------------|---------|-----|
| Everything in one doc | Can't find anything | Split by question answered |
| Rationale in Spec | Spec becomes unmaintainable | Move rationale to Intent |
| Requirements in Intent | Intent becomes binding (wrong) | Move MUST to Contract |
| Implicit contracts | "Everyone knows" → drift | Make contracts explicit |
| Single authority model | Intent can override Contract | Use two-hierarchy model |
| No normative labeling | Arguments about what's binding | Label each document |
| Baseline in policy | Policy changes every freeze | Baseline is output artifact |
| No cross-references | Docs drift apart | Explicit cross-ref rules |
| No versioning | Can't tell what's current | Version everything |
| No gates | Can't verify progress | Define gates with criteria |

---

## 8. Governance Placard

Paste this at the top of every canonical document:

```markdown
---
**Document Governance**

This document is part of the {Project} specification set governed by 
Change Management V{X}.

| Authority | |
|-----------|-|
| Purpose Priority | Intent > Contract > Spec > Directive > README |
| Binding Precedence | Contract > Spec > Directive > Intent > README |
| Override Rule | Intent-Contract conflicts require CR, not override |

**Normative Status:** {Normative | Non-normative (directional) | Non-normative (index)}

**Current Version:** V{X.Y.Z}

**Freeze State:** {FROZEN baseline-id | UNFROZEN | PENDING}

---
```

---

## 9. Version History

| Version | Changes |
|---------|---------|
| 1.0 | Initial document type specifications |
| 2.0 | Added two-hierarchy authority model (Purpose Priority + Binding Precedence); Added normative status classification; Tightened Design Intent scope (no MUST language); Elevated cross-reference rules to standalone section; Added governance placard; Restructured templates to include normative status and cross-references |
| 2.1 | Added Must-Consult Rule to Design Intent (non-normative ≠ ignorable); Added §2.5 Meta-Governance distinguishing process authority from content authority; Added versioned cross-reference format convention |
| 2.1.1 | Removed section about scaling down the documents to a smaller set, because this is about working with agentic systems all the documents are always all required |
---

*Project Documentation System Specification v2.1.1*
*A taxonomy for complex system documentation with explicit authority model*
