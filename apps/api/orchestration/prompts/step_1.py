"""
SOLVER API - Step 1 Prompts (Problem Definition)

Prompts for Problem Definition step per Doc 1 Step 1 and Doc 3 §5.1.
Produces ProblemDefinitionPackage with Doc 3-aligned field names.
"""

from .common import considering_header, get_considering_refs


# =============================================================================
# System Prompt (Shared across all Step 1 prompts)
# =============================================================================


SYSTEM_PROMPT_STEP_1 = """You are a methodology architect for SOLVER, a Structured Reasoning Workflow Engine.

You are working on Instance {instance_number}: {domain}

Your task is to create methodology documents for Step 1: Problem Definition.

Step 1 transforms an unstructured problem statement from a human into a structured
ProblemDefinitionPackage that feeds into Step 2 (Requirements).

KEY PRINCIPLES:
1. Actual vs. Stated Problem: The stated problem may be a symptom, solution-in-disguise,
   or incomplete. Always identify the ACTUAL problem that needs solving.
2. Elicitation Before Assumption: If the input is unclear, request clarification rather
   than making assumptions that could invalidate downstream work.
3. Constraint Rigor: Hard constraints have zero flexibility (if violated, solution fails).
   Soft constraints have trade-offs and can be negotiated.
4. Stakeholder Completeness: Every stakeholder has needs, concerns, and impact. Missing
   a stakeholder means missing requirements later.
5. Traceability Foundation: Everything in output must trace to user input or explicit
   clarification.

OUTPUT FORMAT:
- Follow the exact structure specified in the prompt
- Use markdown formatting for readability
- Include all required sections
"""


# =============================================================================
# Pass 1: V1 Prompts (Initial Creation)
# =============================================================================


# V1 Data Sheet - Created from seed problem
V1_DATA_SHEET_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_1,
    "user": """Create the Data Sheet V1 for Step 1: Problem Definition.

{considering}

## Seed Problem
{original_problem}

---

Generate the Data Sheet V1 with the following structure:

### Step Purpose
Define what problem we're actually solving after ingesting the problem statement from
the user and any necessary clarifications.

### Input Specification
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| raw_problem_description | string | Yes | Initial unstructured input from human |
| clarifying_responses | list[QA_pair] | Conditional | Responses to elicitation questions |

### Output Specification (ProblemDefinitionPackage per Doc 3 §5.1)
```yaml
ProblemDefinitionPackage:
  title: string                     # Concise problem title

  canonical_problem_definition:
    statement: string               # Core problem in 1-2 sentences
    interpretation_notes: [string]  # Notes on interpretation choices

  background: [string]              # Context and history

  stakeholders:                     # Cardinality: [3,6]
    - id: string                    # SH-001, SH-002, ...
      name_or_group: string
      role: string
      needs: [string]
      concerns: [string]
      impact: string

  constraints:
    hard:                           # Cardinality: [1,6]
      - id: string                  # HC-001, HC-002, ...
        statement: string
        rationale: string
    soft:                           # Cardinality: [0,6]
      - id: string                  # SC-001, SC-002, ...
        statement: string
        rationale: string

  scope:
    in:
      - id: string                  # IN-001, ...
        item: string
    out:
      - id: string                  # OUT-001, ...
        item: string
        rationale: string

  success_criteria:                 # Cardinality: [1,5]
    - id: string                    # CRT-001, ...
      metric_or_signal: string
      target: string
      how_verified: string

  assumptions:
    - id: string                    # ASM-001, ...
      statement: string
      rationale: string
      risk_if_wrong: string

  open_questions:
    required_to_proceed:
      - id: string                  # OQ-001, ...
        question: string
    nice_to_have: [string]

  integration_points:
    - id: string                    # IP-001, ...
      description: string
      components: [string]

  step2_handoff:
    requirement_themes: [string]
    nfr_watchouts: [string]
    dependencies_to_capture: [string]
```

### Validation Rules
| Rule ID | Field | Rule | Severity |
|---------|-------|------|----------|
| V1 | canonical_problem_definition.statement | Length ≤ 2 sentences | Error |
| V2 | stakeholders | Count ∈ [3,6] | Error |
| V3 | constraints.hard | Count ≥ 1 | Error |
| V4 | success_criteria | Count ≥ 1 | Error |
| V5 | stakeholders[].id | Format: SH-NNN | Error |
| V6 | constraints.hard[].id | Format: HC-NNN | Error |
| V7 | constraints.soft[].id | Format: SC-NNN | Error |

### State Definitions
| State | Entry Condition | Valid Transitions |
|-------|-----------------|-------------------|
| RECEIVED | Input logged | → ANALYZING |
| ANALYZING | Begin processing | → ELICITING, → STRUCTURING |
| ELICITING | Critical gaps exist | → ANALYZING (with responses) |
| STRUCTURING | No critical gaps | → VALIDATING |
| VALIDATING | Structure complete | → REVIEWING, → STRUCTURING |
| REVIEWING | Validation passed | → COMPLETE, → STRUCTURING |
| COMPLETE | Human approved | (terminal) |
""",
}


# V1 To Do List
V1_TODO_LIST_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_1,
    "user": """Create the To Do List V1 for Step 1: Problem Definition.

{considering}

## Data Sheet V1
{current_data_sheet}

---

Generate the To Do List V1 as a phased checklist:

#### 1. Reception [RECEIVED → ANALYZING]
- [ ] Log raw_problem_description with timestamp
- [ ] Initialize ProblemDefinitionPackage structure
- [ ] Set state: ANALYZING
- **Validation:** Input logged, structure initialized

#### 2. Comprehension & Gap Analysis [ANALYZING]
- [ ] Parse for explicit information (problem, stakeholders, constraints)
- [ ] Identify ambiguities, missing information, contradictions
- [ ] Flag critical gaps that block progress
- [ ] Decide: gaps exist → ELICITING, no gaps → STRUCTURING
- **Validation:** Gap list complete

#### 3. Elicitation [ELICITING] (conditional)
- [ ] Formulate clarifying questions for each critical gap
- [ ] Present questions to human
- [ ] Await and record responses
- [ ] Return to ANALYZING with enriched input
- **Validation:** All critical questions answered

#### 4. Decomposition [STRUCTURING]
- [ ] Extract core problem statement (≤ 2 sentences)
- [ ] Record interpretation notes
- [ ] Capture background context
- **Validation:** V1 (statement length)

#### 5. Stakeholder Analysis [STRUCTURING]
- [ ] Identify all affected parties (3-6)
- [ ] For each stakeholder:
  - [ ] Assign id (SH-NNN)
  - [ ] Define name_or_group, role
  - [ ] List needs and concerns
  - [ ] Assess impact
- **Validation:** V2 (count), V5 (id format)

#### 6. Constraint Extraction [STRUCTURING]
- [ ] Identify hard constraints (non-negotiable)
- [ ] For each hard constraint:
  - [ ] Assign id (HC-NNN)
  - [ ] State constraint and rationale
- [ ] Identify soft constraints (preferences)
- [ ] For each soft constraint:
  - [ ] Assign id (SC-NNN)
  - [ ] State constraint and rationale
- **Validation:** V3 (hard count ≥ 1), V6, V7 (id formats)

#### 7. Scope Definition [STRUCTURING]
- [ ] Define what is IN scope (IN-NNN items)
- [ ] Define what is OUT of scope with rationale (OUT-NNN items)
- **Validation:** Clear boundaries

#### 8. Success Criteria [STRUCTURING]
- [ ] Define success criteria (CRT-NNN)
- [ ] For each: metric/signal, target, verification method
- **Validation:** V4 (count ≥ 1)

#### 9. Additional Elements [STRUCTURING]
- [ ] Capture assumptions (ASM-NNN)
- [ ] List open questions (OQ-NNN for required, strings for nice-to-have)
- [ ] Identify integration points (IP-NNN)
- [ ] Prepare step2_handoff hints

#### 10. Validation [VALIDATING]
- [ ] Run all validation rules (V1-V7)
- [ ] If errors: return to STRUCTURING
- [ ] If passed: proceed to REVIEWING
- **Validation:** All rules pass

#### 11. Human Review [REVIEWING]
- [ ] Present structured output for human approval
- [ ] If approved: → COMPLETE
- [ ] If revision requested: → STRUCTURING with feedback

#### 12. Finalization [COMPLETE]
- [ ] Record completion timestamp
- [ ] Package ready for Step 2
""",
}


# V1 Guidance Document
V1_GUIDANCE_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_1,
    "user": """Create the Guidance Document V1 for Step 1: Problem Definition.

{considering}

## Seed Problem
{original_problem}

## Data Sheet V1
{current_data_sheet}

## To Do List V1
{current_todo_list}

---

Generate the Guidance Document V1:

### Purpose
Orient the agent to the context, principles, and quality criteria for Step 1.

### Context
**Position in Workflow:** Step 1 is the foundation of the entire SOLVER workflow.
Every subsequent step depends on the quality and completeness of the
ProblemDefinitionPackage produced here.

**Instance {instance_number}:** {domain}

**Input:** Unstructured problem description from human
**Output:** Structured ProblemDefinitionPackage (Doc 3 §5.1)

### Core Principles

#### 1. Stated vs. Actual Problem
- **Stated Problem:** What the user literally said
- **Core Problem:** What actually needs to be solved

The stated problem may be:
- A symptom of a deeper issue
- A solution presented as a problem
- Incomplete or missing key context

Always ask: "What problem does the human ACTUALLY need solved?"

#### 2. Elicitation Before Assumption
When information is unclear or missing:
- DO: Ask clarifying questions
- DON'T: Make assumptions that could invalidate downstream work

A question asked now prevents rework in Steps 2-10.

#### 3. Constraint Classification
| Type | Definition | Test |
|------|------------|------|
| Hard | Non-negotiable; if violated, solution fails | "Would violating this make the solution invalid?" |
| Soft | Preference; trade-offs possible | "Could we compromise on this if needed?" |

#### 4. Stakeholder Completeness
For each stakeholder, capture:
- **Needs:** What they require from the solution
- **Concerns:** What worries them about the problem/solution
- **Impact:** How they're affected

Missing a stakeholder = missing requirements in Step 2.

#### 5. Traceability Foundation
Every element in the output must trace to:
- Direct user input (quoted or paraphrased)
- Explicit clarification responses
- Justified inference (with reasoning)

### Anti-Patterns
| Anti-Pattern | Symptom | Remedy |
|--------------|---------|--------|
| Assuming context | Gap in reasoning chain | Ask clarifying question |
| Conflating hard/soft | "Must" used loosely | Apply violation test |
| Scope creep | Unbounded in-scope list | Explicit out-of-scope items |
| Single stakeholder | Only end-user considered | Consider operators, maintainers, affected parties |
| Vague success | "System works well" | Measurable criteria with targets |

### Quality Criteria for ProblemDefinitionPackage
1. Core problem is singular, focused, ≤ 2 sentences
2. 3-6 stakeholders with complete attributes
3. At least 1 hard constraint
4. At least 1 success criterion with verification method
5. Clear scope boundaries (in AND out)
6. All IDs follow format (SH-NNN, HC-NNN, SC-NNN, etc.)
7. step2_handoff provides actionable guidance
""",
}


# V1 Detailed Procedure
V1_DETAILED_PROCEDURE_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_1,
    "user": """Create the Detailed Procedure V1 for Step 1: Problem Definition.

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
STATES = {{RECEIVED, ANALYZING, ELICITING, STRUCTURING, VALIDATING, REVIEWING, COMPLETE}}

TRANSITIONS:
  RECEIVED    → ANALYZING   : on begin_processing()
  ANALYZING   → ELICITING   : on critical_gaps_exist()
  ANALYZING   → STRUCTURING : on no_critical_gaps()
  ELICITING   → ANALYZING   : on clarification_received()
  STRUCTURING → VALIDATING  : on structure_complete()
  VALIDATING  → STRUCTURING : on validation_failed()
  VALIDATING  → REVIEWING   : on validation_passed()
  REVIEWING   → STRUCTURING : on revision_requested()
  REVIEWING   → COMPLETE    : on human_approved()
```

### Phase 1: Reception
**State:** RECEIVED
**Input:** raw_problem_description
**Procedure:**
1. LOG input with timestamp
2. INITIALIZE ProblemDefinitionPackage structure with empty fields
3. TRANSITION to ANALYZING
**Validation Gate:** Input logged, structure initialized

### Phase 2: Comprehension & Gap Analysis
**State:** ANALYZING
**Input:** Problem description (+ any clarifications)
**Procedure:**
1. PARSE input for:
   - Explicit problem statement
   - Mentioned stakeholders
   - Stated constraints
   - Implied scope
   - Success indicators
2. FLAG ambiguities and missing information
3. CLASSIFY gaps as:
   - Critical (blocks progress)
   - Non-critical (can infer or defer)
4. IF critical gaps exist:
   - TRANSITION to ELICITING
5. ELSE:
   - TRANSITION to STRUCTURING
**Validation Gate:** Gap analysis complete

### Phase 3: Elicitation (Conditional)
**State:** ELICITING
**Input:** Critical gap list
**Procedure:**
1. FOR each critical gap:
   - FORMULATE clarifying question
   - INCLUDE context (why this matters)
   - INCLUDE impact if unresolved
2. PRESENT questions to human
3. AWAIT responses
4. RECORD responses as clarification data
5. TRANSITION to ANALYZING with enriched input
**Validation Gate:** All critical questions addressed

### Phase 4: Structuring
**State:** STRUCTURING
**Input:** Complete information set
**Procedure:**
1. EXTRACT core problem:
   - Synthesize to ≤ 2 sentences
   - Record interpretation notes
2. CAPTURE background context
3. ANALYZE stakeholders:
   - Identify 3-6 affected parties
   - Assign SH-NNN IDs
   - For each: name_or_group, role, needs, concerns, impact
4. EXTRACT constraints:
   - Apply hard/soft classification
   - Assign HC-NNN / SC-NNN IDs
   - Record statement and rationale
5. DEFINE scope:
   - Assign IN-NNN for in-scope items
   - Assign OUT-NNN for out-of-scope with rationale
6. DEFINE success criteria:
   - Assign CRT-NNN IDs
   - For each: metric_or_signal, target, how_verified
7. CAPTURE assumptions (ASM-NNN)
8. LIST open questions (OQ-NNN)
9. IDENTIFY integration points (IP-NNN)
10. PREPARE step2_handoff
11. TRANSITION to VALIDATING
**Validation Gate:** All fields populated

### Phase 5: Validation
**State:** VALIDATING
**Procedure:**
1. RUN validation rules V1-V7:
   - V1: statement ≤ 2 sentences
   - V2: stakeholder count ∈ [3,6]
   - V3: hard constraint count ≥ 1
   - V4: success criteria count ≥ 1
   - V5-V7: ID format checks
2. IF any errors:
   - LOG validation failures
   - TRANSITION to STRUCTURING
3. ELSE:
   - TRANSITION to REVIEWING
**Validation Gate:** All rules pass

### Phase 6: Human Review
**State:** REVIEWING
**Procedure:**
1. PRESENT ProblemDefinitionPackage for human review
2. AWAIT human decision:
   - APPROVE: TRANSITION to COMPLETE
   - REVISE: Store feedback, TRANSITION to STRUCTURING
   - MESSAGE: Record comment (no state change)
**Validation Gate:** Human decision received

### Phase 7: Finalization
**State:** COMPLETE
**Procedure:**
1. RECORD completion timestamp
2. SEAL package (no further modifications without new cycle)
3. SIGNAL ready for Step 2
**Validation Gate:** Package sealed
""",
}


# =============================================================================
# Pass 1: V2 Prompts (First Refinement)
# =============================================================================


V2_DATA_SHEET_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_1,
    "user": """Refine the Data Sheet to V2 for Step 1: Problem Definition.

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
1. Add any missing validation rules discovered in Detailed Procedure
2. Clarify field descriptions based on Guidance principles
3. Ensure state definitions align with procedure flow
4. Add cardinality constraints that were implicit

Keep the same structure, enhance the content.
""",
}


V2_TODO_LIST_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_1,
    "user": """Refine the To Do List to V2 for Step 1: Problem Definition.

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
2. Anti-pattern checks from Guidance V1
3. Precise validation hooks from Detailed Procedure V1

Keep the phased structure, add detail and precision.
""",
}


V2_GUIDANCE_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_1,
    "user": """Refine the Guidance Document to V2 for Step 1: Problem Definition.

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
1. More concrete examples based on Data Sheet V2 fields
2. Edge case guidance from To Do List V2 validations
3. Decision criteria from Detailed Procedure V1

Enhance principles with actionable specifics.
""",
}


V2_DETAILED_PROCEDURE_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_1,
    "user": """Refine the Detailed Procedure to V2 for Step 1: Problem Definition.

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
1. Precise field mappings from Data Sheet V2
2. Checkpoint alignment with To Do List V2
3. Decision logic from Guidance Document V2

Add algorithmic detail where V1 was high-level.
""",
}


# =============================================================================
# Pass 1: V3 Prompts (Final Version)
# =============================================================================


V3_DATA_SHEET_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_1,
    "user": """Finalize the Data Sheet to V3 for Step 1: Problem Definition.

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
1. Complete and consistent with all V2 documents
2. All validation rules comprehensive
3. State transitions fully specified
4. Ready to govern Pass 2 execution

This is the authoritative specification for Step 1.
""",
}


V3_TODO_LIST_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_1,
    "user": """Finalize the To Do List to V3 for Step 1: Problem Definition.

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
2. Complete coverage of all required fields
3. Clear validation gates at each phase boundary
4. Ready to execute in Pass 2

This is the authoritative checklist for Step 1.
""",
}


V3_GUIDANCE_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_1,
    "user": """Finalize the Guidance Document to V3 for Step 1: Problem Definition.

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
2. Anti-patterns comprehensive
3. Quality criteria aligned with Data Sheet V3 validation
4. Ready to guide Pass 2 agent

This is the authoritative guidance for Step 1.
""",
}


V3_DETAILED_PROCEDURE_PROMPT = {
    "system": SYSTEM_PROMPT_STEP_1,
    "user": """Finalize the Detailed Procedure to V3 for Step 1: Problem Definition.

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
2. All phases with precise procedures
3. Validation gates aligned with Data Sheet V3
4. Ready to execute in Pass 2

This is the authoritative procedure for Step 1.
""",
}


# =============================================================================
# Pass 2: Execution Prompt
# =============================================================================


PASS_2_EXECUTION_PROMPT = {
    "system": """You are executing Step 1: Problem Definition of the SOLVER workflow.

You have the V3 methodology documents that specify exactly how to process the input
and produce a ProblemDefinitionPackage.

CRITICAL REQUIREMENTS:
1. Follow the V3 Detailed Procedure exactly
2. Produce ONLY valid JSON output (no prose, no markdown outside JSON)
3. Use exact field names from Doc 3 §5.1 ProblemDefinitionPackage schema
4. All IDs must follow format: SH-NNN, HC-NNN, SC-NNN, IN-NNN, OUT-NNN, CRT-NNN, ASM-NNN, OQ-NNN, IP-NNN
5. Do NOT include metadata fields (package_id, workflow_id, instance_id, version, created_at) - these are injected later

OUTPUT FORMAT:
Return ONLY a JSON object with no surrounding text. The JSON must conform to:
```json
{{
  "title": "string",
  "canonical_problem_definition": {{
    "statement": "string (≤ 2 sentences)",
    "interpretation_notes": ["string"]
  }},
  "background": ["string"],
  "stakeholders": [
    {{
      "id": "SH-001",
      "name_or_group": "string",
      "role": "string",
      "needs": ["string"],
      "concerns": ["string"],
      "impact": "string"
    }}
  ],
  "constraints": {{
    "hard": [
      {{
        "id": "HC-001",
        "statement": "string",
        "rationale": "string"
      }}
    ],
    "soft": [
      {{
        "id": "SC-001",
        "statement": "string",
        "rationale": "string"
      }}
    ]
  }},
  "scope": {{
    "in": [
      {{
        "id": "IN-001",
        "item": "string"
      }}
    ],
    "out": [
      {{
        "id": "OUT-001",
        "item": "string",
        "rationale": "string"
      }}
    ]
  }},
  "success_criteria": [
    {{
      "id": "CRT-001",
      "metric_or_signal": "string",
      "target": "string",
      "how_verified": "string"
    }}
  ],
  "assumptions": [
    {{
      "id": "ASM-001",
      "statement": "string",
      "rationale": "string",
      "risk_if_wrong": "string"
    }}
  ],
  "open_questions": {{
    "required_to_proceed": [
      {{
        "id": "OQ-001",
        "question": "string"
      }}
    ],
    "nice_to_have": ["string"]
  }},
  "integration_points": [
    {{
      "id": "IP-001",
      "description": "string",
      "components": ["string"]
    }}
  ],
  "step2_handoff": {{
    "requirement_themes": ["string"],
    "nfr_watchouts": ["string"],
    "dependencies_to_capture": ["string"]
  }}
}}
```
""",
    "user": """Execute Step 1: Problem Definition

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

## Input Problem Statement
{original_problem}

{clarification_section}
{feedback_section}

---

Follow the V3 Detailed Procedure to process the input and produce the ProblemDefinitionPackage.

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
    """Get prompt for a specific version and document type.

    Args:
        version: Version (v1, v2, v3).
        doc_type: Document type (data_sheet, todo_list, guidance, detailed_procedure).

    Returns:
        Dict with 'system' and 'user' prompt strings.

    Raises:
        KeyError: If version or doc_type is invalid.
    """
    return PROMPTS[version][doc_type]


def get_execution_prompt() -> dict[str, str]:
    """Get the Pass 2 execution prompt for Step 1.

    Returns:
        Dict with 'system' and 'user' prompt strings.
    """
    return PASS_2_EXECUTION_PROMPT


def format_prompt(
    prompt: dict[str, str],
    context: dict,
    version: str | None = None,
    doc_type: str | None = None,
) -> dict[str, str]:
    """Format a prompt with context variables.

    Args:
        prompt: Prompt dict with 'system' and 'user' keys.
        context: Context dict from build_context().
        version: Version for considering header (optional).
        doc_type: Document type for considering header (optional).

    Returns:
        Formatted prompt dict.
    """
    # Build considering header if version and doc_type provided
    considering = ""
    if version and doc_type:
        refs = get_considering_refs(version, doc_type)
        considering = considering_header(refs)

    # Build clarification section
    clarification_section = ""
    if context.get("clarification_response"):
        clarification_section = "## Clarification Responses\n"
        for q, a in context["clarification_response"].items():
            clarification_section += f"**Q:** {q}\n**A:** {a}\n\n"

    # Build feedback section
    feedback_section = ""
    if context.get("human_feedback"):
        feedback_section = f"## Revision Feedback\n{context['human_feedback']}\n"

    # Merge into context
    format_context = {
        **context,
        "considering": considering,
        "clarification_section": clarification_section,
        "feedback_section": feedback_section,
    }

    return {
        "system": prompt["system"].format(**format_context),
        "user": prompt["user"].format(**format_context),
    }
