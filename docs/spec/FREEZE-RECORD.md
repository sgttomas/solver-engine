# SOLVER Specification Freeze Record

**Freeze Status:** FROZEN (Phase 7R complete)
**Freeze Date:** 2026-01-06
**Baseline Identifier:** `spec-freeze-v2.8.5`
**Previous Baseline:** `spec-freeze-v2.8.4` (2026-01-07)

---

## Document Manifest

| Document | Version | SHA-256 |
|----------|---------|---------|
| `README.md` | unversioned | `d9a256afdb939e2261762076fe3e6ffd4c2c7e1144da45edba58e4a242e5e918` |
| `0_Document-Type-Specifications-v2.1.1.md` | v2.1.1 | `9be2905307ad211e0e72c2beeca72afc0151879f08c3e5d9aa3ead719365699d` |
| `1_SOLVER-README-v1.0.md` | v1.0 | `55a7be970f250330616ffe1b284f5e5bb09bcf1aef3ee868b33b2ed2885f8607` |
| `2_SOLVER-Design-Intent-v1.1.md` | v1.1 | `f6d248d9a28cf7776c53c6010fc633bdc760bb86cfec2d5f27a51d463af188ff` |
| `3_SOLVER-Architectural-Contract-v3.4.md` | v3.4 | `e43d4128e443c4d26a5703c4c9bfaf3d3ec964c35661f2a03a469a5398c66b84` |
| `4_SOLVER-Technical-Spec-V2.8.4.md` | V2.8.4 | `fa77440347bdd4c2905926cbfba8ddb3c1720ddec11bb6f7f7ba455140f8cad2` |
| `5_SOLVER-Development-Directive-v1.5.1.md` | v1.5.1 | `ce6814b2f447ba881247488936bc895c73a85d5414926d85192a29323f00f08b` |
| `6_SOLVER-Change-Management-v2.0.1.md` | v2.0.1 | `1b6b563654d1bdde915e7e5fbb3bccee79abf32145b92a717ba1bd117b45a853` |

---

**Deferrals Active at This Baseline:**
- P6.6-DEFER-001 (Messages list/query) — permanent MVP deferral
- P6.5 (synthetic artifact.delta) — documented in DECISIONS.md; re-eval if streaming becomes critical path
- P6.4 (mid-step recovery test limitation) — documented in DECISIONS.md; re-eval if mid-step crash reports emerge

**Resolved in V2.8.5:**
- P7.3-DEF-001 (Lease infrastructure) — RESOLVED: ExecutionLock model, LeaseRepository, lease_manager.py implemented with transaction isolation fix
- P7.1-DEF-001 (SSE replay coverage) — RESOLVED: test_workflow_completed_event_replay added in test_sse_replay.py

## Gate Evidence

**Gate Types:**
- F0-F3: Manual review checklist (verified by human reviewer against document manifest)
- F1 (make test): Automated test gate (see P7R DECISIONS entry for LLM test requirements)

### F0: Canonical Set Locked ✓

*Manual verification: documents exist at stated paths with matching versions*

- [x] README.md exists at stated path
- [x] 0_Document-Type-Specifications-v2.1.1.md exists, version matches manifest
- [x] SOLVER-README-v1.0.md exists, version matches manifest
- [x] SOLVER-Design-Intent-v1.1.md exists, version matches manifest
- [x] SOLVER-Architectural-Contract-v3.4.md exists, version matches manifest
- [x] 4_SOLVER-Technical-Spec-V2.8.4.md exists (baseline snapshot), version matches manifest
- [x] SOLVER-Development-Directive-v1.5.1.md exists, version matches manifest
- [x] SOLVER-Change-Management-v2.0.1.md exists, version matches manifest

**Result:** PASS
**Reviewer:** Phase 7 Closure
**Date:** 2026-01-07

### F1: Internal Consistency ✓

- [x] All "see §X" references resolve to existing sections
- [x] All document version references match actual versions
- [x] All filename references match actual filenames
- [x] No document references a version newer than itself

**Result:** PASS
**Reviewer:** Phase 7 Closure
**Date:** 2026-01-07
**Notes:** V2.8.4 cross-references updated to new filename and version; DECISIONS deferrals noted.

### F2: Terminology Stable ✓

- [x] Design Intent §10 (Terminology Mapping) reviewed
- [x] Contract §17 (Glossary) reviewed
- [x] No term defined differently in two places
- [x] All canonical terms used consistently in Spec and Directive

**Result:** PASS
**Reviewer:** Phase 7 Closure
**Date:** 2026-01-07

### F3: Contract Alignment ✓

- [x] Every MUST in Contract has corresponding implementation in Spec
- [x] Every gate in Directive maps to invariant in Contract
- [x] No Spec implementation contradicts Contract requirement
- [x] No Directive sequence violates Contract dependency

**Result:** PASS
**Reviewer:** Phase 7 Closure
**Date:** 2026-01-07
**Notes:** V2.8.4 incorporates P7.1-DEV-001 (completed_at field) and deferral notes; lease recovery remains deferred per DECISIONS.

### F4: Baseline Recorded ✓

- [x] FREEZE-RECORD.md updated with V2.8.4 baseline
- [x] SHA-256 hash computed for V2.8.4 spec
- [x] Timestamp recorded
- [x] All F0-F3 evidence re-verified

**Result:** PASS
**Reviewer:** Phase 7 Closure
**Date:** 2026-01-07

---

## Change Record

### V2.8.5 (2026-01-06)

**Change Request:** Phase 7R Remediation - Lease infrastructure and deferral cleanup

**Scope:**
- Lease infrastructure implemented (P7.3-DEF-001 resolved):
  - ExecutionLock model, LeaseRepository with acquire/renew/release
  - lease_manager.py with run_with_lease wrapper
  - Transaction isolation fix per Co-Developer-1 review: dedicated session with immediate commits
- SSE replay test for workflow.completed added (P7.1-DEF-001 resolved)
- P6.6-DEFER-001 reclassified as permanent MVP deferral
- P6.5/P6.4 updated with re-evaluation triggers
- β4 gate tests (3 e2e, 7 integration) all passing
- Makefile test targets fixed to use `.venv/bin/pytest` (gate tooling reproducibility)

**Approval:** Architect (Ryan Tufts)

**Implementation:**
- `apps/api/infrastructure/db/models/execution_lock.py` — ExecutionLock ORM model
- `apps/api/infrastructure/db/repositories/execution_lock.py` — LeaseRepository
- `apps/api/application/lease_manager.py` — run_with_lease with dedicated session/commits
- `apps/api/tests/e2e/test_gate_beta4.py` — β4 e2e tests
- `apps/api/tests/integration/test_lease_repository.py` — lease repository tests
- `apps/api/tests/e2e/test_sse_replay.py` — workflow.completed replay test
- `Makefile` — test targets use venv pytest with PYTHONPATH

**Verification:**
- `make e2e`: 3/3 passed (Gate E)
- `make test-recovery`: 21/21 passed (Gate D)
- `make test`: 333 passed, 5 skipped (LLM tests, require `RUN_LLM_TESTS=1`), 1 xfailed (asyncio isolation, see DECISIONS.md P7R entry)

---

### V2.8.4 (2026-01-07)

**Change Request:** Governance updates for Phase 7 closure (γ1/γ4/P7.3 alignment)

**Scope:**
- C.2: Reintroduced `completed_at` in WorkflowResponse (additive/backward-compatible; matches implementation and DECISIONS.md P7.1-DEV-001)
- DECISIONS: Added P7.3-DEF-001 (lease recovery deferred; Contract §15.2 / Design Intent §4.8)
- Test coverage: Expanded recovery, replay, OCC, canonical bundle tests; Gate D/E/γ1/γ4 passing

**Approval:** Architect (Ryan Tufts)

**Implementation:**
- Tech Spec V2.8.3 → V2.8.4 (frozen baseline)
- Cross-references updated to new filename and version; FREEZE-RECORD updated

**Verification:** F0–F4 re-run for V2.8.4; all gates exercised (Gate C/D/E, γ1, γ4, recovery suite)

---

### V2.8.3 (2026-01-06)

**Change Request:** C.2 Schema Alignment with Implementation

**Scope:**
- C.2: Changed `id` → `workflow_id` for consistency with C.3
- C.2: Changed `problem` → `original_problem` to match implementation
- C.2: Documented backward-compatibility fields (`current_pass`, `current_step`, `current_step_number`)
- C.2: Documented optional `step_state` field
- C.2: Removed reserved/unimplemented fields (`pass_1_gate_policy`, `created_by`, `last_actor_id`, `completed_at`)
- C.3: Changed `{id}` → `{workflow_id}` in endpoint path for consistency

**Approval:** Architect (Ryan Tufts)

**Implementation:**
- Tech Spec V2.8.2 → V2.8.3
- Cross-references updated: README.md, CLAUDE.md, AGENTS.md

**Verification:** All freeze gates (F0-F4) pass.

---

### V2.8.2 (2026-01-06)

**Change Request:** Schema Remediation Pass 2

**Scope:**
- Message endpoint: Return actual persisted message_id (was random UUID)
- §9.3: Add exception clause for message endpoint minimal response
- §9.4: Align staleness schema with Appendix C.5
- C.3: Clarify `current_step` is string (step name), `current_step_number` is integer
- C.5: Document that can_complete is blocked by stale trace links as well as blocking artifacts

**Approval:** Architect (Ryan Tufts)

**Implementation:**
- Tech Spec V2.8.1 → V2.8.2
- Backend: workflow_service.py returns message from send_message(); routes/workflows.py uses message.id

**Verification:** Backend syntax verified, contract tests pass.

---

### V2.8.1 (2026-01-06)

**Change Request:** API Schema Alignment

**Scope:**
- Message endpoint: Align implementation to spec §16.7 (`{message_id, status}`)
- Progress endpoint: Unify §9.1 and Appendix C.3 schema (resolve inconsistency)
- Staleness endpoint: Add C.5 fields (`has_stale_artifacts`, `position`, `blocking_reasons`, rename `stale_links` → `stale_trace_links`)

**Approval:** Architect (Ryan Tufts)

**Implementation:**
- Tech Spec V2.8.0 → V2.8.1
- Backend: MessageResponse, StepProgressEntry, StaleArtifactEntry, StalenessResponse models updated
- Frontend: types.ts, api.ts, use-message.ts updated
- Tests: 10 contract tests added (test_api_contracts.py)

**Verification:** Contract tests pass (10/10), frontend build passes.

---

## Freeze Behavior

Per Change Management v2.0.1 §3.4:

| Change Type | Allowed During Freeze | Process |
|-------------|----------------------|---------|
| Typo/grammar fixes | Yes | Direct commit, no version bump |
| Clarification (no semantic change) | Yes | Patch bump, note in commit |
| Semantic change | No | Must exit freeze first |
| New requirements | No | Must exit freeze first |

---

## Exit Procedure

To exit freeze state:

1. Document the change requirement
2. Get architecture review approval
3. Update this record to `UNFROZEN` status
4. Make approved changes following Change Management §5
5. Re-execute freeze gates F0-F4 for new baseline

---

*SOLVER Specification Freeze Record v2.0.1*
