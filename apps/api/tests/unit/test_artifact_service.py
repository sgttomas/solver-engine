"""
Unit Tests for P5.3 Artifact Service

Tests artifact storage, schema validation, and metadata injection.
"""

import pytest
from datetime import datetime
from uuid import uuid4

from domain.state import StepName, STEP_NUMBERS
from application.artifact_service import ArtifactService, SchemaValidationError
from application.schemas import (
    get_schema_for_step,
    get_required_content_fields,
    PROBLEM_DEFINITION_SCHEMA,
    REQUIREMENTS_SCHEMA,
    OBJECTIVES_SCHEMA,
)


# =============================================================================
# Test Schema Loading
# =============================================================================


class TestSchemaLoading:
    """Test schema loading and access."""

    def test_problem_definition_schema_loaded(self):
        """Problem definition schema loads successfully."""
        assert PROBLEM_DEFINITION_SCHEMA is not None
        assert PROBLEM_DEFINITION_SCHEMA["title"] == "ProblemDefinitionPackage"
        assert "properties" in PROBLEM_DEFINITION_SCHEMA

    def test_requirements_schema_loaded(self):
        """Requirements schema loads successfully."""
        assert REQUIREMENTS_SCHEMA is not None
        assert REQUIREMENTS_SCHEMA["title"] == "RequirementsPackage"

    def test_objectives_schema_loaded(self):
        """Objectives schema loads successfully."""
        assert OBJECTIVES_SCHEMA is not None
        assert OBJECTIVES_SCHEMA["title"] == "ObjectivesPackage"

    def test_get_schema_for_step(self):
        """get_schema_for_step returns correct schema for each step."""
        assert get_schema_for_step(StepName.PROBLEM_DEFINITION) == PROBLEM_DEFINITION_SCHEMA
        assert get_schema_for_step(StepName.REQUIREMENTS) == REQUIREMENTS_SCHEMA
        assert get_schema_for_step(StepName.OBJECTIVES) == OBJECTIVES_SCHEMA

    def test_get_schema_for_invalid_step_raises(self):
        """get_schema_for_step raises KeyError for unsupported steps."""
        with pytest.raises(KeyError):
            get_schema_for_step(StepName.VERIFICATION_DESIGN)

    def test_get_required_content_fields_step1(self):
        """Step 1 required content fields match schema."""
        fields = get_required_content_fields(StepName.PROBLEM_DEFINITION)
        assert "title" in fields
        assert "canonical_problem_definition" in fields
        assert "stakeholders" in fields
        # Metadata fields should NOT be in content fields
        assert "package_id" not in fields
        assert "workflow_id" not in fields

    def test_get_required_content_fields_step2(self):
        """Step 2 required content fields match schema."""
        fields = get_required_content_fields(StepName.REQUIREMENTS)
        assert "overview" in fields
        assert "requirements" in fields
        assert "coverage_map" in fields

    def test_get_required_content_fields_step3(self):
        """Step 3 required content fields match schema."""
        fields = get_required_content_fields(StepName.OBJECTIVES)
        assert "overview" in fields
        assert "objectives" in fields
        assert "success_framework" in fields
        assert "trace_map" in fields


# =============================================================================
# Test Metadata Injection
# =============================================================================


class TestMetadataInjection:
    """Test metadata injection without mutating original."""

    def test_inject_metadata_creates_copy(self):
        """_inject_metadata does not mutate original dict."""
        service = ArtifactService.__new__(ArtifactService)
        original = {"title": "Test", "data": [1, 2, 3]}

        result = service._inject_metadata(
            content=original,
            package_id="abc-123",
            workflow_id="wf-456",
            instance_id="inst-789",
            step_number=1,
            version=1,
            created_at=datetime.utcnow(),
        )

        # Original unchanged
        assert "package_id" not in original
        assert "workflow_id" not in original

        # Result has metadata
        assert result["package_id"] == "abc-123"
        assert result["workflow_id"] == "wf-456"
        assert result["instance_id"] == "inst-789"
        assert result["step_number"] == 1
        assert result["version"] == 1
        assert "created_at" in result

        # Original content preserved
        assert result["title"] == "Test"
        assert result["data"] == [1, 2, 3]

    def test_inject_metadata_preserves_nested_dicts(self):
        """Nested dicts are deep copied."""
        service = ArtifactService.__new__(ArtifactService)
        original = {"nested": {"key": "value"}}

        result = service._inject_metadata(
            content=original,
            package_id="abc",
            workflow_id="wf",
            instance_id="inst",
            step_number=1,
            version=1,
            created_at=datetime.utcnow(),
        )

        # Modify result nested dict
        result["nested"]["key"] = "modified"

        # Original unchanged
        assert original["nested"]["key"] == "value"


# =============================================================================
# Test Metadata Stripping
# =============================================================================


class TestMetadataStripping:
    """Test metadata stripping for content comparison."""

    def test_strip_metadata_removes_all_fields(self):
        """_strip_metadata removes all 6 metadata fields."""
        service = ArtifactService.__new__(ArtifactService)
        package = {
            "package_id": "abc-123",
            "workflow_id": "wf-456",
            "instance_id": "inst-789",
            "step_number": 1,
            "version": 1,
            "created_at": "2024-01-01T00:00:00Z",
            "title": "Test",
            "content_field": "data",
        }

        result = service._strip_metadata(package)

        # Metadata removed
        assert "package_id" not in result
        assert "workflow_id" not in result
        assert "instance_id" not in result
        assert "step_number" not in result
        assert "version" not in result
        assert "created_at" not in result

        # Content preserved
        assert result["title"] == "Test"
        assert result["content_field"] == "data"


# =============================================================================
# Test Schema Validation
# =============================================================================


class TestSchemaValidation:
    """Test JSON schema validation."""

    def test_validate_valid_step1_content(self):
        """Valid Step 1 content passes validation."""
        service = ArtifactService.__new__(ArtifactService)
        content = {
            "title": "Test Problem",
            "canonical_problem_definition": {"statement": "Test statement"},
            "stakeholders": [{
                "id": "SH-001",
                "name_or_group": "Test User",
                "role": "User",
                "needs": ["Need 1"],
                "concerns": ["Concern 1"],
                "impact": "High",
            }],
            "constraints": {
                "hard": [],
                "soft": [],
            },
            "scope": {
                "in": [],
                "out": [],
            },
            "success_criteria": [{
                "id": "CRT-001",
                "metric_or_signal": "Test metric",
                "target": "100%",
                "how_verified": "Test verification",
            }],
        }

        errors = service.validate_package_content(StepName.PROBLEM_DEFINITION, content)
        assert len(errors) == 0

    def test_validate_missing_required_field(self):
        """Missing required field produces validation error."""
        service = ArtifactService.__new__(ArtifactService)
        content = {
            "title": "Test Problem",
            # Missing canonical_problem_definition and other required fields
        }

        errors = service.validate_package_content(StepName.PROBLEM_DEFINITION, content)
        assert len(errors) > 0
        # Should report missing fields
        messages = [e.get("message", "") for e in errors]
        assert any("required" in msg.lower() for msg in messages)

    def test_validate_invalid_id_pattern(self):
        """Invalid ID pattern produces validation error."""
        service = ArtifactService.__new__(ArtifactService)
        content = {
            "title": "Test Problem",
            "canonical_problem_definition": {"statement": "Test"},
            "stakeholders": [{
                "id": "INVALID-ID",  # Should be SH-NNN
                "name_or_group": "Test",
                "role": "User",
                "needs": [],
                "concerns": [],
                "impact": "High",
            }],
            "constraints": {"hard": [], "soft": []},
            "scope": {"in": [], "out": []},
            "success_criteria": [{
                "id": "CRT-001",
                "metric_or_signal": "Test",
                "target": "100%",
                "how_verified": "Test",
            }],
        }

        errors = service.validate_package_content(StepName.PROBLEM_DEFINITION, content)
        assert len(errors) > 0
        # Should report pattern mismatch
        messages = [e.get("message", "") for e in errors]
        assert any("SH-" in msg or "pattern" in msg.lower() for msg in messages)

    def test_validate_step2_content(self):
        """Valid Step 2 content passes validation."""
        service = ArtifactService.__new__(ArtifactService)
        content = {
            "overview": {
                "summary": "Test requirements",
                "boundaries": [],
                "total_requirements": 1,
                "priority_distribution": {"must": 1, "should": 0, "could": 0},
            },
            "requirements": [{
                "id": "FR-001",
                "category": "FR",
                "priority": "must",
                "statement": "The system shall...",
                "rationale": "Because...",
                "source": {
                    "type": "stakeholder",
                    "id": "SH-001",
                    "aspect": "need",
                },
                "component": ["API"],
                "testability": {
                    "method": "test",
                    "description": "Unit tests",
                },
                "trace": {
                    "stakeholders": ["SH-001"],
                },
            }],
            "coverage_map": [{
                "source_type": "stakeholder",
                "source_id": "SH-001",
                "requirement_ids": ["FR-001"],
                "coverage_note": "Full coverage",
            }],
        }

        errors = service.validate_package_content(StepName.REQUIREMENTS, content)
        assert len(errors) == 0

    def test_validate_step3_content(self):
        """Valid Step 3 content passes validation."""
        service = ArtifactService.__new__(ArtifactService)
        content = {
            "overview": {
                "intent": "Deliver capabilities",
                "measurement_principles": [],
                "boundaries": [],
                "total_objectives": 1,
                "consolidation_ratio": 1.0,
            },
            "objectives": [{
                "id": "CAP-001",
                "category": "CAP",
                "tier": "primary",
                "statement": "Users can manage tasks",
                "rationale": "Core capability",
                "owner_type": "system",
                "linked_requirements": ["FR-001"],
                "consolidated": False,
                "success_criteria": {
                    "definition": "Tasks are manageable",
                    "verification": {
                        "method": "demonstration",
                        "description": "Demo the feature",
                        "evidence_artifacts": ["demo_video"],
                    },
                    "metric": None,
                    "threshold": None,
                },
                "component": ["API"],
                "acceptance_criteria": ["CRT-001"],
            }],
            "success_framework": {
                "minimum_viable": {
                    "description": "MVP",
                    "objectives": ["CAP-001"],
                    "requirement_coverage": ["FR-001"],
                },
                "target": {
                    "description": "Full release",
                    "objectives": ["CAP-001"],
                    "requirement_coverage": ["FR-001"],
                },
                "aspirational": {
                    "description": "Exceeds expectations",
                    "objectives": ["CAP-001"],
                    "requirement_coverage": ["FR-001"],
                },
            },
            "trace_map": [{
                "objective_id": "CAP-001",
                "requirement_ids": ["FR-001"],
                "consolidated": False,
            }],
        }

        errors = service.validate_package_content(StepName.OBJECTIVES, content)
        assert len(errors) == 0


# =============================================================================
# Test validate_output Integration
# =============================================================================


class TestValidateOutputIntegration:
    """Test validate_output function with pass_type."""

    @pytest.mark.asyncio
    async def test_pass1_basic_validation(self):
        """Pass 1 validates methodology structure (v1, v2, v3 keys)."""
        from orchestration.nodes import validate_output
        from domain.state import PassType

        # Pass 1 (DEFINITION) expects methodology structure with v1, v2, v3 versions
        content = {
            "v1": {"approach": "Initial methodology"},
            "v2": {"approach": "Refined methodology"},
            "v3": {"approach": "Final methodology"},
        }

        result = await validate_output(
            step=StepName.PROBLEM_DEFINITION,
            output=content,
            pass_type=PassType.DEFINITION,
        )

        # Should pass with methodology structure validation
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_pass2_full_schema_validation(self):
        """Pass 2 uses full schema validation."""
        from orchestration.nodes import validate_output
        from domain.state import PassType

        # Content that passes basic validation but fails schema
        content = {
            "title": "Test",
            "canonical_problem_definition": {},  # Missing required 'statement'
            "stakeholders": [],  # Empty array (needs minItems: 1)
            "constraints": {},  # Missing 'hard' and 'soft'
            "scope": {},  # Missing 'in' and 'out'
            "success_criteria": [],  # Empty array
        }

        result = await validate_output(
            step=StepName.PROBLEM_DEFINITION,
            output=content,
            pass_type=PassType.EXECUTION,
        )

        # Should fail with full schema validation
        assert result.passed is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_pass2_valid_content_passes(self):
        """Valid content passes Pass 2 schema validation."""
        from orchestration.nodes import validate_output
        from domain.state import PassType

        content = {
            "title": "Test Problem",
            "canonical_problem_definition": {"statement": "Test statement"},
            "stakeholders": [{
                "id": "SH-001",
                "name_or_group": "Test",
                "role": "User",
                "needs": [],
                "concerns": [],
                "impact": "High",
            }],
            "constraints": {"hard": [], "soft": []},
            "scope": {"in": [], "out": []},
            "success_criteria": [{
                "id": "CRT-001",
                "metric_or_signal": "Test",
                "target": "100%",
                "how_verified": "Test",
            }],
        }

        result = await validate_output(
            step=StepName.PROBLEM_DEFINITION,
            output=content,
            pass_type=PassType.EXECUTION,
        )

        assert result.passed is True

    @pytest.mark.asyncio
    async def test_none_output_fails(self):
        """None output fails validation."""
        from orchestration.nodes import validate_output
        from domain.state import PassType

        result = await validate_output(
            step=StepName.PROBLEM_DEFINITION,
            output=None,
            pass_type=PassType.EXECUTION,
        )

        assert result.passed is False
        assert len(result.errors) == 1
        assert "None" in result.errors[0]["message"]
