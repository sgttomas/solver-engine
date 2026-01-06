/**
 * SOLVER Web - Message Action Gating Hook
 *
 * Enforces message action availability per Architectural Contract v3.4 §14.3.
 * Package 6.4 deliverable per Development Directive v1.5.1.
 *
 * Contract Requirements Implemented:
 * - §14.3 canMessage: More permissive than canAct
 *   - Allows connectionStatus ∈ {'connected', 'reconnecting', 'resyncing'}
 *   - Allows position.status ∈ {'awaiting_review', 'awaiting_clarification'}
 *
 * Per Tech Spec §6.5/§16.7:
 * - Message endpoint is NOT state-mutating
 * - Does NOT require expected_state_version
 * - Does NOT require staleness or can_complete checks
 */

'use client';

import type { UseWorkflowConnectionReturn } from './useWorkflowConnection';

// ============================================================================
// Types
// ============================================================================

/**
 * Position status values that allow messaging.
 * Per Contract §14.3.
 */
const MESSAGEABLE_STATUSES = new Set([
  'awaiting_review',
  'awaiting_clarification',
]);

/**
 * Connection statuses that allow messaging.
 * More permissive than canAct per Contract §14.3.
 */
const MESSAGEABLE_CONNECTION_STATUSES = new Set<UseWorkflowConnectionReturn['status']>([
  'connected',
  'reconnecting',
  'resyncing',
]);

/**
 * Parameters for useCanMessage hook.
 *
 * IMPORTANT: `connection` MUST be sourced from useWorkflowConnection.
 * This enforces R7/R13 semantics where connectionStatus reflects
 * canonical refetch success/failure.
 */
export interface UseCanMessageParams {
  /**
   * Connection state from useWorkflowConnection.
   * MUST be from useWorkflowConnection to enforce R7/R13 semantics.
   */
  connection: Pick<UseWorkflowConnectionReturn, 'status'>;
  /** Current workflow position (optional - may not be loaded yet) */
  position?: {
    status: string;
  };
}

/**
 * Return type for useCanMessage hook.
 */
export interface UseCanMessageReturn {
  /** Whether message action is allowed */
  canMessage: boolean;
  /** User-visible reason when canMessage is false, null when true */
  reason: string | null;
}

// ============================================================================
// Reason Strings
// ============================================================================

const REASONS = {
  CONNECTION_LOST: 'Connection lost',
  CONNECTING: 'Connecting...',
  NOT_MESSAGEABLE: 'Not in a messageable state',
  POSITION_UNKNOWN: 'Workflow state loading...',
} as const;

// ============================================================================
// Hook Implementation
// ============================================================================

/**
 * Message action gating hook.
 *
 * Implements the "canMessage iff" conditions from Contract §14.3:
 * 1. connectionStatus ∈ {'connected', 'reconnecting', 'resyncing'}
 * 2. position.status ∈ {'awaiting_review', 'awaiting_clarification'}
 *
 * More permissive than canAct because:
 * - Messages don't mutate workflow state
 * - Messages don't require optimistic concurrency
 * - Users may want to send messages during reconnection
 *
 * @param params - Connection status and position
 * @returns canMessage boolean and reason string
 */
export function useCanMessage(params: UseCanMessageParams): UseCanMessageReturn {
  const { connection, position } = params;

  // -------------------------------------------------------------------------
  // Condition 1: connectionStatus allows messaging
  // -------------------------------------------------------------------------
  if (!MESSAGEABLE_CONNECTION_STATUSES.has(connection.status)) {
    const reason = getConnectionReason(connection.status);
    return { canMessage: false, reason };
  }

  // -------------------------------------------------------------------------
  // Condition 2: position.status allows messaging
  // -------------------------------------------------------------------------
  if (!position) {
    return { canMessage: false, reason: REASONS.POSITION_UNKNOWN };
  }

  if (!MESSAGEABLE_STATUSES.has(position.status)) {
    return { canMessage: false, reason: REASONS.NOT_MESSAGEABLE };
  }

  // -------------------------------------------------------------------------
  // All conditions met
  // -------------------------------------------------------------------------
  return { canMessage: true, reason: null };
}

// ============================================================================
// Helpers
// ============================================================================

/**
 * Get user-visible reason for non-messageable connection status.
 */
function getConnectionReason(status: UseWorkflowConnectionReturn['status']): string {
  switch (status) {
    case 'disconnected':
    case 'failed':
      return REASONS.CONNECTION_LOST;
    case 'connecting':
      return REASONS.CONNECTING;
    default:
      return REASONS.CONNECTION_LOST;
  }
}
