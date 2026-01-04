"""
SOLVER API - Traceability Service

Extracts and persists traceability links from step packages per Doc 2 §6.1.
Chain: Step 1 → Step 2 → Step 3 (no cross-step links).
"""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from domain.state import StepName, STEP_NUMBERS
from infrastructure.db.models import TraceabilityLink
from infrastructure.db.repositories import TraceabilityLinkRepository


logger = logging.getLogger(__name__)


class TraceabilityExtractionError(Exception):
    """Error extracting traceability links from package."""

    pass


class TraceabilityService:
    """Extract and persist traceability links from step packages.

    Uses replace semantics: on each extraction, delete existing links
    for the target step, then insert fresh links from the current package.
    This ensures links always reflect the latest approved revision.
    """

    # Canonical type mapping from ID prefix
    TYPE_MAP = {
        "SH": "stakeholder",
        "HC": "constraint",
        "SC": "constraint",
        "IN": "scope",
        "OUT": "scope",
        "CRT": "success_criterion",
        "ASM": "assumption",
        "OQ": "open_question",
        "IP": "integration_point",
        "FR": "requirement",
        "NFR": "requirement",
        "CR": "requirement",
        "IR": "requirement",
        "CAP": "objective",
        "QUAL": "objective",
        "COMP": "objective",
        "INTF": "objective",
    }

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._trace_repo = TraceabilityLinkRepository(session)

    async def extract_and_persist_links(
        self,
        workflow_id: UUID,
        step_name: StepName,
        package_content: dict[str, Any],
    ) -> list[TraceabilityLink]:
        """Extract trace links from package and persist using replace semantics.

        Deletes all existing links targeting this step, then inserts fresh links
        extracted from the current package. This handles package revisions correctly.

        Args:
            workflow_id: Database workflow UUID.
            step_name: Step name (REQUIREMENTS or OBJECTIVES).
            package_content: Full package dict with metadata.

        Returns:
            List of created TraceabilityLink records.

        Raises:
            TraceabilityExtractionError: If extraction fails.
        """
        step_number = STEP_NUMBERS[step_name]

        # Step 1 has no incoming links (it's the source)
        if step_name == StepName.PROBLEM_DEFINITION:
            return []

        # Extract link data based on step
        try:
            if step_name == StepName.REQUIREMENTS:
                link_data_list = self._extract_step2_links(step_number, package_content)
            elif step_name == StepName.OBJECTIVES:
                link_data_list = self._extract_step3_links(step_number, package_content)
            else:
                return []
        except Exception as e:
            raise TraceabilityExtractionError(
                f"Failed to extract links for {step_name.value}: {e}"
            ) from e

        # Replace semantics: delete existing links to this step
        deleted_count = await self._trace_repo.delete_for_step(workflow_id, step_number)
        if deleted_count > 0:
            logger.debug(f"Deleted {deleted_count} existing links to step {step_number}")

        # Insert fresh links
        created = []
        for link_data in link_data_list:
            link = TraceabilityLink(
                workflow_id=workflow_id,
                from_step=link_data["from_step"],
                from_type=link_data["from_type"],
                from_id=link_data["from_id"],
                to_step=link_data["to_step"],
                to_type=link_data["to_type"],
                to_id=link_data["to_id"],
                link_type=link_data["link_type"],
                consolidated=link_data.get("consolidated", False),
            )
            self._session.add(link)
            created.append(link)

        if created:
            await self._session.flush()
            logger.info(f"Created {len(created)} trace links for step {step_number}")

        return created

    def _extract_step2_links(
        self,
        step_number: int,
        package: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Extract Step 1 → Step 2 links from RequirementsPackage.

        Primary source: coverage_map[] (Doc 3 §5.2)
        Each coverage_map entry maps a Step 1 element to requirement IDs.
        De-duplicates links to avoid unique constraint violations.
        """
        coverage_map = package.get("coverage_map", [])

        if not coverage_map:
            raise TraceabilityExtractionError(
                "RequirementsPackage has empty coverage_map; Step 1→2 links required"
            )

        links = []
        seen: set[tuple[str, str]] = set()  # Track (from_id, to_id) pairs for de-duplication

        for entry in coverage_map:
            source_id = entry.get("source_id")
            source_type = entry.get("source_type")
            requirement_ids = entry.get("requirement_ids", [])

            if not source_id or not requirement_ids:
                continue

            # Map source_type to canonical type
            from_type = self._normalize_source_type(source_type)

            for req_id in requirement_ids:
                # De-duplicate: skip if we've seen this (from_id, to_id) pair
                key = (source_id, req_id)
                if key in seen:
                    continue
                seen.add(key)

                to_type = self._get_type_from_id(req_id)

                links.append({
                    "from_step": 1,
                    "from_type": from_type,
                    "from_id": source_id,
                    "to_step": step_number,
                    "to_type": to_type,
                    "to_id": req_id,
                    "link_type": "derives",
                    "consolidated": False,
                })

        return links

    def _extract_step3_links(
        self,
        step_number: int,
        package: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Extract Step 2 → Step 3 links from ObjectivesPackage.

        Primary source: trace_map[] (Doc 3 §5.3)
        Each trace_map entry maps an objective to requirement IDs.
        De-duplicates links to avoid unique constraint violations.
        """
        trace_map = package.get("trace_map", [])

        if not trace_map:
            raise TraceabilityExtractionError(
                "ObjectivesPackage has empty trace_map; Step 2→3 links required"
            )

        links = []
        seen: set[tuple[str, str]] = set()  # Track (from_id, to_id) pairs for de-duplication

        for entry in trace_map:
            objective_id = entry.get("objective_id")
            requirement_ids = entry.get("requirement_ids", [])
            consolidated = entry.get("consolidated", False)

            if not objective_id or not requirement_ids:
                continue

            to_type = self._get_type_from_id(objective_id)

            for req_id in requirement_ids:
                # De-duplicate: skip if we've seen this (from_id, to_id) pair
                key = (req_id, objective_id)
                if key in seen:
                    continue
                seen.add(key)

                from_type = self._get_type_from_id(req_id)

                links.append({
                    "from_step": 2,
                    "from_type": from_type,
                    "from_id": req_id,
                    "to_step": step_number,
                    "to_type": to_type,
                    "to_id": objective_id,
                    "link_type": "achieves",
                    "consolidated": consolidated,
                })

        return links

    def _get_type_from_id(self, element_id: str) -> str:
        """Infer canonical element type from ID prefix."""
        if not element_id or "-" not in element_id:
            return "unknown"

        prefix = element_id.split("-")[0]
        return self.TYPE_MAP.get(prefix, "unknown")

    def _normalize_source_type(self, source_type: str) -> str:
        """Normalize source_type string to canonical type.

        coverage_map.source_type may be: 'stakeholder', 'constraint',
        'scope', 'success_criterion', 'integration_point', etc.
        """
        if not source_type:
            return "unknown"

        # Already canonical
        canonical_types = {
            "stakeholder",
            "constraint",
            "scope",
            "success_criterion",
            "integration_point",
            "assumption",
        }
        if source_type in canonical_types:
            return source_type

        # Map variations
        type_aliases = {
            "hard_constraint": "constraint",
            "soft_constraint": "constraint",
            "scope_in": "scope",
            "scope_out": "scope",
            "success_criteria": "success_criterion",
        }
        return type_aliases.get(source_type, "unknown")

    async def get_links_for_workflow(
        self,
        workflow_id: UUID,
    ) -> list[TraceabilityLink]:
        """Get all traceability links for a workflow."""
        return await self._trace_repo.list_for_workflow(workflow_id)

    async def get_forward_traces(
        self,
        workflow_id: UUID,
        from_id: str,
    ) -> list[TraceabilityLink]:
        """Get all links originating from an element."""
        return await self._trace_repo.list_from_element(workflow_id, from_id)

    async def get_backward_traces(
        self,
        workflow_id: UUID,
        to_id: str,
    ) -> list[TraceabilityLink]:
        """Get all links pointing to an element."""
        return await self._trace_repo.list_to_element(workflow_id, to_id)
