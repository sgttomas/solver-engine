"""
Integration tests for WorkflowRepository.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import (
    Instance,
    Workflow,
    WorkflowStatus,
    PassType,
    StepName,
    GatePolicy,
)
from infrastructure.db.repositories import WorkflowRepository


class TestWorkflowRepository:
    """Tests for WorkflowRepository CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_workflow(
        self,
        db_session: AsyncSession,
        instance_0: Instance,
    ):
        """Test creating a new workflow."""
        repo = WorkflowRepository(db_session)

        workflow = Workflow(
            workflow_id="test-create-wf",
            thread_id="test-create-thread",
            instance_id=instance_0.id,
            original_problem="Test problem",
            current_pass=PassType.DEFINITION,
            current_step=StepName.PROBLEM_DEFINITION,
            current_step_number=1,
            status=WorkflowStatus.ACTIVE,
            pass_1_gate_policy=GatePolicy.PER_STEP,
            created_by="test-user",
            last_actor_id="test-user",
        )

        created = await repo.create(workflow)

        assert created.id is not None
        assert created.workflow_id == "test-create-wf"
        assert created.thread_id == "test-create-thread"
        assert created.created_at is not None
        assert created.updated_at is not None

    @pytest.mark.asyncio
    async def test_get_by_workflow_id(
        self,
        db_session: AsyncSession,
        test_workflow: Workflow,
    ):
        """Test getting workflow by workflow_id string."""
        repo = WorkflowRepository(db_session)

        result = await repo.get_by_workflow_id(test_workflow.workflow_id)

        assert result is not None
        assert result.id == test_workflow.id
        assert result.workflow_id == test_workflow.workflow_id

    @pytest.mark.asyncio
    async def test_get_by_thread_id(
        self,
        db_session: AsyncSession,
        test_workflow: Workflow,
    ):
        """Test getting workflow by thread_id string."""
        repo = WorkflowRepository(db_session)

        result = await repo.get_by_thread_id(test_workflow.thread_id)

        assert result is not None
        assert result.id == test_workflow.id
        assert result.thread_id == test_workflow.thread_id

    @pytest.mark.asyncio
    async def test_get_by_workflow_id_returns_none_for_missing(
        self,
        db_session: AsyncSession,
    ):
        """Test that missing workflow_id returns None."""
        repo = WorkflowRepository(db_session)

        result = await repo.get_by_workflow_id("nonexistent-workflow")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id(
        self,
        db_session: AsyncSession,
        test_workflow: Workflow,
    ):
        """Test getting workflow by UUID."""
        repo = WorkflowRepository(db_session)

        result = await repo.get_by_id(test_workflow.id)

        assert result is not None
        assert result.id == test_workflow.id

    @pytest.mark.asyncio
    async def test_update_workflow_status(
        self,
        db_session: AsyncSession,
        test_workflow: Workflow,
    ):
        """Test updating workflow status."""
        repo = WorkflowRepository(db_session)

        # Update status
        test_workflow.status = WorkflowStatus.PAUSED
        updated = await repo.update(test_workflow)

        assert updated.status == WorkflowStatus.PAUSED

        # Verify persistence
        fetched = await repo.get_by_id(test_workflow.id)
        assert fetched.status == WorkflowStatus.PAUSED

    @pytest.mark.asyncio
    async def test_list_by_instance(
        self,
        db_session: AsyncSession,
        instance_0: Instance,
        test_workflow: Workflow,
    ):
        """Test listing workflows by instance."""
        repo = WorkflowRepository(db_session)

        results = await repo.list_by_instance(instance_0.id)

        assert len(results) >= 1
        assert any(w.id == test_workflow.id for w in results)

    @pytest.mark.asyncio
    async def test_list_by_status(
        self,
        db_session: AsyncSession,
        test_workflow: Workflow,
    ):
        """Test listing workflows by status."""
        repo = WorkflowRepository(db_session)

        results = await repo.list_by_status(WorkflowStatus.ACTIVE)

        assert len(results) >= 1
        assert any(w.id == test_workflow.id for w in results)

    @pytest.mark.asyncio
    async def test_delete_workflow(
        self,
        db_session: AsyncSession,
        instance_0: Instance,
    ):
        """Test deleting a workflow."""
        repo = WorkflowRepository(db_session)

        # Create a workflow to delete
        workflow = Workflow(
            workflow_id="test-delete-wf",
            thread_id="test-delete-thread",
            instance_id=instance_0.id,
            original_problem="Test problem to delete",
            current_pass=PassType.DEFINITION,
            current_step=StepName.PROBLEM_DEFINITION,
            current_step_number=1,
            status=WorkflowStatus.ACTIVE,
            pass_1_gate_policy=GatePolicy.PER_STEP,
            created_by="test-user",
            last_actor_id="test-user",
        )
        created = await repo.create(workflow)
        workflow_id = created.id

        # Delete it
        await repo.delete(created)

        # Verify deletion
        result = await repo.get_by_id(workflow_id)
        assert result is None
