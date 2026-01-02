"""
SOLVER API - Health Check Routes
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "solver-api"}
