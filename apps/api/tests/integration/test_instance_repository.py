"""
Integration tests for InstanceRepository.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import Instance, InstanceType, GatePolicy
from infrastructure.db.repositories import InstanceRepository


class TestInstanceRepository:
    """Tests for InstanceRepository CRUD operations."""

    @pytest.mark.asyncio
    async def test_get_by_number_returns_instance_0(
        self,
        db_session: AsyncSession,
        instance_0: Instance,
    ):
        """Test that Instance 0 can be retrieved by number."""
        repo = InstanceRepository(db_session)

        result = await repo.get_by_number(0)

        assert result is not None
        assert result.instance_number == 0
        assert result.instance_type == InstanceType.UNIVERSAL
        assert result.name == "Universal Methodology"

    @pytest.mark.asyncio
    async def test_get_universal_returns_instance_0(
        self,
        db_session: AsyncSession,
        instance_0: Instance,
    ):
        """Test convenience method for getting Instance 0."""
        repo = InstanceRepository(db_session)

        result = await repo.get_universal()

        assert result is not None
        assert result.instance_number == 0

    @pytest.mark.asyncio
    async def test_get_by_number_returns_none_for_missing(
        self,
        db_session: AsyncSession,
    ):
        """Test that missing instance returns None."""
        repo = InstanceRepository(db_session)

        result = await repo.get_by_number(9999)

        assert result is None

    @pytest.mark.asyncio
    async def test_create_domain_instance(
        self,
        db_session: AsyncSession,
        instance_0: Instance,
    ):
        """Test creating a domain instance (Instance N >= 2)."""
        repo = InstanceRepository(db_session)

        instance = Instance(
            instance_number=2,
            instance_type=InstanceType.DOMAIN,
            parent_instance_id=instance_0.id,
            name="Test Domain",
            description="A test domain instance",
            pass_1_gate_policy=GatePolicy.PER_STEP,
        )

        created = await repo.create(instance)

        assert created.id is not None
        assert created.instance_number == 2
        assert created.instance_type == InstanceType.DOMAIN
        assert created.created_at is not None

    @pytest.mark.asyncio
    async def test_get_by_id(
        self,
        db_session: AsyncSession,
        instance_0: Instance,
    ):
        """Test getting instance by UUID."""
        repo = InstanceRepository(db_session)

        result = await repo.get_by_id(instance_0.id)

        assert result is not None
        assert result.id == instance_0.id
