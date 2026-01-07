"""
SOLVER API - Main FastAPI Application Entry Point
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.responses import JSONResponse

from routes.workflows import router as workflows_router


# ============================================================================
# Validation Error Response Schema (Spec Compliance)
# ============================================================================

class ValidationErrorResponse(BaseModel):
    """400 response for request validation failures.

    Per spec: Missing required fields should return 400 ValidationErrorResponse,
    not FastAPI's default 422.
    """
    error_code: str = "VALIDATION_ERROR"
    message: str
    errors: list[dict]


# ============================================================================
# Application
# ============================================================================

app = FastAPI(
    title="SOLVER API",
    description="Structured Reasoning Workflow Engine",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(workflows_router, prefix="/api/v1")


# ============================================================================
# Global Exception Handlers (Spec Compliance)
# ============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Convert FastAPI 422 to spec-compliant 400 ValidationErrorResponse.

    Per spec: Missing required fields should return 400 ValidationErrorResponse,
    not FastAPI's default 422. This applies to ALL endpoints globally.
    """
    return JSONResponse(
        status_code=400,
        content=ValidationErrorResponse(
            message="Request validation failed",
            errors=[
                {"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]}
                for e in exc.errors()
            ],
        ).model_dump(),
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "solver-api"}


@app.get("/test-llm")
async def test_llm():
    """Test LLM connectivity directly."""
    import httpx
    from config import settings

    async with httpx.AsyncClient() as client:
        r = await client.post(
            'https://api.openai.com/v1/responses',
            headers={
                'Authorization': f'Bearer {settings.openai_api_key}',
                'Content-Type': 'application/json'
            },
            json={'model': 'gpt-4o', 'input': 'Say hello in 3 words'},
            timeout=60
        )
    return {"status": r.status_code, "ok": r.status_code == 200}


@app.get("/test-llm-adapter")
async def test_llm_adapter():
    """Test LLM via the actual adapter."""
    from orchestration.nodes import get_default_adapter
    adapter = get_default_adapter()
    response = await adapter.generate([
        {"role": "user", "content": "Say hi"}
    ])
    return {"ok": True, "content": response.content[:50]}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "SOLVER API",
        "version": "0.1.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
