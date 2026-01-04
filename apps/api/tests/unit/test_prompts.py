"""
Unit Tests for P5.2 Prompt Templates

Tests prompt template structure, context building, and JSON parsing.
"""

import pytest

from domain.state import (
    WorkflowState,
    StepState,
    StepName,
    PassType,
    StepPhase,
    StepStatus,
)
from orchestration.prompts import (
    get_prompt,
    get_execution_prompt,
    format_prompt,
    build_context,
    parse_json_output,
    considering_header,
    get_considering_refs,
    get_required_keys,
    prev_step,
    prev_version,
    DOC_TYPES,
    DOC_TYPE_NAMES,
    JSONParseError,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_state() -> WorkflowState:
    """Create a sample workflow state for testing."""
    from domain.state import GatePolicy
    return WorkflowState(
        workflow_id="test-workflow-123",
        thread_id="test-thread-123",
        instance_id="test-instance-123",
        instance_number=0,
        original_problem="Build a task management system",
        current_step=StepName.PROBLEM_DEFINITION,
        current_pass=PassType.DEFINITION,
        gate_policy=GatePolicy.PER_STEP,
        step_state=StepState(
            step_name=StepName.PROBLEM_DEFINITION,
            step_number=1,
            pass_type=PassType.DEFINITION,
            phase=StepPhase.STRUCTURING,
            status=StepStatus.IN_PROGRESS,
        ),
    )


@pytest.fixture
def step2_state(sample_state: WorkflowState) -> WorkflowState:
    """Create a Step 2 workflow state."""
    sample_state.current_step = StepName.REQUIREMENTS
    sample_state.step_state.step_name = StepName.REQUIREMENTS
    sample_state.step_state.step_number = 2
    sample_state.artifacts = {
        "problem_definition": {"stakeholders": [], "constraints": {}}
    }
    return sample_state


@pytest.fixture
def step3_state(step2_state: WorkflowState) -> WorkflowState:
    """Create a Step 3 workflow state."""
    step2_state.current_step = StepName.OBJECTIVES
    step2_state.step_state.step_name = StepName.OBJECTIVES
    step2_state.step_state.step_number = 3
    step2_state.artifacts["requirements"] = {"requirements": []}
    return step2_state


# =============================================================================
# Test Constants
# =============================================================================


class TestConstants:
    """Test constant exports."""

    def test_doc_types(self):
        """DOC_TYPES contains 4 document types."""
        assert len(DOC_TYPES) == 4
        assert "data_sheet" in DOC_TYPES
        assert "todo_list" in DOC_TYPES
        assert "guidance" in DOC_TYPES
        assert "detailed_procedure" in DOC_TYPES

    def test_doc_type_names(self):
        """DOC_TYPE_NAMES maps to human-readable names."""
        assert DOC_TYPE_NAMES["data_sheet"] == "Data Sheet"
        assert DOC_TYPE_NAMES["todo_list"] == "To Do List"
        assert DOC_TYPE_NAMES["guidance"] == "Guidance Document"
        assert DOC_TYPE_NAMES["detailed_procedure"] == "Detailed Procedure"


# =============================================================================
# Test Step/Version Navigation
# =============================================================================


class TestStepNavigation:
    """Test step and version navigation helpers."""

    def test_prev_step_from_step1(self):
        """Step 1 has no previous step."""
        assert prev_step(StepName.PROBLEM_DEFINITION) is None

    def test_prev_step_from_step2(self):
        """Step 2's previous step is Step 1."""
        assert prev_step(StepName.REQUIREMENTS) == StepName.PROBLEM_DEFINITION

    def test_prev_step_from_step3(self):
        """Step 3's previous step is Step 2."""
        assert prev_step(StepName.OBJECTIVES) == StepName.REQUIREMENTS

    def test_prev_version_from_v1(self):
        """V1 has no previous version."""
        assert prev_version("v1") is None

    def test_prev_version_from_v2(self):
        """V2's previous version is V1."""
        assert prev_version("v2") == "v1"

    def test_prev_version_from_v3(self):
        """V3's previous version is V2."""
        assert prev_version("v3") == "v2"

    def test_prev_version_invalid(self):
        """Invalid version returns None."""
        assert prev_version("v4") is None
        assert prev_version("invalid") is None


# =============================================================================
# Test Considering Header
# =============================================================================


class TestConsideringHeader:
    """Test considering header generation."""

    def test_empty_refs(self):
        """Empty refs returns empty string."""
        assert considering_header([]) == ""

    def test_single_ref(self):
        """Single reference formats correctly."""
        result = considering_header(["Data Sheet V1"])
        assert result == "Considering: Data Sheet V1"

    def test_multiple_refs(self):
        """Multiple references joined with +."""
        result = considering_header(["Data Sheet V1", "To Do List V1"])
        assert result == "Considering: Data Sheet V1 + To Do List V1"


class TestGetConsideringRefs:
    """Test get_considering_refs for correct dependency chains."""

    def test_v1_data_sheet(self):
        """V1 Data Sheet considers seed problem."""
        refs = get_considering_refs("v1", "data_sheet")
        assert refs == ["Seed Problem"]

    def test_v1_todo_list(self):
        """V1 To Do List considers V1 Data Sheet."""
        refs = get_considering_refs("v1", "todo_list")
        assert refs == ["Data Sheet V1"]

    def test_v1_guidance(self):
        """V1 Guidance considers seed + V1 Data Sheet + V1 To Do List."""
        refs = get_considering_refs("v1", "guidance")
        assert "Seed Problem" in refs
        assert "Data Sheet V1" in refs
        assert "To Do List V1" in refs

    def test_v1_detailed_procedure(self):
        """V1 Detailed Procedure considers V1 docs."""
        refs = get_considering_refs("v1", "detailed_procedure")
        assert "Data Sheet V1" in refs
        assert "To Do List V1" in refs
        assert "Guidance Document V1" in refs

    def test_v2_data_sheet(self):
        """V2 Data Sheet considers V1 complete set."""
        refs = get_considering_refs("v2", "data_sheet")
        assert "Detailed Procedure V1" in refs
        assert "Guidance Document V1" in refs
        assert "To Do List V1" in refs

    def test_v3_data_sheet(self):
        """V3 Data Sheet considers V2 complete set."""
        refs = get_considering_refs("v3", "data_sheet")
        assert "Detailed Procedure V2" in refs
        assert "Guidance Document V2" in refs
        assert "To Do List V2" in refs


# =============================================================================
# Test Get Prompt
# =============================================================================


class TestGetPrompt:
    """Test prompt retrieval."""

    @pytest.mark.parametrize("step", [
        StepName.PROBLEM_DEFINITION,
        StepName.REQUIREMENTS,
        StepName.OBJECTIVES,
    ])
    @pytest.mark.parametrize("version", ["v1", "v2", "v3"])
    @pytest.mark.parametrize("doc_type", DOC_TYPES)
    def test_all_prompts_exist(self, step, version, doc_type):
        """All 36 Pass 1 prompts exist (3 steps × 3 versions × 4 docs)."""
        prompt = get_prompt(step, version, doc_type)
        assert "system" in prompt
        assert "user" in prompt
        assert isinstance(prompt["system"], str)
        assert isinstance(prompt["user"], str)
        assert len(prompt["system"]) > 0
        assert len(prompt["user"]) > 0

    @pytest.mark.parametrize("step", [
        StepName.PROBLEM_DEFINITION,
        StepName.REQUIREMENTS,
        StepName.OBJECTIVES,
    ])
    def test_execution_prompts_exist(self, step):
        """All 3 Pass 2 execution prompts exist."""
        prompt = get_execution_prompt(step)
        assert "system" in prompt
        assert "user" in prompt
        assert isinstance(prompt["system"], str)
        assert isinstance(prompt["user"], str)

    def test_invalid_step_raises(self):
        """Invalid step raises KeyError."""
        with pytest.raises(KeyError):
            get_prompt("invalid", "v1", "data_sheet")

    def test_invalid_version_raises(self):
        """Invalid version raises KeyError."""
        with pytest.raises(KeyError):
            get_prompt(StepName.PROBLEM_DEFINITION, "v4", "data_sheet")

    def test_invalid_doc_type_raises(self):
        """Invalid doc_type raises KeyError."""
        with pytest.raises(KeyError):
            get_prompt(StepName.PROBLEM_DEFINITION, "v1", "invalid")


# =============================================================================
# Test Prompt Content
# =============================================================================


class TestPromptContent:
    """Test prompt content contains expected elements."""

    def test_step1_v3_data_sheet_has_schema(self):
        """Step 1 V3 Data Sheet references schema concepts."""
        prompt = get_prompt(StepName.PROBLEM_DEFINITION, "v3", "data_sheet")
        # V3 is a finalization prompt - check system mentions stakeholder concept
        combined = (prompt["system"] + prompt["user"]).lower()
        assert "stakeholder" in combined or "problemdefinition" in combined

    def test_step2_prompts_allow_ir(self):
        """Step 2 prompts allow IR category."""
        prompt = get_execution_prompt(StepName.REQUIREMENTS)
        combined = prompt["system"] + prompt["user"]
        # Should mention IR as a valid category
        assert "IR" in combined or "Interface" in combined

    def test_step3_prompts_allow_intf(self):
        """Step 3 prompts allow INTF category."""
        prompt = get_execution_prompt(StepName.OBJECTIVES)
        combined = prompt["system"] + prompt["user"]
        # Should mention INTF as a valid category
        assert "INTF" in combined or "Interface" in combined

    def test_execution_prompts_request_json(self):
        """Execution prompts request JSON output."""
        for step in [StepName.PROBLEM_DEFINITION, StepName.REQUIREMENTS, StepName.OBJECTIVES]:
            prompt = get_execution_prompt(step)
            combined = prompt["system"] + prompt["user"]
            assert "json" in combined.lower() or "JSON" in combined


# =============================================================================
# Test Build Context
# =============================================================================


class TestBuildContext:
    """Test context building for prompt formatting."""

    def test_basic_context(self, sample_state):
        """Basic context contains essential fields."""
        context = build_context(sample_state, {}, {})
        assert context["instance_number"] == 0
        assert context["step_name"] == "problem_definition"
        assert context["original_problem"] == "Build a task management system"
        assert context["domain"] == "Universal (Domain-Agnostic)"

    def test_context_with_prior_docs(self, sample_state):
        """Context includes prior version documents."""
        prior_docs = {
            "data_sheet": "V1 Data Sheet Content",
            "todo_list": "V1 Todo List Content",
        }
        context = build_context(sample_state, prior_docs, {})
        assert context["prior_data_sheet"] == "V1 Data Sheet Content"
        assert context["prior_todo_list"] == "V1 Todo List Content"

    def test_context_with_current_docs(self, sample_state):
        """Context includes current version documents built so far."""
        current_docs = {
            "data_sheet": "Current Data Sheet",
        }
        context = build_context(sample_state, {}, current_docs)
        assert context["current_data_sheet"] == "Current Data Sheet"
        assert context["current_todo_list"] == ""  # Not built yet

    def test_context_step2_has_prior_step(self, step2_state):
        """Step 2 context references prior step output."""
        step2_state.current_pass = PassType.EXECUTION
        context = build_context(step2_state, {}, {})
        # Prior step name should be problem_definition
        assert context["prior_step_name"] == "problem_definition"


# =============================================================================
# Test Format Prompt
# =============================================================================


class TestFormatPrompt:
    """Test prompt formatting with context."""

    def test_format_replaces_placeholders(self, sample_state):
        """Format replaces placeholders with context values."""
        context = build_context(sample_state, {}, {})
        # V1 data sheet prompt uses {considering} which is generated by the prompt
        # We need to add it to context or use a simpler test approach
        context["considering"] = "Considering: Seed Problem"
        formatted = format_prompt(
            StepName.PROBLEM_DEFINITION, "v1", "data_sheet", context
        )
        # The formatted prompt should not have {original_problem} placeholder
        assert "{original_problem}" not in formatted["system"]
        assert "{original_problem}" not in formatted["user"]
        # Should have the actual problem text
        assert "task management system" in formatted["user"]


# =============================================================================
# Test JSON Parsing
# =============================================================================


class TestParseJsonOutput:
    """Test JSON parsing from LLM responses."""

    def test_parse_valid_json(self):
        """Parse valid JSON directly."""
        content = '{"key": "value", "number": 42}'
        result = parse_json_output(content)
        assert result["key"] == "value"
        assert result["number"] == 42

    def test_parse_with_whitespace(self):
        """Parse JSON with leading/trailing whitespace."""
        content = '  \n  {"key": "value"}  \n  '
        result = parse_json_output(content)
        assert result["key"] == "value"

    def test_parse_with_code_fences(self):
        """Parse JSON wrapped in markdown code fences."""
        content = '```json\n{"key": "value"}\n```'
        result = parse_json_output(content)
        assert result["key"] == "value"

    def test_parse_with_code_fences_no_lang(self):
        """Parse JSON wrapped in code fences without language."""
        content = '```\n{"key": "value"}\n```'
        result = parse_json_output(content)
        assert result["key"] == "value"

    def test_parse_json_in_prose(self):
        """Extract JSON from surrounding prose."""
        content = 'Here is the output:\n\n{"key": "value"}\n\nThat is all.'
        result = parse_json_output(content)
        assert result["key"] == "value"

    def test_parse_empty_raises(self):
        """Empty content raises JSONParseError."""
        with pytest.raises(JSONParseError):
            parse_json_output("")

    def test_parse_whitespace_only_raises(self):
        """Whitespace-only content raises JSONParseError."""
        with pytest.raises(JSONParseError):
            parse_json_output("   \n\n   ")

    def test_parse_invalid_json_raises(self):
        """Invalid JSON raises JSONParseError."""
        with pytest.raises(JSONParseError):
            parse_json_output("not json at all")

    def test_parse_error_includes_content(self):
        """JSONParseError includes raw content."""
        try:
            parse_json_output("invalid content here")
        except JSONParseError as e:
            assert "invalid content here" in e.raw_content


# =============================================================================
# Test Required Keys
# =============================================================================


class TestGetRequiredKeys:
    """Test required key retrieval for validation."""

    def test_step1_required_keys(self):
        """Step 1 has expected required keys."""
        keys = get_required_keys(StepName.PROBLEM_DEFINITION)
        assert "title" in keys
        assert "canonical_problem_definition" in keys
        assert "stakeholders" in keys
        assert "constraints" in keys
        assert "scope" in keys
        assert "success_criteria" in keys

    def test_step2_required_keys(self):
        """Step 2 has expected required keys."""
        keys = get_required_keys(StepName.REQUIREMENTS)
        assert "overview" in keys
        assert "requirements" in keys
        assert "coverage_map" in keys

    def test_step3_required_keys(self):
        """Step 3 has expected required keys."""
        keys = get_required_keys(StepName.OBJECTIVES)
        assert "overview" in keys
        assert "objectives" in keys
        assert "success_framework" in keys
        assert "trace_map" in keys


# =============================================================================
# Test Prompt Total Count
# =============================================================================


class TestPromptCount:
    """Verify total prompt count matches specification."""

    def test_pass1_prompt_count(self):
        """Pass 1 has 36 prompts (3 steps × 3 versions × 4 docs)."""
        count = 0
        for step in [StepName.PROBLEM_DEFINITION, StepName.REQUIREMENTS, StepName.OBJECTIVES]:
            for version in ["v1", "v2", "v3"]:
                for doc_type in DOC_TYPES:
                    get_prompt(step, version, doc_type)  # Should not raise
                    count += 1
        assert count == 36

    def test_pass2_prompt_count(self):
        """Pass 2 has 3 execution prompts (1 per step)."""
        count = 0
        for step in [StepName.PROBLEM_DEFINITION, StepName.REQUIREMENTS, StepName.OBJECTIVES]:
            get_execution_prompt(step)  # Should not raise
            count += 1
        assert count == 3

    def test_total_prompt_count(self):
        """Total prompts = 39 (36 Pass 1 + 3 Pass 2)."""
        # This is a documentation test - the actual verification
        # is done by the individual count tests above
        pass
