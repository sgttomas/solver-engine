/**
 * SOLVER Web - API Type Definitions
 *
 * TypeScript interfaces matching Tech Spec V2.8.2 §16.9 and Appendix C.
 * Package 6.5 deliverable per Development Directive v1.5.1.
 *
 * DRIFT RISK NOTE: These types are local copies pinned to Tech Spec V2.8.2.
 * No shared TypeScript contract source exists in this repository. Backend types
 * are Python Pydantic models. These types MUST be manually kept in sync with
 * specification updates. When updating, verify against:
 * - docs/spec/4_SOLVER-Technical-Spec-V2.8.2.md §16.9 (API Schemas)
 * - docs/spec/4_SOLVER-Technical-Spec-V2.8.2.md Appendix C (Response Examples)
 */

// ============================================================================
// Core Enums / Literal Types
// ============================================================================

/**
 * Step names (10 total per Tech Spec §4.1)
 */
export type StepName =
  | 'problem_definition'
  | 'requirements'
  | 'objectives'
  | 'verification_design'
  | 'validation_design'
  | 'evaluation_criteria'
  | 'assessment_protocol'
  | 'implementation'
  | 'reflection'
  | 'resolution';

/**
 * Pass types per Tech Spec §4.2
 */
export type PassType = 'definition' | 'execution';

/**
 * Step status values per Tech Spec §4.3
 */
export type StepStatus =
  | 'not_started'
  | 'pending'
  | 'in_progress'
  | 'awaiting_clarification'
  | 'awaiting_review'
  | 'approved'
  | 'revision_requested';

/**
 * Step phase values (fine-grained internal state) per Tech Spec §4.4
 */
export type StepPhase =
  | 'received'
  | 'analyzing'
  | 'eliciting'
  | 'structuring'
  | 'validating'
  | 'reviewing'
  | 'complete';

/**
 * Workflow status (same as StepStatus for workflow-level)
 */
export type WorkflowStatus = StepStatus;

// ============================================================================
// Position Response (used in multiple endpoints)
// ============================================================================

/**
 * Position object per Tech Spec V2.8.2 standard
 */
export interface PositionResponse {
  instance_number: number;
  step_number: number;
  step_name: StepName;
  pass_type: PassType;
  status: StepStatus;
  phase: StepPhase;
}

// ============================================================================
// Workflow Responses
// ============================================================================

/**
 * Step state response (nested in WorkflowResponse)
 */
export interface StepStateResponse {
  step_name: StepName;
  step_number: number;
  pass_type: PassType;
  status: StepStatus;
  phase: StepPhase;
}

/**
 * Workflow response from GET /workflows/{id} and mutation responses
 * Per Tech Spec §16.9 and Appendix C.1
 */
export interface WorkflowResponse {
  workflow_id: string;
  thread_id: string;
  instance_id: string;
  status: WorkflowStatus;

  /** Nested position object (V2.8.2 standard) */
  position: PositionResponse;

  /** Flat fields for backward compatibility */
  current_pass: PassType;
  current_step: StepName;
  current_step_number: number;

  original_problem: string;
  domain: string | null;
  step_state: StepStateResponse | null;

  /** For optimistic concurrency control (OCC) */
  state_version: number;

  created_at: string;
  updated_at: string;
}

// ============================================================================
// Message Response (V2.8.2)
// ============================================================================

/**
 * Message response from POST /workflows/{id}/actions/message
 * Per Tech Spec V2.8.2 §16.7: Message is NOT state-mutating,
 * returns minimal response with message_id and status.
 */
export interface MessageResponse {
  message_id: string;
  status: 'sent';
}

// ============================================================================
// Progress Response
// ============================================================================

/**
 * Step progress entry per Tech Spec V2.8.2 Appendix C.3
 */
export interface StepProgressEntry {
  pass_type: PassType;
  step_number: number;
  step_name: StepName;
  status: StepStatus;
  phase: StepPhase;

  has_artifact: boolean;
  is_stale: boolean;
  artifact_id: string | null;
  artifact_revision: number | null;
  /** V2.8.2: When step execution started */
  started_at: string | null;
  /** V2.8.2: When step execution completed */
  completed_at: string | null;
  updated_at: string | null;
}

/**
 * Progress response from GET /workflows/{id}/progress
 * Per Tech Spec §16.9
 */
export interface ProgressResponse {
  workflow_id: string;
  state_version: number;
  current_pass: PassType;
  current_step: StepName;
  current_step_number: number;
  steps: StepProgressEntry[];
}

// ============================================================================
// Staleness Response
// ============================================================================

/**
 * Stale artifact entry per Tech Spec V2.8.2 Appendix C.5
 */
export interface StaleArtifactEntry {
  artifact_id: string;
  step_number: number;
  step_name: StepName;
  pass_type: PassType;
  /** V2.8.2: Same as step_name (e.g., "requirements") */
  artifact_type: string;
  stale_reason: string | null;
  stale_since: string | null;
  /** V2.8.2: Whether this blocks workflow completion (drives can_complete) */
  blocking: boolean;
}

/**
 * Stale link entry per Tech Spec Appendix C
 */
export interface StaleLinkEntry {
  link_id: string;
  from_step: string;
  to_step: string;
  link_type: string;
  reason: string | null;
  stale_since: string | null;
}

/**
 * Staleness response from GET /workflows/{id}/staleness
 * Per Tech Spec V2.8.2 §16.9 and Appendix C.5
 */
export interface StalenessResponse {
  workflow_id: string;
  state_version: number;
  position: PositionResponse;
  /** V2.8.2: Explicit boolean for quick staleness check */
  has_stale_artifacts: boolean;
  can_complete: boolean;
  blocking_reasons: string[];
  stale_artifacts: StaleArtifactEntry[];
  /** V2.8.2: Renamed from stale_links */
  stale_trace_links: StaleLinkEntry[];
}

// ============================================================================
// Request Types
// ============================================================================

/**
 * Create workflow request
 * Per Tech Spec §16.1
 */
export interface CreateWorkflowRequest {
  problem: string;
  created_by: string;
  instance_number?: number;
  domain?: string | null;
}

/**
 * Expected position for OCC
 * Per Contract §13.5 (R18)
 */
export interface ExpectedPosition {
  pass_type: PassType;
  step_name: StepName;
  step_number: number;
  status: StepStatus;
}

/**
 * Approve request
 * Per Tech Spec §16.5
 * MUST include expected_state_version and expected_position
 */
export interface ApproveRequest {
  actor_id?: string;
  expected_state_version: number;
  expected_position: ExpectedPosition;
}

/**
 * Revise request
 * Per Tech Spec §16.6
 * MUST include expected_state_version, expected_position, and feedback
 */
export interface ReviseRequest {
  feedback: string;
  actor_id?: string;
  expected_state_version: number;
  expected_position: ExpectedPosition;
}

/**
 * Message request
 * Per Tech Spec §16.7
 * Does NOT require expected_state_version
 */
export interface MessageRequest {
  content: string;
  actor_id?: string;
}

// ============================================================================
// Error Types
// ============================================================================

/**
 * State conflict response (409)
 * Per Tech Spec §16.8
 */
export interface StateConflictResponse {
  error_code: 'STATE_CONFLICT';
  message: string;
  current_position: PositionResponse;
  current_state_version: number;
}

/**
 * Generic API error response
 */
export interface ApiErrorResponse {
  detail: string;
}

// ============================================================================
// Artifact Response
// ============================================================================

/**
 * Artifact response from GET /workflows/{id}/artifacts/{aid}
 * Per Tech Spec V2.8.2 Appendix C.4
 *
 * Note: artifact_type uses step_name value (e.g., "requirements"),
 * not the internal DB discriminator ("methodology_doc" or "step_package").
 */
export interface ArtifactResponse {
  id: string;
  workflow_id: string;
  pass_type: PassType;
  step_name: StepName;
  step_number: number;
  artifact_type: StepName; // Uses step_name value per C.4
  revision: number;
  supersedes: string | null;
  superseded_by: string | null;
  /** For methodology docs: { markdown, document_type, version }. For step packages: original JSON. */
  content_jsonb: Record<string, unknown> | null;
  stale: boolean;
  stale_reason: string | null;
  stale_since: string | null;
  trace_id: string | null;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// Utility Types
// ============================================================================

/**
 * Check if error is a state conflict (409)
 */
export function isStateConflict(error: unknown): error is StateConflictResponse {
  return (
    typeof error === 'object' &&
    error !== null &&
    'error_code' in error &&
    (error as StateConflictResponse).error_code === 'STATE_CONFLICT'
  );
}
