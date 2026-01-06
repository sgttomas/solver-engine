# Repository Guidelines

## Project Structure & Module Organization
SOLVER is a Python/FastAPI backend with a Next.js frontend. Key paths:
- `apps/api/`: backend source (domain, application, infrastructure, orchestration, routes).
- `apps/web/`: Next.js frontend (TanStack Query, Zustand, Tailwind).
- `packages/`: shared contracts, instance packs, and shared types/utilities.
- `infra/`: Docker and DB migrations (`infra/db/migrations/`).
- `docs/spec/`: authoritative specs; `docs/spec/DECISIONS.md` logs approved deviations; `docs/spec/FREEZE-RECORD.md` tracks freezes.
- `tests/` and `apps/api/tests/`: unit/integration/e2e tests.

## Build, Test, and Development Commands
Common workflow (from README/CLAUDE):
- `docker compose -f infra/docker/docker-compose.yml up -d` — start Postgres.
- `make migrate` — apply DB migrations.
- `make dev-api` — run API at `http://localhost:8000`.
- `make dev-web` — run Next.js at `http://localhost:3000`.
- `make test` / `make test-unit` / `make test-integration` — API pytest suites.
- `make test-gates`, `make test-recovery`, `make e2e` — gate verification.
- `make lint` / `make format` — ruff + mypy linting, ruff formatting (API).
- `make lint-web` / `make format-web` — ESLint/Prettier (frontend).
- `python tools/validate_schemas.py` — schema validation.

## Coding Style & Naming Conventions
- Python: 4-space indentation; follow existing layer boundaries (no DB calls in routes).
- Use `ruff` for formatting/linting; keep type hints where present.
- Models: Pydantic classes in `PascalCase`; fields in `snake_case`.
- Keep file and function naming consistent with existing modules.

## Testing Guidelines
- Framework: `pytest` with tests in `apps/api/tests/` and `tests/`.
- Naming: `test_*.py` files and `test_*` functions.
- Gate tests are required for release readiness; run Gate C/D/E at minimum.
- Some integration tests require LLM API keys; see `.env` notes below.

## Commit & Pull Request Guidelines
- Recent history uses imperative summaries and occasional type prefixes (e.g., `docs:`).
- Keep commits scoped and descriptive (e.g., `docs: update spec refs`).
- PRs should include a summary, tests run, and any deviations logged in `docs/spec/DECISIONS.md`.

## Configuration & Security
- Backend config: `apps/api/.env` (copy from `.env.example`).
- Never commit API keys or secrets; use env vars for LLM providers.

## Architecture & Spec References
- Follow the authority chain in `docs/spec/` for invariants and API schemas.
- Changes that diverge from spec must be recorded in `docs/spec/DECISIONS.md`.

## Spec Quick Links
- `docs/spec/0_Document-Type-Specifications-v2.1.1.md`
- `docs/spec/1_SOLVER-README-v1.0.md`
- `docs/spec/2_SOLVER-Design-Intent-v1.1.md`
- `docs/spec/3_SOLVER-Architectural-Contract-v3.4.md`
- `docs/spec/4_SOLVER-Technical-Spec-V2.8.3.md`
- `docs/spec/5_SOLVER-Development-Directive-v1.5.1.md`
- `docs/spec/6_SOLVER-Change-Management-v2.0.1.md`
- `docs/spec/7_SOLVER-Sr-Dev-init.md`
- `docs/spec/8_SOLVER-Co-Dev-init.md`
- `docs/spec/9_SOLVER-Decision-Heuristic-v.1.0.md` *(experimental, not authoritative)*
- `docs/spec/DECISIONS.md`
- `docs/spec/FREEZE-RECORD.md`
