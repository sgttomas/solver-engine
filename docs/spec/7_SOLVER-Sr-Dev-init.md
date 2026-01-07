# SOLVER Engine — Senior Developer Init (Phase 8 — Verification)

## Role

Senior developer for Phase 8 verification. Implement acceptance gate tests that prove the
system meets its stated criteria. Stay within the governance chain in docs/spec/.

## Mission

Implement Phase 8: Verification. Create test suites that verify all acceptance gates pass.
Start with Package 8.1 (Gate A — Methodology Exists), then proceed through remaining gates.
Ensure comprehensive coverage of gate criteria per Development Directive.

## Phase 8 Scope

**Objective:** All acceptance gates pass with automated verification.

**Packages:**

| # | Package | Gate | Criterion |
|---|---------|------|-----------|
| 8.1 | Gate A — Methodology Exists | A | Steps 1-3 Pass 1 produces 36 methodology documents (3 steps × 4 types × 3 versions) |
| 8.2 | Gate B — Packages with Traces | B | Steps 1-3 Pass 2 produces packages with correct schema and trace links |
| 8.3 | Gate C — Gating Enforcement | C | Pass 2 cannot advance without `approve`; `revise` loops; `message` doesn't bypass |
| 8.4 | Gate D — Restart/Resume | D | Mid-step and `awaiting_review` recovery with no lost artifacts |
| 8.5 | Gate E — API + SSE Flow | E | End-to-end API and streaming verification |
| 8.6 | Gate F — Human-in-the-Loop | F | Manual verification of human oversight guarantees |

**Current Focus:** Close Phase 7R regression risks (F1 failures) and start Package 8.1 once F1 is green.

**Exit Gate:** All acceptance gates (A, B, C, D, E, F) pass with automated tests and reproducible Makefile targets.

## Package 8.1: Gate A — Methodology Exists

**Goal:** Verify that Pass 1 produces all 36 methodology documents.

**Gate A Criterion:** Steps 1-3 Pass 1 produces 36 methodology documents:
- 3 steps × 4 document types × 3 versions = 36 documents
- Document types: Data Sheet, To Do List, Guidance, Detailed Procedure
- Versions: V1, V2, V3
- Pass type: `definition` (Pass 1)
- Artifact type: `methodology_doc`

**Deliverables:**
- Test script that runs complete Pass 1 for a workflow
- Verification query confirming 36 methodology documents
- Gate A test in `apps/api/tests/e2e/test_gate_a.py`
- DECISIONS entry if any deviations

**Verification Query (per Development Directive):**
```sql
SELECT step_name, document_type, document_version, COUNT(*)
FROM artifacts
WHERE workflow_id = $1
  AND pass_type = 'definition'
  AND artifact_type = 'methodology_doc'
  AND step_number <= 3
GROUP BY step_name, document_type, document_version
HAVING COUNT(*) = 1;
-- Should return 36 rows
```

## Objectives

1. Restore clean F1 gate: fix Makefile-driven `make test` failures (OpenAI API key gaps, asyncio fixture errors).
2. Create automated Gate A test that verifies 36 methodology documents.
3. Ensure tests run in CI/CD via Makefile targets (`.venv/bin/pytest` + `PYTHONPATH`).
4. Document any deviations in DECISIONS.md.
5. Maintain governance integrity; no regression of existing gates (Gate C, D, E, γ1, γ4, β4).

## Scope Boundaries

**In scope:**
- Fixing F1 gate failures (env/config/fixtures)
- Gate A test implementation
- Verification of methodology document production
- Test infrastructure for running complete Pass 1
- Documentation of test approach

**Out of scope:**
- Gates B-F (subsequent packages)
- Production optimizations
- New features beyond gate verification

## Orientation

Run:
```bash
pwd
git status -sb
```

Read in order:
1. README.md
2. AGENTS.md
3. CLAUDE.md
4. docs/spec/5_SOLVER-Development-Directive-v1.5.1.md (Phase 8, Package 8.1)
5. docs/spec/4_SOLVER-Technical-Spec-V2.8.4.md (artifact schema, methodology docs)
6. docs/spec/3_SOLVER-Architectural-Contract-v3.4.md (Gate definitions)
7. docs/spec/DECISIONS.md (prior gate-related decisions)
8. docs/spec/FREEZE-RECORD.md (current baseline V2.8.5)

## Current State

**Phase 7R: Remediation — COMPLETE (spec-freeze-v2.8.5)**

Completed:
- Lease infrastructure implemented (P7.3-DEF-001 resolved)
- SSE replay test for workflow.completed (P7.1-DEF-001 resolved)
- Transaction isolation fix per Co-Developer-1 review
- Makefile test targets fixed to use `.venv/bin/pytest`
- Baseline frozen at `spec-freeze-v2.8.5`

Remaining deferrals (permanent/re-eval triggers):
- P6.6-DEFER-001: Messages list/query (permanent MVP deferral)
- P6.5: Synthetic deltas (re-eval if streaming becomes critical)
- P6.4: Mid-step recovery (re-eval if crash reports emerge)

**Gate status:** `make e2e` and `make test-recovery` pass. `make test` now runs but reports 6 failures (OpenAI API 401) and 6 errors (asyncio fixtures). F1 is not green until these are resolved.

**Phase 8: Verification — NEXT**

Starting with Package 8.1: Gate A — Methodology Exists

## Key Paths

| Path | Focus |
|------|-------|
| apps/api/tests/e2e/test_gate_a.py | Gate A test (new) |
| apps/api/orchestration/graph.py | Pass 1 execution flow |
| apps/api/orchestration/nodes.py | Methodology document generation |
| apps/api/infrastructure/db/models/artifact.py | Artifact model (methodology_doc) |
| apps/api/infrastructure/db/repositories/artifact.py | Artifact queries |
| docs/spec/DECISIONS.md | Deviation logging |

## Testing Strategy

**Pre-work (F1 hygiene):**
- Provide required OpenAI API key (or mark/skip impacted tests with documented DECISIONS entry) to eliminate 401 failures.
- Fix asyncio fixture errors in integration tests so `make test` is green.

**Gate A Test Structure:**
```python
class TestGateAMethodologyExists:
    """Gate A: Verify Pass 1 produces 36 methodology documents."""

    def test_pass1_produces_36_methodology_docs(self, client):
        """Complete Pass 1 produces all methodology documents.

        GIVEN a new workflow is created
        WHEN Pass 1 completes for Steps 1-3
        THEN 36 methodology documents exist:
          - 3 steps × 4 document types × 3 versions
          - All with pass_type='definition', artifact_type='methodology_doc'
        """
        # Create workflow and run through Pass 1
        # Verify 36 documents via query
```

**Verification Commands:**
```bash
# F1 canonical
make test

# Gate A test
PYTHONPATH=apps/api .venv/bin/pytest apps/api/tests/e2e/test_gate_a.py -v

# Regression check
make e2e                # Gate E
make test-recovery      # Gate D
make test-gates         # Gate C
PYTHONPATH=apps/api .venv/bin/pytest apps/api/tests/e2e/test_gate_gamma1.py apps/api/tests/e2e/test_gate_gamma4.py apps/api/tests/e2e/test_gate_beta4.py -v
```

## Anti-Patterns to Avoid

| Pattern | Why |
|---------|-----|
| Mocking methodology generation | Gate requires real document production |
| Partial verification (< 36 docs) | Gate criterion is explicit: 36 documents |
| Skipping version progression | Must verify V1→V2→V3 for each type |
| Ignoring pass_type/artifact_type | These fields define methodology docs |
| No database verification | Gate requires persistence proof |

## Start

After orientation develop a comprehensive plan to do the following:
1. Restore F1 to green (`make test`), addressing API key and asyncio fixture issues.
2. Verify dev environment is running (`make dev-api`) and DB ready.
3. Review existing artifact tests for patterns.
4. Design Gate A test structure.
5. Implement test that runs complete Pass 1.
6. Verify 36 methodology documents exist.
7. Run regression tests to ensure no breakage.
