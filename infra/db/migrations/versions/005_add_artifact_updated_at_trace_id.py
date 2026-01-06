"""Add updated_at and trace_id columns to artifacts table.

Per Tech Spec V2.8.0 Appendix C.4: Artifact response requires updated_at and trace_id fields.
- updated_at: Timestamp with timezone, auto-update on modification (via DB trigger)
- trace_id: String for traceability linking

Revision ID: 005
Revises: 004
Create Date: 2026-01-06
"""
from typing import Sequence, Union

from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # 1. ADD updated_at COLUMN
    # =========================================================================
    op.execute("""
        ALTER TABLE artifacts
        ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    """)

    # =========================================================================
    # 2. ADD trace_id COLUMN
    # =========================================================================
    op.execute("""
        ALTER TABLE artifacts
        ADD COLUMN trace_id VARCHAR(255) NULL
    """)

    # =========================================================================
    # 3. BACKFILL updated_at FROM created_at
    # =========================================================================
    op.execute("UPDATE artifacts SET updated_at = created_at")

    # =========================================================================
    # 4. AUTO-UPDATE TRIGGER (mirrors 003_remediation.py pattern)
    # =========================================================================
    op.execute("""
        CREATE OR REPLACE FUNCTION update_artifact_timestamp()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)

    op.execute("""
        CREATE TRIGGER artifact_updated_at
        BEFORE UPDATE ON artifacts
        FOR EACH ROW
        EXECUTE FUNCTION update_artifact_timestamp()
    """)


def downgrade() -> None:
    # Drop trigger first
    op.execute("DROP TRIGGER IF EXISTS artifact_updated_at ON artifacts")
    op.execute("DROP FUNCTION IF EXISTS update_artifact_timestamp()")

    # Drop columns
    op.execute("ALTER TABLE artifacts DROP COLUMN IF EXISTS trace_id")
    op.execute("ALTER TABLE artifacts DROP COLUMN IF EXISTS updated_at")
