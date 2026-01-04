"""
SOLVER API - Step 3 Prompts (Objectives)

Prompts for Objectives step per Doc 1 Step 3 and Doc 3 §5.3.
Produces ObjectivesPackage with Doc 3-aligned field names.
Includes INTF (Interface Objectives) as optional category derived from IR.
"""

from .common import considering_header, get_considering_refs


# =============================================================================
# System Prompt (Shared across all Step 3 prompts)
# =============================================================================


SYSTEM_PROMPT_STEP_3 = """You are a methodology architect for SOLVER, a Structured Reasoning Workflow Engine.

You are working on Instance {instance_number}: {domain}

Your task is to create methodology documents for Step 3: Objectives.

Step 3 transforms the approved RequirementsPackage from Step 2 into a structured
ObjectivesPackage that defines what success looks like.

KEY PRINCIPLES:
1. Transformation, Not Restatement: Objectives transform requirements into success
   outcomes. FR→CAP, NFR→QUAL, CR→COMP, IR→INTF.
2. Consolidation: Multiple requirements may map to a single objective. This
   reduces redundancy while preserving traceability.
3. Success Tiers: Objectives are tiered as primary (minimum viable), secondary
   (target), tertiary (aspirational).
4. Measurability: Every objective must have clear success criteria with
   verification methods.
5. Bidirectional Traceability: trace_map shows objective→requirements,
   backward_trace shows requirement→objective.

OBJECTIVE CATEGORIES:
- CAP (Capability): System achieves capability (from FR)
- QUAL (Quality): System meets quality bar (from NFR)
- COMP (Compliance): System honors constraint (from CR)
- INTF (Interface): System integrates correctly (from IR - optional)

OUTPUT FORMAT:
- Follow the exact structure specified in the prompt
- Use markdown formatting for readability
- Include all required sections
"""


# =============================================================================
# Pass 1: V1 Prompts (Initial Creation)
# =============================================================================


V1_DATA_SHEET_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_3,
    "user": """Create the Data Sheet V1 for Step 3: Objectives.

{considering}

## Step 2 Output (RequirementsPackage)
{prior_step_output}

---

Generate the Data Sheet V1 with the following structure:

### Step Purpose
Transform requirements into measurable objectives with success criteria,
organized into success tiers.

### Input Specification
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| requirements_package | RequirementsPackage | Yes | Approved Step 2 output |
| step_2_approval | approval_record | Yes | Human approval confirmation |

### Input Validation Gate
Before processing, verify:
- Step 2 status = COMPLETE
- Human approval present
- All required RequirementsPackage fields present

### Transformation Patterns
| Source Category | Target Category | Transformation |
|-----------------|-----------------|----------------|
| FR (Functional) | CAP (Capability) | "System can do X" → "X is achieved" |
| NFR (Non-Functional) | QUAL (Quality) | "System performs at Y" → "Y quality is met" |
| CR (Constraint) | COMP (Compliance) | "System limited to Z" → "Z is honored" |
| IR (Interface) | INTF (Interface) | "System integrates with W" → "W integration works" |

### Tier Assignment
| Priority (from Req) | Tier | Meaning |
|---------------------|------|---------|
| must | primary | Minimum viable - system fails without |
| should | secondary | Target - expected success state |
| could | tertiary | Aspirational - exceeds expectations |

### Output Specification (ObjectivesPackage per Doc 3 §5.3)
```yaml
ObjectivesPackage:
  overview:
    intent: string
    measurement_principles: [string]
    boundaries: [string]
    total_objectives: integer
    consolidation_ratio: float    # requirements / objectives

  objectives:
    - id: string                  # CAP-001, QUAL-001, COMP-001, INTF-001
      category: CAP | QUAL | COMP | INTF
      tier: primary | secondary | tertiary
      statement: string           # "X is achieved"
      rationale: string
      owner_type: process | user | system

      linked_requirements: [string]  # FR-xxx, NFR-xxx, etc.
      consolidated: boolean          # true if multiple reqs → 1 obj

      success_criteria:
        definition: string
        verification:
          method: demonstration | test | inspection | analysis
          description: string
          evidence_artifacts: [string]
        metric: string | null
        threshold: string | null

      component: [string]
      acceptance_criteria: [string]  # CRT-xxx links from Step 1

  success_framework:
    minimum_viable:
      description: string
      objectives: [string]        # Primary objective IDs
      requirement_coverage: [string]

    target:
      description: string
      objectives: [string]        # Primary + secondary IDs
      requirement_coverage: [string]

    aspirational:
      description: string
      objectives: [string]        # All objective IDs
      requirement_coverage: [string]

  trace_map:
    - objective_id: string
      requirement_ids: [string]
      consolidated: boolean

  backward_trace:
    - requirement_id: string
      objective_id: string

  risks_tradeoffs:
    - risk: string
      related_objectives: [string]
      related_requirements: [string]
      monitoring_signal: string
      mitigation_hint: string

  open_questions:
    required_to_finalize: [string]
    deferred: [string]

  step4_handoff:
    sequencing_notes: [string]
    acceptance_gates: [string]
    dependencies_to_plan: [string]
```

### Validation Rules
| Rule ID | Field | Rule | Severity |
|---------|-------|------|----------|
| V1 | objectives | Count ≥ 1 | Error |
| V2 | objectives[].id | Format: (CAP|QUAL|COMP|INTF)-NNN | Error |
| V3 | backward_trace | All requirements mapped | Error |
| V4 | success_framework.minimum_viable.objectives | Count ≥ 1 | Error |
| V5 | consolidation_ratio | Must equal reqs/objs | Error |
| V6 | objectives[].success_criteria | Definition present | Error |

### State Definitions
| State | Entry Condition | Valid Transitions |
|-------|-----------------|-------------------|
| RECEIVED | Input logged | → ANALYZING |
| ANALYZING | Begin processing | → TRANSFORMING |
| TRANSFORMING | Analysis complete | → VALIDATING |
| VALIDATING | Transformation complete | → REVIEWING, → TRANSFORMING |
| REVIEWING | Validation passed | → COMPLETE, → TRANSFORMING |
| COMPLETE | Human approved | (terminal) |
""",
}


V1_TODO_LIST_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_3,
    "user": """Create the To Do List V1 for Step 3: Objectives.

{considering}

## Data Sheet V1
{current_data_sheet}

---

Generate the To Do List V1 as a phased checklist:

#### 1. Reception [RECEIVED → ANALYZING]
- [ ] Receive RequirementsPackage from Step 2
- [ ] Verify Step 2 status = COMPLETE
- [ ] Verify human approval present
- [ ] Initialize ObjectivesPackage structure
- [ ] Set state: ANALYZING
- **Validation:** Input validated, structure initialized

#### 2. Analysis [ANALYZING → TRANSFORMING]
- [ ] Parse RequirementsPackage:
  - [ ] Group requirements by category (FR, NFR, CR, IR)
  - [ ] Group requirements by priority (must, should, could)
  - [ ] Identify consolidation opportunities (similar reqs)
- [ ] Build transformation queue
- [ ] Set state: TRANSFORMING
- **Validation:** All requirements catalogued

#### 3. Transformation [TRANSFORMING]
For each requirement group, apply transformation patterns:

##### 3.1 FR → CAP (Capability Objectives)
- [ ] For each FR requirement:
  - [ ] Transform to capability achievement statement
  - [ ] Assign CAP-NNN ID
  - [ ] Assign tier based on priority (must→primary, should→secondary, could→tertiary)
  - [ ] Define success criteria
  - [ ] Record linked_requirements
- [ ] Consolidate similar CAP objectives where appropriate
- **Validation:** All FR requirements mapped

##### 3.2 NFR → QUAL (Quality Objectives)
- [ ] For each NFR requirement:
  - [ ] Transform to quality achievement statement
  - [ ] Assign QUAL-NNN ID
  - [ ] Assign tier based on priority
  - [ ] Define measurable success criteria with metric/threshold
  - [ ] Record linked_requirements
- [ ] Consolidate related quality objectives
- **Validation:** All NFR requirements mapped

##### 3.3 CR → COMP (Compliance Objectives)
- [ ] For each CR requirement:
  - [ ] Transform to compliance achievement statement
  - [ ] Assign COMP-NNN ID
  - [ ] Assign tier: primary (constraints are must by definition)
  - [ ] Define success criteria
  - [ ] Record linked_requirements
- **Validation:** All CR requirements mapped

##### 3.4 IR → INTF (Interface Objectives - Optional)
- [ ] For each IR requirement (if any):
  - [ ] Transform to interface success statement
  - [ ] Assign INTF-NNN ID
  - [ ] Assign tier based on priority
  - [ ] Define integration success criteria
  - [ ] Record linked_requirements
- [ ] Note: INTF list may be empty if no IR requirements
- **Validation:** All IR requirements mapped (if any)

#### 4. Trace Building [TRANSFORMING]
- [ ] Build trace_map (objective → requirements)
- [ ] Build backward_trace (requirement → objective)
- [ ] Verify all requirements are covered
- [ ] Calculate consolidation_ratio
- **Validation:** V3 (all requirements mapped)

#### 5. Success Framework [TRANSFORMING]
- [ ] Define minimum_viable:
  - [ ] List primary objectives
  - [ ] List covered requirements
  - [ ] Write description
- [ ] Define target:
  - [ ] List primary + secondary objectives
  - [ ] List covered requirements
  - [ ] Write description
- [ ] Define aspirational:
  - [ ] List all objectives
  - [ ] List all requirements
  - [ ] Write description
- **Validation:** V4 (minimum_viable has objectives)

#### 6. Risk Assessment [TRANSFORMING]
- [ ] Identify risks and tradeoffs
- [ ] Link to affected objectives and requirements
- [ ] Define monitoring signals
- [ ] Propose mitigation hints
- **Validation:** Risks documented

#### 7. Validation [VALIDATING]
- [ ] Run validation rules V1-V6
- [ ] If errors: return to TRANSFORMING
- [ ] If passed: proceed to REVIEWING
- **Validation:** All rules pass

#### 8. Handoff Preparation [VALIDATING]
- [ ] Define sequencing notes for Step 4
- [ ] List acceptance gates
- [ ] Note dependencies to plan
- **Validation:** Handoff complete

#### 9. Human Review [REVIEWING]
- [ ] Present ObjectivesPackage for human approval
- [ ] If approved: → COMPLETE
- [ ] If revision requested: → TRANSFORMING with feedback

#### 10. Finalization [COMPLETE]
- [ ] Record completion timestamp
- [ ] Package ready for Step 4
""",
}


V1_GUIDANCE_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_3,
    "user": """Create the Guidance Document V1 for Step 3: Objectives.

{considering}

## Step 2 Output (RequirementsPackage)
{prior_step_output}

## Data Sheet V1
{current_data_sheet}

## To Do List V1
{current_todo_list}

---

Generate the Guidance Document V1:

### Purpose
Orient the agent to the context, principles, and quality criteria for Step 3.

### Context
**Position in Workflow:** Step 3 transforms requirements into objectives,
defining what success looks like. This is the bridge between "what the system
must do" and "how we know it succeeded."

**Instance {instance_number}:** {domain}

**Input:** Approved RequirementsPackage (Step 2)
**Output:** Structured ObjectivesPackage (Doc 3 §5.3)

### Core Principles

#### 1. Transformation, Not Restatement
Objectives are NOT copy-paste of requirements. Transform:
- FR: "System shall X" → CAP: "X is achieved"
- NFR: "System shall perform at Y" → QUAL: "Y performance is met"
- CR: "System shall not exceed Z" → COMP: "Z limit is honored"
- IR: "System shall integrate with W" → INTF: "W integration succeeds"

#### 2. Consolidation Principle
Multiple requirements may consolidate into one objective:
- Similar capabilities → single capability objective
- Related quality attributes → combined quality objective
- Preserve ALL source requirement IDs in linked_requirements
- Mark consolidated: true

Example:
- FR-001: "User can login with email"
- FR-002: "User can login with SSO"
→ CAP-001: "User authentication is achieved" (consolidated: true, linked: [FR-001, FR-002])

#### 3. Success Tier Assignment
| Tier | Source Priority | Description |
|------|-----------------|-------------|
| primary | must | Minimum viable - cannot ship without |
| secondary | should | Target state - expected success |
| tertiary | could | Aspirational - exceeds expectations |

#### 4. Success Criteria Requirements
Every objective needs:
- **definition:** Clear statement of what success means
- **verification.method:** How to verify (demonstration/test/inspection/analysis)
- **metric:** Quantitative measure (if applicable)
- **threshold:** Acceptable value (if applicable)

#### 5. Bidirectional Traceability
- **trace_map:** objective_id → [requirement_ids]
- **backward_trace:** requirement_id → objective_id

Every requirement MUST appear in backward_trace.

### Anti-Patterns
| Anti-Pattern | Symptom | Remedy |
|--------------|---------|--------|
| Copy-paste | Objective = requirement verbatim | Transform to achievement statement |
| Missing tier | No tier assigned | Derive from requirement priority |
| Over-consolidation | All reqs → 1 obj | Maintain meaningful groupings |
| Under-consolidation | 1:1 req:obj everywhere | Look for natural groupings |
| Unmeasurable | "System is good" | Add metric and threshold |
| Orphan requirement | Requirement not in backward_trace | Create or link objective |
| Empty INTF when expected | IR exists but no INTF | Transform each IR to INTF |

### Quality Criteria for ObjectivesPackage
1. All objectives have valid category (CAP/QUAL/COMP/INTF)
2. All objectives have tier assigned (primary/secondary/tertiary)
3. All requirements appear in backward_trace
4. success_framework covers all tiers appropriately
5. consolidation_ratio accurately reflects transformation
6. Every objective has measurable success criteria
7. INTF list is present (may be empty if no IR requirements)
""",
}


V1_DETAILED_PROCEDURE_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_3,
    "user": """Create the Detailed Procedure V1 for Step 3: Objectives.

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
STATES = {{RECEIVED, ANALYZING, TRANSFORMING, VALIDATING, REVIEWING, COMPLETE}}

TRANSITIONS:
  RECEIVED     → ANALYZING    : on input_validated()
  ANALYZING    → TRANSFORMING : on analysis_complete()
  TRANSFORMING → VALIDATING   : on transformation_complete()
  VALIDATING   → TRANSFORMING : on validation_failed()
  VALIDATING   → REVIEWING    : on validation_passed()
  REVIEWING    → TRANSFORMING : on revision_requested()
  REVIEWING    → COMPLETE     : on human_approved()
```

### Phase 1: Reception
**State:** RECEIVED
**Input:** RequirementsPackage + approval_record
**Procedure:**
1. VALIDATE Step 2 status = COMPLETE
2. VALIDATE approval record present
3. PARSE RequirementsPackage
4. INITIALIZE ObjectivesPackage structure
5. TRANSITION to ANALYZING
**Validation Gate:** Input valid, structure ready

### Phase 2: Analysis
**State:** ANALYZING
**Input:** Parsed RequirementsPackage
**Procedure:**
1. GROUP requirements by category:
   - fr_list = [r for r in reqs if r.category == "FR"]
   - nfr_list = [r for r in reqs if r.category == "NFR"]
   - cr_list = [r for r in reqs if r.category == "CR"]
   - ir_list = [r for r in reqs if r.category == "IR"]
2. FOR each group, identify consolidation candidates:
   - Similar statements
   - Same source stakeholder
   - Related components
3. BUILD transformation_queue with consolidation hints
4. INITIALIZE counters: cap_count=0, qual_count=0, comp_count=0, intf_count=0
5. TRANSITION to TRANSFORMING
**Validation Gate:** All requirements grouped

### Phase 3: Transformation
**State:** TRANSFORMING
**Input:** Transformation queue with consolidation hints
**Procedure:**

```python
FOR group IN transformation_queue:
    MATCH group.category:
        CASE "FR":
            IF consolidation_candidates:
                objective = CONSOLIDATE_TO_CAP(group.requirements)
                objective.consolidated = True
            ELSE:
                objective = TRANSFORM_FR_TO_CAP(group.requirements[0])
                objective.consolidated = False
            objective.tier = DERIVE_TIER(group.requirements)
            cap_count += 1
            ASSIGN_ID(objective, "CAP")

        CASE "NFR":
            IF consolidation_candidates:
                objective = CONSOLIDATE_TO_QUAL(group.requirements)
                objective.consolidated = True
            ELSE:
                objective = TRANSFORM_NFR_TO_QUAL(group.requirements[0])
                objective.consolidated = False
            objective.tier = DERIVE_TIER(group.requirements)
            qual_count += 1
            ASSIGN_ID(objective, "QUAL")

        CASE "CR":
            objective = TRANSFORM_CR_TO_COMP(group.requirements[0])
            objective.tier = "primary"  # Constraints are always primary
            objective.consolidated = len(group.requirements) > 1
            comp_count += 1
            ASSIGN_ID(objective, "COMP")

        CASE "IR":
            objective = TRANSFORM_IR_TO_INTF(group.requirements[0])
            objective.tier = DERIVE_TIER(group.requirements)
            objective.consolidated = len(group.requirements) > 1
            intf_count += 1
            ASSIGN_ID(objective, "INTF")

    ADD_SUCCESS_CRITERIA(objective)
    ADD_LINKED_REQUIREMENTS(objective, group.requirements)
    APPEND to objectives[]
    UPDATE trace_map
    UPDATE backward_trace

CALCULATE consolidation_ratio = total_reqs / len(objectives)
BUILD success_framework from tiers
IDENTIFY risks and tradeoffs
TRANSITION to VALIDATING
```

**Validation Gate:** All requirements transformed, traces built

### Phase 4: Validation
**State:** VALIDATING
**Procedure:**
1. RUN validation rules V1-V6:
   - V1: objectives count ≥ 1
   - V2: ID format check
   - V3: backward_trace covers all requirements
   - V4: minimum_viable has objectives
   - V5: consolidation_ratio correct
   - V6: success_criteria present
2. IF errors exist:
   - LOG failures
   - TRANSITION to TRANSFORMING
3. ELSE:
   - PREPARE step4_handoff
   - TRANSITION to REVIEWING
**Validation Gate:** All rules pass

### Phase 5: Human Review
**State:** REVIEWING
**Procedure:**
1. PRESENT ObjectivesPackage for review
2. AWAIT human decision:
   - APPROVE: TRANSITION to COMPLETE
   - REVISE: Store feedback, TRANSITION to TRANSFORMING
   - MESSAGE: Record comment (no state change)
**Validation Gate:** Decision received

### Phase 6: Finalization
**State:** COMPLETE
**Procedure:**
1. RECORD completion timestamp
2. SEAL package
3. SIGNAL ready for Step 4
**Validation Gate:** Package sealed
""",
}


# =============================================================================
# Pass 1: V2 Prompts (First Refinement)
# =============================================================================


V2_DATA_SHEET_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_3,
    "user": """Refine the Data Sheet to V2 for Step 3: Objectives.

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
1. Refine transformation patterns based on procedure logic
2. Add validation rules for edge cases (e.g., empty INTF list)
3. Clarify consolidation rules
4. Ensure state definitions match procedure flow

Keep the same structure, enhance the content.
""",
}


V2_TODO_LIST_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_3,
    "user": """Refine the To Do List to V2 for Step 3: Objectives.

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
2. Edge case handling (empty IR → empty INTF)
3. Consolidation decision points from Guidance V1
4. Precise validation hooks from Detailed Procedure V1

Keep the phased structure, add detail and precision.
""",
}


V2_GUIDANCE_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_3,
    "user": """Refine the Guidance Document to V2 for Step 3: Objectives.

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
1. Concrete examples of transformation patterns
2. Edge case guidance for optional INTF category
3. Decision criteria for consolidation
4. Quality metrics from validation rules

Enhance principles with actionable specifics.
""",
}


V2_DETAILED_PROCEDURE_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_3,
    "user": """Refine the Detailed Procedure to V2 for Step 3: Objectives.

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
1. Precise transformation algorithms from Data Sheet V2
2. Checkpoint alignment with To Do List V2
3. Consolidation logic from Guidance Document V2
4. Edge case handling (empty sources, over-consolidation)

Add algorithmic detail where V1 was high-level.
""",
}


# =============================================================================
# Pass 1: V3 Prompts (Final Version)
# =============================================================================


V3_DATA_SHEET_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_3,
    "user": """Finalize the Data Sheet to V3 for Step 3: Objectives.

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
1. Complete transformation patterns
2. All validation rules comprehensive
3. State transitions fully specified
4. Ready to govern Pass 2 execution

This is the authoritative specification for Step 3.
""",
}


V3_TODO_LIST_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_3,
    "user": """Finalize the To Do List to V3 for Step 3: Objectives.

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
2. Complete coverage of transformation process
3. Clear validation gates at each phase boundary
4. Ready to execute in Pass 2

This is the authoritative checklist for Step 3.
""",
}


V3_GUIDANCE_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_3,
    "user": """Finalize the Guidance Document to V3 for Step 3: Objectives.

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
2. Transformation examples comprehensive
3. Quality criteria aligned with Data Sheet V3 validation
4. Ready to guide Pass 2 agent

This is the authoritative guidance for Step 3.
""",
}


V3_DETAILED_PROCEDURE_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_3,
    "user": """Finalize the Detailed Procedure to V3 for Step 3: Objectives.

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
2. All transformation algorithms precise
3. Validation gates aligned with Data Sheet V3
4. Ready to execute in Pass 2

This is the authoritative procedure for Step 3.
""",
}


# =============================================================================
# Pass 2: Execution Prompt
# =============================================================================


PASS_2_EXECUTION_PROMPT = {
    "system": """You are executing Step 3: Objectives of the SOLVER workflow.

You have the V3 methodology documents that specify exactly how to transform requirements
from the approved RequirementsPackage into objectives.

CRITICAL REQUIREMENTS:
1. Follow the V3 Detailed Procedure exactly
2. Produce ONLY valid JSON output (no prose, no markdown outside JSON)
3. Use exact field names from Doc 3 §5.3 ObjectivesPackage schema
4. All IDs must follow format: CAP-NNN, QUAL-NNN, COMP-NNN, INTF-NNN
5. Every requirement MUST appear in backward_trace
6. INTF category is OPTIONAL - use empty list if no IR requirements exist
7. Do NOT include metadata fields (package_id, workflow_id, etc.) - these are injected later

OUTPUT FORMAT:
Return ONLY a JSON object with no surrounding text. The JSON must conform to:
```json
{{
  "overview": {{
    "intent": "string",
    "measurement_principles": ["string"],
    "boundaries": ["string"],
    "total_objectives": integer,
    "consolidation_ratio": float
  }},
  "objectives": [
    {{
      "id": "CAP-001",
      "category": "CAP",
      "tier": "primary",
      "statement": "string",
      "rationale": "string",
      "owner_type": "system",
      "linked_requirements": ["FR-001", "FR-002"],
      "consolidated": true,
      "success_criteria": {{
        "definition": "string",
        "verification": {{
          "method": "test",
          "description": "string",
          "evidence_artifacts": ["string"]
        }},
        "metric": "string or null",
        "threshold": "string or null"
      }},
      "component": ["string"],
      "acceptance_criteria": ["CRT-001"]
    }}
  ],
  "success_framework": {{
    "minimum_viable": {{
      "description": "string",
      "objectives": ["CAP-001", "COMP-001"],
      "requirement_coverage": ["FR-001", "CR-001"]
    }},
    "target": {{
      "description": "string",
      "objectives": ["CAP-001", "COMP-001", "QUAL-001"],
      "requirement_coverage": ["FR-001", "CR-001", "NFR-001"]
    }},
    "aspirational": {{
      "description": "string",
      "objectives": ["CAP-001", "COMP-001", "QUAL-001", "CAP-002"],
      "requirement_coverage": ["FR-001", "CR-001", "NFR-001", "FR-002"]
    }}
  }},
  "trace_map": [
    {{
      "objective_id": "CAP-001",
      "requirement_ids": ["FR-001", "FR-002"],
      "consolidated": true
    }}
  ],
  "backward_trace": [
    {{
      "requirement_id": "FR-001",
      "objective_id": "CAP-001"
    }}
  ],
  "risks_tradeoffs": [
    {{
      "risk": "string",
      "related_objectives": ["CAP-001"],
      "related_requirements": ["FR-001"],
      "monitoring_signal": "string",
      "mitigation_hint": "string"
    }}
  ],
  "open_questions": {{
    "required_to_finalize": ["string"],
    "deferred": ["string"]
  }},
  "step4_handoff": {{
    "sequencing_notes": ["string"],
    "acceptance_gates": ["string"],
    "dependencies_to_plan": ["string"]
  }}
}}
```
""",
    "user": """Execute Step 3: Objectives

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

## Step 2 Output (RequirementsPackage)
{prior_step_output}

{feedback_section}

---

Follow the V3 Detailed Procedure to transform requirements into objectives.

IMPORTANT:
- Transform: FR→CAP, NFR→QUAL, CR→COMP, IR→INTF
- Every requirement MUST appear in backward_trace
- INTF objectives are only created if IR requirements exist in Step 2
- If no IR requirements, INTF list is empty
- Consolidate similar requirements into single objectives where appropriate

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
    """Get the Pass 2 execution prompt for Step 3."""
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

    # Format prior_step_output as readable JSON
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
