"""Contract alignment - state_version, workflow_events, staleness.

Aligns backend with Architectural Contract v3.4 §9-12:
- §9.1: state_version on workflows (optimistic concurrency)
- §9.2: workflow_events table (durable event log with sequence)
- §9.4: staleness tracking on artifacts

Revision ID: 002
Revises: 001
Create Date: 2026-01-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # 1. Add state_version to workflows (§9.1)
    # =========================================================================
    op.execute("""
        ALTER TABLE workflows
        ADD COLUMN state_version INTEGER NOT NULL DEFAULT 1
    """)

    # =========================================================================
    # 2. Create workflow_events table (§9.2)
    # =========================================================================
    op.execute("""
        CREATE TABLE workflow_events (
            id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            workflow_id         UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
            sequence            INTEGER NOT NULL,
            event_type          VARCHAR(100) NOT NULL,
            payload             JSONB NOT NULL DEFAULT '{}',
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            -- Uniqueness constraint for gap-free monotonic sequence per workflow
            CONSTRAINT uq_workflow_events_sequence UNIQUE (workflow_id, sequence)
        )
    """)

    # Indexes for efficient queries
    op.execute("CREATE INDEX idx_workflow_events_workflow ON workflow_events(workflow_id)")
    op.execute("CREATE INDEX idx_workflow_events_sequence ON workflow_events(workflow_id, sequence)")
    op.execute("CREATE INDEX idx_workflow_events_created ON workflow_events(created_at)")

    # =========================================================================
    # 3. Add staleness columns to artifacts (§9.4)
    # =========================================================================
    op.execute("""
        ALTER TABLE artifacts
        ADD COLUMN is_stale BOOLEAN NOT NULL DEFAULT FALSE
    """)
    op.execute("""
        ALTER TABLE artifacts
        ADD COLUMN stale_reason VARCHAR(500) NULL
    """)
    op.execute("""
        ALTER TABLE artifacts
        ADD COLUMN stale_since TIMESTAMPTZ NULL
    """)

    # Index for staleness queries
    op.execute("CREATE INDEX idx_artifacts_stale ON artifacts(workflow_id, is_stale) WHERE is_stale = TRUE")

    # =========================================================================
    # 4. Function for getting next sequence with advisory lock (§9.2, §11.3)
    # =========================================================================
    op.execute("""
        CREATE OR REPLACE FUNCTION get_next_event_sequence(p_workflow_id UUID)
        RETURNS INTEGER AS $$
        DECLARE
            next_seq INTEGER;
            lock_id BIGINT;
        BEGIN
            -- Generate a consistent lock ID from workflow UUID
            -- Use first 8 bytes of UUID as bigint for advisory lock
            lock_id := ('x' || substr(p_workflow_id::text, 1, 8))::bit(32)::bigint;

            -- Acquire transaction-scoped advisory lock
            PERFORM pg_advisory_xact_lock(lock_id);

            -- Get next sequence number
            SELECT COALESCE(MAX(sequence), 0) + 1 INTO next_seq
            FROM workflow_events
            WHERE workflow_id = p_workflow_id;

            RETURN next_seq;
        END;
        $$ LANGUAGE plpgsql
    """)


def downgrade() -> None:
    # Drop function
    op.execute("DROP FUNCTION IF EXISTS get_next_event_sequence(UUID)")

    # Drop staleness columns from artifacts
    op.execute("DROP INDEX IF EXISTS idx_artifacts_stale")
    op.execute("ALTER TABLE artifacts DROP COLUMN IF EXISTS stale_since")
    op.execute("ALTER TABLE artifacts DROP COLUMN IF EXISTS stale_reason")
    op.execute("ALTER TABLE artifacts DROP COLUMN IF EXISTS is_stale")

    # Drop workflow_events table
    op.execute("DROP INDEX IF EXISTS idx_workflow_events_created")
    op.execute("DROP INDEX IF EXISTS idx_workflow_events_sequence")
    op.execute("DROP INDEX IF EXISTS idx_workflow_events_workflow")
    op.execute("DROP TABLE IF EXISTS workflow_events")

    # Drop state_version from workflows
    op.execute("ALTER TABLE workflows DROP COLUMN IF EXISTS state_version")
