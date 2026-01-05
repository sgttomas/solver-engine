"""Add pending status to step_status enum.

Per V2.8.0 Spec line 876-878: 'pending' = "Queued for (re-)execution"
Required for /re-execute endpoint to set status when queuing step for re-execution.

Revision ID: 004
Revises: 003
Create Date: 2026-01-05
"""
from typing import Union
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels = None
depends_on = None


def upgrade():
    # Add 'pending' value to step_status enum after 'not_started'
    # Using IF NOT EXISTS for idempotency
    op.execute("ALTER TYPE step_status ADD VALUE IF NOT EXISTS 'pending' AFTER 'not_started'")


def downgrade():
    # PostgreSQL does not support removing enum values directly.
    # Would need to:
    # 1. Rename the type
    # 2. Create new type without the value
    # 3. Update all columns to use new type
    # 4. Drop the old type
    #
    # Since 'pending' is a transient state, downgrade is not critical.
    pass
