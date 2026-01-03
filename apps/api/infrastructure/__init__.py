"""
SOLVER Infrastructure Layer.

Provides adapters for external services:
- db: Database models and repositories
- llm: LLM provider adapters
- observability: Tracing and monitoring
"""

from infrastructure import db  # noqa: F401

__all__ = ["db"]
