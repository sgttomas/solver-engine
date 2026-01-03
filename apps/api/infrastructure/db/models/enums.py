"""
PostgreSQL Enum Type Mappings.

All 13 enums defined in 001_initial_schema.py.
Uses create_type=False since enums already exist in database.
Uses values_callable to ensure enum values (not names) are persisted.
"""

import enum
from sqlalchemy import Enum as SAEnum


# =============================================================================
# Python Enum Definitions
# =============================================================================

class PassType(str, enum.Enum):
    """Pass type: definition (Pass 1) or execution (Pass 2)."""
    DEFINITION = "definition"
    EXECUTION = "execution"


class StepName(str, enum.Enum):
    """The 10 workflow steps."""
    PROBLEM_DEFINITION = "problem_definition"
    REQUIREMENTS = "requirements"
    OBJECTIVES = "objectives"
    VERIFICATION_DESIGN = "verification_design"
    VALIDATION_DESIGN = "validation_design"
    EVALUATION_CRITERIA = "evaluation_criteria"
    ASSESSMENT_PROTOCOL = "assessment_protocol"
    IMPLEMENTATION = "implementation"
    REFLECTION = "reflection"
    RESOLUTION = "resolution"


class StepStatus(str, enum.Enum):
    """Coarse-grained step status (external visibility)."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    AWAITING_CLARIFICATION = "awaiting_clarification"
    AWAITING_REVIEW = "awaiting_review"
    APPROVED = "approved"
    REVISION_REQUESTED = "revision_requested"


class StepPhase(str, enum.Enum):
    """Fine-grained step phase (internal state)."""
    RECEIVED = "received"
    ANALYZING = "analyzing"
    ELICITING = "eliciting"
    STRUCTURING = "structuring"
    VALIDATING = "validating"
    REVIEWING = "reviewing"
    COMPLETE = "complete"


class WorkflowStatus(str, enum.Enum):
    """Overall workflow status."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class InstanceType(str, enum.Enum):
    """Instance hierarchy type."""
    UNIVERSAL = "universal"
    IMPLEMENTATION = "implementation"
    DOMAIN = "domain"


class GatePolicy(str, enum.Enum):
    """Pass 1 gate policy."""
    NONE = "none"
    PER_STEP = "per_step"
    END_OF_PASS = "end_of_pass"


class DocumentType(str, enum.Enum):
    """Methodology document types (Pass 1)."""
    DATA_SHEET = "data_sheet"
    TODO_LIST = "todo_list"
    GUIDANCE = "guidance"
    DETAILED_PROCEDURE = "detailed_procedure"


class DocumentVersion(str, enum.Enum):
    """Methodology document iteration versions."""
    V1 = "v1"
    V2 = "v2"
    V3 = "v3"


class MessageRole(str, enum.Enum):
    """Conversation message role."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class HumanAction(str, enum.Enum):
    """Human actions at gates."""
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"
    MESSAGE = "message"


class RequirementCategory(str, enum.Enum):
    """Step 2 requirement categories."""
    FR = "FR"   # Functional
    NFR = "NFR"  # Non-Functional
    CR = "CR"   # Constraint
    IR = "IR"   # Interface


class ObjectiveCategory(str, enum.Enum):
    """Step 3 objective categories."""
    CAP = "CAP"   # Capability
    QUAL = "QUAL"  # Quality
    COMP = "COMP"  # Compliance
    INTF = "INTF"  # Interface


# =============================================================================
# SQLAlchemy Enum Type Factories
# =============================================================================
# These create SQLAlchemy Enum types that:
# 1. Reference existing PostgreSQL enums (create_type=False)
# 2. Persist enum values, not Python names (values_callable)

def _get_enum_values(enum_class):
    """Extract enum values for SQLAlchemy values_callable.

    This function is called by SQLAlchemy with the enum class
    and should return a list of the enum's string values.
    """
    return [e.value for e in enum_class]


# SQLAlchemy enum types for use in Column definitions
PassTypeEnum = SAEnum(
    PassType,
    name="pass_type",
    create_type=False,
    values_callable=_get_enum_values,
)

StepNameEnum = SAEnum(
    StepName,
    name="step_name",
    create_type=False,
    values_callable=_get_enum_values,
)

StepStatusEnum = SAEnum(
    StepStatus,
    name="step_status",
    create_type=False,
    values_callable=_get_enum_values,
)

StepPhaseEnum = SAEnum(
    StepPhase,
    name="step_phase",
    create_type=False,
    values_callable=_get_enum_values,
)

WorkflowStatusEnum = SAEnum(
    WorkflowStatus,
    name="workflow_status",
    create_type=False,
    values_callable=_get_enum_values,
)

InstanceTypeEnum = SAEnum(
    InstanceType,
    name="instance_type",
    create_type=False,
    values_callable=_get_enum_values,
)

GatePolicyEnum = SAEnum(
    GatePolicy,
    name="gate_policy",
    create_type=False,
    values_callable=_get_enum_values,
)

DocumentTypeEnum = SAEnum(
    DocumentType,
    name="document_type",
    create_type=False,
    values_callable=_get_enum_values,
)

DocumentVersionEnum = SAEnum(
    DocumentVersion,
    name="document_version",
    create_type=False,
    values_callable=_get_enum_values,
)

MessageRoleEnum = SAEnum(
    MessageRole,
    name="message_role",
    create_type=False,
    values_callable=_get_enum_values,
)

HumanActionEnum = SAEnum(
    HumanAction,
    name="human_action",
    create_type=False,
    values_callable=_get_enum_values,
)

RequirementCategoryEnum = SAEnum(
    RequirementCategory,
    name="requirement_category",
    create_type=False,
    values_callable=_get_enum_values,
)

ObjectiveCategoryEnum = SAEnum(
    ObjectiveCategory,
    name="objective_category",
    create_type=False,
    values_callable=_get_enum_values,
)
