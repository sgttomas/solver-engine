"""
Integration tests for ArtifactRepository.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import (
    Workflow,
    Artifact,
    PassType,
    StepName,
    DocumentType,
    DocumentVersion,
)
from infrastructure.db.repositories import ArtifactRepository


class TestArtifactRepository:
    """Tests for ArtifactRepository CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_methodology_doc(
        self,
        db_session: AsyncSession,
        test_workflow: Workflow,
    ):
        """Test creating a methodology document artifact."""
        repo = ArtifactRepository(db_session)

        artifact = Artifact(
            workflow_id=test_workflow.id,
            pass_type=PassType.DEFINITION,
            step_name=StepName.PROBLEM_DEFINITION,
            step_number=1,
            artifact_type="methodology_doc",
            document_type=DocumentType.DATA_SHEET,
            document_version=DocumentVersion.V1,
            content_markdown="# Data Sheet V1\n\nContent here...",
        )

        created = await repo.create(artifact)

        assert created.id is not None
        assert created.artifact_type == "methodology_doc"
        assert created.document_type == DocumentType.DATA_SHEET
        assert created.document_version == DocumentVersion.V1
        assert created.created_at is not None

    @pytest.mark.asyncio
    async def test_create_step_package(
        self,
        db_session: AsyncSession,
        test_workflow: Workflow,
    ):
        """Test creating a step package artifact."""
        repo = ArtifactRepository(db_session)

        package_content = {
            "problem_statement": "Test problem",
            "stakeholders": [{"id": "SH-001", "name": "User"}],
        }

        artifact = Artifact(
            workflow_id=test_workflow.id,
            pass_type=PassType.EXECUTION,
            step_name=StepName.PROBLEM_DEFINITION,
            step_number=1,
            artifact_type="step_package",
            package_type="ProblemDefinitionPackage",
            content_jsonb=package_content,
        )

        created = await repo.create(artifact)

        assert created.id is not None
        assert created.artifact_type == "step_package"
        assert created.package_type == "ProblemDefinitionPackage"
        assert created.content_jsonb == package_content

    @pytest.mark.asyncio
    async def test_list_for_workflow(
        self,
        db_session: AsyncSession,
        test_workflow: Workflow,
    ):
        """Test listing all artifacts for a workflow."""
        repo = ArtifactRepository(db_session)

        # Create two artifacts
        artifact1 = Artifact(
            workflow_id=test_workflow.id,
            pass_type=PassType.DEFINITION,
            step_name=StepName.PROBLEM_DEFINITION,
            step_number=1,
            artifact_type="methodology_doc",
            document_type=DocumentType.DATA_SHEET,
            document_version=DocumentVersion.V1,
            content_markdown="# DS V1",
        )
        artifact2 = Artifact(
            workflow_id=test_workflow.id,
            pass_type=PassType.DEFINITION,
            step_name=StepName.PROBLEM_DEFINITION,
            step_number=1,
            artifact_type="methodology_doc",
            document_type=DocumentType.TODO_LIST,
            document_version=DocumentVersion.V1,
            content_markdown="# TDL V1",
        )
        await repo.create(artifact1)
        await repo.create(artifact2)

        results = await repo.list_for_workflow(test_workflow.id)

        assert len(results) >= 2

    @pytest.mark.asyncio
    async def test_list_methodology_docs(
        self,
        db_session: AsyncSession,
        test_workflow: Workflow,
    ):
        """Test listing methodology docs for a step."""
        repo = ArtifactRepository(db_session)

        # Create methodology doc
        artifact = Artifact(
            workflow_id=test_workflow.id,
            pass_type=PassType.DEFINITION,
            step_name=StepName.REQUIREMENTS,
            step_number=2,
            artifact_type="methodology_doc",
            document_type=DocumentType.GUIDANCE,
            document_version=DocumentVersion.V1,
            content_markdown="# Guidance V1",
        )
        await repo.create(artifact)

        results = await repo.list_methodology_docs(
            workflow_id=test_workflow.id,
            step_name=StepName.REQUIREMENTS,
        )

        assert len(results) >= 1
        assert all(a.artifact_type == "methodology_doc" for a in results)

    @pytest.mark.asyncio
    async def test_get_methodology_doc(
        self,
        db_session: AsyncSession,
        test_workflow: Workflow,
    ):
        """Test getting a specific methodology document."""
        repo = ArtifactRepository(db_session)

        # Create the doc
        artifact = Artifact(
            workflow_id=test_workflow.id,
            pass_type=PassType.DEFINITION,
            step_name=StepName.OBJECTIVES,
            step_number=3,
            artifact_type="methodology_doc",
            document_type=DocumentType.DETAILED_PROCEDURE,
            document_version=DocumentVersion.V2,
            content_markdown="# DP V2",
        )
        await repo.create(artifact)

        # Retrieve it
        result = await repo.get_methodology_doc(
            workflow_id=test_workflow.id,
            step_name=StepName.OBJECTIVES,
            document_type=DocumentType.DETAILED_PROCEDURE,
            document_version=DocumentVersion.V2,
        )

        assert result is not None
        assert result.document_type == DocumentType.DETAILED_PROCEDURE
        assert result.document_version == DocumentVersion.V2

    @pytest.mark.asyncio
    async def test_get_by_id(
        self,
        db_session: AsyncSession,
        test_workflow: Workflow,
    ):
        """Test getting artifact by UUID."""
        repo = ArtifactRepository(db_session)

        artifact = Artifact(
            workflow_id=test_workflow.id,
            pass_type=PassType.DEFINITION,
            step_name=StepName.PROBLEM_DEFINITION,
            step_number=1,
            artifact_type="methodology_doc",
            document_type=DocumentType.DATA_SHEET,
            document_version=DocumentVersion.V1,
            content_markdown="# Test",
        )
        created = await repo.create(artifact)

        result = await repo.get_by_id(created.id)

        assert result is not None
        assert result.id == created.id
