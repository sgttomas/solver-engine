"""
Instance Repository - Instance hierarchy data access.

Provides data access for Instance 0/1/N hierarchy.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import Instance
from infrastructure.db.repositories.base import BaseRepository


class InstanceRepository(BaseRepository[Instance]):
    """Repository for Instance entities.

    Instance hierarchy:
    - Instance 0: Universal Methodology (seeded in migration)
    - Instance 1: SOLVER Implementation
    - Instance N (N>=2): Domain specializations
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Instance)

    async def get_by_number(self, instance_number: int) -> Optional[Instance]:
        """Get instance by its unique instance number.

        Args:
            instance_number: The instance number (0, 1, 2, ...)

        Returns:
            Instance if found, None otherwise
        """
        stmt = select(Instance).where(Instance.instance_number == instance_number)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_universal(self) -> Optional[Instance]:
        """Get Instance 0 (Universal Methodology).

        Convenience method for the most commonly accessed instance.

        Returns:
            Instance 0 if it exists, None otherwise
        """
        return await self.get_by_number(0)
