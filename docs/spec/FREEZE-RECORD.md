# SOLVER Specification Freeze Record

**Freeze Status:** UNFROZEN (working toward next baseline)
**Unfreeze Date:** 2026-01-07
**Baseline Identifier:** `spec-freeze-v2.8.3` (last frozen)
**Previous Baseline:** `spec-freeze-v2.8.2` (2026-01-06)

---

## Document Manifest

| Document | Version | SHA-256 |
|----------|---------|---------|
| `README.md` | unversioned | `790f182ba9a95eb0761633773a6781361cf0f6a0038f76bdfeffb3f92d43d8a7` |
| `0_Document-Type-Specifications-v2.1.1.md` | v2.1.1 | `261208f34c5119d52213c0d39877ff61fc68e6bba21510c3c88a57f1f1cb86d5` |
| `1_SOLVER-README-v1.0.md` | v1.0 | `b83569cb1dd5a495067e56a3e457f9e89ec25ea43f669505eced4013b8b39dae` |
| `2_SOLVER-Design-Intent-v1.1.md` | v1.1 | `2eacabe1ec3c335d017c0804e7d5d0ff98b6c72dd580feb5364f83b8961cc53b` |
| `3_SOLVER-Architectural-Contract-v3.4.md` | v3.4 | `f58c1bf057e4361d516ea93de689cf774005bb530d9fdb9344304a6ab1e1254e` |
| `4_SOLVER-Technical-Spec-V2.8.4.md` | V2.8.4 (draft, unfrozen) | `fa77440347bdd4c2905926cbfba8ddb3c1720ddec11bb6f7f7ba455140f8cad2` |
| `5_SOLVER-Development-Directive-v1.5.1.md` | v1.5.1 | `8e76d33d02252675dab81837c916ab5307f458aaff30ef916c190f531f1e2909` |
| `6_SOLVER-Change-Management-v2.0.1.md` | v2.0.1 | `1b6b563654d1bdde915e7e5fbb3bccee79abf32145b92a717ba1bd117b45a853` |

---

**Note:** Gate evidence below reflects the last frozen baseline (spec-freeze-v2.8.3). With the spec now UNFROZEN for V2.8.4 work, gates F0–F4 will be re-executed when the new baseline is frozen.

## Gate Evidence

### F0: Canonical Set Locked ✓

- [x] README.md exists at stated path
- [x] 0_Document-Type-Specifications-v2.1.1.md exists, version matches manifest
- [x] SOLVER-README-v1.0.md exists, version matches manifest
- [x] SOLVER-Design-Intent-v1.1.md exists, version matches manifest
- [x] SOLVER-Architectural-Contract-v3.4.md exists, version matches manifest
- [x] 4_SOLVER-Technical-Spec-V2.8.3.md exists (baseline snapshot), version matches manifest
- [x] SOLVER-Development-Directive-v1.5.1.md exists, version matches manifest
- [x] SOLVER-Change-Management-v2.0.1.md exists, version matches manifest

**Result:** PASS
**Reviewer:** Claude Opus 4.5 (AI Assistant)
**Date:** 2026-01-06
**Notes:** V2.8.3 spec created, cross-references updated in README.md, CLAUDE.md, AGENTS.md.

### F1: Internal Consistency ✓

- [x] All "see §X" references resolve to existing sections
- [x] All document version references match actual versions
- [x] All filename references match actual filenames
- [x] No document references a version newer than itself

**Result:** PASS
**Reviewer:** Claude Opus 4.5 (AI Assistant)
**Date:** 2026-01-06
**Notes:** V2.8.3: C.2 now uses `workflow_id` (consistent with C.3); C.2/C.3 internal inconsistency resolved. All cross-references updated to V2.8.3.

### F2: Terminology Stable ✓

- [x] Design Intent §10 (Terminology Mapping) reviewed
- [x] Contract §17 (Glossary) reviewed
- [x] No term defined differently in two places
- [x] All canonical terms used consistently in Spec and Directive

**Result:** PASS
**Reviewer:** Claude Opus 4.5 (AI Assistant)
**Date:** 2026-01-06
**Notes:** Four document types (data_sheet, todo_list, guidance, detailed_procedure) verified consistent. V2.8.2 field names (stale_trace_links, stale_reason, artifact_type, blocking, current_step_number) verified.

### F3: Contract Alignment ✓

- [x] Every MUST in Contract has corresponding implementation in Spec
- [x] Every gate in Directive maps to invariant in Contract
- [x] No Spec implementation contradicts Contract requirement
- [x] No Directive sequence violates Contract dependency

**Result:** PASS
**Reviewer:** Claude Opus 4.5 (AI Assistant)
**Date:** 2026-01-06
**Notes:** V2.8.3: C.2 schema now matches implementation exactly (workflow_id, original_problem, backward-compat fields documented). C.2/C.3 field naming is now consistent.

### F4: Baseline Recorded ✓

- [x] FREEZE-RECORD.md updated with V2.8.3 baseline
- [x] SHA-256 hash computed for V2.8.3 spec
- [x] Timestamp recorded
- [x] All F0-F3 evidence re-verified

**Result:** PASS
**Reviewer:** Claude Opus 4.5 (AI Assistant)
**Date:** 2026-01-06

---

## Change Record

### V2.8.4 (UNFROZEN, in progress - 2026-01-07)

**Change Request:** Governance updates for Phase 7 (γ1) alignment

**Scope:**
- C.2: Reintroduced `completed_at` in WorkflowResponse (additive/backward-compatible; matches implementation and DECISIONS.md P7.1-DEV-001)
- Governance: Spec unfrozen for Phase 7 work; new baseline will be recorded at end of phase

**Approval:** Architect (Ryan Tufts)

**Implementation:**
- Tech Spec V2.8.3 → V2.8.4 (draft)
- Cross-references updated to new filename and version

**Verification:** Pending re-freeze; F0–F4 will be re-run at next baseline.

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
