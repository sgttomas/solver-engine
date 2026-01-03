"""
Base Repository - Generic async repository pattern.

Provides common CRUD operations for SQLAlchemy models.
Repositories never commit/rollback - caller owns the transaction.
"""

from typing import Generic, TypeVar, Optional, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models.base import Base

# Type variable for model classes
T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Generic async repository with common CRUD operations.

    Transaction Ownership:
    - Repositories use flush() to send SQL to DB
    - Repositories use refresh() to load DB-generated values
    - Repositories NEVER call commit() or rollback()
    - Caller (service layer) owns the transaction

    Usage:
        class WorkflowRepository(BaseRepository[Workflow]):
            def __init__(self, session: AsyncSession):
                super().__init__(session, Workflow)
    """

    def __init__(self, session: AsyncSession, model: type[T]) -> None:
        """Initialize repository with session and model class.

        Args:
            session: Async SQLAlchemy session (injected by caller)
            model: SQLAlchemy model class for this repository
        """
        self._session = session
        self._model = model

    async def get_by_id(self, id: UUID) -> Optional[T]:
        """Get entity by primary key UUID.

        Args:
            id: Primary key UUID

        Returns:
            Entity if found, None otherwise
        """
        return await self._session.get(self._model, id)

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """Get all entities with pagination.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of entities
        """
        stmt = select(self._model).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, entity: T) -> T:
        """Create a new entity.

        Adds entity to session, flushes to get DB-generated values,
        and refreshes to load those values into the entity.

        Args:
            entity: Entity to create

        Returns:
            Created entity with DB-generated values (id, timestamps, etc.)
        """
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def update(self, entity: T) -> T:
        """Update an existing entity.

        Flushes changes to DB and refreshes to ensure consistency.
        Entity must already be attached to the session.

        Args:
            entity: Entity to update

        Returns:
            Updated entity
        """
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def delete(self, entity: T) -> None:
        """Delete an entity.

        Marks entity for deletion. Deletion occurs on flush/commit.

        Args:
            entity: Entity to delete
        """
        await self._session.delete(entity)
        await self._session.flush()
