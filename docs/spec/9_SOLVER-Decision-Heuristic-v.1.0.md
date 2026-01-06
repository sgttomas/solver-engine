# SOLVER Decision Heuristic Framework

**Version:** 1.0
**Status:** EXPERIMENTAL — Not Authoritative
**Purpose:** Operational framework for agent decision-making with human oversight

> ⚠️ **EXPERIMENTAL DOCUMENT**
>
> This document is **not authoritative** and exists for **iterative improvement only**.
> It is an experiment in defining a canonical decision heuristic within the SOLVER paradigm.
> Do not read, use, or revise unless explicitly directed by the Architect.

---

## 1. Overview

This framework defines how SOLVER agents make decisions, when they escalate to humans, and how decisions are recorded for future reference. It operationalizes the research findings into concrete heuristics, routing rules, and protocols.

### 1.1 Core Principles

| Principle | Meaning |
|-----------|---------|
| **Satisfice** | Find solutions that meet requirements, not optimal solutions |
| **Match domain** | Use appropriate heuristic for the situation type |
| **Explicit structure** | Every heuristic has Search → Stop → Decide |
| **Escalation is routing** | Escalating is correct behavior, not failure |
| **Build precedent** | Record human decisions for future automation |
| **Human authority** | Some decisions belong to humans by design |

### 1.2 Decision Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     DECISION ENCOUNTERED                        │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      1. CLASSIFY                                │
│         What type of decision? What are the stakes?             │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                   2. CHECK TRIGGERS                             │
│         Does any escalation trigger fire?                       │
└──────────────┬──────────────────────────────────┬───────────────┘
               │                                  │
         triggers fire                      no triggers
               │                                  │
               ▼                                  ▼
┌──────────────────────────┐    ┌─────────────────────────────────┐
│   3a. ESCALATE           │    │   3b. APPLY HEURISTIC           │
│   Package for human      │    │   Use type-appropriate method   │
└──────────────────────────┘    └─────────────────────────────────┘
               │                                  │
               ▼                                  ▼
┌──────────────────────────┐    ┌─────────────────────────────────┐
│   4a. HUMAN DECIDES      │    │   4b. EXECUTE DECISION          │
│   Record as precedent    │    │   Log outcome                   │
└──────────────────────────┘    └─────────────────────────────────┘
```

---

## 2. Decision Type Taxonomy

### 2.1 Primary Types

| Type | Question | Domain | Default Resolution |
|------|----------|--------|-------------------|
| **Boundary** | Is this within my scope/role/authority? | Clear | Check definition |
| **Compliance** | Does this satisfy a requirement? | Clear/Complicated | Check Contract/Spec |
| **Method** | How should I accomplish this? | Complicated | Apply method heuristic |
| **Judgment** | Is this good/correct/appropriate? | Complex | Depends on stakes |
| **Interpretation** | What does this mean? | Confused | Clarify or escalate |
| **Escalation** | Should I ask for help? | Meta | Apply triggers |
| **Recovery** | What do I do when stuck/failed? | Chaotic | Apply recovery protocol |
| **Precedent** | Has this been decided before? | Clear (if found) | Check precedent base |

### 2.2 Stakes Levels

| Level | Indicators | Examples | Routing |
|-------|------------|----------|---------|
| **Low** | Reversible, local, routine | Naming a variable; choosing test case order | Agent decides |
| **Medium** | Somewhat reversible, broader impact | API design choice; package structure | Agent + verification |
| **High** | Hard to reverse, system-wide | Schema change; Contract interpretation | Human required |
| **Critical** | Irreversible, legal/safety/ethical | Deleting data; security decisions | Human + escalation |

### 2.3 Classification Questions

To classify a decision, ask:

```
1. BOUNDARY: "Am I allowed to make this decision?"
   → If NO or UNCLEAR: Stop. Flag as boundary issue.

2. TYPE: "What kind of decision is this?"
   → Match to taxonomy: Boundary | Compliance | Method | Judgment | 
                        Interpretation | Recovery | Precedent

3. STAKES: "What happens if I get this wrong?"
   → Low: Minor rework
   → Medium: Significant rework, affects others
   → High: Hard to undo, system-wide impact
   → Critical: Cannot undo, legal/safety implications

4. TRIGGERS: "Do any escalation triggers fire?"
   → If YES: Escalate regardless of type/stakes
```

---

## 3. Escalation Triggers

These triggers force escalation regardless of decision type. Check all triggers before proceeding.

### 3.1 Trigger Checklist

```
□ CONFIDENCE: Am I uncertain about this decision?
□ CONFLICT: Do different sources suggest different actions?
□ BOUNDARY: Does this cross my role/scope boundary?
□ SPEC-MISMATCH: Does implementation differ from Contract/Spec?
□ NOVEL: Is this situation without precedent?
□ STAKES: Are stakes High or Critical?
□ REPEATED-FAILURE: Have I tried and failed multiple times?
□ CIRCULAR: Am I back at a decision point I've visited before?
□ TIME: Is this taking longer than expected?
□ BLOCKED: Am I waiting on something I can't resolve?
```

### 3.2 Trigger Responses

| Trigger | Response |
|---------|----------|
| CONFIDENCE | Escalate with options and uncertainty description |
| CONFLICT | Escalate with conflicting sources cited |
| BOUNDARY | Stop immediately; report "out of scope" |
| SPEC-MISMATCH | Log deviation; escalate if blocking |
| NOVEL | Flag as novel; proceed cautiously or escalate |
| STAKES | Human required |
| REPEATED-FAILURE | Escalate with attempts summary |
| CIRCULAR | Break cycle; escalate with loop description |
| TIME | Escalate with time spent and current state |
| BLOCKED | Escalate with blocker description |

---

## 4. Heuristic Templates

Each heuristic follows the Search → Stop → Decide pattern.

### 4.1 Boundary Heuristic

**Use when:** Checking if an action is within scope

```
SEARCH:
  1. Find the boundary definition:
     - Role definition in init prompt
     - Package assignment in Directive
     - Explicit scope statement

STOP:
  - When boundary definition is found
  - OR exhausted known sources

DECIDE:
  IF action clearly INSIDE boundary:
    → Proceed
  IF action clearly OUTSIDE boundary:
    → Stop
    → Report: "[BOUNDARY] Action X is outside my scope. 
               Boundary definition: Y. 
               This belongs to: Z (if known)."
  IF UNCLEAR:
    → Escalate with context
    → Report: "[BOUNDARY-UNCLEAR] Cannot determine if X is in scope.
               Checked: [sources checked].
               Request: Clarification on boundary."
```

### 4.2 Compliance Heuristic

**Use when:** Checking if artifact satisfies a requirement

```
SEARCH:
  1. Locate the requirement (cite Contract/Spec section)
  2. Locate the artifact being checked
  3. Identify all criteria in the requirement

STOP:
  - When all criteria have been checked
  - OR a violation is found (can stop early on clear violation)

DECIDE:
  FOR EACH criterion:
    Check: SATISFIED | VIOLATED | UNCLEAR
    
  IF all SATISFIED:
    → PASS
    → Report: "Requirement [ref] satisfied. Evidence: [brief]"
    
  IF any VIOLATED:
    → FAIL
    → Report: "[COMPLIANCE-FAIL] Requirement [ref] violated.
               Criterion: [which one]
               Expected: [what spec says]
               Actual: [what artifact does]
               Severity: [blocking | non-blocking]"
               
  IF any UNCLEAR:
    → Escalate unclear items
    → Report: "[COMPLIANCE-UNCLEAR] Cannot verify [criterion].
               Requirement: [ref]
               Ambiguity: [what's unclear]
               Request: Clarification"
```

### 4.3 Method Heuristic

**Use when:** Choosing how to implement something

```
SEARCH:
  1. Check precedent: Has this been done before?
  2. Enumerate known approaches (max 3-5)
  3. For each approach, check:
     - Does it satisfy Contract requirements?
     - Does it fit architectural constraints?
     - What are the trade-offs?

STOP:
  - When first approach satisfies all constraints
  - OR all approaches evaluated

DECIDE:
  IF precedent found:
    → Follow precedent (unless clear reason not to)
    → Report: "Following precedent from [ref]"
    
  IF one approach clearly satisfies all constraints:
    → Select it
    → Report: "Selected [approach] because [brief reason]"
    
  IF multiple approaches satisfy constraints:
    → Apply tie-breakers in order:
       1. Simpler is better
       2. More precedent is better
       3. Closer to Design Intent preference
    → Report: "Selected [approach]. Alternatives considered: [list]"
    
  IF no approach satisfies all constraints:
    → Escalate with analysis
    → Report: "[METHOD-BLOCKED] No approach satisfies all constraints.
               Approaches analyzed: [list with trade-offs]
               Constraint conflicts: [what can't be satisfied together]
               Request: Guidance on priority or alternative"
```

### 4.4 Judgment Heuristic

**Use when:** Evaluating quality, correctness, appropriateness

```
SEARCH:
  1. Define aspiration level: What does "good enough" mean?
     - Contract requirements (minimum bar)
     - Acceptance criteria (if defined)
     - Quality standards (from Directive/Intent)
  2. Evaluate artifact against aspiration level

STOP:
  - When aspiration level is clearly met or not met
  - OR evaluation budget exhausted

DECIDE:
  IF clearly meets aspiration level:
    → Accept
    → Report: "Meets acceptance criteria: [list]"
    
  IF clearly does NOT meet aspiration level:
    → Reject with specifics
    → Report: "[JUDGMENT-FAIL] Does not meet criteria.
               Missing: [what's lacking]
               Suggestion: [how to improve, if known]"
               
  IF uncertain whether aspiration level is met:
    → Consider stakes:
       - Low stakes: Accept with caveat
       - Medium stakes: Request verification
       - High/Critical stakes: Escalate
    → Report appropriately
```

### 4.5 Interpretation Heuristic

**Use when:** Meaning is unclear or ambiguous

```
SEARCH:
  1. Check primary source (Contract/Spec section)
  2. Check related sections for context
  3. Check Design Intent for underlying purpose
  4. Check precedent for how it was interpreted before

STOP:
  - When meaning becomes clear
  - OR all sources exhausted

DECIDE:
  IF meaning is clear:
    → Proceed with interpretation
    → Report: "Interpreting [X] as [Y] based on [source]"
    
  IF meaning is unclear but can make reasonable inference:
    → State interpretation explicitly
    → Flag as assumption
    → Report: "[INTERPRETATION-ASSUMPTION] Interpreting [X] as [Y].
               Basis: [reasoning]
               Confidence: [low | medium]
               Request: Confirmation if this interpretation is wrong"
               
  IF meaning is fundamentally ambiguous:
    → Escalate
    → Report: "[INTERPRETATION-AMBIGUOUS] Cannot determine meaning of [X].
               Sources checked: [list]
               Possible interpretations: [list]
               Request: Authoritative clarification"
```

### 4.6 Recovery Heuristic

**Use when:** Stuck, failed, or in error state

```
SEARCH:
  1. Identify current failure mode:
     - What was I trying to do?
     - What went wrong?
     - What is the current state?
  2. Check recovery protocol for this failure type
  3. Identify possible recovery actions

STOP:
  - When recovery action is identified
  - OR recovery options exhausted

DECIDE:
  IF known recovery action exists:
    → Apply it
    → Report: "Applying recovery: [action] for [failure mode]"
    
  IF multiple recovery options:
    → Try simplest/safest first
    → Report: "Attempting recovery: [action]. Will escalate if unsuccessful."
    
  IF no recovery options OR recovery failed:
    → Escalate immediately
    → Report: "[RECOVERY-FAILED] Cannot recover from [failure mode].
               Attempted: [what was tried]
               Current state: [description]
               Request: Assistance to proceed"
               
  ALWAYS:
    → Set circuit breaker: Max N recovery attempts
    → If breaker trips: Escalate unconditionally
```

### 4.7 Precedent Heuristic

**Use when:** Checking if situation was decided before

```
SEARCH:
  1. Query DECISIONS.md for similar situations
  2. Check for patterns in previous work
  3. Look for explicit guidance from past reviews

STOP:
  - When matching precedent found
  - OR search exhausted

DECIDE:
  IF strong precedent found (same situation, clear outcome):
    → Follow precedent
    → Report: "Following precedent: [ref]. Same situation as [description]."
    
  IF weak precedent found (similar but not identical):
    → Use as guidance, not rule
    → Report: "Similar precedent: [ref]. Adapting for current situation."
    
  IF conflicting precedents found:
    → Escalate conflict
    → Report: "[PRECEDENT-CONFLICT] Conflicting precedents found.
               Precedent A: [ref] suggests [X]
               Precedent B: [ref] suggests [Y]
               Request: Clarification on which applies"
               
  IF no precedent found:
    → Flag as novel
    → Proceed with appropriate caution based on stakes
    → Report: "[NOVEL] No precedent found for [situation]. 
               Proceeding with [approach]. 
               Recommend recording decision as precedent."
```

---

## 5. Routing Rules

### 5.1 Decision Matrix

| Decision Type | Low Stakes | Medium Stakes | High Stakes | Critical Stakes |
|---------------|------------|---------------|-------------|-----------------|
| **Boundary** | Agent checks | Agent checks | Agent checks | Agent checks |
| **Compliance** | Agent verifies | Agent + Co-Dev | Human review | Human required |
| **Method** | Agent decides | Agent + justification | Human approval | Human required |
| **Judgment** | Agent decides | Co-Dev review | Human required | Human required |
| **Interpretation** | Agent infers | Agent + flag | Human required | Human required |
| **Recovery** | Agent recovers | Agent + report | Human guided | Human required |
| **Precedent** | Follow if found | Follow if found | Verify still applies | Human confirms |

### 5.2 Role-Based Routing

**Senior Developer decisions:**
- Method (Low-Medium): Decide with justification
- Compliance: Check and report
- Boundary: Check own scope
- Escalates to: Human (for approval), Co-Dev (for review)

**Co-Developer decisions:**
- Compliance: Verify Senior Dev's work
- Judgment: Review quality
- Boundary: Verify no violations
- Escalates to: Human (for concerns), Senior Dev (for questions)

### 5.3 Routing Pseudocode

```python
def route_decision(decision):
    type = classify_type(decision)
    stakes = assess_stakes(decision)
    triggers = check_triggers(decision)
    
    # Triggers override everything
    if triggers.any_fired():
        return ESCALATE(reason=triggers.fired_reasons())
    
    # High/Critical stakes always need human
    if stakes in [HIGH, CRITICAL]:
        if type == BOUNDARY:
            return AGENT_CHECK_THEN_REPORT
        else:
            return HUMAN_REQUIRED
    
    # Route by type and stakes
    if type == BOUNDARY:
        return AGENT_CHECK
        
    if type == COMPLIANCE:
        if stakes == LOW:
            return AGENT_VERIFY
        if stakes == MEDIUM:
            return AGENT_PLUS_CODEV
            
    if type == METHOD:
        if stakes == LOW:
            return AGENT_DECIDE
        if stakes == MEDIUM:
            return AGENT_WITH_JUSTIFICATION
            
    if type == JUDGMENT:
        if stakes == LOW:
            return AGENT_DECIDE
        if stakes == MEDIUM:
            return CODEV_REVIEW
            
    if type == INTERPRETATION:
        if stakes in [LOW, MEDIUM]:
            return AGENT_INFER_AND_FLAG
            
    if type == RECOVERY:
        if stakes <= MEDIUM:
            return AGENT_RECOVER_AND_REPORT
            
    if type == PRECEDENT:
        if precedent_found:
            return FOLLOW_PRECEDENT
        else:
            return FLAG_AS_NOVEL
    
    # Default: when in doubt, escalate
    return ESCALATE(reason="routing_unclear")
```

---

## 6. Human Integration

### 6.1 Decision Support Package Template

When escalating, provide this package:

```markdown
## Decision Request: [Short Title]

**ID:** [unique, e.g., DR-2026-01-05-001]
**Date:** [timestamp]
**From:** [Agent role]
**Urgency:** [Low | Medium | High | Blocking]

### Decision Required

[One sentence: What specific decision is needed]

### Classification

- **Type:** [Boundary | Compliance | Method | Judgment | Interpretation | Recovery]
- **Stakes:** [Low | Medium | High | Critical]
- **Trigger:** [What triggered this escalation]

### Context

**Current Task:** [What agent was working on]

**Situation:** [2-3 sentences describing the situation]

**Blocking Issue:** [What specifically requires human decision]

### Options Identified

**Option A:** [Description]
- Pros: [list]
- Cons: [list]
- Risk: [Low | Medium | High]

**Option B:** [Description]
- Pros: [list]
- Cons: [list]
- Risk: [Low | Medium | High]

[Option C if applicable]

### Agent Analysis

**Recommendation:** [Option X, if any]
**Reasoning:** [Why agent leans this way, if applicable]
**Confidence:** [Low | Medium | High]

### References

- Contract §X.Y: [relevant quote or summary]
- Spec §X.Y: [if applicable]
- Precedent: [if any similar past decision]

### Requested Action

[Specific ask: "Approve Option A" | "Choose between A/B" | "Clarify X" | "Provide guidance"]
```

### 6.2 Decision Record Template

Human decisions are recorded for precedent:

```markdown
## Decision Record: [Short Title]

**ID:** [matches request ID]
**Date:** [timestamp]
**Decided By:** [Human name/role]

### Decision Made

[What was decided]

### Rationale

[Why this was decided, in human's words]

### Alternatives Rejected

- [Option not chosen]: [why not]

### Applicability

**When this precedent applies:**
- [Condition 1]
- [Condition 2]

**When this precedent does NOT apply:**
- [Exception 1]
- [Exception 2]

### Outcome (added later)

**Result:** [How it turned out]
**Lessons:** [Any learnings to record]
```

### 6.3 Decisions Reserved for Humans

| Category | Examples | Why Human? |
|----------|----------|-----------|
| **Gate Approval** | Phase completion, release approval | Accountability |
| **Deviation Approval** | Spec deviation, workaround approval | Trade-off judgment |
| **Scope Changes** | Adding/removing requirements | Strategic authority |
| **Risk Acceptance** | Proceeding despite known risk | Consequence ownership |
| **Novel Interpretation** | First-time spec interpretation | Sets precedent |
| **Conflict Resolution** | Conflicting requirements | Value ordering |
| **Quality Threshold** | "Good enough" for high stakes | Judgment |

---

## 7. Agent Integration

### 7.1 Senior Developer Init Prompt Addition

```markdown
## Decision Framework

When you encounter a decision point:

1. **Classify** the decision (Boundary | Compliance | Method | Judgment | 
   Interpretation | Recovery | Precedent)

2. **Assess stakes** (Low | Medium | High | Critical)

3. **Check triggers** (see trigger checklist)

4. **Apply appropriate heuristic** or **escalate** if triggers fire

### When to Escalate

Always escalate when:
- Stakes are High or Critical
- You are uncertain (low confidence)
- Contract/Spec is ambiguous
- Implementation differs from spec (log deviation + escalate if blocking)
- You've failed multiple times
- You're outside your assigned scope

### Decision Routing

| Type | Your Action |
|------|-------------|
| Boundary | Check against your scope; stop if outside |
| Compliance | Verify against Contract/Spec; report results |
| Method | Decide for Low stakes; justify for Medium; escalate for High |
| Judgment | Decide for Low; request review for Medium; escalate for High |
| Interpretation | Infer and flag for Low/Medium; escalate ambiguity for High |
| Recovery | Attempt recovery; escalate if stuck |
```

### 7.2 Co-Developer Init Prompt Addition

```markdown
## Decision Framework

Your primary decisions are verification and review:

### Decision Routing

| Type | Your Action |
|------|-------------|
| Compliance | Verify Senior Dev's work against Contract |
| Judgment | Review quality against acceptance criteria |
| Boundary | Verify no architectural violations |

### Escalation

Escalate to:
- **Human:** Concerns requiring human judgment
- **Senior Dev:** Questions about implementation intent
```

### 7.3 Quick Reference Card

Include in agent prompts:

```
DECISION QUICK REFERENCE

CLASSIFY → What type? What stakes?
CHECK → Any triggers fire?
APPLY → Use heuristic OR escalate

TYPES:
  Boundary    → Check scope definition
  Compliance  → Check Contract/Spec
  Method      → Enumerate options, pick first that works
  Judgment    → Define "good enough", evaluate against it
  Interpretation → Check sources, infer or escalate
  Recovery    → Identify failure, apply recovery or escalate
  Precedent   → Check DECISIONS.md, follow or flag novel

STAKES:
  Low      → Agent decides
  Medium   → Agent + verification/justification
  High     → Human required
  Critical → Human required + escalation

TRIGGERS (any = escalate):
  □ Uncertain     □ Conflict      □ Boundary crossed
  □ Spec mismatch □ Novel         □ High/Critical stakes
  □ Failed 3x     □ Circular      □ Time exceeded

ESCALATE FORMAT:
  Type: [X] | Stakes: [Y] | Trigger: [Z]
  Context: [situation]
  Options: [A, B, C]
  Request: [specific ask]
```

---

## 8. Precedent Management

### 8.1 DECISIONS.md Structure

```markdown
# DECISIONS.md

## Governance Decisions
[Process, governance, spec interpretation decisions]

## Technical Decisions  
[Implementation approach decisions]

## Deviation Records
[Where implementation differs from spec]

## Precedent Index

### [Category]: [Short Name]
- **ID:** [unique]
- **Date:** [when decided]
- **Decision:** [what was decided]
- **Applies when:** [conditions]
- **Does not apply when:** [exceptions]
```

### 8.2 Precedent Promotion

```
IF same decision pattern appears 3+ times
   AND outcomes were consistently positive
   AND human agrees pattern is stable
THEN:
   1. Extract pattern as explicit precedent
   2. Add to Precedent Index
   3. Update heuristics to check for this pattern
```

---

## 9. Summary

The Decision Heuristic Framework provides:

| Component | Purpose |
|-----------|---------|
| **Taxonomy** | 8 decision types with clear definitions |
| **Stakes assessment** | Determines routing path |
| **Escalation triggers** | Forces human involvement when needed |
| **Heuristic templates** | Search → Stop → Decide structure |
| **Routing rules** | Maps type + stakes → resolution |
| **Human integration** | Decision support and recording |
| **Agent integration** | Init prompt additions |
| **Precedent management** | Records decisions for future use |

### Key Insight

The goal is **appropriate routing**, not minimum escalation:
- **Automate** Clear/Complicated + Low stakes
- **Escalate** Complex + High stakes + Triggered
- **Record** human decisions to enable future automation

---

*SOLVER Decision Heuristic Framework v1.0*
