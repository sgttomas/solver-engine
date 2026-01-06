/**
 * SOLVER Web - Action Gating Hook
 *
 * Enforces approve/revise action availability per Architectural Contract v3.4 §14.3.
 * Package 6.4 deliverable per Development Directive v1.5.1.
 *
 * Contract Requirements Implemented:
 * - R3: canAct=false until staleness query completes successfully
 * - R4: canAct=false while resyncing (connectionStatus !== 'connected')
 * - R5: canAct=false while reconnecting (connectionStatus !== 'connected')
 * - R6: canAct=false if staleness.can_complete === false
 * - R14: canAct=false if ANY canonical query is fetching
 * - R15: canAct=false unless connectionStatus === 'connected'
 * - §14.3: canAct requires position.status === 'awaiting_review'
 *
 * NOTE: Background refetch error handling is wired in Package 6.6.
 * Per R13, canonical refetch failure transitions connectionStatus to 'failed',
 * which this hook respects via the connection.status check.
 */

'use client';

import type { UseWorkflowConnectionReturn } from './useWorkflowConnection';

// ============================================================================
// Types
// ============================================================================

/**
 * Query state shape for gating checks.
 * Matches TanStack Query return signature (subset).
 */
interface QueryState<T> {
  data?: T;
  isFetching: boolean;
  isSuccess: boolean;
  isError: boolean;
}

/**
 * Minimal workflow response shape for gating.
 * Only includes fields needed for action eligibility.
 */
interface WorkflowData {
  position: {
    status: string;
  };
  state_version: number;
}

/**
 * Minimal staleness response shape for gating.
 */
interface StalenessData {
  can_complete: boolean;
}

/**
 * Parameters for useCanAct hook.
 *
 * IMPORTANT: `connection` MUST be sourced from useWorkflowConnection.
 * This enforces R7/R13 semantics where connectionStatus reflects
 * canonical refetch success/failure.
 */
export interface UseCanActParams {
  /**
   * Connection state from useWorkflowConnection.
   * MUST be from useWorkflowConnection to enforce R7/R13 semantics.
   */
  connection: Pick<UseWorkflowConnectionReturn, 'status'>;

  /**
   * Workflow query state (GET /workflows/{id}).
   * Part of canonical refetch bundle per Contract §10.4.
   */
  workflowQuery: QueryState<WorkflowData>;

  /**
   * Progress query state (GET /workflows/{id}/progress).
   * Part of canonical refetch bundle per Contract §10.4.
   */
  progressQuery: Pick<QueryState<unknown>, 'isFetching'>;

  /**
   * Staleness query state (GET /workflows/{id}/staleness).
   * Part of canonical refetch bundle per Contract §10.4.
   */
  stalenessQuery: QueryState<StalenessData>;
}

/**
 * Return type for useCanAct hook.
 */
export interface UseCanActReturn {
  /** Whether approve/revise actions are allowed */
  canAct: boolean;
  /** User-visible reason when canAct is false, null when true */
  reason: string | null;
}

// ============================================================================
// Reason Strings
// ============================================================================

const REASONS = {
  DISCONNECTED: 'Disconnected',
  RECONNECTING: 'Reconnecting...',
  RESYNCING: 'Syncing...',
  CONNECTING: 'Connecting...',
  FAILED: 'Connection failed',
  FETCHING_WORKFLOW: 'Fetching workflow state...',
  FETCHING_PROGRESS: 'Fetching progress...',
  FETCHING_STALENESS: 'Checking staleness...',
  NOT_AT_GATE: 'Not at review gate',
  STALENESS_LOADING: 'Loading staleness status...',
  STALENESS_ERROR: 'Failed to check staleness',
  STALE_ARTIFACTS: 'Cannot complete — stale artifacts exist',
} as const;

// ============================================================================
// Hook Implementation
// ============================================================================

/**
 * Action gating hook for approve/revise eligibility.
 *
 * Implements the exact "canAct iff" conditions from Contract §14.3:
 * 1. connectionStatus === 'connected'
 * 2. position.status === 'awaiting_review'
 * 3. Staleness state is known (isSuccess && !isError)
 * 4. All canonical queries are idle (!isFetching)
 * 5. staleness.can_complete === true
 *
 * Returns a user-visible reason when canAct is false.
 *
 * @param params - Query states and connection from useWorkflowConnection
 * @returns canAct boolean and reason string
 */
export function useCanAct(params: UseCanActParams): UseCanActReturn {
  const { connection, workflowQuery, progressQuery, stalenessQuery } = params;

  // -------------------------------------------------------------------------
  // Condition 1: connectionStatus === 'connected' (R15, R4, R5)
  // -------------------------------------------------------------------------
  if (connection.status !== 'connected') {
    const reason = getConnectionReason(connection.status);
    return { canAct: false, reason };
  }

  // -------------------------------------------------------------------------
  // Condition 4 (partial): Check isFetching on canonical queries (R14)
  // Check this early to provide specific feedback about which query is loading
  // -------------------------------------------------------------------------
  if (workflowQuery.isFetching) {
    return { canAct: false, reason: REASONS.FETCHING_WORKFLOW };
  }

  if (progressQuery.isFetching) {
    return { canAct: false, reason: REASONS.FETCHING_PROGRESS };
  }

  if (stalenessQuery.isFetching) {
    return { canAct: false, reason: REASONS.FETCHING_STALENESS };
  }

  // -------------------------------------------------------------------------
  // Condition 2: position.status === 'awaiting_review'
  // -------------------------------------------------------------------------
  const positionStatus = workflowQuery.data?.position?.status;
  if (positionStatus !== 'awaiting_review') {
    return { canAct: false, reason: REASONS.NOT_AT_GATE };
  }

  // -------------------------------------------------------------------------
  // Condition 3: Staleness state is known (not undefined, not errored) (R3)
  // Check isError BEFORE !isSuccess — when query errors, isSuccess=false
  // and isError=true, so checking !isSuccess first would mask the error.
  // -------------------------------------------------------------------------
  if (stalenessQuery.isError) {
    return { canAct: false, reason: REASONS.STALENESS_ERROR };
  }

  if (!stalenessQuery.isSuccess) {
    return { canAct: false, reason: REASONS.STALENESS_LOADING };
  }

  // -------------------------------------------------------------------------
  // Condition 5: staleness.can_complete === true (R6)
  // -------------------------------------------------------------------------
  if (stalenessQuery.data?.can_complete !== true) {
    return { canAct: false, reason: REASONS.STALE_ARTIFACTS };
  }

  // -------------------------------------------------------------------------
  // All conditions met
  // -------------------------------------------------------------------------
  return { canAct: true, reason: null };
}

// ============================================================================
// Helpers
// ============================================================================

/**
 * Get user-visible reason for non-connected status.
 */
function getConnectionReason(
  status: UseWorkflowConnectionReturn['status']
): string {
  switch (status) {
    case 'disconnected':
      return REASONS.DISCONNECTED;
    case 'connecting':
      return REASONS.CONNECTING;
    case 'reconnecting':
      return REASONS.RECONNECTING;
    case 'resyncing':
      return REASONS.RESYNCING;
    case 'failed':
      return REASONS.FAILED;
    default:
      return REASONS.DISCONNECTED;
  }
}
