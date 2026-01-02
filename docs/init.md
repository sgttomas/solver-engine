## Getting Started: Step-by-Step

### 1. Set Up Your Project Folder

```bash
mkdir solver-engine && cd solver-engine

# Create the docs structure
mkdir -p docs/spec

# Place your 4 documents:
# docs/spec/1_meta-prompt-structured-reasoning.md
# docs/spec/2_structured-reasoning-architecture.md
# docs/spec/3_solver-technical-spec.md
# docs/spec/0_SOLVER-Development-Directive.md   ← This is v1.2

# Create the deviation log
touch docs/DECISIONS.md

# Initialize git
git init
```

### 2. Prime Your Agent

When you start your AI coding agent session (Gemini Code Assist, Claude Code, Cursor, Aider, etc.), paste this as your first message:

```
Read docs/spec/0_SOLVER-Development-Directive.md in full. This is your authoritative operating manual.

Confirm you understand by stating:
1. Your role
2. The three authority documents and what each governs
3. The six acceptance gates (A-F)
4. The six build phases (P1-P6)

Then wait for my first slice assignment.
```

### 3. Verify the Agent Understood

The agent should respond with something like:

> **My Role:** Senior Developer implementing SOLVER per your specifications.
>
> **Authority Documents:**
> - Doc 1 (Why): Process/reasoning rules
> - Doc 2 (Where): System shape/invariants  
> - Doc 3 (What): Schemas/endpoints/paths
>
> **Gates A-F:** Methodology, Packages+Traces, Gating, Restart, API+SSE, Audit
>
> **Phases P1-P6:** Foundation, Persistence, Orchestration, API, Content, Verification
>
> Ready for first slice assignment.

If it doesn't get this right, have it re-read the directive.

### 4. Assign the First Slice

```
Begin slice P1.1
```

The agent should:
1. Read Doc 3 — Repository Structure
2. Output a plan (files to create, approach)
3. Wait for your approval

### 5. Your Workflow Loop

```
┌─────────────────────────────────────────┐
│  You: "Begin slice P1.1"                │
│                  ↓                      │
│  Agent: [outputs plan]                  │
│                  ↓                      │
│  You: "Approved" or "Adjust X"          │
│                  ↓                      │
│  Agent: [implements + runs commands]    │
│                  ↓                      │
│  Agent: [outputs slice report]          │
│                  ↓                      │
│  You: "Approved. Begin slice P1.2"      │
│                  ↓                      │
│  [repeat until P6.6 complete]           │
└─────────────────────────────────────────┘
```

### 6. The Full Slice Sequence

| Phase | Slices | Focus |
|-------|--------|-------|
| P1 | P1.1 → P1.2 → P1.3 | Folder structure, Docker, DB schema |
| P2 | P2.1 → P2.2 → P2.3 | Models, repositories, checkpoints |
| P3 | P3.1 → P3.2 → P3.3 → P3.4 | State models, graph, nodes, interrupts |
| P4 | P4.1 → P4.2 → P4.3 → P4.4 | Endpoints, actions, SSE, wiring |
| P5 | P5.1 → P5.2 → P5.3 → P5.4 | LLM adapter, prompts, storage, traces |
| P6 | P6.1 → P6.2 → P6.3 → P6.4 → P6.5 → P6.6 | Gate tests |

### Quick Commands Reference

| When | You Say |
|------|---------|
| Start a slice | `Begin slice P#.#` |
| Approve plan | `Approved` |
| Adjust plan | `Adjust: [your change]` |
| Approve slice report | `Approved. Begin slice P#.#` |
| Question | `Before proceeding: [question]` |
| Stop | `Halt` |

---

**You're ready. Start your agent and paste the priming message.**
