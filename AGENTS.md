# AGENTS — Solver Engine

This file defines how a CLI coding agent should operate in the `solver-engine` repo.
It complements the environment-level instructions in `/Users/ryan/ai-env/AGENTS.md`.

## Orientation (Required)

1) Confirm location and repo state:
   - `pwd`
   - `git status -sb`
2) Read the local docs before changes:
   - `README.md`
   - `docs/spec/1_SOLVER-README.md` (project orientation)
3) Stay within MVP scope (Steps 1–3) unless explicitly directed.

## Specification Documents (Authoritative)

Read in this order:

1. `docs/spec/0_Document-Type-Specifications-v2.1.md` — Governance framework
2. `docs/spec/2_SOLVER-Design-Intent-v1.1.md` — Why² (principles, rationale)
3. `docs/spec/3_SOLVER-Architectural-Contract-v3.4.md` — Why (invariants, R1–R19)
4. `docs/spec/4_solver-technical-spec-V2.8.0.md` — What (schemas, APIs)
5. `docs/spec/5_SOLVER-Development-Directive-v1.5.md` — How (phases, packages, gates)
6. `docs/spec/6_SOLVER-Change-Management-v1.2.md` — Process (change control)

Note: `docs/spec/1_SOLVER-README.md` is project orientation (read after repo README).

## Legacy Documents (Reference Only)

The following docs in `docs/legacy/` are superseded but retained for historical context:
- `0_SOLVER-Development-Directive.md` → superseded by `5_SOLVER-Development-Directive`
- `1_meta-prompt-structured-reasoning.md` → superseded by `docs/spec/4_solver-technical-spec-V2.8.0.md` Appendix D (historical only)
- `2_structured-reasoning-architecture.md` → superseded by `3_SOLVER-Architectural-Contract`
- `3_solver-technical-spec.md` → superseded by `4_solver-technical-spec`

## Authority Hierarchy

From Document-Type-Specifications v2.1, two hierarchies govern:

| Hierarchy | Order | Use When |
|-----------|-------|----------|
| **Purpose Priority** | Intent > Contract > Spec > Directive > README | Choosing between compliant options |
| **Binding Precedence** | Contract > Spec > Directive > Intent > README | Resolving conflicts about what must be true |

**Rule:** Contract wins conflicts. Intent is tie-breaker only among compliant solutions.

If a deviation is needed, use the deviation protocol in
`docs/spec/6_SOLVER-Change-Management-v1.2.md` and log it in `docs/DECISIONS.md`.

## Execution Protocol (Packages)

Work only on the assigned package. For each package:

1) Provide a short plan:
   - Files to create/modify
   - 3–5 bullet approach summary
   - Up to 3 questions if blocked
2) Wait for approval
3) Implement only the approved package
4) End with:
   - Changed files list
   - Commands run + results
   - Gate(s) satisfied
   - Next package plan

## Non-Negotiables

- Do not invent new architecture or paths.
- Do not reintroduce a `src/` layout under `apps/api` (flat layout per Technical Spec §11).
- Do not skip gates; verify with the required commands.
- No hidden chain-of-thought; provide reviewable, traceable rationale only.
- Never advance workflow state without explicit approval action.
- Do not implement Steps 4–10 (stubs only if explicitly requested).
- Do not implement deferred items listed in `docs/DECISIONS.md` unless explicitly assigned.
- If a gate scenario is only partially met, log the deviation in `docs/DECISIONS.md` and add a brief note in the relevant spec section.

## Backend Contract Guardrails

- Persist all SSE events to `workflow_events` with monotonic sequences before publish.
- `/stream` must support `from_sequence` replay with gap handling and no broker backlog mixing.
- Action endpoints must require `expected_state_version` and `expected_position` and return 409 on mismatch.
- Applied migrations are immutable; add a new migration for changes.

## Orchestration Note

- LangGraph checkpoint restores yield dicts; normalize with `ensure_workflow_state`/`ensure_step_state` in `apps/api/domain/state.py` before node logic.

## API Wiring Note

- Use the cached graph singleton (`get_graph()` in `apps/api/routes/workflows.py`) instead of per-request graph construction.
- When resuming from review, pass `as_node="review"` in `graph.aupdate_state(...)` (see interrupt/resume tests).

## Methodology Caching Note

- Treat cached methodology as versioned artifacts; validate scope fit before reuse.

## Tooling and Edits

- Use `rg` for search (`rg -n`, `rg --files`).
- Prefer patch-style edits with minimal diffs.
- Keep changes small and reversible.
- Avoid network access or installs without approval.
- Docker Compose file lives at `infra/docker/docker-compose.yml`.
- `make e2e` requires a running database (see `README.md`).

## Key References

- `README.md` — project overview and API summary
- `docs/spec/3_SOLVER-Architectural-Contract-v3.4.md` — invariants and reliability rules (R1–R19)
- `docs/spec/4_solver-technical-spec-V2.8.0.md` — exact schemas and endpoints (Appendix D is normative methodology)
- `docs/spec/5_SOLVER-Development-Directive-v1.5.md` — phases, packages, gates
- `docs/legacy/1_meta-prompt-structured-reasoning.md` — historical context only
- `docs/DECISIONS.md` — approved deviations from spec (must be respected)
