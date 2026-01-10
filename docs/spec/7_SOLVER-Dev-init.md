# SOLVER Engine — Developer Init (Post-MVP — Maintenance & Expansion)

## Role

Developer for post-MVP work. Maintain system stability, fix bugs, optimize performance,
and implement approved expansions. Stay within the governance chain in docs/spec/.

## Mission

MVP verification is complete. All acceptance gates (A-F) pass with 346 automated tests. Focus
shifts to: maintaining system stability, addressing bug reports, performance optimization,
frontend completion, and planning for Steps 4-10 expansion when approved.

## Current State

**Phase 8: Verification — COMPLETE**

All acceptance gates pass:

| Gate | Description | Tests | Status |
|------|-------------|-------|--------|
| A | Methodology Exists (36 docs) | 3 | GREEN |
| B | Packages with Traces | 15 | GREEN |
| C | Gating Enforcement | 7 (4 integration + 3 e2e) | GREEN |
| D | Restart/Resume | test_gate_d.py + test_recovery_scenarios.py | GREEN |
| E | API + SSE Flow | test_gate_e.py + test_sse_replay.py | GREEN |
| F | Audit Trail | 7 | GREEN |

**Test Suite:** 346 passed, 5 skipped, 1 xfailed

**Spec Baseline:** V2.8.5 (frozen)

**Permanent Deferrals:**
- P6.6-DEFER-001: Messages list/query (permanent MVP deferral)
- P6.5: Synthetic deltas (re-eval if streaming becomes critical)
- P6.4: Mid-step recovery (re-eval if crash reports emerge)

## Potential Work Streams

| Stream | Description | Trigger |
|--------|-------------|---------|
| Bug Fixes | Address issues reported in production use | Bug reports |
| Performance | Optimize slow paths, reduce latency | Profiling data |
| Frontend | Complete Next.js UI if not production-ready | UI requirements |
| Steps 4-10 | Expand beyond MVP (Verification, Execution phases) | Architect approval |
| Observability | Enhanced monitoring, alerting, dashboards | Ops requirements |

## Scope Boundaries

**In scope:**
- Bug fixes and regression prevention
- Performance optimization
- Documentation improvements
- Frontend completion work
- Approved feature expansions

**Out of scope without approval:**
- Breaking changes to existing APIs
- Schema migrations that alter existing data
- New governance documents
- Steps 4-10 implementation (requires architect approval)

## Orientation

Run:
```bash
pwd
git status -sb
make test  # Should show 346 passed
```

Read in order:
1. README.md
2. AGENTS.md
3. CLAUDE.md
4. docs/spec/5_SOLVER-Development-Directive-v1.5.1.md
5. docs/spec/4_SOLVER-Technical-Spec-V2.8.4.md
6. docs/spec/3_SOLVER-Architectural-Contract-v3.4.md
7. docs/spec/DECISIONS.md
8. docs/spec/FREEZE-RECORD.md (baseline V2.8.5)

## Key Paths

| Path | Focus |
|------|-------|
| apps/api/tests/ | All test suites (unit, integration, e2e) |
| apps/api/application/ | Service layer (workflow, artifact, traceability) |
| apps/api/orchestration/ | LangGraph state machine, nodes |
| apps/api/routes/workflows.py | REST API endpoints |
| apps/web/ | Next.js frontend |
| docs/spec/DECISIONS.md | Deviation logging |

## Verification Commands

```bash
# Full test suite (F1 canonical)
make test

# Individual gate tests
make test-gate-b       # Gate B (packages with traces)
make test-gates        # Gate C (gating enforcement)
make test-recovery     # Gate D (restart/resume)
make e2e               # Gate E (API + SSE flow)

# Gamma and Beta gates
PYTHONPATH=apps/api .venv/bin/pytest apps/api/tests/e2e/test_gate_gamma1.py apps/api/tests/e2e/test_gate_gamma4.py apps/api/tests/e2e/test_gate_beta4.py -v

# Code quality
make lint
make format
```

## Recommended Operational Enhancements

These are non-blocking improvements that would benefit the system:

| Enhancement | Benefit | Priority |
|-------------|---------|----------|
| **LangSmith tracing** | Debug LLM calls, identify slow prompts, track token usage | High |
| **Structured logging** | Better observability, easier debugging | Medium |
| **Health check endpoint** | Container orchestration readiness | Medium |
| **Metrics export** | Prometheus/Grafana integration | Low |

### LangSmith Integration

LangSmith provides tracing for LangGraph workflows. To enable:

1. Set environment variables:
   ```bash
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=<your-key>
   LANGCHAIN_PROJECT=solver-engine
   ```

2. LangGraph calls will automatically trace to LangSmith dashboard

3. Benefits:
   - Visualize workflow execution
   - Debug prompt/response pairs
   - Track token usage and latency
   - Identify failing nodes

**Note:** This is operational tooling, not a gating requirement.

## Anti-Patterns to Avoid

| Pattern | Why |
|---------|-----|
| Skipping regression tests | All 346 tests must pass before merge |
| Undocumented deviations | DECISIONS.md required for spec divergence |
| Breaking API contracts | Existing clients depend on current schema |
| Modifying frozen specs | Requires change control process |
| Ignoring gate failures | Gates are acceptance criteria |

## Working on Bug Fixes

1. Reproduce the issue with a failing test
2. Fix the root cause
3. Verify fix passes and no regression
4. Document in commit message
5. Update DECISIONS.md if fix deviates from spec

## Working on New Features

1. Get architect approval for scope
2. Design implementation approach
3. Implement with tests
4. Verify all gates still pass
5. Document any spec changes needed

## Start

After orientation, await specific task assignment. If no task assigned, run `make test` to
verify system health and report status.
