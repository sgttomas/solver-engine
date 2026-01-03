"""
Integration tests for StepExecutionRepository.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import (
    Workflow,
    StepExecution,
    PassType,
    StepName,
    StepStatus,
    StepPhase,
)
from infrastructure.db.repositories import StepExecutionRepository


class TestStepExecutionRepository:
    """Tests for StepExecutionRepository CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_step_execution(
        self,
        db_session: AsyncSession,
        test_workflow: Workflow,
    ):
        """Test creating a step execution."""
        repo = StepExecutionRepository(db_session)

        step = StepExecution(
            workflow_id=test_workflow.id,
            pass_type=PassType.DEFINITION,
            step_name=StepName.REQUIREMENTS,
            step_number=2,
            status=StepStatus.NOT_STARTED,
            phase=StepPhase.RECEIVED,
        )

        created = await repo.create(step)

        assert created.id is not None
        assert created.workflow_id == test_workflow.id
        assert created.step_name == StepName.REQUIREMENTS
        assert created.step_number == 2

    @pytest.mark.asyncio
    async def test_get_by_composite(
        self,
        db_session: AsyncSession,
        test_workflow: Workflow,
        test_step_execution: StepExecution,
    ):
        """Test getting step by composite unique key."""
        repo = StepExecutionRepository(db_session)

        result = await repo.get_by_composite(
            workflow_id=test_workflow.id,
            pass_type=PassType.DEFINITION,
            step_name=StepName.PROBLEM_DEFINITION,
        )

        assert result is not None
        assert result.id == test_step_execution.id

    @pytest.mark.asyncio
    async def test_get_by_composite_returns_none_for_missing(
        self,
        db_session: AsyncSession,
        test_workflow: Workflow,
    ):
        """Test that missing step returns None."""
        repo = StepExecutionRepository(db_session)

        result = await repo.get_by_composite(
            workflow_id=test_workflow.id,
            pass_type=PassType.DEFINITION,
            step_name=StepName.RESOLUTION,  # Step 10, not created
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_list_for_workflow(
        self,
        db_session: AsyncSession,
        test_workflow: Workflow,
        test_step_execution: StepExecution,
    ):
        """Test listing all steps for a workflow."""
        repo = StepExecutionRepository(db_session)

        # Create additional step
        step2 = StepExecution(
            workflow_id=test_workflow.id,
            pass_type=PassType.DEFINITION,
            step_name=StepName.REQUIREMENTS,
            step_number=2,
            status=StepStatus.NOT_STARTED,
            phase=StepPhase.RECEIVED,
        )
        await repo.create(step2)

        results = await repo.list_for_workflow(test_workflow.id)

        assert len(results) >= 2
        # Should be ordered by step_number
        step_numbers = [s.step_number for s in results]
        assert step_numbers == sorted(step_numbers)

    @pytest.mark.asyncio
    async def test_list_for_pass(
        self,
        db_session: AsyncSession,
        test_workflow: Workflow,
        test_step_execution: StepExecution,
    ):
        """Test listing steps for a specific pass."""
        repo = StepExecutionRepository(db_session)

        results = await repo.list_for_pass(
            workflow_id=test_workflow.id,
            pass_type=PassType.DEFINITION,
        )

        assert len(results) >= 1
        assert all(s.pass_type == PassType.DEFINITION for s in results)

    @pytest.mark.asyncio
    async def test_update_step_status(
        self,
        db_session: AsyncSession,
        test_step_execution: StepExecution,
    ):
        """Test updating step status and phase."""
        repo = StepExecutionRepository(db_session)

        test_step_execution.status = StepStatus.IN_PROGRESS
        test_step_execution.phase = StepPhase.ANALYZING
        updated = await repo.update(test_step_execution)

        assert updated.status == StepStatus.IN_PROGRESS
        assert updated.phase == StepPhase.ANALYZING

    @pytest.mark.asyncio
    async def test_get_by_id(
        self,
        db_session: AsyncSession,
        test_step_execution: StepExecution,
    ):
        """Test getting step by UUID."""
        repo = StepExecutionRepository(db_session)

        result = await repo.get_by_id(test_step_execution.id)

        assert result is not None
        assert result.id == test_step_execution.id
