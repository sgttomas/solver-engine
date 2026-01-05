 # SOLVER Engine — Senior Developer Init

  ## Mission

  1. Confirm backend alignment with unified governance docs (V2.8.0 + Appendix D).
  2. Proceed to frontend integration per Development Directive.

  ## Project Description & Objectives

  Description: SOLVER is a structured reasoning workflow engine that turns unstructured problems into
  versioned, traceable artifacts via a two‑pass, human‑gated methodology (MVP Steps 1–3).

  Objectives:

  - Enforce two‑pass methodology (Pass 1 methodology → Pass 2 execution).
  - Require human approval gates before any Pass 2 advancement.
  - Persist artifacts, audit trail, and event log for restart/replay.
  - Provide REST + SSE for interactive review and synchronization.
  - Preserve traceability from Step 1 → Step 2 → Step 3.

  ## Orientation

  Run:

  - pwd
  - git status -sb

  Read in order:

  1. README.md — project context
  2. AGENTS.md — repository guidelines
  3. CLAUDE.md — tooling/environment commands
  

  Then read in this sequence the governance docs in docs/spec/  

  - 0_Document-Type-Specifications-v{X}.md
  - 1_SOLVER-README-v{X}.md
  - 2_SOLVER-Design-Intent-v{X}.md
  - 3_SOLVER-Architectural-Contract-v{X}.md
  - 4_SOLVER-Technical-Spec-v{X}.md (relevant sections only is sufficient if necessary)
  - 5_SOLVER-Development-Directive-v{X}.md
  - 6_SOLVER-Change-Management-v{X}.md
  - DECISIONS.md — approved deviations
  
  
  ## Current State

  - Backend is spec‑aligned; gates A–F pass offline.
  - LLM integration tests require a live API key and may fail without it.
  - acknowledge-stale now spec‑aligned and SSE payloads include workflow_id, instance_id, actor_id, and
    position.
  - Migration 004_add_pending_status.py adds pending to step_status.

  ## Gates (High Level)

  - α: Environment runs, schema applied, graph operational
  - β: Sequencing, replay correctness, OCC, audit attribution, broadcast‑after‑commit, leases
  - γ: Lifecycle, SSE sync, action gating, staleness flow
  - A–F: Methodology, traces, gating enforcement, restart/resume, SSE flow, audit trail

  ## Current Phase

  Phase 6: Frontend
  Package 6.1: Project Setup

  ## Verification Commands

  - make test-gates
  - make test-recovery
  - make e2e
  - pytest apps/api/tests/e2e/test_sse_replay.py

  ## Key Paths

  - apps/api/routes/workflows.py
  - apps/api/application/workflow_service.py
  - apps/api/application/event_stream.py
  - apps/api/tests/e2e/
  - infra/db/migrations/versions/

  ## Working Protocol

  - Work in packages; each package is a set of deliverables, completed through tasks.
  - Propose a plan for the next package → wait for approval → implement only approved work.
  - Log deviations in docs/DECISIONS.md.
  - Do not edit applied migrations; add new ones.

  ## Start

  After orientation, wait for further instructions.
