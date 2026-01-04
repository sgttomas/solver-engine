# Architecture Decisions Log

This log records approved deviations from specification documents per
docs/spec/0_SOLVER-Development-Directive.md.

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

## 2026-01-03 - P5.4
**Deviation:** Defer `/workflows/{id}/traceability` endpoint and `tools/verify_traces.py` (Gate B verification tool) beyond MVP; traceability_links persistence is implemented, but read/verification utilities are postponed.
**Document:** docs/spec/3_solver-technical-spec.md §9 API Endpoints; Appendix A (Gate B)
**Reason:** Scope reduction for current release; storage is in place, but the read API and Gate B tooling will ship in a later phase (P6.2+).
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
