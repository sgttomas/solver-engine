"""Remediation - staleness alignment, lineage, optimistic concurrency fixes.

Addresses Co-Developer-1 findings for Contract alignment:
- §7: Artifact lineage (supersedes/superseded_by) for insert-per-revision model
- §7: Staleness propagation trigger (marks downstream on new revision)
- §7: Traceability link staleness columns + validated_at
- §9.2: Fix advisory lock collision risk (use hashtext)
- §9.4: Rename is_stale → stale (spec alignment)
- §10.2: step_executions.updated_at for progress endpoint

Revision ID: 003
Revises: 002
Create Date: 2026-01-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # 1. ARTIFACT LINEAGE COLUMNS (spec §7)
    # =========================================================================
    op.execute("""
        ALTER TABLE artifacts
        ADD COLUMN supersedes UUID REFERENCES artifacts(id)
    """)
    op.execute("""
        ALTER TABLE artifacts
        ADD COLUMN superseded_by UUID REFERENCES artifacts(id)
    """)

    # Index for lineage traversal
    op.execute("CREATE INDEX idx_artifacts_supersedes ON artifacts(supersedes)")
    op.execute("CREATE INDEX idx_artifacts_superseded_by ON artifacts(superseded_by)")

    # =========================================================================
    # 2. RENAME is_stale → stale (spec alignment)
    # =========================================================================
    # Drop old index first
    op.execute("DROP INDEX IF EXISTS idx_artifacts_stale")

    # Rename column
    op.execute("ALTER TABLE artifacts RENAME COLUMN is_stale TO stale")

    # Recreate index with new column name
    op.execute("CREATE INDEX idx_artifacts_stale ON artifacts(workflow_id, stale) WHERE stale = TRUE")

    # =========================================================================
    # 3. UNIQUE INDEXES FOR "LATEST" PER LINEAGE (spec §7)
    # =========================================================================
    # Exactly one artifact per lineage has superseded_by IS NULL

    # For methodology_doc artifacts
    op.execute("""
        CREATE UNIQUE INDEX idx_latest_methodology_doc ON artifacts(
            workflow_id, step_name, artifact_type, document_type, document_version
        ) WHERE artifact_type = 'methodology_doc' AND superseded_by IS NULL
    """)

    # For step_package artifacts
    op.execute("""
        CREATE UNIQUE INDEX idx_latest_step_package ON artifacts(
            workflow_id, step_name, artifact_type
        ) WHERE artifact_type = 'step_package' AND superseded_by IS NULL
    """)

    # =========================================================================
    # 4. LATEST ARTIFACTS VIEW (convenience)
    # =========================================================================
    op.execute("""
        CREATE VIEW latest_artifacts AS
        SELECT * FROM artifacts WHERE superseded_by IS NULL
    """)

    # =========================================================================
    # 5. TRACEABILITY LINK STALENESS (spec §7)
    # =========================================================================
    op.execute("""
        ALTER TABLE traceability_links
        ADD COLUMN stale BOOLEAN NOT NULL DEFAULT FALSE
    """)
    op.execute("""
        ALTER TABLE traceability_links
        ADD COLUMN stale_reason VARCHAR(500) NULL
    """)
    op.execute("""
        ALTER TABLE traceability_links
        ADD COLUMN stale_since TIMESTAMPTZ NULL
    """)
    op.execute("""
        ALTER TABLE traceability_links
        ADD COLUMN validated_at TIMESTAMPTZ NULL
    """)

    # Index for stale links queries
    op.execute("""
        CREATE INDEX idx_trace_stale ON traceability_links(workflow_id, stale)
        WHERE stale = TRUE
    """)

    # =========================================================================
    # 6. STALENESS PROPAGATION TRIGGER (spec §7 - exact SQL)
    # =========================================================================
    # When a new artifact revision is inserted (supersedes IS NOT NULL),
    # mark DOWNSTREAM latest artifacts and traceability links as stale.
    op.execute("""
        CREATE OR REPLACE FUNCTION propagate_staleness()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Only propagate if this is a new revision (not first creation)
            IF NEW.supersedes IS NOT NULL THEN
                -- Mark downstream latest artifacts as stale
                UPDATE artifacts
                SET stale = TRUE,
                    stale_reason = 'upstream_step_' || NEW.step_number || '_revised',
                    stale_since = NOW()
                WHERE workflow_id = NEW.workflow_id
                  AND step_number > NEW.step_number  -- DOWNSTREAM steps
                  AND superseded_by IS NULL  -- Only mark latest versions
                  AND stale = FALSE;

                -- Also mark affected traceability links
                UPDATE traceability_links
                SET stale = TRUE,
                    stale_reason = 'source_step_' || NEW.step_number || '_revised',
                    stale_since = NOW()
                WHERE workflow_id = NEW.workflow_id
                  AND from_step = NEW.step_number  -- Links FROM this step
                  AND stale = FALSE;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)

    # Trigger fires on INSERT when supersedes IS NOT NULL (new revision)
    op.execute("""
        CREATE TRIGGER artifact_staleness_trigger
        AFTER INSERT ON artifacts
        FOR EACH ROW
        WHEN (NEW.supersedes IS NOT NULL)
        EXECUTE FUNCTION propagate_staleness()
    """)

    # =========================================================================
    # 7. FIX ADVISORY LOCK (collision-resistant with hashtext)
    # =========================================================================
    op.execute("""
        CREATE OR REPLACE FUNCTION get_next_event_sequence(p_workflow_id UUID)
        RETURNS INTEGER AS $$
        DECLARE
            next_seq INTEGER;
            lock_id BIGINT;
        BEGIN
            -- Use hashtext for collision-resistant lock ID
            lock_id := hashtext(p_workflow_id::text)::bigint;

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

    # =========================================================================
    # 8. STEP EXECUTION UPDATED_AT (for progress endpoint)
    # =========================================================================
    op.execute("""
        ALTER TABLE step_executions
        ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    """)

    # Auto-update trigger
    op.execute("""
        CREATE OR REPLACE FUNCTION update_step_execution_timestamp()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)

    op.execute("""
        CREATE TRIGGER step_execution_updated_at
        BEFORE UPDATE ON step_executions
        FOR EACH ROW
        EXECUTE FUNCTION update_step_execution_timestamp()
    """)


def downgrade() -> None:
    # Drop step_execution updated_at trigger and column
    op.execute("DROP TRIGGER IF EXISTS step_execution_updated_at ON step_executions")
    op.execute("DROP FUNCTION IF EXISTS update_step_execution_timestamp()")
    op.execute("ALTER TABLE step_executions DROP COLUMN IF EXISTS updated_at")

    # Revert advisory lock function to original (first 8 chars)
    op.execute("""
        CREATE OR REPLACE FUNCTION get_next_event_sequence(p_workflow_id UUID)
        RETURNS INTEGER AS $$
        DECLARE
            next_seq INTEGER;
            lock_id BIGINT;
        BEGIN
            lock_id := ('x' || substr(p_workflow_id::text, 1, 8))::bit(32)::bigint;
            PERFORM pg_advisory_xact_lock(lock_id);
            SELECT COALESCE(MAX(sequence), 0) + 1 INTO next_seq
            FROM workflow_events
            WHERE workflow_id = p_workflow_id;
            RETURN next_seq;
        END;
        $$ LANGUAGE plpgsql
    """)

    # Drop staleness trigger and function
    op.execute("DROP TRIGGER IF EXISTS artifact_staleness_trigger ON artifacts")
    op.execute("DROP FUNCTION IF EXISTS propagate_staleness()")

    # Drop traceability link staleness columns
    op.execute("DROP INDEX IF EXISTS idx_trace_stale")
    op.execute("ALTER TABLE traceability_links DROP COLUMN IF EXISTS validated_at")
    op.execute("ALTER TABLE traceability_links DROP COLUMN IF EXISTS stale_since")
    op.execute("ALTER TABLE traceability_links DROP COLUMN IF EXISTS stale_reason")
    op.execute("ALTER TABLE traceability_links DROP COLUMN IF EXISTS stale")

    # Drop latest artifacts view
    op.execute("DROP VIEW IF EXISTS latest_artifacts")

    # Drop unique indexes for latest
    op.execute("DROP INDEX IF EXISTS idx_latest_step_package")
    op.execute("DROP INDEX IF EXISTS idx_latest_methodology_doc")

    # Rename stale back to is_stale
    op.execute("DROP INDEX IF EXISTS idx_artifacts_stale")
    op.execute("ALTER TABLE artifacts RENAME COLUMN stale TO is_stale")
    op.execute("CREATE INDEX idx_artifacts_stale ON artifacts(workflow_id, is_stale) WHERE is_stale = TRUE")

    # Drop lineage columns and indexes
    op.execute("DROP INDEX IF EXISTS idx_artifacts_superseded_by")
    op.execute("DROP INDEX IF EXISTS idx_artifacts_supersedes")
    op.execute("ALTER TABLE artifacts DROP COLUMN IF EXISTS superseded_by")
    op.execute("ALTER TABLE artifacts DROP COLUMN IF EXISTS supersedes")
