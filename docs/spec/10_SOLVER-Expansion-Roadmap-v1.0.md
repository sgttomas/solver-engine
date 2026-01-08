# SOLVER Expansion Roadmap v1.0

**Document Type:** Roadmap / Problem Statement Collection
**Status:** Draft
**Author:** Ryan Tufts (Architect)
**Date:** 2025-01-07

---

## 1. Meta-Objective

Design problem statements for SOLVER to generate detailed plans for its own expansion into a comprehensive human-AI hybrid orchestration layer for high-stakes knowledge work.

### 1.1 End State Vision

- **Orchestration Layer:** SOLVER serves as the planning layer that AI coding agents and other agentic systems call to generate detailed specifications—not as an implementation tool itself
- **Judge-Based Correctness:** Solutions validated by human and AI judges at step and workflow levels, not solely by automated testing
- **Knowledge Graph Persistence:** Entities, methodology patterns, and artifact lineage persist across workflows for cross-problem intelligence
- **Human Responsibility:** Human accountability preserved throughout; judges inform but never bypass approval gates

### 1.2 Design Principles

1. **Correct solutions are judge-determined**, not test-determined
2. **Output must facilitate graph transposition** even when semi-structured
3. **SOLVER orchestrates; other systems execute** (clear separation of concerns)
4. **Human-in-the-loop is legislated, not optional** in high-stakes knowledge work

---

## 2. Problem Statement 1: Knowledge Graph Integration

**Priority:** 1 (First)
**Dependencies:** None

### 2.1 Problem Statement (SOLVER Input)

```
PROBLEM STATEMENT: Design a knowledge graph integration layer for SOLVER that enables:

1. ARTIFACT TRANSPOSITION
   - Parse step artifacts (Problem Definition, Requirements, Objectives packages)
     into graph-friendly structures
   - Handle semi-structured output that may not perfectly conform to schemas
   - Support incremental transposition as artifacts are approved (not batch
     after workflow completion)

2. ENTITY PERSISTENCE
   - Stakeholders, constraints, requirements, objectives as reusable nodes
   - Cross-workflow deduplication (same stakeholder appearing in multiple problems)
   - Entity versioning when definitions evolve across workflows

3. METHODOLOGY PATTERNS
   - Successful V3 methodologies as retrievable patterns
   - Pattern matching to suggest prior methodologies for similar problem types
   - Pattern evolution tracking (how methodologies improve over time)

4. TRACEABILITY LINEAGE
   - Complete provenance: which workflow -> which step -> which artifact -> which entity
   - Dependency graphs: which requirements satisfy which stakeholder needs
   - Impact analysis: if requirement R changes, what objectives are affected?

5. METHODOLOGY LIBRARY ARCHITECTURE
   - problem_type classification field on workflows for categorization
   - pgvector integration for semantic similarity search across methodologies
   - Quality signals tracking: approval_rate, revision_count, time_to_approval
   - Methodology versioning with cross-workflow lineage (how V3s evolve)
   - Cacheable methodology retrieval by problem_type similarity
   - Foundation for expert-contributed and organization-proprietary templates

CONSTRAINTS:
- Must not break existing REST + SSE API contracts
- Must integrate with existing insert-per-revision artifact model
- Graph queries must not block workflow execution (async transposition)
- Human judges must be able to query the graph for context during review

SCOPE:
- IN: Graph schema design, transposition pipeline, query patterns for judges
- OUT: Graph database selection (assume Neo4j or similar; specify interface)
- OUT: Frontend visualization (separate problem)

SUCCESS CRITERIA:
- Cross-workflow entity queries return in <100ms
- Methodology pattern retrieval suggests relevant prior work
- Full provenance traceable from any graph node back to source artifact
```

### 2.2 Expected Outputs

| Step | Artifact | Purpose |
|------|----------|---------|
| 1 | ProblemDefinitionPackage | Scoped graph integration problem with stakeholders, constraints |
| 2 | RequirementsPackage | Functional/non-functional requirements for graph layer |
| 3 | ObjectivesPackage | Measurable success criteria for graph integration |

---

## 3. Problem Statement 2: Judge Framework

**Priority:** 2
**Dependencies:** Graph Integration (for querying prior judgments)

### 3.1 Problem Statement (SOLVER Input)

```
PROBLEM STATEMENT: Design a judge-based correctness evaluation framework for SOLVER
that operates at both step-level and workflow-level.

1. STEP-LEVEL JUDGES
   - Evaluate each artifact before approval gate
   - Multiple judge perspectives possible (domain expert, methodology auditor,
     stakeholder advocate)
   - Judges may be human, AI, or hybrid (AI drafts evaluation, human confirms)
   - Judge verdict does NOT auto-approve; informs but does not replace human gate

2. WORKFLOW-LEVEL JUDGES
   - Evaluate complete workflow output (all approved artifacts)
   - Assess coherence: do objectives actually trace to requirements that trace
     to problem?
   - Assess completeness: are there gaps in coverage?
   - Assess correctness: would a domain expert accept this as sound?

3. JUDGE CRITERIA REGISTRY
   - Domain-specific evaluation criteria (healthcare has different standards
     than software)
   - Criteria versioning (standards evolve)
   - Criteria composition (combine base criteria + domain criteria + instance criteria)

4. VERDICT ARTIFACTS
   - Judge evaluations become first-class artifacts in the workflow
   - Traceable to specific artifact versions they evaluated
   - Auditable: who judged, when, using what criteria, what verdict

CONSTRAINTS:
- Judges inform but never bypass human approval gates (human responsibility
  is non-negotiable)
- Judge evaluations must be visible via SSE stream for real-time feedback
- Must integrate with knowledge graph (judges can query prior judgments on
  similar artifacts)

SCOPE:
- IN: Judge interface contracts, criteria schema, verdict artifact model,
      workflow integration points
- OUT: Specific domain criteria (separate problem per domain)
- OUT: AI judge implementation (specify interface, not implementation)

SUCCESS CRITERIA:
- Every approved artifact has at least one judge evaluation recorded
- Judge verdicts traceable in audit trail (Gate F compliance)
- Human reviewer sees judge evaluation before making approve/revise decision
```

### 3.2 Expected Outputs

| Step | Artifact | Purpose |
|------|----------|---------|
| 1 | ProblemDefinitionPackage | Scoped judge framework problem |
| 2 | RequirementsPackage | Judge interface and criteria requirements |
| 3 | ObjectivesPackage | Measurable criteria for judge framework |

---

## 4. Problem Statement 3: Extended Workflow (Steps 4-10)

**Priority:** 3
**Dependencies:** Graph Integration, Judge Framework

### 4.1 Problem Statement (SOLVER Input)

```
PROBLEM STATEMENT: Design the extended SOLVER workflow adding Steps 4-10 to the
existing Steps 1-3 (Problem Definition -> Requirements -> Objectives).

CURRENT STATE (Steps 1-3):
- Step 1: Problem Definition - scope, stakeholders, constraints
- Step 2: Requirements - functional/non-functional needs traced to Step 1
- Step 3: Objectives - measurable success criteria traced to Step 2

EXTENDED STEPS TO DESIGN:

1. STEP 4: VERIFICATION DESIGN
   - How will we verify each requirement is met?
   - Test strategies, inspection protocols, analysis methods
   - Traces to: Requirements (what we verify) + Objectives (success thresholds)

2. STEP 5: VALIDATION DESIGN
   - How will we validate the solution actually solves the problem?
   - Acceptance criteria, user acceptance protocols, stakeholder sign-off
     requirements
   - Traces to: Stakeholders (who validates) + Success Criteria (what they accept)

3. STEP 6: EVALUATION CRITERIA
   - How will judges assess correctness?
   - Domain-specific quality criteria
   - Traces to: Objectives + Verification Design + Validation Design

4. STEP 7: ASSESSMENT PROTOCOL
   - End-to-end process for evaluating a candidate solution
   - Sequence of verification -> validation -> judgment
   - Gate conditions for each assessment stage

5. STEP 8: IMPLEMENTATION STRATEGY
   - High-level approach to solving the problem (NOT implementation code)
   - Component decomposition, integration approach, risk mitigation
   - Traces to: Requirements + Constraints + Objectives

6. STEPS 9-10: RESERVED FOR DOMAIN EXTENSION
   - Placeholder for Instance N specialization
   - Healthcare might add: Regulatory Compliance Design
   - Software might add: Architecture Decision Records

CONSTRAINTS:
- Each step must follow two-pass model (methodology -> execution)
- Each step must have mandatory human approval gate in Pass 2
- Each step artifact must have full traceability to upstream steps
- Must integrate with judge framework (judges evaluate each step)
- Must integrate with knowledge graph (entities flow into graph)
- Instance N extension points must be defined even if not implemented in MVP
- Template injection points for domain-specific methodology contributions
- Schema extension mechanism for domain-specific artifact fields

SCOPE:
- IN: Step definitions, artifact schemas, traceability rules, gate requirements
- OUT: Prompt engineering for each step (separate problem)
- OUT: Domain-specific Step 9-10 content (separate problem per domain)

SUCCESS CRITERIA:
- Complete workflow from problem statement to assessment protocol
- Every downstream artifact traces to upstream sources
- Judge framework can evaluate each step
- Graph integration captures entities from all steps
```

### 4.2 Expected Outputs

| Step | Artifact | Purpose |
|------|----------|---------|
| 1 | ProblemDefinitionPackage | Scoped workflow extension problem |
| 2 | RequirementsPackage | Requirements for Steps 4-10 |
| 3 | ObjectivesPackage | Success criteria for extended workflow |

---

## 5. Problem Statement 4: AI Agent Orchestration Interface

**Priority:** 4
**Dependencies:** All above

### 5.1 Problem Statement (SOLVER Input)

```
PROBLEM STATEMENT: Design the interface by which AI coding agents and other
agentic systems call SOLVER as an orchestration layer.

1. AGENT API CONTRACT
   - REST endpoints for: workflow creation, status polling, artifact retrieval
   - SSE subscription for real-time workflow events
   - Webhook callbacks for workflow state changes (agent doesn't need to poll)

2. AGENT AUTHENTICATION & AUTHORIZATION
   - Agent identity distinct from human identity
   - Agent can create workflows, cannot approve (human responsibility preserved)
   - Agent can request revision with feedback, triggering re-execution

3. MULTI-WORKFLOW COORDINATION
   - Agent managing multiple related workflows (decomposed problem)
   - Dependency declarations: Workflow B depends on Workflow A completion
   - Aggregation: Combine outputs from multiple workflows into unified deliverable

4. KNOWLEDGE GRAPH ACCESS
   - Agent can query graph for context before creating workflow
   - "Has this problem been solved before?" -> retrieve prior artifacts
   - "What methodology worked for similar problems?" -> retrieve patterns

5. HANDOFF PROTOCOL
   - When SOLVER produces Implementation Strategy (Step 8), agent receives it
   - Agent uses strategy to guide its implementation work
   - Agent can report implementation issues back to SOLVER for workflow revision

CONSTRAINTS:
- Human approval gates remain mandatory (agent cannot bypass)
- Agent actions audited in same trail as human actions
- Rate limiting to prevent runaway agent workflow creation
- Agent cannot modify graph directly (only read; write happens via workflow)

SCOPE:
- IN: API contract extensions, authentication model, multi-workflow coordination,
      graph query interface
- OUT: Agent implementation (specify interface, not agent code)
- OUT: Specific agent types (coding agent, research agent, etc. - separate problems)

SUCCESS CRITERIA:
- Agent can create workflow, subscribe to updates, retrieve artifacts,
  request revision
- Multi-workflow dependencies execute in correct order
- Agent can query knowledge graph for context
- All agent actions appear in audit trail
```

### 5.2 Expected Outputs

| Step | Artifact | Purpose |
|------|----------|---------|
| 1 | ProblemDefinitionPackage | Scoped agent interface problem |
| 2 | RequirementsPackage | Agent API and coordination requirements |
| 3 | ObjectivesPackage | Success criteria for agent orchestration |

---

## 6. Problem Statement 5: Workflow Visualization UI

**Priority:** 5
**Dependencies:** Graph Integration, Judge Framework

### 6.1 Problem Statement (SOLVER Input)

```
PROBLEM STATEMENT: Design the visualization layer for SOLVER workflows that enables
human reviewers to understand, evaluate, and act on workflow state effectively.

1. ARTIFACT TIMELINE VISUALIZATION
   - Visual trace links showing Problem -> Requirements -> Objectives flow
   - Revision history display (V1 -> V2 -> V3) with inline diff capability
   - Staleness propagation visualization (upstream change -> downstream impact)
   - Step-by-step progression with current position indicator

2. APPROVAL WORKFLOW INTERFACE
   - Side-by-side artifact comparison for revision review
   - Judge evaluation display integrated before approval decision
   - Comment/feedback capture for revision requests with context preservation
   - Methodology pattern suggestions ("Similar problems used these approaches")
   - Clear action buttons: Approve / Revise / Message

3. DIFF AND COMPARISON VIEWS
   - V1 -> V2 -> V3 methodology refinement visualization
   - Cross-revision artifact diff (what changed between revisions?)
   - Cross-workflow comparison (how does this problem compare to similar ones?)
   - Highlighted changes with accept/reject granularity for feedback

4. GRAPH EXPLORATION INTERFACE
   - Cross-workflow entity browser (stakeholders, requirements across problems)
   - Impact analysis visualization (if X changes, what's affected?)
   - Methodology pattern discovery (find successful approaches for problem type)
   - Traceability explorer (navigate from any node to its provenance)

5. STALENESS MANAGEMENT UX
   - Clear visual indicators for stale artifacts
   - Impact scope display (which downstream artifacts are affected?)
   - Resolution workflow (acknowledge vs. re-execute options)
   - Cascade preview (what will happen if I re-execute this step?)

CONSTRAINTS:
- Must consume existing REST + SSE API (no backend changes required)
- Real-time updates via SSE subscription
- Responsive design for desktop primary, tablet secondary
- Accessibility compliance (WCAG 2.1 AA minimum)
- Must integrate with judge evaluation display

SCOPE:
- IN: UI component design, interaction patterns, data flow, state management
- OUT: Specific frontend framework choice (specify requirements, not implementation)
- OUT: Mobile-first design (desktop primary for MVP)
- OUT: Collaborative real-time editing (single reviewer per workflow for MVP)

SUCCESS CRITERIA:
- Reviewer can understand full workflow state within 30 seconds of viewing
- Diff view clearly shows changes between any two artifact versions
- Staleness impact is immediately visible without navigation
- Approval/revision workflow completable in under 3 clicks
- Graph exploration enables cross-workflow insight discovery
```

### 6.2 Expected Outputs

| Step | Artifact | Purpose |
|------|----------|---------|
| 1 | ProblemDefinitionPackage | Scoped UI/UX problem with user personas |
| 2 | RequirementsPackage | Functional requirements for visualization |
| 3 | ObjectivesPackage | Measurable UX success criteria |

---

## 7. Execution Sequence

| Phase | Problem Statement | Dependencies | Output |
|-------|-------------------|--------------|--------|
| 1 | Graph DB Integration | None | Graph schema, transposition pipeline, methodology library |
| 2 | Judge Framework | Graph (for querying prior judgments) | Judge contracts, verdict artifacts |
| 3 | Extended Workflow (4-10) | Graph + Judges | Step definitions, schemas, Instance N hooks |
| 4 | Agent Orchestration | All above | Agent API, multi-workflow coordination |
| 5 | Workflow Visualization UI | Graph + Judges | Timeline, diff, staleness, graph explorer |

---

## 8. Process

### 8.1 For Each Problem Statement

1. **Feed problem statement** into SOLVER workflow via API
2. **SOLVER executes** Problem Definition -> Requirements -> Objectives
3. **Architect reviews** and approves each step artifact
4. **Approved artifacts** become input for AI coding agent implementation
5. **Implementation** proceeds with SOLVER-generated specifications
6. **Repeat** for next problem statement in sequence

### 8.2 Human Checkpoints

- **Per-step approval:** Architect reviews each artifact before advancement
- **Per-problem completion:** Architect validates complete output before implementation
- **Per-implementation review:** Architect reviews implementation against specifications

---

## 9. Relationship to Existing Specs

| Document | Relationship |
|----------|--------------|
| Technical Spec v2.8.4 | This roadmap extends beyond MVP scope defined there |
| Architectural Contract v3.4 | All extensions must comply with invariants |
| Development Directive v1.5.1 | New phases to be added for expansion work |
| DECISIONS.md | Expansion decisions to be recorded as they occur |

---

## 10. Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-01-07 | Ryan Tufts | Initial draft |
| 1.1 | 2025-01-07 | Ryan Tufts | Added methodology library architecture to PS1, Instance N hooks to PS3, new PS5 for UI |
