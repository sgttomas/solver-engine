"""
SOLVER API - PostgreSQL Infrastructure Adapter

Async database engine and session factory using SQLAlchemy.
Per Doc 2 Section 7 - Persistence Layer.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config import settings


def create_engine() -> AsyncEngine:
    """Create async SQLAlchemy engine using asyncpg driver.

    Uses settings.postgres_url which returns the async connection string:
    postgresql+asyncpg://user:pass@host:port/db
    """
    return create_async_engine(
        settings.postgres_url,
        echo=settings.debug,
        pool_pre_ping=True,
    )


# Global async engine instance
engine = create_engine()

# Async session factory
# expire_on_commit=False prevents lazy loading issues after commit
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session.

    Usage in FastAPI (P4):
        async def endpoint(session: AsyncSession = Depends(get_session)):
            ...

    For now (P2.2), used directly in tests and repositories.
    """
    async with async_session_factory() as session:
        yield session
