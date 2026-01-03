# AGENTS — Solver Engine

This file defines how a CLI coding agent should operate in the `solver-engine` repo.
It complements the environment-level instructions in `/Users/ryan/ai-env/AGENTS.md`.

## Orientation (Required)

1) Confirm location and repo state:
   - `pwd`
   - `git status -sb`
2) Read the local docs before changes:
   - `README.md`
   - `docs/spec/0_SOLVER-Development-Directive.md`
   - If touching reasoning logic or prompts: also read `docs/spec/1_meta-prompt-structured-reasoning.md`
3) Stay within MVP scope (Steps 1–3) unless explicitly directed.

## Authority Stack (Hard Rule)

Follow the doc hierarchy for decisions:

1) `docs/spec/1_meta-prompt-structured-reasoning.md` — Why / reasoning rules
2) `docs/spec/2_structured-reasoning-architecture.md` — Where / boundaries
3) `docs/spec/3_solver-technical-spec.md` — What / schemas, paths, endpoints

If a deviation is needed, use the deviation protocol in
`docs/spec/0_SOLVER-Development-Directive.md` and log it in `docs/DECISIONS.md`.

## Execution Protocol (Slices)

Work only on the assigned slice. For each slice:

1) Provide a short plan:
   - Files to create/modify
   - 3–5 bullet approach summary
   - Up to 3 questions if blocked
2) Wait for approval
3) Implement only the approved slice
4) End with:
   - Changed files list
   - Commands run + results
   - Gate(s) satisfied
   - Next slice plan

## Non-Negotiables

- Do not invent new architecture or paths.
- Do not reintroduce a `src/` layout under `apps/api` (flat layout per Doc 3 §11).
- Do not skip gates; verify with the required commands.
- No hidden chain-of-thought; provide reviewable, traceable rationale only.
- Never advance workflow state without explicit approval action.
- Do not implement Steps 4–10 (stubs only if explicitly requested).

## Orchestration Note

- LangGraph checkpoint restores yield dicts; normalize with `ensure_workflow_state`/`ensure_step_state` in `apps/api/domain/state.py` before node logic.

## Methodology Caching Note

- Hypothesis: caching V3 methodology docs for well-defined problem types
  (e.g., deliverables/packages) can provide reusable domain scaffolding and
  SME-like behavior across similar tasks.
- Treat cached methods as versioned artifacts; validate scope fit and update
  via gate review rather than assuming transfer.

## Tooling and Edits

- Use `rg` for search (`rg -n`, `rg --files`).
- Prefer patch-style edits with minimal diffs.
- Keep changes small and reversible.
- Avoid network access or installs without approval.
- Docker Compose file lives at `infra/docker/docker-compose.yml`.

## Key References

- `README.md` — project overview and API summary
- `docs/spec/0_SOLVER-Development-Directive.md` — operating manual for agents
- `docs/spec/1_meta-prompt-structured-reasoning.md` — methodology rules
- `docs/spec/2_structured-reasoning-architecture.md` — system boundaries
- `docs/spec/3_solver-technical-spec.md` — exact schemas and endpoints
- `docs/DECISIONS.md` — approved deviations from spec (must be respected)
