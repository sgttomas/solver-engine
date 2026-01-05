# SOLVER Change Management

**Purpose:** Governance of specification documents — what stability means, how changes are controlled, and what commitments are made to implementers.

**Scope:** SOLVER MVP (Steps 1-3) specification documents

---

## 0. Authority & Procedures

### 0.1 Authority Model

When documents appear to conflict, use the two-hierarchy model from
`0_Document-Type-Specifications-v2.1.1.md`:

**Purpose Priority (what we are trying to accomplish):**
1. Design Intent (Why²)
2. Architectural Contract (Why)
3. Technical Specification (What)
4. Development Directive (How)
5. README (Orientation)

**Binding Precedence (what must be true):**
1. Architectural Contract (Why)
2. Technical Specification (What)
3. Development Directive (How)
4. Design Intent (Why²) — tie-breaker among compliant solutions only
5. README (Orientation) — never normative

**Override rule:** If Design Intent conflicts with Contract/Spec, do NOT override
Contract/Spec. Treat as a governance mismatch and open a Change Request; if frozen,
use the freeze change path.

### 0.2 Policy and Procedures

This document (**Change Management**) defines the change-control **policy** for SOLVER specifications. Specific operational activities are defined as **procedures** under this policy:

| Procedure | Purpose | Defined In |
|-----------|---------|------------|
| **Document Freeze** | Lock specifications at a verified baseline | §3 of this document |
| **Change Request** | Propose and approve specification changes | §5 of this document |
| **Emergency Change** | Expedited fixes for blocking errors | §5.4 of this document |

**Hierarchy:** Change Management (policy) governs all procedures. If any procedure conflicts with this policy, the policy controls.

---

## 1. Governed Documents

### 1.1 Canonical Document Set (Policy Definition)

The governed document set consists of these document types:

| Document Type | Role | Filename Pattern |
|---------------|------|------------------|
| Project Orientation | Entry point, navigation | `README.md` |
| Project Documentation System Specification | Governance framework | `0_Document-Type-Specifications-v*.md` |
| Project Governance Model Orientation | conceptual navigation | `SOLVER-README-v*.md` |
| Design Intent | Why² — first principles, rationale | `SOLVER-Design-Intent-v*.md` |
| Architectural Contract | Why — invariants, contracts | `SOLVER-Architectural-Contract-v*.md` |
| Technical Specification | What — schemas, endpoints, code | `4_SOLVER-Technical-Spec-V*.md` |
| Development Directive | How — phases, packages, gates | `SOLVER-Development-Directive-v*.md` |
| Change Management | Governance — this document | `SOLVER-Change-Management-v*.md` |

**Policy rule:** These eight document types constitute the canonical set. Adding or removing document types from this set is a Major change requiring architecture review.

### 1.2 Baseline Artifact (Snapshot Definition)

A **baseline** is a reproducible snapshot of the governed document set at a specific point in time. Baselines are **output artifacts** of the Freeze procedure (§3), not part of this policy document.

**Baseline requirements:**

| Component | Required? | Purpose |
|-----------|-----------|---------|
| Baseline identifier | **MUST** | Git tag or commit SHA — immutable anchor |
| Document manifest | **MUST** | Exact filename + version for each document |
| SHA-256 hashes | **MUST** | Integrity verification for each file |
| Timestamp | **MUST** | When baseline was created |
| Freeze gate evidence | **MUST** | Proof that F0-F4 passed |

**Baseline storage:** Baselines are stored in a `FREEZE-RECORD.md` file (or equivalent artifact) created by the Freeze procedure. This policy document does NOT contain baseline snapshots — it defines what baselines must contain.

**Current baseline status:** See §3.6 for freeze state and baseline identifier.

### 1.3 Governance of This Document

Changes to Change Management itself require **additional scrutiny** because this document governs all other changes:

| Change Type | Additional Requirement |
|-------------|----------------------|
| Typo/grammar | None (same as other docs) |
| Clarification | Peer review + explicit note that governance doc was changed |
| Gate definition change | Architecture review + migration note |
| Authority order change | Architecture review + migration note + notify all implementers |
| Add/remove governed doc type | Architecture review + migration note |

**Rule:** Any change to §0 (Authority), §3 (Freeze Procedure), or §5 (Change Control) requires architecture review regardless of whether it appears "minor."

---

## 2. Stability Principles

### 2.1 Why Change Management Matters

Specification stability enables:
- **Parallel work** — Implementers build against stable contracts
- **Verifiable compliance** — Reviewers assess against known criteria
- **Agent execution** — AI agents operate without re-reading evolving specs
- **Reduced coordination** — Teams don't chase moving targets

Change management doesn't mean "no changes." It means changes are deliberate, versioned, and communicated.

### 2.2 The Seven Governance Principles

**Principle 1: Stabilize what must not change without breaking the system**

These are correctness invariants. If they drift, you get subtle, compounding failures.

| Stabilized Invariant | Why It's Stabilized |
|----------------------|---------------------|
| Event ordering & replay | Clients rely on monotonic, gap-free sequences for correctness |
| Optimistic concurrency | `expected_state_version` semantics define action safety |
| Artifact revision model | Insert-per-revision with deterministic supersession enables audit |
| Staleness propagation | Blocking completion on stale artifacts prevents corrupt approvals |
| Actor attribution | Audit trail reconstruction depends on consistent identity injection |

**Principle 2: Stabilize contracts at boundaries, not implementation details**

What matters is observable behavior, not internal mechanics.

| Stabilized (Boundary) | Flexible (Implementation) |
|-----------------------|---------------------------|
| Endpoint shapes, required params, error codes | Internal module structure |
| Event payload schemas | How events are routed internally |
| Database constraints and triggers | Query optimization strategies |
| Frontend reliability rules | Component hierarchy and styling |
| Sequence guard semantics | State management library choice |

**Principle 3: Stabilize when ambiguity has been eliminated**

A document set is stable when a reader cannot reasonably interpret a core rule two different ways.

Signals of stability:
- Single canonical statement for each invariant
- MUST/MUST NOT/SHOULD language for correctness-critical items
- Terms defined once (glossary) and reused consistently
- No contradictions between documents

**Principle 4: Stabilize only what you can verify**

If you can't test it, you can't meaningfully stabilize it — because you can't detect drift.

The governed set includes:
- Gate definitions with runnable verification tests
- Precise specs that are immediately testable once code exists
- Checklists that map to concrete queries or assertions

**Principle 5: Stabilize the user-facing interaction grammar**

SOLVER is a human-in-the-loop protocol. The protocol is stabilized; the presentation is not.

| Stabilized (Protocol) | Flexible (Presentation) |
|-----------------------|-------------------------|
| States user can be in (`awaiting_review`, `stale`, etc.) | UI layout and styling |
| Actions and when they're allowed | Button labels and copy |
| Meaning of actions (approve advances, message doesn't) | Animation and transitions |
| Action gating reasons must be visible | How reasons are displayed |

**Principle 6: Semantic stability, not editorial rigidity**

| Level | Scope | Change Control |
|-------|-------|----------------|
| **Semantic** | Meanings, invariants, schemas, gates | Requires version bump |
| **Editorial** | Phrasing, examples, formatting | Allowed under review |

Editorial improvements may continue without version bumps — as long as semantics don't change.

**Principle 7: Stability is about reducing coordination cost**

The primary benefit is enabling work to proceed:
- Changes require explicit version bumps, patch notes, and re-verification
- Implementers are protected from churn
- Semantic drift is prevented through explicit review

---

## 3. Document Freeze Procedure

### 3.1 What "Freeze" Means

**Document Freeze** is a controlled procedure that locks the specification set at a verified baseline. During freeze:

- **Allowed:** Typos, grammar, clarifying examples (no semantic change)
- **Allowed with patch bump:** Non-breaking clarifications that don't alter invariants
- **Requires unfreeze:** Any semantic change to contracts, invariants, gates, or state machines

Freeze is a *state*, not an event. The specification enters freeze when all gates pass, and exits freeze when a semantic change is approved.

**Critical requirement:** A freeze is invalid without a baseline identifier (git tag or commit SHA). Freeze MUST anchor to an immutable repository state.

### 3.2 Freeze Gates

| Gate | Name | Criterion | Pass Evidence |
|------|------|-----------|---------------|
| **F0** | Canonical Set Locked | All six document types have exact filename + version | Manifest file listing all docs with versions |
| **F1** | Internal Consistency | Cross-references resolve; no version mismatches | Script output OR signed checklist (see §3.2.1) |
| **F2** | Terminology Stable | All canonical terms defined once; no contradictions | Terminology audit checklist signed by reviewer |
| **F3** | Contract Alignment | No contradictory MUSTs between Contract/Spec/Directive | Contract alignment checklist signed by reviewer |
| **F4** | Baseline Recorded | Git tag/SHA + hashes + manifest recorded | `FREEZE-RECORD.md` artifact exists and is valid |

**Gate execution order:** F0 → F1 → F2 → F3 → F4 (each depends on prior)

### 3.2.1 Gate Evidence Requirements

Each gate MUST produce one of:
- **Script output:** Automated check with pass/fail result and timestamp
- **Signed checklist:** Reviewer name + date + explicit "PASS" or "FAIL" + any notes

**F0 evidence (Canonical Set Locked):**
```
□ README.md exists at stated path
□ 0_Document-Type-Specifications-v{X}.md exists, version X matches manifest
□ SOLVER-README-v{X}.md exists at stated path
□ SOLVER-Design-Intent-v{X}.md exists, version X matches manifest
□ SOLVER-Architectural-Contract-v{X}.md exists, version X matches manifest
□ 4_SOLVER-Technical-Spec-V{X}.md exists, version X matches manifest
□ SOLVER-Development-Directive-v{X}.md exists, version X matches manifest
□ SOLVER-Change-Management-v{X}.md exists, version X matches manifest
Reviewer: _____________ Date: _____________ Result: PASS / FAIL
```

**F1 evidence (Internal Consistency):**
```
□ All "see §X" references resolve to existing sections
□ All document version references match actual versions
□ All filename references match actual filenames
□ No document references a version newer than itself
Reviewer: _____________ Date: _____________ Result: PASS / FAIL
```

**F2 evidence (Terminology Stable):**
```
□ Design Intent §10 (Terminology Mapping) reviewed
□ Contract §17 (Glossary) reviewed
□ No term defined differently in two places
□ All canonical terms used consistently in Spec and Directive
Reviewer: _____________ Date: _____________ Result: PASS / FAIL
```

**F3 evidence (Contract Alignment):**
```
□ Every MUST in Contract has corresponding implementation in Spec
□ Every gate in Directive maps to invariant in Contract
□ No Spec implementation contradicts Contract requirement
□ No Directive sequence violates Contract dependency
Reviewer: _____________ Date: _____________ Result: PASS / FAIL
```

**F4 evidence (Baseline Recorded):**
```
□ Git tag or commit SHA recorded: _______________________
□ FREEZE-RECORD.md created with all required fields
□ SHA-256 hash computed for each governed document in the canonical set (FREEZE-RECORD.md excluded)
□ Timestamp recorded
□ All F0-F3 evidence attached or referenced
Reviewer: _____________ Date: _____________ Result: PASS / FAIL
```

### 3.3 Entering Freeze

To enter freeze state:

1. Complete freeze gates F0-F3 with signed evidence
2. Update §3.6 to reflect `FROZEN` state with the intended baseline identifier
3. Commit governed document changes (baseline commit)
4. Create git tag for baseline commit (baseline identifier)
5. Create `FREEZE-RECORD.md` artifact containing:
   - Baseline identifier (git tag or commit SHA) — **REQUIRED**
   - Document manifest (filename + version + SHA-256 for each governed document in the canonical set; FREEZE-RECORD.md excluded)
   - Timestamp
   - References to gate evidence
6. Commit `FREEZE-RECORD.md` in a follow-up commit (not part of baseline)
7. Announce freeze to all implementers

F4 is satisfied when the `FREEZE-RECORD.md` artifact is committed with the baseline tag/SHA and manifest.

### 3.4 Behavior During Freeze

| Change Type | Allowed During Freeze? | Process |
|-------------|------------------------|---------|
| Typo/grammar fix | ✅ Yes | Direct commit, note "Editorial" |
| Clarifying example | ✅ Yes | Peer review, no version bump |
| Patch clarification | ✅ Yes | Tech lead approval, patch version bump |
| New optional field | ❌ No | Requires unfreeze |
| Contract change | ❌ No | Requires unfreeze |
| Gate definition change | ❌ No | Requires unfreeze |
| Invariant modification | ❌ No | Requires unfreeze |

**Rule:** If unsure whether a change is semantic, it requires unfreeze.

### 3.5 Exiting Freeze (Unfreeze)

To exit freeze state and allow semantic changes:

1. Document the required change and rationale
2. Get architecture review approval
3. Update §3.6 to reflect `UNFROZEN` state
4. Make the approved changes following §5 (Change Control)
5. Re-execute freeze gates F0-F4
6. Re-enter freeze with new baseline and new `FREEZE-RECORD.md`

### 3.6 Current Freeze State

| Property | Value |
|----------|-------|
| **State** | `FROZEN` |
| **Baseline ID** | `spec-freeze-v2.0.1` |
| **Git Commit** | Recorded in `docs/spec/FREEZE-RECORD.md` |
| **Last Verified** | 2026-01-05 |
| **Gates Passed** | F0 ✓, F1 ✓, F2 ✓, F3 ✓, F4 ✓ |
| **Freeze Record** | `docs/spec/FREEZE-RECORD.md` |

---

## 4. What Is Governed vs. Flexible

### 4.1 Governed (Semantic Stability Required)

| Category | Specific Items |
|----------|----------------|
| **Correctness Invariants** | Event sequence gap-free, state_version monotonicity, broadcast-after-commit, atomic transitions, exclusive execution, latest artifact uniqueness |
| **API Contracts** | Endpoint paths, required parameters, response schemas, error codes (409 shape), SSE event structure |
| **Database Contracts** | Table schemas, constraints, required triggers, required functions, enum values |
| **Frontend Contracts** | R1-R19 reliability rules, connection status semantics, canAct/canMessage rules, sequence guard behavior |
| **Gate Definitions** | α1-α3, β1-β6a, γ1-γ4, A-F criteria and verification approaches |
| **State Machines** | Workflow status transitions, step status transitions, step phase transitions |
| **Terminology** | Canonical terms in glossary and terminology mapping |

### 4.2 Flexible (May Evolve Without Version Bump)

| Category | Examples |
|----------|----------|
| **Internal Implementation** | Module structure, class hierarchies, utility functions |
| **Performance Optimization** | Query optimization, caching strategies, batch sizes |
| **UI/UX Polish** | Layout, styling, animations, copy/labels |
| **Prompt Engineering** | LLM prompt templates, system instructions |
| **Development Process** | Sprint assignments, task breakdown, tooling choices |
| **Examples and Tutorials** | Code samples, walkthroughs (unless they define behavior) |

### 4.3 Explicitly Deferred (Out of Current Scope)

These items are documented as out-of-scope and may be designed later without affecting governed documents:

| Item | Status | Notes |
|------|--------|-------|
| Event retention/compaction | Deferred | Invariants for future implementation are specified |
| Multi-tenant isolation | Deferred | Auth integration points are defined |
| Steps 4-10 implementation | Deferred | Scaffolded as stubs |
| SSO/billing integration | Deferred | Identity hooks exist |
| Horizontal scaling | Deferred | Seams are identified |

---

## 5. Change Control

### 5.1 Change Categories

| Category | Version Impact | Approval Required | Examples |
|----------|----------------|-------------------|----------|
| **Typo/Grammar** | None | Self-review | Spelling, punctuation |
| **Clarifying Example** | None | Peer review | Additional code sample |
| **Editorial Rewrite** | None | Peer review | Restructure for clarity |
| **Patch (non-breaking)** | Patch bump (x.y.Z) | Tech lead | Add detail without changing semantics |
| **Minor (backward-compatible)** | Minor bump (x.Y.0) | Team review | New optional field, new endpoint |
| **Major (breaking)** | Major bump (X.0.0) | Architecture review | Change invariant, remove field, alter semantics |

### 5.2 Change Process

```
1. Identify change category (see §5.1)

2. If semantic change:
   a. Document rationale in change request
   b. Identify affected gates
   c. Update all affected documents atomically
   d. Bump versions appropriately
   e. Re-run affected gate verifications
   f. Update cross-references
   
3. If editorial change:
   a. Make change
   b. Note in commit message: "Editorial: [description]"
   
4. Record change in Version History of affected documents
```

### 5.3 Breaking Change Criteria

A change is **breaking** if it would cause:
- Existing compliant code to become non-compliant
- Existing tests to fail without code changes
- Clients to receive unexpected responses
- Data written under old spec to be invalid under new spec

Breaking changes require:
- Explicit migration path documented
- Deprecation period (if applicable)
- Coordination with all implementers
- Architecture review approval

### 5.4 Emergency Changes

If a specification error is discovered that blocks implementation:

1. Document the error and its impact
2. Propose minimal fix
3. Get expedited approval (tech lead minimum)
4. Apply fix with patch version bump
5. Notify all implementers immediately
6. Retrospective on how error occurred

---

## 6. Verification Requirements

### 6.1 Invariant Coverage

Every correctness-critical invariant must have:

| Invariant | Canonical Location | Gate | Verification Approach |
|-----------|-------------------|------|----------------------|
| Event sequence gap-free | Contract §9.2 | β1 | Concurrent emission test |
| Replay query correctness | Contract §12.1 | β2a | Ordered replay test |
| SSE replay-then-live | Contract §12.1 | β2 | Stream integration test |
| Optimistic concurrency | Contract §11.1 | β3 | Stale version rejection test |
| Runner exclusivity | Contract §15.2 | β4 | Concurrent runner test |
| Audit attribution | Contract §15.3 | β5 | Actor reconstruction test |
| Broadcast after commit | Spec §16.2 | β6a | Failed broadcast recovery test |

### 6.2 Boundary Coverage

Every external boundary must have defined behavior:

| Boundary | Contract Location | Spec Location |
|----------|-------------------|---------------|
| REST API | Contract §10 | Spec §9.1 |
| SSE Stream | Contract §12 | Spec §16.4 |
| Database | Contract §9 | Spec §7 |
| Frontend State | Contract §13-14 | (Frontend implements) |
| Runner Interface | Contract §15 | Spec §16.5 |

### 6.3 Ambiguity Resolution

| Potential Ambiguity | Resolution Location |
|--------------------|---------------------|
| When does state_version increment? | Spec §7.3 (MUST/MUST NOT list) |
| lastContiguous vs maxSeen difference? | Contract §14.2 (explicit table) |
| Which triggers are required vs optional? | Spec §7 header (requirements table) |
| What actor is attributed to each event type? | Spec §9.2 (mapping table) |
| What happens if broadcast fails? | Spec §16.2 (NEVER DO + recovery) |

---

## 7. Commitments

### 7.1 To Implementers

- Governed documents will not change semantically without version bumps
- Any semantic change will be communicated with explicit migration notes
- You may rely on governed invariants for correctness
- Breaking changes will include deprecation periods where feasible

### 7.2 To Reviewers

- Gate criteria are stable and testable
- Verification approaches are defined
- Compliance is measurable against documented versions
- Changes to gates require re-verification

### 7.3 To AI Agents

- Document versions are explicit and stable
- Cross-references are maintained
- Terminology is consistent across documents
- Changes are recorded in version history

### 7.4 To Future Maintainers

- Change control rules govern all modifications
- Breaking changes require explicit justification
- Editorial improvements are welcome under review
- Version history documents evolution

---

## 8. Quick Reference

### 8.1 One-Line Invariants

Memorize these — they're the correctness backbone:

1. **Sequences are gap-free** — `sorted(sequences) == range(1, max+1)`
2. **Broadcast after commit** — Event in DB before broadcast attempted
3. **Version on every mutation** — `state_version` increments atomically with state change
4. **Replay then live** — SSE serves historical events before switching to live
5. **Exclusive execution** — Only lease holder advances workflow
6. **One latest per lineage** — Exactly one artifact with `superseded_by IS NULL`
7. **Actor on every action** — Audit log captures actor for all state changes

### 8.2 One-Line Boundaries

These are the interfaces — changes here affect consumers:

1. **REST** — CRUD + actions + progress + staleness (all return position)
2. **SSE** — Sequenced events with `from_sequence` replay
3. **Database** — Triggers enforce staleness propagation and audit
4. **Frontend** — Sequence guard + connection state + action gating
5. **Runner** — Lease-protected advancement with idempotent retry

### 8.3 Change Decision Tree

```
START: What type of change is this?

┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 1: Is the document set currently FROZEN?                          │
├─────────────────────────────────────────────────────────────────────────┤
│ Yes → Go to STEP 1a (Freeze Rules)                                     │
│ No  → Go to STEP 2 (Normal Classification)                             │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 1a: FREEZE RULES - Is the change allowed during freeze?           │
├─────────────────────────────────────────────────────────────────────────┤
│ Typo/grammar fix?           → ✅ Allowed, proceed to STEP 2            │
│ Clarifying example?         → ✅ Allowed, proceed to STEP 2            │
│ Non-semantic clarification? → ✅ Allowed (patch bump), proceed to STEP 2│
│ Anything else?              → ❌ Requires UNFREEZE first               │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 2: Which document is affected?                                    │
├─────────────────────────────────────────────────────────────────────────┤
│ README only?                → Low impact, peer review                  │
│ Design Intent?              → High impact, architecture review         │
│ Architectural Contract?     → High impact, affects all downstream      │
│ Technical Specification?    → Medium impact, may affect Directive      │
│ Development Directive?      → Lower impact, may affect schedule only   │
│ Multiple documents?         → Update atomically, highest impact rules  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 3: What kind of content is changing?                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│ TYPO/GRAMMAR                                                           │
│   → No version bump, note "Editorial" in commit                        │
│                                                                         │
│ EXAMPLE/CLARIFICATION (no semantic change)                             │
│   → No version bump, peer review                                       │
│                                                                         │
│ TERMINOLOGY (glossary, term definitions)                               │
│   → Patch bump if clarifying existing term                             │
│   → Minor bump if adding new canonical term                            │
│   → Major bump if changing meaning of existing term                    │
│                                                                         │
│ CONTRACT RULE (invariant, MUST statement, reliability rule)            │
│   → Major bump, architecture review, affects all implementations       │
│                                                                         │
│ SCHEMA/ENDPOINT (API surface)                                          │
│   → Patch if adding optional field                                     │
│   → Minor if adding new endpoint                                       │
│   → Major if removing/changing existing                                │
│                                                                         │
│ GATE DEFINITION (criterion, verification, blocking rules)              │
│   → Major bump, architecture review                                    │
│                                                                         │
│ DIRECTIVE SEQUENCING (phase order, package structure)                  │
│   → Patch if clarification                                             │
│   → Minor if reordering within phase                                   │
│   → Major if changing phase boundaries or gates                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

SUMMARY:
  Typo/grammar → Fix, no bump
  Clarification → Peer review, no bump  
  Patch-level → Tech lead, x.y.Z bump
  Minor-level → Team review, x.Y.0 bump
  Major-level → Architecture review, X.0.0 bump, migration plan
```

---

## 9. FAQ

**Q: Can I fix a typo?**
A: Yes, no version bump needed. Note "Editorial" in commit message.

**Q: Can I add an example?**
A: Yes, if it doesn't change semantics. Peer review recommended.

**Q: Can I add a new optional field to an API response?**
A: Yes, this is a minor (backward-compatible) change. Bump minor version.

**Q: Can I change when state_version increments?**
A: No, this is a breaking change. Requires major version bump and architecture review.

**Q: Can I change internal module structure?**
A: Yes, internal implementation is not governed. No version bump needed.

**Q: Can I change prompt templates?**
A: Yes, prompt engineering is not governed. No version bump needed.

**Q: What if I find a bug in the spec?**
A: Document it, assess impact, follow change process in §5.2. Bug fixes that change semantics still require version bumps.

**Q: What if a gate is impossible to pass as written?**
A: This is a spec bug. Fix requires patch version bump at minimum. Document the issue and resolution.

**Q: Who approves breaking changes?**
A: Architecture review (documented owner or designated reviewer).

**Q: How do I propose a change?**
A: Open a change request documenting: what, why, impact, affected gates, migration path (if breaking).

**Q: What's the difference between Change Management and Document Freeze?**
A: Change Management is the **policy** (the rules). Document Freeze is a **procedure** executed under that policy. Freeze is a controlled state with entry/exit gates; Change Management governs how changes happen in any state.

**Q: Can I make semantic changes during freeze?**
A: No. Only typos, grammar, clarifying examples, and non-semantic clarifications are allowed during freeze. Semantic changes require exiting freeze first.

**Q: How do I know if the specs are frozen?**
A: Check §3.6 (Current Freeze State) in this document. It shows the current state and which gates have passed.

**Q: What if two documents disagree?**
A: The higher-authority document controls (see §0.1). Fix the lower-authority document to align.

**Q: How do I change the Change Management document itself?**
A: See §1.3. Changes to governance sections (§0, §3, §5) require architecture review regardless of apparent scope. Other changes follow normal rules but require explicit note that governance doc was changed.

**Q: What makes a freeze valid?**
A: A freeze MUST have a baseline identifier (git tag or commit SHA). Without an immutable anchor, freeze is invalid. See §3.1.

---

## 10. Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2025-01-04 | Initial change management framework; baseline all documents |
| v1.1 | 2025-01-04 | Added §0 Authority & Procedures (document authority order, policy/procedure hierarchy); Added §3 Document Freeze Procedure with gates F0-F4; Self-validating document list with SHA-256 hashes; Freeze state behavior table; Renumbered subsequent sections |
| v1.2 | 2025-01-04 | Separated policy (§1.1 document types) from snapshot (FREEZE-RECORD.md artifact); Added §1.3 governance-of-governance rules; Added §3.2.1 objective gate evidence requirements with checklists; Made git tag/SHA anchoring a MUST for valid freeze; Expanded FAQ |
| v1.3 | 2025-01-05 | Added the "SOLVER-README-v{X}" from docs/specs/   to the canonical set, disambiguated it from the project README.me in the root folder |
| v2.0.1 | 2026-01-05 | Aligned freeze procedure to tag baseline before committing FREEZE-RECORD; clarified F4 timing |
| v2.0 | 2026-01-05 | Adopted two-hierarchy authority model; added Document-Type Specifications to canonical set and F0 checklist; standardized Technical Spec filename casing |
---

*SOLVER Change Management v2.0.1*
*Specification Governance Framework*
