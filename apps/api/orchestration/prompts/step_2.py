"""
SOLVER API - Step 2 Prompts (Requirements)

Prompts for Requirements step per Doc 1 Step 2 and Doc 3 §5.2.
Produces RequirementsPackage with Doc 3-aligned field names.
Includes IR (Interface Requirements) as optional category.
"""

from .common import considering_header, get_considering_refs


# =============================================================================
# System Prompt (Shared across all Step 2 prompts)
# =============================================================================


SYSTEM_PROMPT_STEP_2 = """You are a methodology architect for SOLVER, a Structured Reasoning Workflow Engine.

You are working on Instance {instance_number}: {domain}

Your task is to create methodology documents for Step 2: Requirements.

Step 2 transforms the approved ProblemDefinitionPackage from Step 1 into a structured
RequirementsPackage that feeds into Step 3 (Objectives).

KEY PRINCIPLES:
1. Derivation, Not Invention: Requirements derive from Step 1 elements. Every requirement
   must trace to stakeholders, constraints, scope items, or success criteria.
2. Category Precision: FR (Functional), NFR (Non-Functional), CR (Constraint),
   IR (Interface - optional). Each has distinct derivation patterns.
3. Priority Rigor: must/should/could based on source priority and impact.
4. Testability: Every requirement must have a verification method.
5. Coverage: Every Step 1 element must map to at least one requirement.

REQUIREMENT CATEGORIES:
- FR (Functional): What the system must DO (capabilities, behaviors)
- NFR (Non-Functional): How well the system must perform (quality attributes)
- CR (Constraint): Limits and boundaries from hard constraints
- IR (Interface): Requirements from integration points (optional - empty if none)

OUTPUT FORMAT:
- Follow the exact structure specified in the prompt
- Use markdown formatting for readability
- Include all required sections
"""


# =============================================================================
# Pass 1: V1 Prompts (Initial Creation)
# =============================================================================


V1_DATA_SHEET_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_2,
    "user": """Create the Data Sheet V1 for Step 2: Requirements.

{considering}

## Step 1 Output (ProblemDefinitionPackage)
{prior_step_output}

---

Generate the Data Sheet V1 with the following structure:

### Step Purpose
Derive structured requirements from the approved ProblemDefinitionPackage,
ensuring complete coverage and traceability.

### Input Specification
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| problem_definition_package | ProblemDefinitionPackage | Yes | Approved Step 1 output |
| step_1_approval | approval_record | Yes | Human approval confirmation |

### Input Validation Gate
Before processing, verify:
- Step 1 status = COMPLETE
- Human approval present
- All required ProblemDefinitionPackage fields present

### Derivation Patterns
| Source Type | Source Element | Derivation Pattern | Category | Priority |
|-------------|----------------|-------------------|----------|----------|
| Core Problem | statement | Problem → Capability needed | FR | must |
| Stakeholder | needs[] | Need → What satisfies it | FR/NFR | must/should |
| Stakeholder | concerns[] | Concern → What mitigates it | NFR | should |
| Hard Constraint | statement | Constraint → CR directly | CR | must |
| Soft Constraint | statement | Preference → FR/NFR | FR/NFR | should/could |
| Success Criterion | metric_or_signal | Criterion → Verification need | FR/NFR | must/should |
| Scope In | item | In-scope item → Capability | FR | should |
| Integration Point | description | Integration need → IR | IR | should |

### Output Specification (RequirementsPackage per Doc 3 §5.2)
```yaml
RequirementsPackage:
  overview:
    summary: string
    boundaries: [string]
    total_requirements: integer
    priority_distribution:
      must: integer
      should: integer
      could: integer

  requirements:
    - id: string                  # FR-001, NFR-001, CR-001, IR-001
      category: FR | NFR | CR | IR
      priority: must | should | could
      statement: string
      rationale: string

      source:
        type: stakeholder | constraint | scope | success_criterion | integration_point
        id: string                # SH-001, HC-001, etc.
        aspect: string            # need, concern, item, etc.

      component: [string]         # Affected components

      testability:
        method: demonstration | test | inspection | analysis
        description: string

      trace:
        stakeholders: [string]    # SH-xxx IDs
        constraints: [string]     # HC-xxx, SC-xxx IDs
        scope_in: [string]        # IN-xxx IDs
        success_criteria: [string] # CRT-xxx IDs
        integration_points: [string] # IP-xxx IDs (for IR)

  coverage_map:
    - source_type: string         # stakeholder, constraint, etc.
      source_id: string           # SH-001, HC-001, etc.
      requirement_ids: [string]   # FR-001, NFR-002, etc.
      coverage_note: string

  conflicts_tradeoffs:
    - conflict: string
      impacted_requirement_ids: [string]
      proposed_resolution: string

  open_questions:
    required_to_finalize: [string]
    deferred: [string]

  step3_handoff:
    objective_mapping_rules: [string]
    objective_seeds:
      primary_from_must: [string]
      secondary_from_should: [string]
      tertiary_from_could: [string]
```

### Validation Rules
| Rule ID | Field | Rule | Severity |
|---------|-------|------|----------|
| V1 | requirements | Count ≥ 1 | Error |
| V2 | requirements[].id | Format: (FR|NFR|CR|IR)-NNN | Error |
| V3 | requirements[].source.id | Must exist in Step 1 | Error |
| V4 | coverage_map | All Step 1 elements covered | Warning |
| V5 | priority_distribution | must + should + could = total | Error |
| V6 | requirements[].testability | Method specified | Error |

### State Definitions
| State | Entry Condition | Valid Transitions |
|-------|-----------------|-------------------|
| RECEIVED | Input logged | → ANALYZING |
| ANALYZING | Begin processing | → DERIVING |
| DERIVING | Analysis complete | → VALIDATING |
| VALIDATING | Derivation complete | → REVIEWING, → DERIVING |
| REVIEWING | Validation passed | → COMPLETE, → DERIVING |
| COMPLETE | Human approved | (terminal) |
""",
}


V1_TODO_LIST_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_2,
    "user": """Create the To Do List V1 for Step 2: Requirements.

{considering}

## Data Sheet V1
{current_data_sheet}

---

Generate the To Do List V1 as a phased checklist:

#### 1. Reception [RECEIVED → ANALYZING]
- [ ] Receive ProblemDefinitionPackage from Step 1
- [ ] Verify Step 1 status = COMPLETE
- [ ] Verify human approval present
- [ ] Initialize RequirementsPackage structure
- [ ] Set state: ANALYZING
- **Validation:** Input validated, structure initialized

#### 2. Analysis [ANALYZING → DERIVING]
- [ ] Parse ProblemDefinitionPackage:
  - [ ] Extract stakeholders (SH-xxx) with needs and concerns
  - [ ] Extract constraints (HC-xxx, SC-xxx)
  - [ ] Extract scope items (IN-xxx)
  - [ ] Extract success criteria (CRT-xxx)
  - [ ] Extract integration points (IP-xxx)
- [ ] Build derivation queue
- [ ] Set state: DERIVING
- **Validation:** All source elements catalogued

#### 3. Derivation [DERIVING]
For each source element, apply derivation patterns:

##### 3.1 Core Problem → FR
- [ ] Derive capability requirements from core problem
- [ ] Assign FR-NNN IDs, priority: must
- [ ] Record source and trace

##### 3.2 Stakeholder Needs → FR/NFR
- [ ] For each stakeholder.needs[]:
  - [ ] Derive requirement (what satisfies the need)
  - [ ] Classify as FR or NFR
  - [ ] Assign priority based on stakeholder impact
- **Validation:** All needs addressed

##### 3.3 Stakeholder Concerns → NFR
- [ ] For each stakeholder.concerns[]:
  - [ ] Derive quality/mitigation requirement
  - [ ] Classify as NFR
  - [ ] Assign priority: should
- **Validation:** All concerns addressed

##### 3.4 Hard Constraints → CR
- [ ] For each constraint.hard[]:
  - [ ] Create CR directly from constraint
  - [ ] Assign CR-NNN ID, priority: must
- **Validation:** All hard constraints captured

##### 3.5 Soft Constraints → FR/NFR
- [ ] For each constraint.soft[]:
  - [ ] Derive preference requirement
  - [ ] Classify as FR or NFR
  - [ ] Assign priority: should/could
- **Validation:** All soft constraints addressed

##### 3.6 Success Criteria → FR/NFR
- [ ] For each success_criteria[]:
  - [ ] Derive verification requirement
  - [ ] Ensure testability specified
- **Validation:** All success criteria traceable

##### 3.7 Integration Points → IR (Optional)
- [ ] For each integration_point[]:
  - [ ] Derive interface requirement
  - [ ] Assign IR-NNN ID
  - [ ] Note: IR list may be empty if no integration points
- **Validation:** All integration points addressed (if any)

#### 4. Coverage Mapping [DERIVING]
- [ ] For each Step 1 source element:
  - [ ] List requirement IDs that address it
  - [ ] Add coverage note
- [ ] Verify no orphan elements
- **Validation:** V4 (coverage check)

#### 5. Conflict Resolution [DERIVING]
- [ ] Identify conflicting requirements
- [ ] Document tradeoffs
- [ ] Propose resolutions
- **Validation:** Conflicts documented

#### 6. Validation [VALIDATING]
- [ ] Run validation rules V1-V6
- [ ] Calculate priority distribution
- [ ] If errors: return to DERIVING
- [ ] If passed: proceed to REVIEWING
- **Validation:** All rules pass

#### 7. Handoff Preparation [VALIDATING]
- [ ] Define objective mapping rules
- [ ] Seed objectives by priority tier:
  - [ ] Primary from must requirements
  - [ ] Secondary from should requirements
  - [ ] Tertiary from could requirements
- **Validation:** Handoff complete

#### 8. Human Review [REVIEWING]
- [ ] Present RequirementsPackage for human approval
- [ ] If approved: → COMPLETE
- [ ] If revision requested: → DERIVING with feedback

#### 9. Finalization [COMPLETE]
- [ ] Record completion timestamp
- [ ] Package ready for Step 3
""",
}


V1_GUIDANCE_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_2,
    "user": """Create the Guidance Document V1 for Step 2: Requirements.

{considering}

## Step 1 Output (ProblemDefinitionPackage)
{prior_step_output}

## Data Sheet V1
{current_data_sheet}

## To Do List V1
{current_todo_list}

---

Generate the Guidance Document V1:

### Purpose
Orient the agent to the context, principles, and quality criteria for Step 2.

### Context
**Position in Workflow:** Step 2 transforms the problem definition into actionable
requirements. Quality here determines whether Step 3 objectives are achievable.

**Instance {instance_number}:** {domain}

**Input:** Approved ProblemDefinitionPackage (Step 1)
**Output:** Structured RequirementsPackage (Doc 3 §5.2)

### Core Principles

#### 1. Derivation, Not Invention
Requirements MUST derive from Step 1 elements:
- Every requirement traces to a source
- No "invented" requirements without clear origin
- Inference is allowed but must be justified

#### 2. Category Precision
| Category | What It Is | Derivation Source |
|----------|-----------|-------------------|
| FR | System capability/behavior | Needs, core problem, scope |
| NFR | Quality attribute | Concerns, constraints |
| CR | Hard limit/boundary | Hard constraints |
| IR | Interface specification | Integration points |

IR is OPTIONAL - if no integration_points exist in Step 1, the IR list is empty.

#### 3. Priority Assignment
| Priority | Meaning | Source Signals |
|----------|---------|----------------|
| must | System fails without it | Hard constraints, critical needs |
| should | Expected for success | Stakeholder expectations |
| could | Nice to have | Soft constraints, enhancements |

#### 4. Testability Requirement
Every requirement must specify HOW it will be verified:
| Method | When Used |
|--------|-----------|
| demonstration | Show it works |
| test | Run automated/manual tests |
| inspection | Review artifacts |
| analysis | Mathematical/logical proof |

#### 5. Complete Coverage
Every Step 1 element must map to at least one requirement.
"Orphan" elements indicate missing requirements.

### Anti-Patterns
| Anti-Pattern | Symptom | Remedy |
|--------------|---------|--------|
| Invention | Requirement has no source.id | Trace to Step 1 element |
| Over-specification | Too many must requirements | Review priority criteria |
| Vague statement | "System should be good" | Make specific and testable |
| Missing testability | No verification method | Add testability section |
| Category confusion | NFR treated as FR | Review category definitions |
| Empty IR when expected | Integration points exist but no IR | Derive IR from each IP |

### Quality Criteria for RequirementsPackage
1. All requirements have valid source traceability
2. Coverage map shows every Step 1 element addressed
3. Priority distribution is reasonable (not all "must")
4. Every requirement has testability specified
5. Conflicts are documented with proposed resolutions
6. step3_handoff provides clear objective seeds
7. IR list is present (may be empty if no integration points)
""",
}


V1_DETAILED_PROCEDURE_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_2,
    "user": """Create the Detailed Procedure V1 for Step 2: Requirements.

{considering}

## Data Sheet V1
{current_data_sheet}

## To Do List V1
{current_todo_list}

## Guidance Document V1
{current_guidance}

---

Generate the Detailed Procedure V1:

### State Machine Specification
```
STATES = {{RECEIVED, ANALYZING, DERIVING, VALIDATING, REVIEWING, COMPLETE}}

TRANSITIONS:
  RECEIVED   → ANALYZING  : on input_validated()
  ANALYZING  → DERIVING   : on analysis_complete()
  DERIVING   → VALIDATING : on derivation_complete()
  VALIDATING → DERIVING   : on validation_failed()
  VALIDATING → REVIEWING  : on validation_passed()
  REVIEWING  → DERIVING   : on revision_requested()
  REVIEWING  → COMPLETE   : on human_approved()
```

### Phase 1: Reception
**State:** RECEIVED
**Input:** ProblemDefinitionPackage + approval_record
**Procedure:**
1. VALIDATE Step 1 status = COMPLETE
2. VALIDATE approval record present
3. PARSE ProblemDefinitionPackage
4. INITIALIZE RequirementsPackage structure
5. TRANSITION to ANALYZING
**Validation Gate:** Input valid, structure ready

### Phase 2: Analysis
**State:** ANALYZING
**Input:** Parsed ProblemDefinitionPackage
**Procedure:**
1. EXTRACT all source elements:
   - stakeholders[] with needs[], concerns[]
   - constraints.hard[], constraints.soft[]
   - scope.in[]
   - success_criteria[]
   - integration_points[]
2. BUILD derivation queue (ordered by category)
3. INITIALIZE counters: fr_count=0, nfr_count=0, cr_count=0, ir_count=0
4. TRANSITION to DERIVING
**Validation Gate:** All sources catalogued

### Phase 3: Derivation
**State:** DERIVING
**Input:** Derivation queue
**Procedure:**

```python
FOR source IN derivation_queue:
    MATCH source.type:
        CASE "core_problem":
            requirement = DERIVE_FR(source, priority="must")
            fr_count += 1

        CASE "stakeholder_need":
            requirement = DERIVE_FR_OR_NFR(source)
            UPDATE appropriate counter

        CASE "stakeholder_concern":
            requirement = DERIVE_NFR(source, priority="should")
            nfr_count += 1

        CASE "hard_constraint":
            requirement = DERIVE_CR(source, priority="must")
            cr_count += 1

        CASE "soft_constraint":
            requirement = DERIVE_FR_OR_NFR(source, priority="should|could")
            UPDATE appropriate counter

        CASE "success_criterion":
            requirement = DERIVE_VERIFICATION_REQ(source)
            UPDATE appropriate counter

        CASE "integration_point":
            requirement = DERIVE_IR(source, priority="should")
            ir_count += 1

    ASSIGN_ID(requirement)  # FR-NNN, NFR-NNN, CR-NNN, IR-NNN
    ADD_TESTABILITY(requirement)
    ADD_TRACE(requirement, source)
    APPEND to requirements[]

BUILD coverage_map from source → requirement mappings
IDENTIFY conflicts and tradeoffs
TRANSITION to VALIDATING
```

**Validation Gate:** All sources processed, coverage map built

### Phase 4: Validation
**State:** VALIDATING
**Procedure:**
1. RUN validation rules V1-V6:
   - V1: requirements count ≥ 1
   - V2: ID format check
   - V3: source.id exists in Step 1
   - V4: coverage check (warning only)
   - V5: priority sum check
   - V6: testability present
2. CALCULATE priority_distribution
3. IF errors exist:
   - LOG failures
   - TRANSITION to DERIVING
4. ELSE:
   - PREPARE step3_handoff
   - TRANSITION to REVIEWING
**Validation Gate:** All rules pass

### Phase 5: Human Review
**State:** REVIEWING
**Procedure:**
1. PRESENT RequirementsPackage for review
2. AWAIT human decision:
   - APPROVE: TRANSITION to COMPLETE
   - REVISE: Store feedback, TRANSITION to DERIVING
   - MESSAGE: Record comment (no state change)
**Validation Gate:** Decision received

### Phase 6: Finalization
**State:** COMPLETE
**Procedure:**
1. RECORD completion timestamp
2. SEAL package
3. SIGNAL ready for Step 3
**Validation Gate:** Package sealed
""",
}


# =============================================================================
# Pass 1: V2 Prompts (First Refinement)
# =============================================================================


V2_DATA_SHEET_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_2,
    "user": """Refine the Data Sheet to V2 for Step 2: Requirements.

{considering}

## Prior Documents
### Detailed Procedure V1
{prior_detailed_procedure}

### Guidance Document V1
{prior_guidance}

### To Do List V1
{prior_todo_list}

---

Produce Data Sheet V2 by refining V1 based on insights from the other documents.

Improvements to make:
1. Refine derivation patterns based on procedure logic
2. Add validation rules for edge cases (e.g., empty IR list)
3. Clarify testability requirements
4. Ensure state definitions match procedure flow

Keep the same structure, enhance the content.
""",
}


V2_TODO_LIST_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_2,
    "user": """Refine the To Do List to V2 for Step 2: Requirements.

{considering}

## Current Documents
### Data Sheet V2
{current_data_sheet}

## Prior Documents
### Guidance Document V1
{prior_guidance}

### Detailed Procedure V1
{prior_detailed_procedure}

---

Produce To Do List V2 by refining V1 with:
1. More specific checkpoints from Data Sheet V2
2. Edge case handling (empty integration points → empty IR)
3. Conflict detection steps from Guidance V1
4. Precise validation hooks from Detailed Procedure V1

Keep the phased structure, add detail and precision.
""",
}


V2_GUIDANCE_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_2,
    "user": """Refine the Guidance Document to V2 for Step 2: Requirements.

{considering}

## Current Documents
### Data Sheet V2
{current_data_sheet}

### To Do List V2
{current_todo_list}

## Prior Documents
### Detailed Procedure V1
{prior_detailed_procedure}

---

Produce Guidance Document V2 by refining V1 with:
1. Concrete examples of derivation patterns
2. Edge case guidance for optional IR category
3. Decision criteria for FR vs NFR classification
4. Quality metrics from validation rules

Enhance principles with actionable specifics.
""",
}


V2_DETAILED_PROCEDURE_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_2,
    "user": """Refine the Detailed Procedure to V2 for Step 2: Requirements.

{considering}

## Current Documents
### Data Sheet V2
{current_data_sheet}

### To Do List V2
{current_todo_list}

### Guidance Document V2
{current_guidance}

---

Produce Detailed Procedure V2 by refining V1 with:
1. Precise derivation algorithms from Data Sheet V2
2. Checkpoint alignment with To Do List V2
3. Decision logic from Guidance Document V2
4. Edge case handling (empty sources, conflicts)

Add algorithmic detail where V1 was high-level.
""",
}


# =============================================================================
# Pass 1: V3 Prompts (Final Version)
# =============================================================================


V3_DATA_SHEET_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_2,
    "user": """Finalize the Data Sheet to V3 for Step 2: Requirements.

{considering}

## Prior V2 Documents
### Detailed Procedure V2
{prior_detailed_procedure}

### Guidance Document V2
{prior_guidance}

### To Do List V2
{prior_todo_list}

---

Produce the FINAL Data Sheet V3:
1. Complete derivation patterns
2. All validation rules comprehensive
3. State transitions fully specified
4. Ready to govern Pass 2 execution

This is the authoritative specification for Step 2.
""",
}


V3_TODO_LIST_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_2,
    "user": """Finalize the To Do List to V3 for Step 2: Requirements.

{considering}

## Current Documents
### Data Sheet V3
{current_data_sheet}

## Prior V2 Documents
### Guidance Document V2
{prior_guidance}

### Detailed Procedure V2
{prior_detailed_procedure}

---

Produce the FINAL To Do List V3:
1. Every checkpoint traceable to Data Sheet V3 rules
2. Complete coverage of derivation process
3. Clear validation gates at each phase boundary
4. Ready to execute in Pass 2

This is the authoritative checklist for Step 2.
""",
}


V3_GUIDANCE_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_2,
    "user": """Finalize the Guidance Document to V3 for Step 2: Requirements.

{considering}

## Current Documents
### Data Sheet V3
{current_data_sheet}

### To Do List V3
{current_todo_list}

## Prior V2 Documents
### Detailed Procedure V2
{prior_detailed_procedure}

---

Produce the FINAL Guidance Document V3:
1. Principles refined and complete
2. Derivation examples comprehensive
3. Quality criteria aligned with Data Sheet V3 validation
4. Ready to guide Pass 2 agent

This is the authoritative guidance for Step 2.
""",
}


V3_DETAILED_PROCEDURE_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_2,
    "user": """Finalize the Detailed Procedure to V3 for Step 2: Requirements.

{considering}

## Current Documents
### Data Sheet V3
{current_data_sheet}

### To Do List V3
{current_todo_list}

### Guidance Document V3
{current_guidance}

---

Produce the FINAL Detailed Procedure V3:
1. State machine complete and deterministic
2. All derivation algorithms precise
3. Validation gates aligned with Data Sheet V3
4. Ready to execute in Pass 2

This is the authoritative procedure for Step 2.
""",
}


# =============================================================================
# Pass 2: Execution Prompt
# =============================================================================


PASS_2_EXECUTION_PROMPT = {
    "system": """You are executing Step 2: Requirements of the SOLVER workflow.

You have the V3 methodology documents that specify exactly how to derive requirements
from the approved ProblemDefinitionPackage.

CRITICAL REQUIREMENTS:
1. Follow the V3 Detailed Procedure exactly
2. Produce ONLY valid JSON output (no prose, no markdown outside JSON)
3. Use exact field names from Doc 3 §5.2 RequirementsPackage schema
4. All IDs must follow format: FR-NNN, NFR-NNN, CR-NNN, IR-NNN
5. Every requirement MUST have a source tracing to Step 1
6. IR category is OPTIONAL - use empty list if no integration_points exist
7. Do NOT include metadata fields (package_id, workflow_id, etc.) - these are injected later

OUTPUT FORMAT:
Return ONLY a JSON object with no surrounding text. The JSON must conform to:
```json
{{
  "overview": {{
    "summary": "string",
    "boundaries": ["string"],
    "total_requirements": integer,
    "priority_distribution": {{
      "must": integer,
      "should": integer,
      "could": integer
    }}
  }},
  "requirements": [
    {{
      "id": "FR-001",
      "category": "FR",
      "priority": "must",
      "statement": "string",
      "rationale": "string",
      "source": {{
        "type": "stakeholder",
        "id": "SH-001",
        "aspect": "need"
      }},
      "component": ["string"],
      "testability": {{
        "method": "test",
        "description": "string"
      }},
      "trace": {{
        "stakeholders": ["SH-001"],
        "constraints": [],
        "scope_in": [],
        "success_criteria": [],
        "integration_points": []
      }}
    }}
  ],
  "coverage_map": [
    {{
      "source_type": "stakeholder",
      "source_id": "SH-001",
      "requirement_ids": ["FR-001", "NFR-001"],
      "coverage_note": "string"
    }}
  ],
  "conflicts_tradeoffs": [
    {{
      "conflict": "string",
      "impacted_requirement_ids": ["FR-001", "NFR-002"],
      "proposed_resolution": "string"
    }}
  ],
  "open_questions": {{
    "required_to_finalize": ["string"],
    "deferred": ["string"]
  }},
  "step3_handoff": {{
    "objective_mapping_rules": ["string"],
    "objective_seeds": {{
      "primary_from_must": ["FR-001"],
      "secondary_from_should": ["NFR-001"],
      "tertiary_from_could": []
    }}
  }}
}}
```
""",
    "user": """Execute Step 2: Requirements

## V3 Methodology

### Data Sheet V3
{v3_data_sheet}

### To Do List V3
{v3_todo_list}

### Guidance Document V3
{v3_guidance}

### Detailed Procedure V3
{v3_detailed_procedure}

---

## Step 1 Output (ProblemDefinitionPackage)
{prior_step_output}

{feedback_section}

---

Follow the V3 Detailed Procedure to derive requirements from the ProblemDefinitionPackage.

IMPORTANT:
- Every requirement MUST trace to a Step 1 source element
- IR requirements are only created if integration_points exist in Step 1
- If no integration_points, IR list is empty

Return ONLY the JSON object. No prose before or after.
""",
}


# =============================================================================
# Prompt Registry
# =============================================================================


PROMPTS = {
    "v1": {
        "data_sheet": V1_DATA_SHEET_PROMPT,
        "todo_list": V1_TODO_LIST_PROMPT,
        "guidance": V1_GUIDANCE_PROMPT,
        "detailed_procedure": V1_DETAILED_PROCEDURE_PROMPT,
    },
    "v2": {
        "data_sheet": V2_DATA_SHEET_PROMPT,
        "todo_list": V2_TODO_LIST_PROMPT,
        "guidance": V2_GUIDANCE_PROMPT,
        "detailed_procedure": V2_DETAILED_PROCEDURE_PROMPT,
    },
    "v3": {
        "data_sheet": V3_DATA_SHEET_PROMPT,
        "todo_list": V3_TODO_LIST_PROMPT,
        "guidance": V3_GUIDANCE_PROMPT,
        "detailed_procedure": V3_DETAILED_PROCEDURE_PROMPT,
    },
}


def get_prompt(version: str, doc_type: str) -> dict[str, str]:
    """Get prompt for a specific version and document type."""
    return PROMPTS[version][doc_type]


def get_execution_prompt() -> dict[str, str]:
    """Get the Pass 2 execution prompt for Step 2."""
    return PASS_2_EXECUTION_PROMPT


def format_prompt(
    prompt: dict[str, str],
    context: dict,
    version: str | None = None,
    doc_type: str | None = None,
) -> dict[str, str]:
    """Format a prompt with context variables."""
    considering = ""
    if version and doc_type:
        refs = get_considering_refs(version, doc_type)
        considering = considering_header(refs)

    feedback_section = ""
    if context.get("human_feedback"):
        feedback_section = f"## Revision Feedback\n{context['human_feedback']}\n"

    # Format prior_step_output as readable JSON/YAML
    prior_step_output = context.get("prior_step_output", {})
    if isinstance(prior_step_output, dict):
        import json
        prior_step_output = json.dumps(prior_step_output, indent=2)

    format_context = {
        **context,
        "considering": considering,
        "feedback_section": feedback_section,
        "prior_step_output": prior_step_output,
    }

    return {
        "system": prompt["system"].format(**format_context),
        "user": prompt["user"].format(**format_context),
    }
