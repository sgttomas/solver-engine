# Manual Gamma-1 Verification Procedure

## Overview

This document provides step-by-step procedures for manually verifying Gate γ1:
**"Create → execute → gate → approve → advance works end-to-end"**

## Prerequisites

### Services Running

```bash
# Terminal 1: Start PostgreSQL
docker compose -f infra/docker/docker-compose.yml up -d

# Terminal 2: Start API server
make dev-api
# Verify: http://localhost:8000/docs should show Swagger UI

# Terminal 3: Start Web UI
make dev-web
# Verify: http://localhost:3000 should show the application
```

### Database Ready

```bash
# Apply migrations
make migrate

# Verify: No errors in API logs
```

## LLM Configuration

### Mode 1: Mock LLM (Deterministic)

For reproducible testing without API keys:

1. In `apps/api/.env`, ensure no valid LLM API keys are set
2. The system will use stub responses for step execution
3. Useful for CI/CD and reproducible manual testing

### Mode 2: Real LLM (Full Integration)

For complete end-to-end verification:

1. Configure at least one provider in `apps/api/.env`:
   ```
   DEFAULT_LLM_PROVIDER=openai   # or anthropic, google
   OPENAI_API_KEY=sk-...
   # OR
   ANTHROPIC_API_KEY=...
   # OR
   GOOGLE_API_KEY=...
   ```
2. Responses will be non-deterministic
3. Useful for validating actual LLM integration

## Verification Steps

### Step 1: Create Workflow

**Action:**
1. Navigate to http://localhost:3000
2. Click "New Workflow" or equivalent
3. Enter problem statement: "Test workflow for γ1 verification"
4. Click "Create"

**Expected Results:**
- Workflow ID displayed
- Status: `active`
- Current Pass: `definition` (Pass 1)
- Current Step: `problem_definition` (Step 1)

**API Verification:**
```bash
curl http://localhost:8000/api/v1/workflows/{workflow_id}
```
- `status`: `"active"`
- `current_pass`: `"definition"`
- `current_step`: `"problem_definition"`
- `current_step_number`: `1`

---

### Step 2: Observe Pass 1 Step 1 Execution

**Action:**
1. Watch the workflow execute (automatic)
2. Wait for status to reach `awaiting_review`

**Expected Results:**
- Step executes methodology generation
- Status transitions to `awaiting_review`
- Phase shows `reviewing`

---

### Step 3: Approve Pass 1 Steps

**Action:** For each of Steps 1, 2, 3 in Pass 1:
1. Click "Approve" at the review gate
2. Verify step advances

**Expected Results after each approval:**

| After Approval | Next Step | Pass |
|----------------|-----------|------|
| Step 1 | requirements (Step 2) | definition |
| Step 2 | objectives (Step 3) | definition |
| Step 3 | problem_definition (Step 1) | **execution** |

**Key Checkpoint:** After Step 3 approval, verify transition to Pass 2:
- `current_pass`: `"execution"`
- `current_step`: `"problem_definition"`

---

### Step 4: Approve Pass 2 Steps

**Action:** For each of Steps 1, 2, 3 in Pass 2:
1. Review the step package artifact (if displayed)
2. Click "Approve" at the review gate
3. Verify step advances

**Expected Results after each approval:**

| After Approval | Next Step | Pass | Status |
|----------------|-----------|------|--------|
| P2 Step 1 | requirements | execution | active |
| P2 Step 2 | objectives | execution | active |
| P2 Step 3 | objectives | execution | **completed** |

---

### Step 5: Final Verification

**Action:**
1. Refresh workflow state
2. Query history for audit trail

**Expected Final State:**
```json
{
  "status": "completed",
  "current_pass": "execution",
  "current_step": "objectives",
  "current_step_number": 3,
  "completed_at": "2024-01-01T00:00:00Z"
}
```

**Artifact Verification (Gate A Scope):**
Note: Artifact counts and presence are Gate A scope (Phase 8), not γ1 scope.
For manual inspection, artifacts can be verified via:
```bash
curl "http://localhost:8000/api/v1/workflows/{workflow_id}/history?type=artifact"
```

**Audit Trail Verification:**
```bash
curl "http://localhost:8000/api/v1/workflows/{workflow_id}/history?type=event&limit=100"
```

Expected events (minimum):
- 6 `step_approved` events (3 Pass 1 + 3 Pass 2)
- 1 `workflow.completed` event (dot notation per spec §9.2.1)
- Various `state_change` events

---

## Verification Checklist

- [ ] Workflow created with status `active`
- [ ] Pass 1 Step 1 executes to `awaiting_review`
- [ ] Pass 1 Step 1 approval advances to Step 2
- [ ] Pass 1 Step 2 approval advances to Step 3
- [ ] Pass 1 Step 3 approval transitions to Pass 2 Step 1
- [ ] Pass 2 Step 1 approval advances to Step 2
- [ ] Pass 2 Step 2 approval advances to Step 3
- [ ] Pass 2 Step 3 approval completes workflow
- [ ] Final status is `completed`
- [ ] `completed_at` timestamp is set (non-null)
- [ ] History shows 6 `step_approved` events
- [ ] History shows 1 `workflow.completed` event

---

## Troubleshooting

### Workflow Stuck at Creation

**Symptoms:** Workflow created but doesn't execute
**Check:**
- API logs for errors
- LLM configuration (if using real LLM)
- Database connection

### Approval Fails with 409 Conflict

**Symptoms:** "State conflict" error on approval
**Cause:** Another process modified the workflow
**Solution:**
- Refresh workflow state
- Retry approval with updated `state_version`

### Missing Artifacts

**Symptoms:** No artifacts displayed for review
**Note:** This is expected for Pass 1 (methodology docs tracked via /history, not /progress)
**Check:** Query `/history?type=artifact` for artifact records

---

## Resolved Issues (Round 4)

1. **completed_at now exposed:** The `completed_at` timestamp is now included in `WorkflowResponse` API schema.

2. **workflow.completed event in /history:** The `workflow.completed` event (dot notation per spec §9.2.1) now appears in `/history?type=event` response via audit entry creation. Actor is always resolved to ensure reliable event recording.

3. **Artifact presence verification:** The `/progress` endpoint now works correctly and verifies artifact presence at each gate.

---

## Reference

- **Exit Gate:** γ1 (Workflow Lifecycle)
- **Package:** 7.1 Workflow Lifecycle Integration
- **Spec Reference:** Development Directive §7.1
