"""
SOLVER API - Artifact Service

Use cases for artifact management with idempotent storage and schema validation.
"""

import copy
import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import jsonschema
from sqlalchemy.ext.asyncio import AsyncSession

from domain.state import StepName, STEP_NUMBERS
from infrastructure.db.models import (
    Artifact,
    PassType,
    DocumentType,
    DocumentVersion,
)
from infrastructure.db.repositories import ArtifactRepository
from application.schemas import get_schema_for_step


logger = logging.getLogger(__name__)


class SchemaValidationError(Exception):
    """Error validating artifact against JSON schema."""

    def __init__(self, errors: list[dict[str, Any]], raw_content: dict | None = None):
        self.errors = errors
        self.raw_content = raw_content
        super().__init__(f"Schema validation failed: {errors}")


class ArtifactService:
    """Service for artifact storage and validation.

    Handles two artifact types:
    - Methodology docs (Pass 1): 12 docs per step (4 doc_types × 3 versions)
    - Step packages (Pass 2): JSON packages with schema validation
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._artifact_repo = ArtifactRepository(session)

    async def store_methodology_docs(
        self,
        workflow_id: UUID,
        step_name: StepName,
        methodology_output: dict[str, dict[str, str]],
    ) -> list[Artifact]:
        """Store 12 methodology docs (4 doc_types × 3 versions) idempotently.

        Idempotency: Check (workflow_id, step_name, doc_type, doc_version) before insert.
        Skip if already exists.

        Args:
            workflow_id: Database workflow UUID.
            step_name: Step name (PROBLEM_DEFINITION, REQUIREMENTS, OBJECTIVES).
            methodology_output: Dict with structure {"v1": {...}, "v2": {...}, "v3": {...}}.

        Returns:
            List of created Artifact records (may be empty if all exist).
        """
        created_artifacts = []
        step_number = STEP_NUMBERS[step_name]

        # Map string keys to enums
        version_map = {"v1": DocumentVersion.V1, "v2": DocumentVersion.V2, "v3": DocumentVersion.V3}
        doc_type_map = {
            "data_sheet": DocumentType.DATA_SHEET,
            "todo_list": DocumentType.TODO_LIST,
            "guidance": DocumentType.GUIDANCE,
            "detailed_procedure": DocumentType.DETAILED_PROCEDURE,
        }

        for version_str, docs in methodology_output.items():
            if version_str not in version_map:
                logger.warning(f"Unknown version in methodology output: {version_str}")
                continue

            version_enum = version_map[version_str]

            for doc_type_str, content in docs.items():
                if doc_type_str not in doc_type_map:
                    logger.warning(f"Unknown doc type in methodology output: {doc_type_str}")
                    continue

                doc_type_enum = doc_type_map[doc_type_str]

                # Check if already exists (idempotent)
                existing = await self._artifact_repo.get_methodology_doc(
                    workflow_id=workflow_id,
                    step_name=step_name,
                    document_type=doc_type_enum,
                    document_version=version_enum,
                )
                if existing:
                    logger.debug(
                        f"Methodology doc already exists: {step_name.value} {doc_type_str} {version_str}"
                    )
                    continue

                # Create artifact
                artifact = Artifact(
                    id=uuid4(),
                    workflow_id=workflow_id,
                    pass_type=PassType.DEFINITION,
                    step_name=step_name,
                    step_number=step_number,
                    artifact_type="methodology_doc",
                    document_type=doc_type_enum,
                    document_version=version_enum,
                    content_markdown=content,
                    revision=1,
                    schema_version=None,
                    validation_status=None,
                    created_at=datetime.utcnow(),
                )
                self._session.add(artifact)
                created_artifacts.append(artifact)

                logger.info(
                    f"Created methodology doc: {step_name.value} {doc_type_str} {version_str}"
                )

        if created_artifacts:
            await self._session.flush()

        return created_artifacts

    async def store_step_package(
        self,
        workflow_id: UUID,
        instance_id: str,
        workflow_external_id: str,
        step_name: StepName,
        package_content: dict[str, Any],
        validate: bool = True,
    ) -> Artifact:
        """Store Pass 2 package with metadata injection and validation.

        Idempotency: Compare content against latest revision; only create new
        revision if content changed.

        Metadata injection (into COPY, not original):
        - package_id: Pre-generate artifact UUID, use for both content and row ID
        - workflow_id: External workflow ID string
        - instance_id: Instance ID string from workflow record
        - step_number: From STEP_NUMBERS mapping
        - version: Revision number (starts at 1)
        - created_at: ISO-8601 UTC timestamp

        Args:
            workflow_id: Database workflow UUID.
            instance_id: Instance ID string.
            workflow_external_id: External workflow ID string.
            step_name: Step name.
            package_content: Content-only dict from LLM (no metadata).
            validate: Whether to validate against schema (default True).

        Returns:
            Created or existing Artifact.

        Raises:
            SchemaValidationError: If validation fails and validate=True.
        """
        step_number = STEP_NUMBERS[step_name]

        # Check for existing package
        existing = await self._artifact_repo.get_step_package(
            workflow_id=workflow_id,
            step_name=step_name,
        )

        # Determine revision number
        if existing:
            # Compare content (excluding metadata for comparison)
            existing_content = existing.content_jsonb or {}
            existing_content_only = self._strip_metadata(existing_content)
            if existing_content_only == package_content:
                logger.debug(f"Package content unchanged: {step_name.value}")
                return existing
            revision = existing.revision + 1
        else:
            revision = 1

        # Pre-generate artifact ID (package_id = artifact.id)
        artifact_id = uuid4()
        created_at = datetime.utcnow()

        # Create copy with injected metadata (don't mutate original)
        package_with_metadata = self._inject_metadata(
            content=package_content,
            package_id=str(artifact_id),
            workflow_id=workflow_external_id,
            instance_id=instance_id,
            step_number=step_number,
            version=revision,
            created_at=created_at,
        )

        # Validate against schema
        validation_status = "valid"
        if validate:
            errors = self.validate_package(step_name, package_with_metadata)
            if errors:
                validation_status = "invalid"
                raise SchemaValidationError(errors=errors, raw_content=package_with_metadata)

        # Determine package type from step name
        package_type_map = {
            StepName.PROBLEM_DEFINITION: "ProblemDefinitionPackage",
            StepName.REQUIREMENTS: "RequirementsPackage",
            StepName.OBJECTIVES: "ObjectivesPackage",
        }
        package_type = package_type_map.get(step_name, f"{step_name.value}_package")

        # Create artifact
        artifact = Artifact(
            id=artifact_id,
            workflow_id=workflow_id,
            pass_type=PassType.EXECUTION,
            step_name=step_name,
            step_number=step_number,
            artifact_type="step_package",
            package_type=package_type,
            content_jsonb=package_with_metadata,
            revision=revision,
            schema_version="1.0.0",
            validation_status=validation_status,
            created_at=created_at,
        )
        self._session.add(artifact)
        await self._session.flush()

        logger.info(
            f"Created step package: {step_name.value} revision {revision}"
        )

        return artifact

    def validate_package(
        self,
        step_name: StepName,
        package: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Validate package against JSON schema.

        Args:
            step_name: Step name for schema lookup.
            package: Package dict with metadata injected.

        Returns:
            List of validation error dicts, empty if valid.
        """
        try:
            schema = get_schema_for_step(step_name)
        except KeyError:
            return [{"message": f"No schema defined for step: {step_name}"}]

        validator = jsonschema.Draft7Validator(schema)
        errors = []

        for error in validator.iter_errors(package):
            errors.append({
                "path": list(error.path),
                "message": error.message,
                "validator": error.validator,
                "schema_path": list(error.schema_path),
            })

        return errors

    def validate_package_content(
        self,
        step_name: StepName,
        content: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Validate content-only package by injecting temporary metadata.

        Used for validation during node execution (before persistence).
        Injects placeholder metadata to satisfy schema requirements.

        Args:
            step_name: Step name for schema lookup.
            content: Content-only dict (no metadata).

        Returns:
            List of validation error dicts, empty if valid.
        """
        # Inject placeholder metadata into copy
        temp_package = self._inject_metadata(
            content=content,
            package_id="00000000-0000-0000-0000-000000000000",
            workflow_id="00000000-0000-0000-0000-000000000000",
            instance_id="00000000-0000-0000-0000-000000000000",
            step_number=STEP_NUMBERS[step_name],
            version=1,
            created_at=datetime.utcnow(),
        )

        return self.validate_package(step_name, temp_package)

    def _inject_metadata(
        self,
        content: dict[str, Any],
        package_id: str,
        workflow_id: str,
        instance_id: str,
        step_number: int,
        version: int,
        created_at: datetime,
    ) -> dict[str, Any]:
        """Inject metadata fields into a copy of the content.

        Does NOT mutate the original content dict.

        Args:
            content: Original content dict.
            package_id: Package UUID string.
            workflow_id: Workflow UUID string.
            instance_id: Instance UUID string.
            step_number: Step number (1, 2, 3).
            version: Revision number.
            created_at: Creation timestamp.

        Returns:
            New dict with metadata fields merged.
        """
        result = copy.deepcopy(content)
        result["package_id"] = package_id
        result["workflow_id"] = workflow_id
        result["instance_id"] = instance_id
        result["step_number"] = step_number
        result["version"] = version
        result["created_at"] = created_at.isoformat() + "Z"
        return result

    def _strip_metadata(self, package: dict[str, Any]) -> dict[str, Any]:
        """Remove metadata fields from package for content comparison.

        Args:
            package: Package dict with metadata.

        Returns:
            New dict with metadata fields removed.
        """
        metadata_keys = {
            "package_id",
            "workflow_id",
            "instance_id",
            "step_number",
            "version",
            "created_at",
        }
        return {k: v for k, v in package.items() if k not in metadata_keys}

    async def get_methodology_doc(
        self,
        workflow_id: UUID,
        step_name: StepName,
        document_type: DocumentType,
        document_version: DocumentVersion,
    ) -> Artifact | None:
        """Get a specific methodology document.

        Args:
            workflow_id: Database workflow UUID.
            step_name: Step name.
            document_type: Document type enum.
            document_version: Document version enum.

        Returns:
            Artifact if found, None otherwise.
        """
        return await self._artifact_repo.get_methodology_doc(
            workflow_id=workflow_id,
            step_name=step_name,
            document_type=document_type,
            document_version=document_version,
        )

    async def get_step_package(
        self,
        workflow_id: UUID,
        step_name: StepName,
        revision: int | None = None,
    ) -> Artifact | None:
        """Get the step package for a step.

        Args:
            workflow_id: Database workflow UUID.
            step_name: Step name.
            revision: Specific revision (latest if None).

        Returns:
            Artifact if found, None otherwise.
        """
        return await self._artifact_repo.get_step_package(
            workflow_id=workflow_id,
            step_name=step_name,
            revision=revision,
        )

    async def list_methodology_docs(
        self,
        workflow_id: UUID,
        step_name: StepName,
    ) -> list[Artifact]:
        """List all methodology docs for a step.

        Args:
            workflow_id: Database workflow UUID.
            step_name: Step name.

        Returns:
            List of methodology doc artifacts.
        """
        return await self._artifact_repo.list_methodology_docs(
            workflow_id=workflow_id,
            step_name=step_name,
        )
