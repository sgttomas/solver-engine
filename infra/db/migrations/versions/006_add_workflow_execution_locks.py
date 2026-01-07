"""Add workflow_execution_locks table for runner lease management.

Per Tech Spec V2.8.4 Section 16.5: Runner lease management.
Enables exclusive execution via time-bounded leases.

Revision ID: 006
Revises: 005
Create Date: 2026-01-06
"""

from typing import Sequence, Union

from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # 1. CREATE workflow_execution_locks TABLE
    # =========================================================================
    op.execute("""
        CREATE TABLE workflow_execution_locks (
            workflow_id UUID PRIMARY KEY REFERENCES workflows(id) ON DELETE CASCADE,
            locked_by VARCHAR(255) NOT NULL,
            locked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            expires_at TIMESTAMPTZ NOT NULL,
            CONSTRAINT valid_expiry CHECK (expires_at > locked_at)
        )
    """)

    # =========================================================================
    # 2. CREATE INDEX for expired lease lookup
    # =========================================================================
    op.execute("""
        CREATE INDEX idx_locks_expiry ON workflow_execution_locks(expires_at)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_locks_expiry")
    op.execute("DROP TABLE IF EXISTS workflow_execution_locks")
