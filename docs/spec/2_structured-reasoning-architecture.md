# Structured Reasoning Workflow
## Technical Architecture Specification V2.2

---

## 1. Overview

This specification defines a structured reasoning process for producing high-quality solutions through systematic methodology development and execution.

### 1.1 Design Principles

1. **Methodology before execution** — Define how to solve before solving
2. **Iteration improves quality** — Refine through multiple passes
3. **Human judgment at gates** — Agent recommends, human decides
4. **Traceability** — Every output traces to its source
5. **Explicit contracts** — Inputs and outputs formally specified
6. **Externalized reasoning** — Methodology is inspectable, not hidden

### 1.2 Technology Stack

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND LAYER                                  │
│                    Next.js 14+ / Vercel AI SDK / assistant-ui               │
├─────────────────────────────────────────────────────────────────────────────┤
│                              API LAYER                                       │
│                         FastAPI (Python 3.11+)                              │
│                    SSE Streaming / REST Endpoints                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                          ORCHESTRATION LAYER                                 │
│                             LangGraph 1.0+                                   │
│              State Machine / Interrupt Gates / Checkpointing                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                          PERSISTENCE LAYER                                   │
│                    PostgreSQL + pgvector extension                          │
│            Checkpoints / Conversations / Audit Logs / Embeddings            │
├─────────────────────────────────────────────────────────────────────────────┤
│                         OBSERVABILITY LAYER                                  │
│                        LangSmith or Langfuse                                │
│                  Tracing / Debugging / Cost Tracking                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                              LLM LAYER                                       │
│                            Claude API                                        │
│                      Agent Reasoning / Generation                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Architecture

### 2.1 Instance Hierarchy (Three-Tier)

```
┌─────────────────────────────────────────────────────────────────┐
│  INSTANCE 0 (Universal Methodology)                             │
│  "The Constitution"                                             │
│  • Domain-agnostic, abstract                                    │
│  • Defines HOW to do structured reasoning                       │
│  • Created once, inherited by Instance 1                        │
│  • Epistemological level: meta-methodology                      │
├─────────────────────────────────────────────────────────────────┤
│                          ▼ inherits                             │
├─────────────────────────────────────────────────────────────────┤
│  INSTANCE 1 (Software Implementation)                           │
│  "The Institution"                                              │
│  • Implements Instance 0 as executable software                 │
│  • Adds technology-specific concerns (stack, integration)       │
│  • Created once, provides execution engine                      │
│  • Epistemological level: enforcement mechanism                 │
├─────────────────────────────────────────────────────────────────┤
│                          ▼ used by                              │
├─────────────────────────────────────────────────────────────────┤
│  INSTANCE N (Domain-Specific, N ≥ 2)                            │
│  "The Practice"                                                 │
│  • Uses Instance 1 software for specific problem domains        │
│  • Inherits Instance 0 methodology via Instance 1               │
│  • Adds domain-specific categories, validations, knowledge      │
│  • Produces actual solution artifacts                           │
│  • Epistemological level: substantive knowledge                 │
└─────────────────────────────────────────────────────────────────┘
```

**Conceptual Model:**

| Instance | Analogy | Role | Knowledge Type |
|----------|---------|------|----------------|
| 0 | Constitution | Defines the rules | Procedural (how) |
| 1 | Institution | Enforces the rules | Implementational (where) |
| N | Practice | Applies the rules | Substantive (what) |

**Instance Type Definitions:**

| Instance | Type | Purpose | Created |
|----------|------|---------|---------|
| 0 | Universal | Define abstract methodology | Once |
| 1 | Implementation | Build software system | Once |
| N (N≥2) | Domain | Solve specific problems | Per domain |

### 2.2 Two-Pass Execution

Each step executes in two passes:

| Pass | Name | Mode | Output | Gate |
|------|------|------|--------|------|
| 1 | Definition | Configurable | Methodology documents | Policy-based |
| 2 | Execution | Supervised | Step deliverables | Human approval required |

**Pass 1 Gate Policy:**

| Policy | Behavior | Use Case |
|--------|----------|----------|
| `none` | Fully autonomous, no gates | Batch processing, trusted methodology |
| `per_step` | Human approval after each step's V3 | Interactive development (default) |
| `end_of_pass` | Human approval after all 10 steps complete | Semi-automated pipeline |

Default: `per_step` in interactive mode, `end_of_pass` in batch mode.

**Pass Characteristics:**

| Aspect | Pass 1 (Definition) | Pass 2 (Execution) |
|--------|---------------------|---------------------|
| Autonomy | Per gate policy | Agent pauses at gate |
| Output | How to do (methodology) | What is done (deliverable) |
| Human role | Policy-dependent | Must approve (required) |
| Failure mode | Restart pass | Revise with feedback |

### 2.3 Ten-Step Workflow

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                         DEFINITION PHASE                                   ║
║                      "What are we solving?"                               ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Step 1:  Problem Definition   Define the problem, stakeholders,          ║
║                                constraints, scope                          ║
║  Step 2:  Requirements         Derive what the solution must do           ║
║  Step 3:  Objectives           Define success criteria and framework      ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                        VERIFICATION PHASE                                  ║
║                   "How will we know it works?"                            ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Step 4:  Verification Design  Plan internal correctness checks           ║
║                                (Does build match requirements?)            ║
║  Step 5:  Validation Design    Plan external fitness checks               ║
║                                (Does build solve the problem?)             ║
║  Step 6:  Evaluation Criteria  Define metrics for success measurement     ║
║  Step 7:  Assessment Protocol  Define measurement and reporting process   ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                         EXECUTION PHASE                                    ║
║                        "Build and learn"                                  ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Step 8:  Implementation       Build the solution                         ║
║  Step 9:  Reflection           Assess results against criteria            ║
║  Step 10: Resolution           Conclude with findings and recommendations ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

**Step Purposes:**

| Step | Question Answered | Primary Output |
|------|-------------------|----------------|
| 1 | What problem are we solving? | Problem Definition |
| 2 | What must the solution do? | Requirements |
| 3 | What does success look like? | Objectives |
| 4 | How do we check correctness? | Verification Plan |
| 5 | How do we check fitness? | Validation Plan |
| 6 | What metrics matter? | Evaluation Criteria |
| 7 | How do we measure and report? | Assessment Protocol |
| 8 | What is the solution? | Implementation |
| 9 | How did it perform? | Reflection Report |
| 10 | What do we conclude? | Resolution |

### 2.4 Step Artifact Types

Pass 2 produces a specific deliverable artifact for each step:

| Step | Artifact Name | Description | Key Contents |
|------|---------------|-------------|--------------|
| 1 | Problem Definition Package | Complete problem analysis | Stakeholders, constraints, scope, success criteria, assumptions |
| 2 | Requirements Package | Full requirements specification | FR, NFR, CR, IR with traceability |
| 3 | Objectives Package | Success framework | CAP, QUAL, COMP, INTF objectives with criteria |
| 4 | Verification Plan | Internal correctness strategy | Test cases, inspection checklists, requirement coverage matrix |
| 5 | Validation Plan | External fitness strategy | User acceptance criteria, fitness-for-purpose checks |
| 6 | Evaluation Criteria | Success metrics | Quantitative metrics, qualitative criteria, thresholds |
| 7 | Assessment Protocol | Measurement process | Data collection, analysis methods, reporting templates |
| 8 | Implementation Artifact | The solution itself | Code, documents, designs (respects "no external actions" constraint) |
| 9 | Reflection Report | Performance assessment | Results vs. criteria, lessons learned, gaps identified |
| 10 | Resolution Statement | Closure document | Findings, recommendations, closure confirmation |

**Step 8 Clarification:**

Implementation behavior depends on instance type:
- **Instance 0/1**: Produces implementation plans, specifications, code artifacts
- **Instance N**: May produce domain deliverables (documents, analyses, recommendations)

All external actions (API calls, file writes, deployments) require explicit human approval before execution. The Implementation step produces *artifacts*, not *side effects*.

---

## 3. Document System

### 3.1 Four Document Types

Pass 1 (Definition) produces four documents per step:

| Document | Purpose | Key Contents |
|----------|---------|--------------|
| **Data Sheet** | Define contracts | Input spec, output spec, schemas, validation rules |
| **To Do List** | Specify tasks | Phases, tasks, checkpoints, validation hooks |
| **Guidance** | Orient execution | Context, principles, anti-patterns, quality criteria |
| **Detailed Procedure** | Direct execution | State machine, algorithms, decision logic, gates |

### 3.2 Document Iteration (V1 → V2 → V3)

Documents are created and refined through three versions with explicit dependencies:

**V1 (Initial Creation):**
```
1. DATA SHEET V1
   Input: Step purpose + prior step output contract
   Creates: Input specification, output contract, schemas
   
2. TO DO LIST V1
   Considering: Data Sheet V1
   Creates: Phased tasks to transform input to output
   Why: Tasks must produce what Data Sheet promises
   
3. GUIDANCE V1
   Considering: Seed context + step purpose + constraints + Data Sheet V1 + To Do List V1
   Creates: Context, principles, anti-patterns
   Why: Guidance orients to the specific contract and tasks
   
4. DETAILED PROCEDURE V1
   Considering: Data Sheet V1 + To Do List V1 + Guidance V1
   Creates: State machine, algorithmic steps, gates
   Why: Procedure operationalizes all three prior documents
```

**V2 (First Refinement):**
```
1. DATA SHEET V2
   Considering: Detailed Proc V1 + Guidance V1 + To Do V1
   Refines: Schemas, validation rules based on procedure insights
   
2. TO DO LIST V2
   Considering: Data Sheet V2 + Guidance V1 + Detailed Proc V1
   Refines: Tasks based on updated contract and procedure
   
3. GUIDANCE V2
   Considering: Data Sheet V2 + To Do List V2 + Detailed Proc V1
   Refines: Principles based on emerging patterns
   
4. DETAILED PROCEDURE V2
   Considering: Data Sheet V2 + To Do List V2 + Guidance V2
   Refines: Algorithms, state machine, decision logic
```

**V3 (Final Refinement):**
```
Same pattern as V2, using V2 documents as input.
V3 documents are the authoritative methodology for Pass 2.
```

**Note:** References to "prior step output" are generalized. For Step 1, this is the user's problem description. For Steps 2-10, this is the approved Pass 2 artifact from the previous step.

### 3.3 Document Schemas

Each document type has a defined structure:

**DATA SHEET:**
```yaml
DataSheet:
  metadata:
    step: number
    version: V1 | V2 | V3
    
  input_specification:
    required_inputs: list
    validation_rules: list
    
  output_contract:
    fields: list
    cardinality: constraints
    
  schemas:
    input_schema: definition
    output_schema: definition
    
  validation_rules:
    - id: string
      rule: string
      severity: error | warning
      
  state_definitions:
    states: list
    transitions: list
```

**TO DO LIST:**
```yaml
ToDoList:
  metadata:
    step: number
    version: V1 | V2 | V3
    
  phases:
    - name: string
      entry_condition: string
      exit_condition: string
      tasks:
        - id: string
          description: string
          validation_hook: string | null
```

**GUIDANCE:**
```yaml
Guidance:
  metadata:
    step: number
    version: V1 | V2 | V3
    
  position:
    workflow_context: string
    inputs_from: list
    outputs_to: list
    
  principles:
    - name: string
      description: string
      rationale: string
      
  anti_patterns:
    - name: string
      symptom: string
      remedy: string
      
  quality_criteria:
    - criterion: string
      verification: string
```

**DETAILED PROCEDURE:**
```yaml
DetailedProcedure:
  metadata:
    step: number
    version: V1 | V2 | V3
    
  state_machine:
    states: list
    initial: string
    terminal: string
    transitions: list
    human_gates: list
    
  phases:
    - name: string
      entry_state: string
      exit_state: string
      procedure: string  # Algorithmic description
      
  decision_logic:
    - condition: string
      action: string
      
  human_protocol:
    gate_presentation: string
    available_actions: list
```

### 3.4 Requirement Categories

Step 2 produces requirements in four categories:

| Category | Prefix | Description | Derived From |
|----------|--------|-------------|--------------|
| Functional | FR | What the system does | Problem definition, stakeholder needs, scope |
| Non-Functional | NFR | Quality attributes | Stakeholder concerns, soft constraints |
| Constraint | CR | Non-negotiable limits | Hard constraints |
| Interface | IR | Component interactions | Integration points |

**Requirement Schema:**
```yaml
Requirement:
  id: string           # FR-001, NFR-001, CR-001, IR-001
  statement: string    # "The system shall..."
  category: FR | NFR | CR | IR
  priority: must | should | could
  source:
    type: string       # stakeholder, constraint, scope, integration
    id: string         # Source element ID
    aspect: string     # need, concern, item, point
  component: list      # Affected technology components
  rationale: string
  testability:
    method: demonstration | test | inspection | analysis
    description: string
```

**Priority Definitions:**

| Priority | Meaning | Consequence if Missing |
|----------|---------|------------------------|
| must | Non-negotiable | System fails |
| should | Expected | System disappoints |
| could | Nice to have | System adequate |

### 3.5 Objective Categories

Step 3 produces objectives in four categories:

| Category | Prefix | Description | Derived From |
|----------|--------|-------------|--------------|
| Capability | CAP | What is achieved functionally | Functional requirements |
| Quality | QUAL | Quality levels achieved | Non-functional requirements |
| Compliance | COMP | Constraints satisfied | Constraint requirements |
| Interface | INTF | Integrations working | Interface requirements |

**Objective Schema:**
```yaml
Objective:
  id: string           # CAP-001, QUAL-001, COMP-001, INTF-001
  statement: string    # "X is achieved"
  category: CAP | QUAL | COMP | INTF
  priority: primary | secondary | tertiary
  success_criteria:
    definition: string
    verification:
      method: demonstration | test | inspection | analysis
      description: string
      evidence: string
    metric: string | null
    threshold: string | null
  traces_to:
    requirements: list  # Requirement IDs
    consolidated: boolean
  component: list
```

### 3.6 Success Framework

Objectives are organized into a three-level success framework:

```
┌─────────────────────────────────────────────────────────────────┐
│  ASPIRATIONAL                                                    │
│  • All objectives (primary + secondary + tertiary)              │
│  • System exceeds expectations                                  │
│  • Maps to: all requirements                                    │
├─────────────────────────────────────────────────────────────────┤
│  TARGET                                                          │
│  • Primary + secondary objectives                               │
│  • System meets full expectations                               │
│  • Maps to: must + should requirements                          │
├─────────────────────────────────────────────────────────────────┤
│  MINIMUM VIABLE                                                  │
│  • Primary objectives only                                      │
│  • System is functional but basic                               │
│  • Maps to: must requirements                                   │
└─────────────────────────────────────────────────────────────────┘
```

**Framework Schema:**
```yaml
SuccessFramework:
  minimum_viable:
    description: "Must achieve for system to be viable"
    objectives: list[ObjectiveID]
    requirement_coverage: list[RequirementID]
    
  target:
    description: "Expected full success state"
    objectives: list[ObjectiveID]
    requirement_coverage: list[RequirementID]
    
  aspirational:
    description: "Exceeds expectations"
    objectives: list[ObjectiveID]
    requirement_coverage: list[RequirementID]
```

---

## 4. State Model

### 4.1 Workflow State

```yaml
WorkflowState:
  # Identifiers
  workflow_id: string          # Unique workflow identifier
  instance_id: string          # Parent instance identifier
  
  # Position
  current_pass: definition | execution
  current_step: 1..10
  
  # Accumulated outputs
  methodology: map[step → documents]    # Pass 1 outputs
  artifacts: map[step → deliverable]    # Pass 2 outputs
  
  # Instance relationship
  instance_type: universal | implementation | domain
  instance_number: 0 | 1 | N (N≥2)
  parent_instance_id: string | null     # null for Instance 0
  
  # Timestamps
  created_at: datetime
  updated_at: datetime
  
  # Actor tracking
  created_by: string           # User or system identifier
  last_actor_id: string        # Most recent actor
```

### 4.2 Step State

```yaml
StepState:
  step_number: 1..10
  pass_type: definition | execution
  
  # Coarse-grained status (external visibility / API consumers)
  status: not_started | in_progress | awaiting_clarification | awaiting_review | approved | revision_requested
  
  # Fine-grained phase (internal tracking)
  phase: received | analyzing | eliciting | structuring | validating | reviewing | complete
  
  # Content
  output: current output
  human_feedback: feedback if revision requested
  clarification_request: pending questions if awaiting_clarification
  
  # Conversation
  messages: list[Message]
  
  # Timestamps
  started_at: datetime | null
  completed_at: datetime | null
```

**Status Definitions (Coarse-Grained):**

| Status | Description | API Response Code | Human Action Required |
|--------|-------------|-------------------|----------------------|
| `not_started` | Step has not begun | 200 | No |
| `in_progress` | Agent is actively working | 200 | No |
| `awaiting_clarification` | Agent needs user input before proceeding | 202 | Yes (answer questions) |
| `awaiting_review` | Agent output ready for approval | 202 | Yes (approve/reject) |
| `approved` | Human approved, step complete | 200 | No |
| `revision_requested` | Human rejected, revision in progress | 200 | No |

**Phase Definitions (Fine-Grained):**

| Phase | Description | Maps to Status |
|-------|-------------|----------------|
| received | Input received, not yet processing | in_progress |
| analyzing | Parsing and understanding input | in_progress |
| eliciting | Waiting for clarification | awaiting_clarification |
| structuring | Building output structure | in_progress |
| validating | Checking output against rules | in_progress |
| reviewing | Awaiting human approval | awaiting_review |
| complete | Approved and finalized | approved |

### 4.3 State Transitions

```
Step Status Transitions:

  not_started ──────────────► in_progress
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
                    ▼                             ▼
         awaiting_clarification           awaiting_review ◄────┐
                    │                       /    │    \        │
                    │                      /     │     \       │ (message)
                    ▼                     ▼      ▼      ▼      │
              in_progress           approved  revision  ───────┘
                                              requested
                                                 │
                                                 ▼
                                            in_progress
```

**Transition Triggers:**

| From | To | Trigger |
|------|-----|---------|
| not_started | in_progress | Step execution begins |
| in_progress | awaiting_clarification | Sufficiency check fails, questions generated |
| awaiting_clarification | in_progress | User provides clarification (POST /clarify) |
| in_progress | awaiting_review | Output complete, validation passed |
| awaiting_review | approved | Human approves (POST /resume with approve) |
| awaiting_review | revision_requested | Human rejects (POST /resume with reject) |
| awaiting_review | awaiting_review | Human sends message (no state change) |
| revision_requested | in_progress | Agent begins revision |

**Message Action Clarification:**

The "Message" action allows conversation while remaining in the current state:
- If in `awaiting_review`: Message exchanges do not change approval state
- If in `in_progress`: Message exchanges continue work without requiring re-review
- Messages are recorded but do not trigger state transitions

**Phase State Machine:**
```
                                    ┌──────────────┐
                                    │   RECEIVED   │
                                    └──────┬───────┘
                                           │
                                           ▼
                                    ┌──────────────┐
                    ┌───────────────│  ANALYZING   │
                    │               └──────┬───────┘
                    │                      │
                    │         ┌────────────┴────────────┐
                    │         │                         │
                    │         ▼                         ▼
                    │  ┌──────────────┐         ┌──────────────┐
                    │  │  ELICITING   │         │  STRUCTURING │
                    │  │  (awaiting   │         └──────┬───────┘
                    │  │clarification)│                │
                    │  └──────┬───────┘                │
                    │         │                        ▼
                    │         │                 ┌──────────────┐
                    │         └────────────────►│  VALIDATING  │
                    │                           └──────┬───────┘
                    │                                  │
                    │                  ┌───────────────┼───────────────┐
                    │                  │ (fail)        │ (pass)        │
                    │                  ▼               ▼               │
                    │           ┌──────────────┐ ┌──────────────┐      │
                    │           │  STRUCTURING │ │  REVIEWING   │      │
                    │           └──────────────┘ │  (awaiting   │      │
                    │                            │    review)   │      │
                    │                            └──────┬───────┘      │
                    │                                   │              │
                    │                   ┌───────────────┼──────────────┤
                    │                   │               │              │
                    │                   ▼               ▼              ▼
                    │            ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
                    └───────────►│  STRUCTURING │ │  VALIDATING  │ │   COMPLETE   │
                                 │  (rejected)  │ │  (modified)  │ │  (approved)  │
                                 └──────────────┘ └──────────────┘ └──────────────┘
```

### 4.4 Validation Rules

Each step has validation rules that must pass before human review:

**Severity Levels:**

| Severity | Meaning | Action |
|----------|---------|--------|
| Error | Output is invalid | Must remediate before review |
| Warning | Output may have issues | Note in review, may proceed |

**Common Validation Patterns:**

| Pattern | Description | Example |
|---------|-------------|---------|
| Cardinality | Element count within range | "3-6 stakeholders required" |
| Coverage | All sources have derived elements | "Every FR must have a CAP" |
| Completeness | Required fields present | "All requirements have testability" |
| Consistency | No contradictions | "No duplicate requirement statements" |
| Traceability | All outputs trace to sources | "All objectives trace to requirements" |
| Typing | Correct types and formats | "All CR have priority = must" |

**Validation Execution:**
```
1. Validation executes automatically before REVIEWING state
2. All errors must be remediated (return to STRUCTURING)
3. Warnings are noted but do not block
4. Validation results presented with output at review
```

---

## 5. Human Interaction

### 5.1 Interaction Points

| Point | Type | Behavior |
|-------|------|----------|
| Pass 1 step completion | Policy-based | Per gate policy (none / per_step / end_of_pass) |
| Pass 2 step completion | Required gate | Must wait for explicit approval |
| Unclear input | Elicitation | Agent asks clarifying questions |
| Validation failure | Escalation | Agent presents issue for guidance |

**Pass 1 Gate Policy Configuration:**

```yaml
WorkflowConfig:
  pass_1_gate_policy: none | per_step | end_of_pass
  
  # Defaults by mode
  interactive_mode_default: per_step
  batch_mode_default: end_of_pass
```

### 5.2 Human Review Protocol

At each gate, the system executes a defined protocol:

**Step 1: PRESENTATION**

The system presents to the human:
- Step output (the deliverable)
- Methodology used (V3 documents)
- Traceability (source → output links)
- Validation results (errors, warnings)
- Coverage summary

**Step 2: ACTIONS OFFERED**

| Action | Effect | Required Input | Next State |
|--------|--------|----------------|------------|
| Approve | Advance to next step | None | COMPLETE |
| Reject | Return with feedback | Feedback text | STRUCTURING |
| Modify | Apply changes, revalidate | Specific modifications | VALIDATING |
| Message | Continue conversation | Message text | (no change) |

**Message Action Note:** The Message action allows the human to ask questions, request clarification, or discuss the output without changing the approval state. The system remains in REVIEWING until an Approve, Reject, or Modify action is taken.

**Step 3: WAIT**

System waits indefinitely for human response. No timeout.

**Step 4: PROCESS DECISION**

| Decision | System Response |
|----------|-----------------|
| Approve | Record approval, emit output, advance to next step |
| Reject | Incorporate feedback into context, re-execute, re-present |
| Modify | Apply modifications to output, re-validate, re-present |
| Message | Respond to message, remain in REVIEWING state |

### 5.3 Elicitation Protocol

When the agent encounters insufficient information:

**Step 1: SUFFICIENCY CHECK**
```
Evaluate:
  - Can the core output be produced?
  - Are critical gaps present?
  
If sufficient:
  - Proceed with assumptions documented
  - Do not elicit
  
If insufficient:
  - Proceed to elicitation
```

**Step 2: QUESTION FORMULATION**

| Constraint | Value |
|------------|-------|
| Maximum questions | 5 (prefer ≤3) |
| Question format | Question + Context + Impact if unresolved |

**Step 3: PRESENTATION**
```
Questions presented as batch:

"I need clarification on the following before proceeding:

1. [Question]
   Context: [Why this matters]
   If unresolved: [What will be assumed]

2. [Question]
   ...

You may answer all, some, or none. You may also direct me 
to proceed with assumptions."
```

**Step 4: PROCESSING**

| Response | Action |
|----------|--------|
| Question answered | Incorporate response |
| Question unanswered | Document assumption with rationale |
| "Proceed with assumptions" | Document all assumptions |

**Step 5: LIMITS**
```
- Maximum 3 elicitation rounds per step
- After limit: proceed with documented assumptions
- All assumptions recorded in output traceability
```

### 5.4 Assumption Documentation

When proceeding without complete information:

```yaml
Assumption:
  id: ASM-NNN
  statement: string           # What is assumed
  rationale: string           # Why this assumption was made
  elicitation_attempted: boolean
  risk_if_wrong: string       # Consequence if assumption is incorrect
  resolution_path: string     # How to resolve in future
```

---

## 6. Traceability

### 6.1 Traceability Chain

Every output element traces to its source via unique identifiers:

```
Step 1: Problem Definition
├── Stakeholders (SH-NNN)
│   ├── needs → FR
│   └── concerns → NFR
├── Hard Constraints (HC-NNN) → CR
├── Soft Constraints (SC-NNN) → NFR
├── Success Criteria (CRT-NNN) → acceptance criteria
├── Scope In (IN-NNN) → FR
├── Scope Out (OUT-NNN)
└── Integration Points (IP-NNN) → IR
         │
         ▼ derives
Step 2: Requirements
├── Functional (FR-NNN) → CAP
├── Non-Functional (NFR-NNN) → QUAL
├── Constraint (CR-NNN) → COMP
└── Interface (IR-NNN) → INTF
         │
         ▼ achieves
Step 3: Objectives
├── Capability (CAP-NNN)
├── Quality (QUAL-NNN)
├── Compliance (COMP-NNN)
└── Interface (INTF-NNN)
         │
         ├──► Step 4-7: Verification/Validation
         │
         └──► Step 8-10: Implementation/Assessment
```

### 6.2 Cross-Pass Traceability

```
Definition Pass                    Execution Pass
═══════════════                    ══════════════

Step N Methodology  ──guides──►   Step N Execution
(V3 Documents)                    (Deliverable)
```

### 6.3 Identifier Conventions

All traceable elements use standardized IDs:

| Step | Element | Format | Example |
|------|---------|--------|---------|
| 1 | Stakeholder | SH-NNN | SH-001 |
| 1 | Hard Constraint | HC-NNN | HC-001 |
| 1 | Soft Constraint | SC-NNN | SC-001 |
| 1 | Success Criterion | CRT-NNN | CRT-001 |
| 1 | Scope In | IN-NNN | IN-001 |
| 1 | Scope Out | OUT-NNN | OUT-001 |
| 1 | Integration Point | IP-NNN | IP-001 |
| 1 | Assumption | ASM-NNN | ASM-001 |
| 1 | Open Question | OQ-NNN | OQ-001 |
| 2 | Functional Req | FR-NNN | FR-001 |
| 2 | Non-Functional Req | NFR-NNN | NFR-001 |
| 2 | Constraint Req | CR-NNN | CR-001 |
| 2 | Interface Req | IR-NNN | IR-001 |
| 3 | Capability Obj | CAP-NNN | CAP-001 |
| 3 | Quality Obj | QUAL-NNN | QUAL-001 |
| 3 | Compliance Obj | COMP-NNN | COMP-001 |
| 3 | Interface Obj | INTF-NNN | INTF-001 |

**ID Rules:**
- IDs are unique within their category
- NNN is zero-padded three digits (001, 002, ...)
- Cross-references use full ID (e.g., traces_to: [FR-001, FR-002])
- Instance prefix optional: I1-FR-001 (Instance 1, FR-001)

### 6.4 Traceability Requirements

| Requirement | Description |
|-------------|-------------|
| Every output has source | All derived elements have traces_to with ≥1 source ID |
| Bidirectional | Forward (source→derived) and backward (derived→source) queryable |
| 100% coverage | Every source element has ≥1 derived element |
| Preservation | Consolidation preserves all source IDs |

### 6.5 Consolidation

When deriving elements, multiple sources may map to one derived element:

```
Example:
  FR-001, FR-002, FR-003 (three requirements)
       ↓ consolidate
  CAP-001 (one objective)
  
  CAP-001.traces_to = [FR-001, FR-002, FR-003]
  CAP-001.consolidated = true
```

**Consolidation Rules:**

| Rule | Description |
|------|-------------|
| Shared success | Only consolidate when sources share a single success condition |
| Preserve IDs | All source IDs must appear in traces_to |
| Mark consolidated | Set consolidated = true |
| Priority escalation | Use highest priority among sources |
| No obscuration | Do not consolidate if traceability would become unclear |

**Consolidation Ratio:**
```
ratio = source_count / derived_count
Typical range: 1.2 to 2.0 (mild consolidation expected)
Below 1.0: Invalid (derived exceeds sources without justification)
Above 3.0: Possible over-consolidation (review)
```

---

## 7. Persistence (PostgreSQL)

### 7.1 Storage Requirements

| Data | Storage | Purpose |
|------|---------|---------|
| Workflow state | PostgreSQL | Track current position and status |
| Checkpoints | PostgreSQL (LangGraph) | Enable recovery from any point |
| Messages | PostgreSQL | Preserve conversation context |
| Documents | PostgreSQL (JSONB) | Store methodology and artifacts |
| Audit log | PostgreSQL | Record all state transitions |
| Embeddings | pgvector | Semantic search over messages |
| Traceability | PostgreSQL | Store forward/backward links |

### 7.2 Minimum Schema Commitments

The following tables represent the minimum schema required for recoverability and audit:

**Core Tables:**

```sql
-- Workflow tracking
workflows (
  workflow_id         UUID PRIMARY KEY,
  instance_id         UUID NOT NULL,
  instance_type       VARCHAR(20) NOT NULL,  -- universal, implementation, domain
  instance_number     INTEGER NOT NULL,
  parent_instance_id  UUID,
  current_step        INTEGER NOT NULL,
  current_pass        VARCHAR(20) NOT NULL,  -- definition, execution
  status              VARCHAR(20) NOT NULL,
  created_at          TIMESTAMP NOT NULL,
  updated_at          TIMESTAMP NOT NULL,
  created_by          VARCHAR(100) NOT NULL,
  last_actor_id       VARCHAR(100) NOT NULL
)

-- Step state tracking
steps (
  workflow_id         UUID NOT NULL,
  step_number         INTEGER NOT NULL,
  pass_type           VARCHAR(20) NOT NULL,
  status              VARCHAR(30) NOT NULL,  -- includes awaiting_clarification
  phase               VARCHAR(20) NOT NULL,
  started_at          TIMESTAMP,
  completed_at        TIMESTAMP,
  PRIMARY KEY (workflow_id, step_number, pass_type)
)

-- Artifacts (methodology documents and deliverables)
artifacts (
  artifact_id         UUID PRIMARY KEY,
  workflow_id         UUID NOT NULL,
  step_number         INTEGER NOT NULL,
  pass_type           VARCHAR(20) NOT NULL,
  artifact_type       VARCHAR(50) NOT NULL,  -- data_sheet, todo_list, etc.
  version             VARCHAR(10),           -- V1, V2, V3 for methodology
  content             JSONB NOT NULL,
  validation_status   VARCHAR(20),
  created_at          TIMESTAMP NOT NULL,
  updated_at          TIMESTAMP NOT NULL
)

-- Audit trail
audit_events (
  event_id            UUID PRIMARY KEY,
  workflow_id         UUID NOT NULL,
  step_number         INTEGER,
  actor_id            VARCHAR(100) NOT NULL,
  event_type          VARCHAR(50) NOT NULL,
  from_state          VARCHAR(20),
  to_state            VARCHAR(20),
  details             JSONB,
  created_at          TIMESTAMP NOT NULL
)

-- LangGraph checkpoint mapping
checkpoints (
  thread_id           VARCHAR(100) PRIMARY KEY,
  workflow_id         UUID NOT NULL,
  checkpoint_data     BYTEA,                 -- Or reference to checkpoint store
  created_at          TIMESTAMP NOT NULL
)

-- Conversation messages
messages (
  message_id          UUID PRIMARY KEY,
  workflow_id         UUID NOT NULL,
  step_number         INTEGER NOT NULL,
  role                VARCHAR(20) NOT NULL,  -- user, assistant, system
  content             TEXT NOT NULL,
  created_at          TIMESTAMP NOT NULL
)

-- Embeddings for semantic search
embeddings (
  embedding_id        UUID PRIMARY KEY,
  source_type         VARCHAR(50) NOT NULL,  -- message, artifact
  source_id           UUID NOT NULL,
  embedding           VECTOR(1536),          -- Adjust dimension as needed
  created_at          TIMESTAMP NOT NULL
)
```

**Indexes (minimum required):**
```sql
CREATE INDEX idx_workflows_instance ON workflows(instance_id);
CREATE INDEX idx_steps_workflow ON steps(workflow_id);
CREATE INDEX idx_artifacts_workflow_step ON artifacts(workflow_id, step_number);
CREATE INDEX idx_audit_workflow ON audit_events(workflow_id);
CREATE INDEX idx_messages_workflow_step ON messages(workflow_id, step_number);
```

### 7.3 Recovery Guarantees

- LangGraph checkpointing enables recovery from any point
- No work loss on failure
- Full state restoration including conversation history
- Recovery time target: ≤ 5 seconds

---

## 8. Execution Protocol

### 8.1 Workflow Initialization

```
1. Receive problem description via FastAPI endpoint
2. Determine instance type:
   - Instance 0: No parent, universal methodology
   - Instance 1: Parent = Instance 0, implementation focus
   - Instance N: Uses Instance 1 software, domain focus
3. Create workflow in PostgreSQL with initial state:
   - workflow_id = new UUID
   - instance_id = assigned or inherited
   - current_pass = definition
   - current_step = 1 (Problem Definition)
   - status = not_started
   - phase = received
   - created_at = now()
   - created_by = actor_id
4. Initialize LangGraph with thread_id
5. Load seed material based on instance type:
   a. If Instance 0: 
      - No seed (bootstrap)
   b. If Instance 1: 
      - Load Instance 0 V3 Methodology (the "How")
   c. If Instance N:
      - Load Instance 0 V3 Methodology via Instance 1 (the "How")
      - Ingest User's Problem Context (the "What")
      - Combine as seed for Step 1, Pass 1
6. Record initialization in audit_events
```

**Instance N Seeding Detail:**

Instance N workflows require BOTH methodology (how to solve) AND problem context (what to solve):

```yaml
InstanceNSeed:
  methodology:
    source: Instance 0 V3 (via Instance 1)
    content: All 10 steps' Data Sheet, To Do List, Guidance, Detailed Procedure
    purpose: Defines HOW to execute each step
    
  problem_context:
    source: User input
    content: Problem description, domain constraints, success criteria
    purpose: Defines WHAT problem to solve
    
  combination:
    step_1_input: problem_context
    step_1_methodology: methodology.step_1
    result: Agent knows both WHAT to solve and HOW to solve it
```

### 8.2 Step Execution (LangGraph)

```
For each step:

  Pass 1 (Definition):
    1. Check gate policy:
       - If policy = none: proceed without gates
       - If policy = per_step: gate after V3 completion
       - If policy = end_of_pass: gate only after Step 10 Pass 1
    2. LangGraph executes (with or without interrupt per policy)
    3. Generate methodology documents (V1 → V2 → V3)
    4. Store methodology in PostgreSQL
    5. Checkpoint state
    6. If gate required: present for review, wait for approval
    7. If no gate or approved: proceed to next step
  
  Pass 2 (Execution):
    1. Load V3 methodology from Pass 1
    2. Set phase = received, status = in_progress
    3. Execute per Detailed Procedure V3:
       a. RECEIVED → ANALYZING: Parse and validate input
       b. ANALYZING: Perform sufficiency check
          - If sufficient: → STRUCTURING
          - If insufficient: → ELICITING (status = awaiting_clarification)
       c. ELICITING: Wait for user clarification
          - LangGraph raises Interrupt exception (suspends execution)
          - API returns 202 Accepted with status awaiting_clarification
          - System waits for POST /clarify with user answers
          - LangGraph resumes with clarification → STRUCTURING
       d. STRUCTURING → VALIDATING: Build output
       e. VALIDATING:
          - If pass: → REVIEWING
          - If fail: → STRUCTURING (remediate errors)
       f. REVIEWING: Human approval gate
          - LangGraph raises Interrupt exception (suspends execution)
          - API returns 202 Accepted with status awaiting_review
          - System waits for POST /resume with human decision
          - Decision processing:
            * approve: LangGraph resumes → COMPLETE
            * reject: LangGraph resumes with feedback → STRUCTURING
            * modify: Apply changes → VALIDATING
    4. On COMPLETE: store artifact, advance to next step
```

**LangGraph Interrupt/Resume Protocol:**

```python
# At any gate (clarification or review):

# 1. Agent reaches gate
raise Interrupt(
    gate_type="clarification" | "review",
    payload={
        "questions": [...],      # For clarification
        "output": {...},         # For review
        "validation": {...}
    }
)

# 2. API handles interrupt
@app.post("/workflow/{workflow_id}/clarify")
async def handle_clarification(workflow_id: str, answers: ClarificationAnswers):
    # Update state with answers
    await graph.update_state(thread_id, {"clarification": answers})
    # Resume graph execution
    return await graph.ainvoke(None, config={"thread_id": thread_id})

@app.post("/workflow/{workflow_id}/resume")
async def handle_resume(workflow_id: str, decision: HumanDecision):
    # Update state with decision
    await graph.update_state(thread_id, {"human_decision": decision})
    # Resume graph execution  
    return await graph.ainvoke(None, config={"thread_id": thread_id})

# 3. Response codes
# - 202 Accepted: Workflow suspended at gate, waiting for input
# - 200 OK: Workflow advanced, here's the new state
# - 409 Conflict: Invalid state transition attempted
```

### 8.3 Completion Criteria

**Pass 1 Complete:**
```
- All 10 steps have V3 methodology documents
- Gate policy satisfied:
  - If none: automatic
  - If per_step: each step approved
  - If end_of_pass: final approval received
```

**Pass 2 Complete:**
```
- Each step has approved deliverable artifact
- Human approval received for each step
- Validation rules passed for each step
- Traceability chain intact
```

**Workflow Complete:**
```
- Pass 2 Step 10 Resolution approved, OR
- Workflow explicitly abandoned by human

Abandonment requires:
  - Explicit human action (not timeout)
  - Recorded in audit_events
  - State preserved for potential resumption
```

**Step Complete:**
```
- Pass 2 output approved by human
- Validation rules passed
- Traceability chain intact
- Artifact stored in PostgreSQL
- Audit event recorded
```

---

## 9. Integration Points

### 9.1 Layer Responsibilities

| Layer | Technology | Responsibility |
|-------|------------|----------------|
| Frontend | Next.js + assistant-ui | User interface, streaming display |
| API | FastAPI | REST endpoints, SSE streaming, request handling |
| Orchestration | LangGraph | State machine, interrupt gates, step sequencing |
| Persistence | PostgreSQL + pgvector | Checkpoints, messages, audit, embeddings |
| Observability | LangSmith/Langfuse | Tracing, debugging, cost tracking |
| LLM | Claude API | Agent reasoning and generation |

### 9.2 Interface Specifications

| Interface | From | To | Protocol | Data |
|-----------|------|-----|----------|------|
| IP-001 | Frontend | API | REST | Workflow commands, decisions |
| IP-002 | API | Frontend | SSE | Streaming responses, state updates |
| IP-003 | API | LangGraph | Python API | Graph invocation, interrupts |
| IP-004 | LangGraph | PostgreSQL | PostgresSaver | Checkpoints, state |
| IP-005 | LangGraph | Claude | Claude API | Prompts, completions |
| IP-006 | System | Observability | SDK | Traces, metrics |

### 9.3 SSE Event Types

The SSE stream (IP-002) delivers typed events to the frontend:

| Event Type | Purpose | Payload | Frontend Action |
|------------|---------|---------|-----------------|
| `text_delta` | LLM token streaming | `{ "delta": "..." }` | Append to response display |
| `status_update` | Workflow state change | `{ "status": "...", "phase": "...", "step": N }` | Update progress indicator |
| `interrupt` | Gate activation | `{ "type": "clarification" \| "review", "payload": {...} }` | Show gate UI |
| `error` | Error occurred | `{ "code": "...", "message": "..." }` | Display error |
| `complete` | Step/workflow complete | `{ "artifact_id": "..." }` | Show completion, enable next action |

**SSE Message Format:**

```
event: text_delta
data: {"delta": "The system shall"}

event: text_delta  
data: {"delta": " provide..."}

event: status_update
data: {"status": "in_progress", "phase": "structuring", "step": 2}

event: interrupt
data: {"type": "review", "payload": {"output": {...}, "validation": {...}}}
```

**Frontend Handling:**

```typescript
const eventSource = new EventSource(`/workflow/${workflowId}/stream`);

eventSource.addEventListener('text_delta', (e) => {
  const { delta } = JSON.parse(e.data);
  appendToResponse(delta);
});

eventSource.addEventListener('status_update', (e) => {
  const { status, phase, step } = JSON.parse(e.data);
  updateProgressIndicator(status, phase, step);
});

eventSource.addEventListener('interrupt', (e) => {
  const { type, payload } = JSON.parse(e.data);
  if (type === 'clarification') {
    showClarificationDialog(payload.questions);
  } else if (type === 'review') {
    showReviewDialog(payload.output, payload.validation);
  }
});
```

### 9.4 Event Flow

```
Frontend (Next.js)
    │
    ▼
API Layer (FastAPI) ──────► PostgreSQL (checkpoint)
    │
    ▼
Orchestration (LangGraph) ──► Claude API
    │
    ▼
Response ───────► PostgreSQL (state sync)
    │
    ▼
SSE Stream ──► Frontend
    │
    ▼
Human Review ──► API (POST /resume) ──► LangGraph (resume from Interrupt)
```

### 9.5 LangGraph Integration

- PostgresSaver for checkpoint persistence
- Interrupt gates at Pass 2 step boundaries
- Configurable gates at Pass 1 step boundaries
- State machine manages step/pass transitions
- Human input resumes graph execution via `graph.update_state()` + `graph.ainvoke()`
- Automatic checkpointing at defined points

---

## 10. Constraints

### 10.1 Behavioral Constraints

| ID | Constraint | Consequence if Violated |
|----|------------|------------------------|
| BC-001 | Pass 2 must not advance without human approval | Human oversight bypassed |
| BC-002 | Agent must not take external actions without approval | Unauthorized side effects |
| BC-003 | All decision-relevant rationale must be externalized as reviewable justification and traceability, not hidden in model state | Audit impossible, trust undermined |
| BC-004 | LangGraph interrupts must be honored immediately | Gate enforcement broken |
| BC-005 | All outputs must be traceable to sources | Audit trail broken |

**BC-003 Clarification:**

"Externalized rationale" means:
- Structured justification in output documents
- Trace links connecting outputs to sources
- Evidence artifacts supporting claims
- Decision logs explaining choices

This does NOT require:
- Exposure of raw chain-of-thought
- Access to internal model activations
- Real-time visibility into inference

The system is designed for stateless LLM interaction; reasoning is made auditable through persistent, reviewable artifacts rather than model introspection.

### 10.2 State Constraints

| ID | Constraint | Consequence if Violated |
|----|------------|------------------------|
| SC-001 | LangGraph checkpoints must be recoverable | Work loss on failure |
| SC-002 | No state stored in LLM (stateless agent) | Inconsistent behavior |
| SC-003 | Instance isolation (no cross-instance state access) | Data leakage |
| SC-004 | Traceability chain must be intact | Audit failure |

### 10.3 Technology Constraints

| ID | Constraint | Rationale |
|----|------------|-----------|
| TC-001 | Next.js 14+ for frontend | App Router, React Server Components |
| TC-002 | FastAPI for API | Async support, OpenAPI generation |
| TC-003 | LangGraph 1.0+ for orchestration | Checkpointing, interrupt support |
| TC-004 | PostgreSQL for persistence | JSONB, pgvector, PostgresSaver |
| TC-005 | Claude API for LLM | Agent reasoning capability |

---

## 11. Extension Mechanism

### 11.1 Instance Pack Structure

Domain-specific instances (Instance N, N≥2) are packaged as "Instance Packs":

```yaml
InstancePack:
  manifest:
    name: string              # e.g., "healthcare-clinical-trials"
    version: string           # Semantic version
    description: string
    core_schema_version: string  # Compatible architecture version
    parent_instance: 0 | 1    # What this extends
    
  schemas:
    step_1_extensions: object  # Additional fields for Problem Definition
    step_2_extensions: object  # Additional requirement categories
    step_3_extensions: object  # Additional objective categories
    # ... steps 4-10
    
  validations:
    custom_rules: list        # Domain-specific validation rules
    
  templates:
    methodology_seeds: map    # Pre-built methodology for common patterns
```

### 11.2 Extension Points

| Extension Point | Location | Purpose |
|-----------------|----------|---------|
| Schema extensions | Per-step | Add domain-specific fields |
| Validation rules | Per-step | Add domain-specific checks |
| Methodology seeds | Per-step | Pre-built document templates |
| Category extensions | Steps 2, 3 | Add domain requirement/objective types |
| Success criteria | Step 3 | Domain-specific success definitions |

### 11.3 Loading Process

```
1. Validate manifest:
   - Check core_schema_version compatibility
   - Verify parent_instance exists
   
2. Merge schemas:
   - Base schemas from Instance 0/1
   - Extension schemas from pack
   - Validate no conflicts
   
3. Register validations:
   - Load custom validation rules
   - Merge with base validation rules
   
4. Load templates:
   - Methodology seeds available for Pass 1
   - May be used or overridden
   
5. Initialize Instance N workflow:
   - Apply merged configuration
   - Record instance_pack_id in workflow
```

### 11.4 Compatibility Rules

| Rule | Description |
|------|-------------|
| Additive only | Extensions may add fields, not remove base fields |
| Optional fields | Extended fields should be optional to preserve base compatibility |
| Version pinning | Pack must specify compatible core_schema_version |
| Backward compatible | Newer packs should handle workflows from older packs |

---

## 12. Schema Registry

### 12.1 Purpose

The Schema Registry provides centralized management of step schemas, enabling:
- Validation of step inputs and outputs
- Schema evolution with versioning
- Deterministic behavior across instances

### 12.2 Registry Structure

```
/schemas
├── core/
│   ├── v1.0/
│   │   ├── step_1_problem_definition.json
│   │   ├── step_2_requirements.json
│   │   ├── step_3_objectives.json
│   │   └── ... (steps 4-10)
│   └── v1.1/
│       └── ... (updated schemas)
├── extensions/
│   └── {instance_pack_name}/
│       └── v1.0/
│           └── ... (extension schemas)
└── registry.yaml
```

### 12.3 Registry Manifest

```yaml
SchemaRegistry:
  current_version: "1.0"
  
  core_schemas:
    - step: 1
      name: "Problem Definition"
      schema_file: "step_1_problem_definition.json"
      validation_mode: strict | lenient
      
    - step: 2
      name: "Requirements"
      schema_file: "step_2_requirements.json"
      validation_mode: strict
      
    # ... steps 3-10
    
  extension_schemas:
    - pack_name: string
      pack_version: string
      schemas: list
```

### 12.4 Validation Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| `strict` | Reject any schema violations | Production, audit-critical |
| `lenient` | Log violations, allow processing | Development, exploration |
| `off` | No validation | Testing only |

### 12.5 Schema Evolution

| Change Type | Compatibility | Process |
|-------------|---------------|---------|
| Add optional field | Backward compatible | Minor version bump |
| Add required field | Breaking | Major version bump + migration |
| Remove field | Breaking | Major version bump + migration |
| Change field type | Breaking | Major version bump + migration |

**Migration Process:**
```
1. Define new schema version
2. Create migration script (old → new)
3. Test migration on sample workflows
4. Deploy new schema
5. Migrate existing workflows (if needed)
6. Deprecate old schema (after grace period)
```

---

## 13. Appendix: Quick Reference

### 13.1 ID Format Summary

```
Step 1: SH-NNN, HC-NNN, SC-NNN, CRT-NNN, IN-NNN, OUT-NNN, IP-NNN, ASM-NNN, OQ-NNN
Step 2: FR-NNN, NFR-NNN, CR-NNN, IR-NNN
Step 3: CAP-NNN, QUAL-NNN, COMP-NNN, INTF-NNN
```

### 13.2 Priority Mapping

```
Requirement Priority  →  Objective Priority  →  Framework Level
─────────────────────────────────────────────────────────────────
must                  →  primary             →  Minimum Viable
should                →  secondary           →  Target
could                 →  tertiary            →  Aspirational
```

### 13.3 Status and Phase Mapping

```
Status (External)              Phase (Internal)
─────────────────────────────────────────────────
not_started                    (n/a)
in_progress                    received, analyzing, structuring, validating
awaiting_clarification         eliciting
awaiting_review                reviewing
approved                       complete
revision_requested             (transitions to in_progress)
```

### 13.4 Phase Flow

```
RECEIVED → ANALYZING → [ELICITING] → STRUCTURING → VALIDATING → REVIEWING → COMPLETE
                           ↑                            │
                           └────────────────────────────┘ (validation failure)
```

### 13.5 Document Versions

```
V1: Initial creation (forward dependencies only)
V2: First refinement (cross-document feedback)
V3: Final refinement (authoritative for Pass 2)
```

### 13.6 Pass 1 Gate Policies

```
none:        No gates, fully autonomous
per_step:    Gate after each step's V3 (default interactive)
end_of_pass: Gate only after all 10 steps complete
```

### 13.7 Instance Types

```
Instance 0:  Universal       "Constitution"   Meta-methodology
Instance 1:  Implementation  "Institution"    Enforcement mechanism  
Instance N:  Domain          "Practice"       Substantive knowledge
```

### 13.8 API Endpoints Summary

```
POST   /workflow                    Create new workflow
GET    /workflow/{id}               Get workflow state
POST   /workflow/{id}/clarify       Submit clarification answers
POST   /workflow/{id}/resume        Submit human decision (approve/reject/modify)
GET    /workflow/{id}/stream        SSE stream for real-time updates
DELETE /workflow/{id}               Abandon workflow
```

### 13.9 SSE Event Types

```
text_delta:     LLM token streaming
status_update:  Workflow state change
interrupt:      Gate activation (clarification or review)
error:          Error occurred
complete:       Step or workflow complete
```

---

*This specification defines the process architecture implemented with Next.js, FastAPI, LangGraph, PostgreSQL, and LangSmith/Langfuse.*

*Version 2.2 — Adds implementation-precision details: awaiting_clarification status, LangGraph interrupt/resume protocol, SSE event types, Instance N seeding with user context.*
