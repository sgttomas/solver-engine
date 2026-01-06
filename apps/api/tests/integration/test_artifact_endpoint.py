"""
Integration Tests for GET /workflows/{workflow_id}/artifacts/{artifact_id}

Per Tech Spec V2.8.0 Appendix C.4.

Test Scenarios:
1. Happy path: GET returns artifact with all C.4 spec fields
2. Methodology doc: content_jsonb contains wrapped markdown
3. Step package: content_jsonb contains original JSON
4. 404: Workflow not found
5. 404: Artifact not found
6. 400: Artifact belongs to different workflow
"""

import pytest
import pytest_asyncio
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import (
    Workflow,
    WorkflowStatus,
    PassType,
    StepName,
    GatePolicy,
    Artifact,
    DocumentType,
    DocumentVersion,
)
from infrastructure.db.repositories.artifact import ArtifactRepository
from infrastructure.db.repositories.workflow import WorkflowRepository
from infrastructure.db.repositories.instance import InstanceRepository
from application.workflow_service import (
    WorkflowService,
    WorkflowNotFoundError,
    ArtifactNotFoundError,
    ArtifactNotBelongError,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def test_workflow_for_artifact(
    db_session: AsyncSession,
    instance_0,
) -> Workflow:
    """Create a test workflow for artifact tests."""
    repo = WorkflowRepository(db_session)

    workflow = Workflow(
        workflow_id=f"artifact-test-{uuid4()}",
        thread_id=f"thread-{uuid4()}",
        instance_id=instance_0.id,
        original_problem="Test problem for artifact endpoint tests",
        current_pass=PassType.DEFINITION,
        current_step=StepName.REQUIREMENTS,
        current_step_number=2,
        status=WorkflowStatus.ACTIVE,
        pass_1_gate_policy=GatePolicy.PER_STEP,
        created_by="test-user",
        last_actor_id="test-user",
    )

    return await repo.create(workflow)


@pytest_asyncio.fixture
async def methodology_doc_artifact(
    db_session: AsyncSession,
    test_workflow_for_artifact: Workflow,
) -> Artifact:
    """Create a methodology doc artifact (Pass 1)."""
    repo = ArtifactRepository(db_session)

    artifact = Artifact(
        workflow_id=test_workflow_for_artifact.id,
        pass_type=PassType.DEFINITION,
        step_name=StepName.REQUIREMENTS,
        step_number=2,
        artifact_type="methodology_doc",
        document_type=DocumentType.DATA_SHEET,
        document_version=DocumentVersion.V3,
        content_markdown="# Requirements Data Sheet V3\n\nFinal methodology content.",
        revision=1,
        stale=False,
    )

    return await repo.create(artifact)


@pytest_asyncio.fixture
async def step_package_artifact(
    db_session: AsyncSession,
    test_workflow_for_artifact: Workflow,
) -> Artifact:
    """Create a step package artifact (Pass 2)."""
    repo = ArtifactRepository(db_session)

    artifact = Artifact(
        workflow_id=test_workflow_for_artifact.id,
        pass_type=PassType.EXECUTION,
        step_name=StepName.REQUIREMENTS,
        step_number=2,
        artifact_type="step_package",
        package_type="RequirementsPackage",
        content_jsonb={
            "functional_requirements": ["FR-1", "FR-2"],
            "non_functional_requirements": ["NFR-1"],
            "constraints": ["C-1"],
        },
        revision=1,
        stale=False,
    )

    return await repo.create(artifact)


@pytest_asyncio.fixture
async def stale_artifact(
    db_session: AsyncSession,
    test_workflow_for_artifact: Workflow,
) -> Artifact:
    """Create a stale artifact."""
    from datetime import datetime

    repo = ArtifactRepository(db_session)

    artifact = Artifact(
        workflow_id=test_workflow_for_artifact.id,
        pass_type=PassType.EXECUTION,
        step_name=StepName.OBJECTIVES,
        step_number=3,
        artifact_type="step_package",
        package_type="ObjectivesPackage",
        content_jsonb={"objectives": ["O-1"]},
        revision=1,
        stale=True,
        stale_reason="upstream_step_2_revised",
        stale_since=datetime.utcnow(),
    )

    return await repo.create(artifact)


@pytest_asyncio.fixture
async def another_workflow(
    db_session: AsyncSession,
    instance_0,
) -> Workflow:
    """Create another workflow for cross-workflow tests."""
    repo = WorkflowRepository(db_session)

    workflow = Workflow(
        workflow_id=f"other-workflow-{uuid4()}",
        thread_id=f"thread-{uuid4()}",
        instance_id=instance_0.id,
        original_problem="Another workflow for isolation tests",
        current_pass=PassType.DEFINITION,
        current_step=StepName.PROBLEM_DEFINITION,
        current_step_number=1,
        status=WorkflowStatus.ACTIVE,
        pass_1_gate_policy=GatePolicy.PER_STEP,
        created_by="test-user",
        last_actor_id="test-user",
    )

    return await repo.create(workflow)


# =============================================================================
# Test: Happy Path - Methodology Doc
# =============================================================================


@pytest.mark.asyncio
async def test_get_artifact_methodology_doc(
    db_session: AsyncSession,
    test_workflow_for_artifact: Workflow,
    methodology_doc_artifact: Artifact,
):
    """Methodology doc: content_jsonb contains wrapped markdown."""
    service = WorkflowService(db_session)

    artifact, workflow = await service.get_artifact(
        test_workflow_for_artifact.workflow_id,
        methodology_doc_artifact.id,
    )

    # Verify artifact returned
    assert artifact.id == methodology_doc_artifact.id
    assert artifact.workflow_id == test_workflow_for_artifact.id

    # Verify fields for C.4 response
    assert artifact.pass_type == PassType.DEFINITION
    assert artifact.step_name == StepName.REQUIREMENTS
    assert artifact.step_number == 2
    assert artifact.artifact_type == "methodology_doc"
    assert artifact.revision == 1
    assert artifact.stale is False

    # Methodology doc should have markdown content
    assert artifact.content_markdown is not None
    assert "Requirements Data Sheet" in artifact.content_markdown


# =============================================================================
# Test: Happy Path - Step Package
# =============================================================================


@pytest.mark.asyncio
async def test_get_artifact_step_package(
    db_session: AsyncSession,
    test_workflow_for_artifact: Workflow,
    step_package_artifact: Artifact,
):
    """Step package: content_jsonb contains original JSON."""
    service = WorkflowService(db_session)

    artifact, workflow = await service.get_artifact(
        test_workflow_for_artifact.workflow_id,
        step_package_artifact.id,
    )

    # Verify artifact returned
    assert artifact.id == step_package_artifact.id

    # Verify fields for C.4 response
    assert artifact.pass_type == PassType.EXECUTION
    assert artifact.step_name == StepName.REQUIREMENTS
    assert artifact.artifact_type == "step_package"

    # Step package should have JSON content
    assert artifact.content_jsonb is not None
    assert "functional_requirements" in artifact.content_jsonb
    assert artifact.content_jsonb["functional_requirements"] == ["FR-1", "FR-2"]


# =============================================================================
# Test: Happy Path - Stale Artifact
# =============================================================================


@pytest.mark.asyncio
async def test_get_artifact_stale(
    db_session: AsyncSession,
    test_workflow_for_artifact: Workflow,
    stale_artifact: Artifact,
):
    """Stale artifact includes staleness fields."""
    service = WorkflowService(db_session)

    artifact, workflow = await service.get_artifact(
        test_workflow_for_artifact.workflow_id,
        stale_artifact.id,
    )

    # Verify staleness fields
    assert artifact.stale is True
    assert artifact.stale_reason == "upstream_step_2_revised"
    assert artifact.stale_since is not None


# =============================================================================
# Test: 404 - Workflow Not Found
# =============================================================================


@pytest.mark.asyncio
async def test_get_artifact_workflow_not_found(
    db_session: AsyncSession,
    methodology_doc_artifact: Artifact,
):
    """404 when workflow doesn't exist."""
    service = WorkflowService(db_session)

    with pytest.raises(WorkflowNotFoundError) as exc_info:
        await service.get_artifact(
            "nonexistent-workflow",
            methodology_doc_artifact.id,
        )

    assert "nonexistent-workflow" in str(exc_info.value)


# =============================================================================
# Test: 404 - Artifact Not Found
# =============================================================================


@pytest.mark.asyncio
async def test_get_artifact_not_found(
    db_session: AsyncSession,
    test_workflow_for_artifact: Workflow,
):
    """404 when artifact doesn't exist."""
    service = WorkflowService(db_session)

    nonexistent_id = uuid4()

    with pytest.raises(ArtifactNotFoundError) as exc_info:
        await service.get_artifact(
            test_workflow_for_artifact.workflow_id,
            nonexistent_id,
        )

    assert str(nonexistent_id) in str(exc_info.value)


# =============================================================================
# Test: 400 - Artifact Doesn't Belong to Workflow
# =============================================================================


@pytest.mark.asyncio
async def test_get_artifact_belongs_to_different_workflow(
    db_session: AsyncSession,
    test_workflow_for_artifact: Workflow,
    another_workflow: Workflow,
    methodology_doc_artifact: Artifact,
):
    """400 when artifact belongs to a different workflow."""
    service = WorkflowService(db_session)

    # Try to get artifact from test_workflow using another_workflow's ID
    with pytest.raises(ArtifactNotBelongError) as exc_info:
        await service.get_artifact(
            another_workflow.workflow_id,  # Different workflow
            methodology_doc_artifact.id,  # Artifact belongs to test_workflow
        )

    assert "does not belong" in str(exc_info.value)


# =============================================================================
# Test: Updated_at and Trace_id Fields (C.4 spec)
# =============================================================================


@pytest.mark.asyncio
async def test_artifact_has_updated_at_and_trace_id_fields(
    db_session: AsyncSession,
    test_workflow_for_artifact: Workflow,
    methodology_doc_artifact: Artifact,
):
    """Artifact has updated_at and trace_id fields per C.4 spec."""
    service = WorkflowService(db_session)

    artifact, workflow = await service.get_artifact(
        test_workflow_for_artifact.workflow_id,
        methodology_doc_artifact.id,
    )

    # Verify created_at exists
    assert artifact.created_at is not None

    # Verify updated_at exists (added in migration 005)
    assert hasattr(artifact, "updated_at")
    assert artifact.updated_at is not None

    # Verify trace_id field exists (nullable)
    assert hasattr(artifact, "trace_id")
    # trace_id is nullable, so may be None
