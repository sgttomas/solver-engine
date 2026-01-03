"""
Artifact Repository - Artifact data access.

Provides data access for methodology documents and step packages.
"""

from typing import Optional, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import (
    Artifact,
    PassType,
    StepName,
    DocumentType,
    DocumentVersion,
)
from infrastructure.db.repositories.base import BaseRepository


class ArtifactRepository(BaseRepository[Artifact]):
    """Repository for Artifact entities.

    Artifacts store two types of content:
    - 'methodology_doc': Pass 1 documents (DataSheet, ToDoList, etc.)
    - 'step_package': Pass 2 deliverables (ProblemDefinitionPackage, etc.)
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Artifact)

    async def list_for_workflow(self, workflow_id: UUID) -> List[Artifact]:
        """List all artifacts for a workflow.

        Args:
            workflow_id: Workflow UUID

        Returns:
            List of artifacts ordered by step number and revision
        """
        stmt = (
            select(Artifact)
            .where(Artifact.workflow_id == workflow_id)
            .order_by(Artifact.step_number, Artifact.revision)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_step(
        self,
        workflow_id: UUID,
        step_name: StepName,
    ) -> List[Artifact]:
        """List all artifacts for a specific step.

        Args:
            workflow_id: Workflow UUID
            step_name: Step name enum

        Returns:
            List of artifacts for the step
        """
        stmt = (
            select(Artifact)
            .where(
                Artifact.workflow_id == workflow_id,
                Artifact.step_name == step_name,
            )
            .order_by(Artifact.revision)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_methodology_docs(
        self,
        workflow_id: UUID,
        step_name: StepName,
        document_type: Optional[DocumentType] = None,
    ) -> List[Artifact]:
        """List methodology documents for a step.

        Args:
            workflow_id: Workflow UUID
            step_name: Step name enum
            document_type: Optional filter by document type

        Returns:
            List of methodology document artifacts
        """
        stmt = select(Artifact).where(
            Artifact.workflow_id == workflow_id,
            Artifact.step_name == step_name,
            Artifact.artifact_type == "methodology_doc",
        )

        if document_type is not None:
            stmt = stmt.where(Artifact.document_type == document_type)

        stmt = stmt.order_by(Artifact.document_version)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_methodology_doc(
        self,
        workflow_id: UUID,
        step_name: StepName,
        document_type: DocumentType,
        document_version: DocumentVersion,
    ) -> Optional[Artifact]:
        """Get a specific methodology document.

        Args:
            workflow_id: Workflow UUID
            step_name: Step name enum
            document_type: Document type (data_sheet, todo_list, etc.)
            document_version: Document version (v1, v2, v3)

        Returns:
            Artifact if found, None otherwise
        """
        stmt = select(Artifact).where(
            Artifact.workflow_id == workflow_id,
            Artifact.step_name == step_name,
            Artifact.artifact_type == "methodology_doc",
            Artifact.document_type == document_type,
            Artifact.document_version == document_version,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_step_package(
        self,
        workflow_id: UUID,
        step_name: StepName,
        revision: Optional[int] = None,
    ) -> Optional[Artifact]:
        """Get the step package for a step.

        Args:
            workflow_id: Workflow UUID
            step_name: Step name enum
            revision: Optional specific revision (latest if None)

        Returns:
            Artifact if found, None otherwise
        """
        stmt = select(Artifact).where(
            Artifact.workflow_id == workflow_id,
            Artifact.step_name == step_name,
            Artifact.artifact_type == "step_package",
        )

        if revision is not None:
            stmt = stmt.where(Artifact.revision == revision)
        else:
            stmt = stmt.order_by(Artifact.revision.desc())

        result = await self._session.execute(stmt)
        return result.scalars().first()
