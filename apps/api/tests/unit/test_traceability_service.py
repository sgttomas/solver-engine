"""
Unit Tests for P5.4 Traceability Service

Tests link extraction from coverage_map (Step 1→2) and trace_map (Step 2→3).
"""

import pytest
from uuid import uuid4

from application.traceability_service import TraceabilityService, TraceabilityExtractionError


# =============================================================================
# Test Type Mapping
# =============================================================================


class TestGetTypeFromId:
    """Test canonical type inference from ID prefix."""

    def test_stakeholder(self):
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._get_type_from_id("SH-001") == "stakeholder"

    def test_hard_constraint(self):
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._get_type_from_id("HC-001") == "constraint"

    def test_soft_constraint(self):
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._get_type_from_id("SC-001") == "constraint"

    def test_scope_in(self):
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._get_type_from_id("IN-001") == "scope"

    def test_scope_out(self):
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._get_type_from_id("OUT-001") == "scope"

    def test_success_criterion(self):
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._get_type_from_id("CRT-001") == "success_criterion"

    def test_assumption(self):
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._get_type_from_id("ASM-001") == "assumption"

    def test_open_question(self):
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._get_type_from_id("OQ-001") == "open_question"

    def test_integration_point(self):
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._get_type_from_id("IP-001") == "integration_point"

    def test_functional_requirement(self):
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._get_type_from_id("FR-001") == "requirement"

    def test_nonfunctional_requirement(self):
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._get_type_from_id("NFR-001") == "requirement"

    def test_cross_cutting_requirement(self):
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._get_type_from_id("CR-001") == "requirement"

    def test_interface_requirement(self):
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._get_type_from_id("IR-001") == "requirement"

    def test_capability_objective(self):
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._get_type_from_id("CAP-001") == "objective"

    def test_quality_objective(self):
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._get_type_from_id("QUAL-001") == "objective"

    def test_compatibility_objective(self):
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._get_type_from_id("COMP-001") == "objective"

    def test_interface_objective(self):
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._get_type_from_id("INTF-001") == "objective"

    def test_unknown_prefix(self):
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._get_type_from_id("XX-001") == "unknown"

    def test_empty_id(self):
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._get_type_from_id("") == "unknown"

    def test_no_hyphen(self):
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._get_type_from_id("invalid") == "unknown"

    def test_none_id(self):
        """None ID returns unknown."""
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._get_type_from_id(None) == "unknown"


# =============================================================================
# Test Source Type Normalization
# =============================================================================


class TestNormalizeSourceType:
    """Test source_type normalization."""

    def test_already_canonical_stakeholder(self):
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._normalize_source_type("stakeholder") == "stakeholder"

    def test_already_canonical_constraint(self):
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._normalize_source_type("constraint") == "constraint"

    def test_already_canonical_scope(self):
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._normalize_source_type("scope") == "scope"

    def test_already_canonical_success_criterion(self):
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._normalize_source_type("success_criterion") == "success_criterion"

    def test_already_canonical_integration_point(self):
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._normalize_source_type("integration_point") == "integration_point"

    def test_already_canonical_assumption(self):
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._normalize_source_type("assumption") == "assumption"

    def test_alias_hard_constraint(self):
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._normalize_source_type("hard_constraint") == "constraint"

    def test_alias_soft_constraint(self):
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._normalize_source_type("soft_constraint") == "constraint"

    def test_alias_scope_in(self):
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._normalize_source_type("scope_in") == "scope"

    def test_alias_scope_out(self):
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._normalize_source_type("scope_out") == "scope"

    def test_alias_success_criteria(self):
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._normalize_source_type("success_criteria") == "success_criterion"

    def test_empty_returns_unknown(self):
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._normalize_source_type("") == "unknown"

    def test_none_returns_unknown(self):
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._normalize_source_type(None) == "unknown"

    def test_unknown_returns_unknown(self):
        """Unrecognized source types return 'unknown'."""
        service = TraceabilityService.__new__(TraceabilityService)
        assert service._normalize_source_type("custom_type") == "unknown"


# =============================================================================
# Test Step 1 → Step 2 Link Extraction
# =============================================================================


class TestExtractStep2Links:
    """Test link extraction from coverage_map."""

    def test_extracts_from_coverage_map(self):
        """coverage_map entries produce derives links."""
        service = TraceabilityService.__new__(TraceabilityService)
        package = {
            "coverage_map": [{
                "source_type": "stakeholder",
                "source_id": "SH-001",
                "requirement_ids": ["FR-001", "FR-002"],
                "coverage_note": "Full coverage",
            }]
        }
        links = service._extract_step2_links(2, package)

        assert len(links) == 2
        assert all(l["from_step"] == 1 for l in links)
        assert all(l["to_step"] == 2 for l in links)
        assert all(l["link_type"] == "derives" for l in links)
        assert all(l["from_id"] == "SH-001" for l in links)
        assert all(l["from_type"] == "stakeholder" for l in links)
        assert {l["to_id"] for l in links} == {"FR-001", "FR-002"}
        assert all(l["to_type"] == "requirement" for l in links)
        assert all(l["consolidated"] is False for l in links)

    def test_multiple_coverage_map_entries(self):
        """Multiple coverage_map entries all extracted."""
        service = TraceabilityService.__new__(TraceabilityService)
        package = {
            "coverage_map": [
                {
                    "source_type": "stakeholder",
                    "source_id": "SH-001",
                    "requirement_ids": ["FR-001"],
                    "coverage_note": "",
                },
                {
                    "source_type": "constraint",
                    "source_id": "HC-001",
                    "requirement_ids": ["NFR-001"],
                    "coverage_note": "",
                },
            ]
        }
        links = service._extract_step2_links(2, package)

        assert len(links) == 2
        from_ids = {l["from_id"] for l in links}
        assert from_ids == {"SH-001", "HC-001"}

        from_types = {l["from_type"] for l in links}
        assert from_types == {"stakeholder", "constraint"}

    def test_constraint_type_normalized(self):
        """hard_constraint and soft_constraint normalized to constraint."""
        service = TraceabilityService.__new__(TraceabilityService)
        package = {
            "coverage_map": [
                {
                    "source_type": "hard_constraint",
                    "source_id": "HC-001",
                    "requirement_ids": ["FR-001"],
                },
                {
                    "source_type": "soft_constraint",
                    "source_id": "SC-001",
                    "requirement_ids": ["FR-002"],
                },
            ]
        }
        links = service._extract_step2_links(2, package)

        assert len(links) == 2
        assert all(l["from_type"] == "constraint" for l in links)

    def test_empty_coverage_map_raises_error(self):
        """Empty coverage_map raises TraceabilityExtractionError."""
        service = TraceabilityService.__new__(TraceabilityService)
        package = {"coverage_map": []}
        with pytest.raises(TraceabilityExtractionError) as exc_info:
            service._extract_step2_links(2, package)
        assert "empty coverage_map" in str(exc_info.value)

    def test_missing_coverage_map_raises_error(self):
        """Missing coverage_map raises TraceabilityExtractionError."""
        service = TraceabilityService.__new__(TraceabilityService)
        package = {}
        with pytest.raises(TraceabilityExtractionError) as exc_info:
            service._extract_step2_links(2, package)
        assert "empty coverage_map" in str(exc_info.value)

    def test_skips_entries_without_source_id(self):
        """Entries without source_id are skipped."""
        service = TraceabilityService.__new__(TraceabilityService)
        package = {
            "coverage_map": [{
                "source_type": "stakeholder",
                # Missing source_id
                "requirement_ids": ["FR-001"],
            }]
        }
        links = service._extract_step2_links(2, package)
        assert links == []

    def test_skips_entries_with_empty_requirement_ids(self):
        """Entries with empty requirement_ids are skipped."""
        service = TraceabilityService.__new__(TraceabilityService)
        package = {
            "coverage_map": [{
                "source_type": "stakeholder",
                "source_id": "SH-001",
                "requirement_ids": [],
            }]
        }
        links = service._extract_step2_links(2, package)
        assert links == []

    def test_skips_entries_with_missing_requirement_ids(self):
        """Entries without requirement_ids key are skipped."""
        service = TraceabilityService.__new__(TraceabilityService)
        package = {
            "coverage_map": [{
                "source_type": "stakeholder",
                "source_id": "SH-001",
                # Missing requirement_ids
            }]
        }
        links = service._extract_step2_links(2, package)
        assert links == []

    def test_infers_to_type_from_requirement_id(self):
        """Requirement type inferred from ID prefix."""
        service = TraceabilityService.__new__(TraceabilityService)
        package = {
            "coverage_map": [{
                "source_type": "stakeholder",
                "source_id": "SH-001",
                "requirement_ids": ["FR-001", "NFR-001", "CR-001", "IR-001"],
            }]
        }
        links = service._extract_step2_links(2, package)

        assert len(links) == 4
        # All should be 'requirement' type
        assert all(l["to_type"] == "requirement" for l in links)


# =============================================================================
# Test Step 2 → Step 3 Link Extraction
# =============================================================================


class TestExtractStep3Links:
    """Test link extraction from trace_map."""

    def test_extracts_from_trace_map(self):
        """trace_map entries produce achieves links."""
        service = TraceabilityService.__new__(TraceabilityService)
        package = {
            "trace_map": [{
                "objective_id": "CAP-001",
                "requirement_ids": ["FR-001", "FR-002"],
                "consolidated": False,
            }]
        }
        links = service._extract_step3_links(3, package)

        assert len(links) == 2
        assert all(l["from_step"] == 2 for l in links)
        assert all(l["to_step"] == 3 for l in links)
        assert all(l["link_type"] == "achieves" for l in links)
        assert all(l["to_id"] == "CAP-001" for l in links)
        assert all(l["to_type"] == "objective" for l in links)
        assert all(l["from_type"] == "requirement" for l in links)
        assert {l["from_id"] for l in links} == {"FR-001", "FR-002"}

    def test_consolidated_flag_preserved(self):
        """consolidated flag is preserved in links."""
        service = TraceabilityService.__new__(TraceabilityService)
        package = {
            "trace_map": [{
                "objective_id": "CAP-001",
                "requirement_ids": ["FR-001"],
                "consolidated": True,
            }]
        }
        links = service._extract_step3_links(3, package)

        assert len(links) == 1
        assert links[0]["consolidated"] is True

    def test_consolidated_false_by_default(self):
        """consolidated defaults to False if not specified."""
        service = TraceabilityService.__new__(TraceabilityService)
        package = {
            "trace_map": [{
                "objective_id": "CAP-001",
                "requirement_ids": ["FR-001"],
                # No consolidated key
            }]
        }
        links = service._extract_step3_links(3, package)

        assert len(links) == 1
        assert links[0]["consolidated"] is False

    def test_multiple_trace_map_entries(self):
        """Multiple trace_map entries all extracted."""
        service = TraceabilityService.__new__(TraceabilityService)
        package = {
            "trace_map": [
                {
                    "objective_id": "CAP-001",
                    "requirement_ids": ["FR-001"],
                    "consolidated": False,
                },
                {
                    "objective_id": "QUAL-001",
                    "requirement_ids": ["NFR-001"],
                    "consolidated": False,
                },
            ]
        }
        links = service._extract_step3_links(3, package)

        assert len(links) == 2
        to_ids = {l["to_id"] for l in links}
        assert to_ids == {"CAP-001", "QUAL-001"}

        to_types = set(l["to_type"] for l in links)
        assert to_types == {"objective"}

    def test_different_objective_types(self):
        """Different objective ID prefixes all map to 'objective'."""
        service = TraceabilityService.__new__(TraceabilityService)
        package = {
            "trace_map": [
                {"objective_id": "CAP-001", "requirement_ids": ["FR-001"]},
                {"objective_id": "QUAL-001", "requirement_ids": ["FR-002"]},
                {"objective_id": "COMP-001", "requirement_ids": ["FR-003"]},
                {"objective_id": "INTF-001", "requirement_ids": ["FR-004"]},
            ]
        }
        links = service._extract_step3_links(3, package)

        assert len(links) == 4
        assert all(l["to_type"] == "objective" for l in links)

    def test_empty_trace_map_raises_error(self):
        """Empty trace_map raises TraceabilityExtractionError."""
        service = TraceabilityService.__new__(TraceabilityService)
        package = {"trace_map": []}
        with pytest.raises(TraceabilityExtractionError) as exc_info:
            service._extract_step3_links(3, package)
        assert "empty trace_map" in str(exc_info.value)

    def test_missing_trace_map_raises_error(self):
        """Missing trace_map raises TraceabilityExtractionError."""
        service = TraceabilityService.__new__(TraceabilityService)
        package = {}
        with pytest.raises(TraceabilityExtractionError) as exc_info:
            service._extract_step3_links(3, package)
        assert "empty trace_map" in str(exc_info.value)

    def test_skips_entries_without_objective_id(self):
        """Entries without objective_id are skipped."""
        service = TraceabilityService.__new__(TraceabilityService)
        package = {
            "trace_map": [{
                # Missing objective_id
                "requirement_ids": ["FR-001"],
                "consolidated": False,
            }]
        }
        links = service._extract_step3_links(3, package)
        assert links == []

    def test_skips_entries_with_empty_requirement_ids(self):
        """Entries with empty requirement_ids are skipped."""
        service = TraceabilityService.__new__(TraceabilityService)
        package = {
            "trace_map": [{
                "objective_id": "CAP-001",
                "requirement_ids": [],
                "consolidated": False,
            }]
        }
        links = service._extract_step3_links(3, package)
        assert links == []

    def test_does_not_extract_acceptance_criteria(self):
        """acceptance_criteria NOT extracted (chain directive: Step 1→2→3 only)."""
        service = TraceabilityService.__new__(TraceabilityService)
        package = {
            "objectives": [{
                "id": "CAP-001",
                "acceptance_criteria": ["CRT-001", "CRT-002"],
                "linked_requirements": ["FR-001"],
            }],
            "trace_map": [{
                "objective_id": "CAP-001",
                "requirement_ids": ["FR-001"],
                "consolidated": False,
            }],
        }
        links = service._extract_step3_links(3, package)

        # Only trace_map links, no Step 1→3 acceptance_criteria links
        assert len(links) == 1
        assert links[0]["from_step"] == 2  # Not 1
        assert all(l["from_id"] != "CRT-001" for l in links)
        assert all(l["from_id"] != "CRT-002" for l in links)

    def test_does_not_extract_from_linked_requirements(self):
        """Does not extract from objectives[].linked_requirements (use trace_map)."""
        service = TraceabilityService.__new__(TraceabilityService)
        package = {
            "objectives": [{
                "id": "CAP-001",
                "linked_requirements": ["FR-001", "FR-002", "FR-003"],
            }],
            "trace_map": [{
                "objective_id": "CAP-001",
                "requirement_ids": ["FR-001"],  # Only one in trace_map
                "consolidated": False,
            }],
        }
        links = service._extract_step3_links(3, package)

        # Only trace_map entry extracted
        assert len(links) == 1
        assert links[0]["from_id"] == "FR-001"


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_large_coverage_map(self):
        """Handle large coverage_map with many entries."""
        service = TraceabilityService.__new__(TraceabilityService)
        package = {
            "coverage_map": [
                {
                    "source_type": "stakeholder",
                    "source_id": f"SH-{i:03d}",
                    "requirement_ids": [f"FR-{j:03d}" for j in range(10)],
                }
                for i in range(10)
            ]
        }
        links = service._extract_step2_links(2, package)

        # 10 sources × 10 requirements each = 100 links
        assert len(links) == 100

    def test_large_trace_map(self):
        """Handle large trace_map with many entries."""
        service = TraceabilityService.__new__(TraceabilityService)
        package = {
            "trace_map": [
                {
                    "objective_id": f"CAP-{i:03d}",
                    "requirement_ids": [f"FR-{j:03d}" for j in range(5)],
                    "consolidated": False,
                }
                for i in range(20)
            ]
        }
        links = service._extract_step3_links(3, package)

        # 20 objectives × 5 requirements each = 100 links
        assert len(links) == 100

    def test_mixed_valid_invalid_entries(self):
        """Valid entries extracted, invalid entries skipped."""
        service = TraceabilityService.__new__(TraceabilityService)
        package = {
            "coverage_map": [
                {  # Valid
                    "source_type": "stakeholder",
                    "source_id": "SH-001",
                    "requirement_ids": ["FR-001"],
                },
                {  # Invalid - missing source_id
                    "source_type": "stakeholder",
                    "requirement_ids": ["FR-002"],
                },
                {  # Valid
                    "source_type": "constraint",
                    "source_id": "HC-001",
                    "requirement_ids": ["NFR-001"],
                },
                {  # Invalid - empty requirement_ids
                    "source_type": "scope",
                    "source_id": "IN-001",
                    "requirement_ids": [],
                },
            ]
        }
        links = service._extract_step2_links(2, package)

        assert len(links) == 2  # Only 2 valid entries
        from_ids = {l["from_id"] for l in links}
        assert from_ids == {"SH-001", "HC-001"}


# =============================================================================
# Test De-duplication
# =============================================================================


class TestDeduplication:
    """Test de-duplication of links to prevent unique constraint violations."""

    def test_duplicate_requirement_ids_in_array_deduplicated(self):
        """Duplicate requirement_ids within a single entry are de-duplicated."""
        service = TraceabilityService.__new__(TraceabilityService)
        package = {
            "coverage_map": [{
                "source_type": "stakeholder",
                "source_id": "SH-001",
                "requirement_ids": ["FR-001", "FR-001", "FR-001"],  # 3 duplicates
            }]
        }
        links = service._extract_step2_links(2, package)

        assert len(links) == 1  # De-duplicated to one unique link
        assert links[0]["from_id"] == "SH-001"
        assert links[0]["to_id"] == "FR-001"

    def test_duplicate_entries_across_coverage_map_deduplicated(self):
        """Duplicate links across multiple coverage_map entries are de-duplicated."""
        service = TraceabilityService.__new__(TraceabilityService)
        package = {
            "coverage_map": [
                {
                    "source_type": "stakeholder",
                    "source_id": "SH-001",
                    "requirement_ids": ["FR-001"],
                },
                {
                    "source_type": "stakeholder",
                    "source_id": "SH-001",
                    "requirement_ids": ["FR-001"],  # Same link as above
                },
            ]
        }
        links = service._extract_step2_links(2, package)

        assert len(links) == 1  # De-duplicated

    def test_different_links_not_deduplicated(self):
        """Different (from_id, to_id) pairs are not de-duplicated."""
        service = TraceabilityService.__new__(TraceabilityService)
        package = {
            "coverage_map": [
                {
                    "source_type": "stakeholder",
                    "source_id": "SH-001",
                    "requirement_ids": ["FR-001", "FR-002"],
                },
                {
                    "source_type": "stakeholder",
                    "source_id": "SH-002",
                    "requirement_ids": ["FR-001"],  # Different source
                },
            ]
        }
        links = service._extract_step2_links(2, package)

        assert len(links) == 3  # All unique pairs

    def test_step3_duplicate_requirement_ids_deduplicated(self):
        """Duplicate requirement_ids in trace_map are de-duplicated."""
        service = TraceabilityService.__new__(TraceabilityService)
        package = {
            "trace_map": [{
                "objective_id": "CAP-001",
                "requirement_ids": ["FR-001", "FR-001", "FR-002"],  # FR-001 duplicated
                "consolidated": False,
            }]
        }
        links = service._extract_step3_links(3, package)

        assert len(links) == 2  # Only 2 unique links
        from_ids = {l["from_id"] for l in links}
        assert from_ids == {"FR-001", "FR-002"}

    def test_step3_duplicate_across_trace_map_deduplicated(self):
        """Duplicate links across multiple trace_map entries are de-duplicated."""
        service = TraceabilityService.__new__(TraceabilityService)
        package = {
            "trace_map": [
                {
                    "objective_id": "CAP-001",
                    "requirement_ids": ["FR-001"],
                    "consolidated": False,
                },
                {
                    "objective_id": "CAP-001",
                    "requirement_ids": ["FR-001"],  # Same link as above
                    "consolidated": True,  # Even with different consolidated flag
                },
            ]
        }
        links = service._extract_step3_links(3, package)

        assert len(links) == 1  # De-duplicated
