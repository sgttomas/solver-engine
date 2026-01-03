"""
SOLVER Database Models Package.

Exports all SQLAlchemy models and enums for database operations.
Models map to tables defined in 001_initial_schema.py.
"""

# Base class
from infrastructure.db.models.base import Base

# Enums (Python enum classes)
from infrastructure.db.models.enums import (
    PassType,
    StepName,
    StepStatus,
    StepPhase,
    WorkflowStatus,
    InstanceType,
    GatePolicy,
    DocumentType,
    DocumentVersion,
    MessageRole,
    HumanAction,
    RequirementCategory,
    ObjectiveCategory,
)

# SQLAlchemy enum types (for column definitions)
from infrastructure.db.models.enums import (
    PassTypeEnum,
    StepNameEnum,
    StepStatusEnum,
    StepPhaseEnum,
    WorkflowStatusEnum,
    InstanceTypeEnum,
    GatePolicyEnum,
    DocumentTypeEnum,
    DocumentVersionEnum,
    MessageRoleEnum,
    HumanActionEnum,
    RequirementCategoryEnum,
    ObjectiveCategoryEnum,
)

# Models (9 tables)
from infrastructure.db.models.instance import Instance
from infrastructure.db.models.workflow import Workflow
from infrastructure.db.models.step_execution import StepExecution
from infrastructure.db.models.artifact import Artifact
from infrastructure.db.models.traceability import TraceabilityLink
from infrastructure.db.models.message import Message
from infrastructure.db.models.audit import AuditLog
from infrastructure.db.models.checkpoint import Checkpoint, CheckpointWrite

__all__ = [
    # Base
    "Base",
    # Python enums
    "PassType",
    "StepName",
    "StepStatus",
    "StepPhase",
    "WorkflowStatus",
    "InstanceType",
    "GatePolicy",
    "DocumentType",
    "DocumentVersion",
    "MessageRole",
    "HumanAction",
    "RequirementCategory",
    "ObjectiveCategory",
    # SQLAlchemy enum types
    "PassTypeEnum",
    "StepNameEnum",
    "StepStatusEnum",
    "StepPhaseEnum",
    "WorkflowStatusEnum",
    "InstanceTypeEnum",
    "GatePolicyEnum",
    "DocumentTypeEnum",
    "DocumentVersionEnum",
    "MessageRoleEnum",
    "HumanActionEnum",
    "RequirementCategoryEnum",
    "ObjectiveCategoryEnum",
    # Models
    "Instance",
    "Workflow",
    "StepExecution",
    "Artifact",
    "TraceabilityLink",
    "Message",
    "AuditLog",
    "Checkpoint",
    "CheckpointWrite",
]
