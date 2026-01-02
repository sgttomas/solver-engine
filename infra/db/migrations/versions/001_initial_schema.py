"""Initial SOLVER database schema - Doc 3 Section 7

Revision ID: 001
Revises: 
Create Date: 2026-01-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # 1. Extensions (Doc 3 §7.1)
    # =========================================================================
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')

    # =========================================================================
    # 2. Enums (Doc 3 §7.2)
    # =========================================================================
    op.execute("CREATE TYPE pass_type AS ENUM ('definition', 'execution')")
    
    op.execute("""
        CREATE TYPE step_name AS ENUM (
            'problem_definition',
            'requirements',
            'objectives',
            'verification_design',
            'validation_design',
            'evaluation_criteria',
            'assessment_protocol',
            'implementation',
            'reflection',
            'resolution'
        )
    """)
    
    op.execute("""
        CREATE TYPE step_status AS ENUM (
            'not_started',
            'in_progress',
            'awaiting_clarification',
            'awaiting_review',
            'approved',
            'revision_requested'
        )
    """)
    
    op.execute("""
        CREATE TYPE step_phase AS ENUM (
            'received',
            'analyzing',
            'eliciting',
            'structuring',
            'validating',
            'reviewing',
            'complete'
        )
    """)
    
    op.execute("CREATE TYPE workflow_status AS ENUM ('active', 'paused', 'completed', 'abandoned')")
    op.execute("CREATE TYPE instance_type AS ENUM ('universal', 'implementation', 'domain')")
    op.execute("CREATE TYPE gate_policy AS ENUM ('none', 'per_step', 'end_of_pass')")
    op.execute("CREATE TYPE document_type AS ENUM ('data_sheet', 'todo_list', 'guidance', 'detailed_procedure')")
    op.execute("CREATE TYPE document_version AS ENUM ('v1', 'v2', 'v3')")
    op.execute("CREATE TYPE message_role AS ENUM ('user', 'assistant', 'system')")
    op.execute("CREATE TYPE human_action AS ENUM ('approve', 'reject', 'modify', 'message')")
    op.execute("CREATE TYPE requirement_category AS ENUM ('FR', 'NFR', 'CR', 'IR')")
    op.execute("CREATE TYPE objective_category AS ENUM ('CAP', 'QUAL', 'COMP', 'INTF')")

    # =========================================================================
    # 3. Tables (Doc 3 §7.3)
    # =========================================================================
    
    # instances - Instance 0/1/N hierarchy
    op.execute("""
        CREATE TABLE instances (
            id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            instance_number     INTEGER NOT NULL UNIQUE,
            instance_type       instance_type NOT NULL,
            parent_instance_id  UUID REFERENCES instances(id),
            name                VARCHAR(255) NOT NULL,
            description         TEXT,
            pass_1_gate_policy  gate_policy NOT NULL DEFAULT 'per_step',
            pack_manifest       JSONB,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            
            CONSTRAINT valid_instance_hierarchy CHECK (
                (instance_number = 0 AND instance_type = 'universal' AND parent_instance_id IS NULL) OR
                (instance_number = 1 AND instance_type = 'implementation') OR
                (instance_number >= 2 AND instance_type = 'domain')
            )
        )
    """)
    
    # workflows - Master workflow record
    op.execute("""
        CREATE TABLE workflows (
            id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            workflow_id         VARCHAR(255) UNIQUE NOT NULL,
            thread_id           VARCHAR(255) UNIQUE NOT NULL,
            instance_id         UUID NOT NULL REFERENCES instances(id),
            
            original_problem    TEXT NOT NULL,
            domain              VARCHAR(255),
            
            current_pass        pass_type NOT NULL DEFAULT 'definition',
            current_step        step_name NOT NULL DEFAULT 'problem_definition',
            current_step_number INTEGER NOT NULL DEFAULT 1,
            status              workflow_status NOT NULL DEFAULT 'active',
            
            pass_1_gate_policy  gate_policy NOT NULL DEFAULT 'per_step',
            
            created_by          VARCHAR(255) NOT NULL,
            last_actor_id       VARCHAR(255) NOT NULL,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            completed_at        TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX idx_workflows_thread ON workflows(thread_id)")
    op.execute("CREATE INDEX idx_workflows_instance ON workflows(instance_id)")
    op.execute("CREATE INDEX idx_workflows_status ON workflows(status)")
    
    # step_executions - Per-step state
    op.execute("""
        CREATE TABLE step_executions (
            id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            workflow_id         UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
            
            pass_type           pass_type NOT NULL,
            step_name           step_name NOT NULL,
            step_number         INTEGER NOT NULL,
            
            status              step_status NOT NULL DEFAULT 'not_started',
            phase               step_phase NOT NULL DEFAULT 'received',
            
            latest_artifact_id  UUID,
            human_feedback      TEXT,
            clarification_request JSONB,
            
            validation_status   VARCHAR(20),
            validation_errors   JSONB DEFAULT '[]',
            validation_warnings JSONB DEFAULT '[]',
            
            started_at          TIMESTAMPTZ,
            completed_at        TIMESTAMPTZ,
            
            turn_count          INTEGER NOT NULL DEFAULT 0,
            total_tokens        INTEGER NOT NULL DEFAULT 0,
            
            UNIQUE(workflow_id, pass_type, step_name)
        )
    """)
    op.execute("CREATE INDEX idx_steps_workflow ON step_executions(workflow_id)")
    op.execute("CREATE INDEX idx_steps_status ON step_executions(status)")
    
    # artifacts - Pass 1 methodology + Pass 2 packages
    op.execute("""
        CREATE TABLE artifacts (
            id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            workflow_id         UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
            
            pass_type           pass_type NOT NULL,
            step_name           step_name NOT NULL,
            step_number         INTEGER NOT NULL,
            
            artifact_type       VARCHAR(50) NOT NULL,
            
            document_type       document_type,
            document_version    document_version,
            content_markdown    TEXT,
            
            package_type        VARCHAR(50),
            content_jsonb       JSONB,
            revision            INTEGER NOT NULL DEFAULT 1,
            
            schema_version      VARCHAR(20),
            validation_status   VARCHAR(20),
            
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            
            CONSTRAINT valid_artifact_type CHECK (
                (artifact_type = 'methodology_doc' AND document_type IS NOT NULL AND document_version IS NOT NULL) OR
                (artifact_type = 'step_package' AND package_type IS NOT NULL AND content_jsonb IS NOT NULL)
            )
        )
    """)
    op.execute("CREATE INDEX idx_artifacts_workflow ON artifacts(workflow_id)")
    op.execute("CREATE INDEX idx_artifacts_step ON artifacts(step_name)")
    
    # traceability_links - Forward/backward trace relationships
    op.execute("""
        CREATE TABLE traceability_links (
            id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            workflow_id         UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
            
            from_step           INTEGER NOT NULL,
            from_type           VARCHAR(50) NOT NULL,
            from_id             VARCHAR(20) NOT NULL,
            
            to_step             INTEGER NOT NULL,
            to_type             VARCHAR(50) NOT NULL,
            to_id               VARCHAR(20) NOT NULL,
            
            link_type           VARCHAR(50) NOT NULL,
            consolidated        BOOLEAN NOT NULL DEFAULT FALSE,
            
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            
            UNIQUE(workflow_id, from_id, to_id, link_type)
        )
    """)
    op.execute("CREATE INDEX idx_trace_workflow ON traceability_links(workflow_id)")
    op.execute("CREATE INDEX idx_trace_from ON traceability_links(from_id)")
    op.execute("CREATE INDEX idx_trace_to ON traceability_links(to_id)")
    
    # messages - Conversation history
    op.execute("""
        CREATE TABLE messages (
            id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            workflow_id         UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
            step_execution_id   UUID NOT NULL REFERENCES step_executions(id) ON DELETE CASCADE,
            
            role                message_role NOT NULL,
            content             TEXT NOT NULL,
            metadata            JSONB NOT NULL DEFAULT '{}',
            
            input_tokens        INTEGER,
            output_tokens       INTEGER,
            
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            embedding           vector(1536)
        )
    """)
    op.execute("CREATE INDEX idx_messages_workflow ON messages(workflow_id)")
    op.execute("CREATE INDEX idx_messages_step ON messages(step_execution_id)")
    op.execute("CREATE INDEX idx_messages_embedding ON messages USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)")
    
    # audit_log - Immutable event record
    op.execute("""
        CREATE TABLE audit_log (
            id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            workflow_id         UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
            
            event_type          VARCHAR(50) NOT NULL,
            actor_id            VARCHAR(255) NOT NULL,
            
            pass_type           pass_type,
            step_name           step_name,
            step_number         INTEGER,
            
            from_status         step_status,
            to_status           step_status,
            from_phase          step_phase,
            to_phase            step_phase,
            
            artifact_id         UUID,
            details             JSONB NOT NULL DEFAULT '{}',
            
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX idx_audit_workflow ON audit_log(workflow_id)")
    op.execute("CREATE INDEX idx_audit_event ON audit_log(event_type)")
    op.execute("CREATE INDEX idx_audit_created ON audit_log(created_at)")
    
    # checkpoints - LangGraph state persistence
    op.execute("""
        CREATE TABLE checkpoints (
            thread_id           VARCHAR(255) NOT NULL,
            checkpoint_id       VARCHAR(255) NOT NULL,
            parent_checkpoint_id VARCHAR(255),
            checkpoint          JSONB NOT NULL,
            metadata            JSONB NOT NULL DEFAULT '{}',
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (thread_id, checkpoint_id)
        )
    """)
    op.execute("CREATE INDEX idx_checkpoints_thread ON checkpoints(thread_id)")
    
    # checkpoint_writes - LangGraph checkpoint writes
    op.execute("""
        CREATE TABLE checkpoint_writes (
            thread_id           VARCHAR(255) NOT NULL,
            checkpoint_id       VARCHAR(255) NOT NULL,
            task_id             VARCHAR(255) NOT NULL,
            idx                 INTEGER NOT NULL,
            channel             VARCHAR(255) NOT NULL,
            value               JSONB,
            PRIMARY KEY (thread_id, checkpoint_id, task_id, idx)
        )
    """)

    # =========================================================================
    # 4. Audit Trigger (Doc 3 §7.4)
    # =========================================================================
    op.execute("""
        CREATE OR REPLACE FUNCTION record_step_audit()
        RETURNS TRIGGER AS $$
        BEGIN
            IF OLD.status IS DISTINCT FROM NEW.status OR OLD.phase IS DISTINCT FROM NEW.phase THEN
                INSERT INTO audit_log (
                    workflow_id, event_type, actor_id,
                    pass_type, step_name, step_number,
                    from_status, to_status, from_phase, to_phase
                )
                SELECT 
                    NEW.workflow_id, 'state_change',
                    (SELECT last_actor_id FROM workflows WHERE id = NEW.workflow_id),
                    NEW.pass_type, NEW.step_name, NEW.step_number,
                    OLD.status, NEW.status, OLD.phase, NEW.phase;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    op.execute("""
        CREATE TRIGGER step_audit_trigger
        AFTER UPDATE ON step_executions
        FOR EACH ROW EXECUTE FUNCTION record_step_audit()
    """)

    # =========================================================================
    # 5. Seed Instance 0 (Doc 3 §7.3)
    # =========================================================================
    op.execute("""
        INSERT INTO instances (instance_number, instance_type, name, description)
        VALUES (0, 'universal', 'Universal Methodology', 
                'Domain-agnostic structured reasoning protocol')
    """)


def downgrade() -> None:
    # Drop in reverse order
    op.execute("DROP TRIGGER IF EXISTS step_audit_trigger ON step_executions")
    op.execute("DROP FUNCTION IF EXISTS record_step_audit()")
    
    op.execute("DROP TABLE IF EXISTS checkpoint_writes")
    op.execute("DROP TABLE IF EXISTS checkpoints")
    op.execute("DROP TABLE IF EXISTS audit_log")
    op.execute("DROP TABLE IF EXISTS messages")
    op.execute("DROP TABLE IF EXISTS traceability_links")
    op.execute("DROP TABLE IF EXISTS artifacts")
    op.execute("DROP TABLE IF EXISTS step_executions")
    op.execute("DROP TABLE IF EXISTS workflows")
    op.execute("DROP TABLE IF EXISTS instances")
    
    op.execute("DROP TYPE IF EXISTS objective_category")
    op.execute("DROP TYPE IF EXISTS requirement_category")
    op.execute("DROP TYPE IF EXISTS human_action")
    op.execute("DROP TYPE IF EXISTS message_role")
    op.execute("DROP TYPE IF EXISTS document_version")
    op.execute("DROP TYPE IF EXISTS document_type")
    op.execute("DROP TYPE IF EXISTS gate_policy")
    op.execute("DROP TYPE IF EXISTS instance_type")
    op.execute("DROP TYPE IF EXISTS workflow_status")
    op.execute("DROP TYPE IF EXISTS step_phase")
    op.execute("DROP TYPE IF EXISTS step_status")
    op.execute("DROP TYPE IF EXISTS step_name")
    op.execute("DROP TYPE IF EXISTS pass_type")
