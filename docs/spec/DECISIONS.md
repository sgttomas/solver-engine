# Architecture Decisions Log

This log records approved deviations from specification documents per
`docs/spec/6_SOLVER-Change-Management-v1.2.md`.

Note: filenames in this log reflect the names at the time of each decision.
Current canonical filenames may differ; see `docs/spec/` for the latest names.

---

## 2026-01-04 - Governance Transition: Unified Specification Set

**Context:** Backend (Phases 1–5) was built against partial specification set (Docs 0–3).
A comprehensive unified specification set (Docs 0–6) has been issued covering both
backend and frontend as one system.

**Action Taken:**
- Legacy docs moved to `docs/legacy/` (retained for reference)
- Unified docs installed to `docs/spec/` (now authoritative)
- Repository references updated (AGENTS.md, CLAUDE.md, README.md)

**Authority:** Unified docs in `docs/spec/` are now the single source of truth.
Legacy docs in `docs/legacy/` are not authoritative.

**Document Mapping:**

| Old (Legacy) | New (Authoritative) |
|--------------|---------------------|
| `0_SOLVER-Development-Directive.md` | `5_SOLVER-Development-Directive-v1.5.md` |
| `1_meta-prompt-structured-reasoning.md` | (retained in legacy; methodology source) |
| `2_structured-reasoning-architecture.md` | `3_SOLVER-Architectural-Contract-v3.4.md` |
| `3_solver-technical-spec.md` | `4_solver-technical-spec-V2.8.0.md` |

**New Documents:**
- `0_Document-Type-Specifications-v2.1.md` — Governance framework
- `1_SOLVER-README.md` — Project orientation
- `2_SOLVER-Design-Intent-v1.1.md` — Design rationale
- `6_SOLVER-Change-Management-v1.2.md` — Change control process

**Backend Contract Alignment:** The backend implementation is being updated to align
with the unified Architectural Contract (§9–12). Progress/staleness endpoints, state_version,
workflow_events table, and SSE from_sequence replay are being implemented.

---

## 2026-01-02 - P2.3
**Deviation:** Use custom SolverCheckpointSaver instead of langgraph.checkpoint.postgres.PostgresSaver
**Document:** docs/spec/3_solver-technical-spec.md
**Reason:** Installed langgraph-checkpoint-postgres v3.0.2 expects columns/tables absent from 001_initial_schema.py (checkpoint_ns, checkpoint_blobs, checkpoint_writes.type, checkpoint_writes.task_path, BYTEA storage); migrations are out of scope for P2.
**Approved by:** Architect
**Incorporated into spec:** docs/spec/3_solver-technical-spec.md updated to reference SolverCheckpointSaver and Gate D test changes.

## 2026-01-03 - P3.3
**Deviation:** Clear human_decision after routing instead of in process_decision_node
**Document:** docs/spec/3_solver-technical-spec.md §8.4
**Reason:** Doc 3 §8.4 clears human_decision in process_decision_node, but §8.2 route_after_decision reads it AFTER that node runs. Clearing before routing causes graph to default to "end" instead of correct branch. Resolution: clear in advance_node (approve path), structure_node (reject path), and validate_node (modify path).
**Approved by:** Co-Developer review + plan approval
**Incorporated into spec:** Updated docs/spec/3_solver-technical-spec.md §8.4 process_decision_node and advance_node.

## 2026-01-03 - P5.4 (RESOLVED 2026-01-05)
**Original Deviation:** Defer `/workflows/{id}/traceability` endpoint and `tools/verify_traces.py` (Gate B verification tool) beyond MVP; traceability_links persistence is implemented, but read/verification utilities are postponed.
**Document:** docs/spec/4_solver-technical-spec-V2.8.0.md §9 API Endpoints; Appendix A (Gate B)
**Resolution:** `/traceability` endpoint implemented with full filtering (from_step, to_step, stale_only). Gate B tests (7/7) passing. `verify_traces.py` tool remains deferred.
**Approved by:** Architect

## 2026-01-04 - P6.4
**Deviation:** Gate D mid-step recovery is not tested; restart/resume verification only covers awaiting_review checkpoints.
**Document:** docs/spec/3_solver-technical-spec.md Appendix A (Gate D)
**Reason:** LangGraph checkpoints at interrupt boundaries; deterministic mid-step recovery tests are brittle and non-deterministic in current harness.
**Approved by:** Architect

## 2026-01-04 - P6.5
**Deviation:** SSE `artifact.delta` events are emitted post-execution with synthetic chunks rather than true real-time streaming during generation.
**Document:** docs/spec/3_solver-technical-spec.md §9.2 SSE Event Types; Appendix A (Gate E)
**Reason:** MVP implements deterministic SSE sequence at API boundaries; true streaming during LLM generation is deferred.
**Approved by:** Architect
