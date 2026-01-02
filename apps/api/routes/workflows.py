"""
SOLVER API - Workflow Routes

Endpoints for workflow management per Doc 3 Section 9.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/workflows", tags=["workflows"])

# stub - P4 will implement:
# POST   /workflows                    Create new workflow
# GET    /workflows/{id}               Get workflow state
# POST   /workflows/{id}/clarify       Submit clarification answers
# POST   /workflows/{id}/resume        Submit human decision
# GET    /workflows/{id}/stream        SSE stream
# DELETE /workflows/{id}               Abandon workflow
