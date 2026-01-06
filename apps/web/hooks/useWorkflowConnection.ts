/**
 * SOLVER Web - Workflow Connection Provider Hook
 *
 * Wires useSequenceGuard + useConnectionManager together for consumption by
 * Package 6.5 (Workflow UI) and Package 6.6 (SSE Event Handling).
 *
 * Package 6.3 deliverable per Development Directive v1.5.
 *
 * Contract Requirements Implemented:
 * - R8: Gap triggers resync with from_sequence = lastContiguous
 * - R12: Overflow triggers recovery
 * - R16: Gap reconnect does NOT transition through 'connecting'
 * - R19: Resync guard prevents reconnect storms
 * - §16.4.1: Unsequenced events flagged for idle-timer (6.6 handoff)
 */

'use client';

import { useCallback, useEffect, useRef } from 'react';
import { useConnectionManager } from './useConnectionManager';
import { useSequenceGuard } from './useSequenceGuard';
import type { ConnectionStatus } from '@/stores/connection';

// ============================================================================
// Types
// ============================================================================

/**
 * Minimal SSE event shape for sequence guard processing.
 * Only `sequence` is used by Package 6.3; all other fields are opaque.
 * Package 6.6 will define specific event types.
 */
export type SSEEvent = {
  sequence?: number;
} & Record<string, unknown>;

/**
 * Options for useWorkflowConnection hook.
 */
export interface UseWorkflowConnectionOptions {
  /** Workflow ID to connect to */
  workflowId: string;

  /**
   * Perform canonical refetch (workflow, progress, staleness).
   * Per R7/C2: Must complete before entering 'connected' state.
   * @returns Promise resolving to success status
   */
  onRefetchRequired: () => Promise<{ success: boolean }>;

  /**
   * Called with contiguous events ready for dispatch.
   * Package 6.6 will implement TanStack Query invalidation here.
   */
  onDispatch?: (events: SSEEvent[]) => void;

  /**
   * Called when unsequenced event received (e.g., heartbeat).
   * Package 6.6 MUST implement idle-timer reset here.
   *
   * TODO(6.6): Implement idle-timer reset when onUnsequencedEvent called
   * Per Tech Spec §16.4.1:
   * - Reset idle timer on each heartbeat
   * - If no heartbeat for 60s, call triggerResync() or transition to 'reconnecting'
   * - If reconnect fails 3x, transition to 'failed'
   */
  onUnsequencedEvent?: (event: SSEEvent) => void;

  /**
   * Called when an error occurs.
   */
  onError?: (error: Error) => void;

  /** Auto-connect on mount (default: true) */
  autoConnect?: boolean;

  /** Maximum retry attempts before entering 'failed' (default: 5) */
  maxRetries?: number;
}

/**
 * Return type for useWorkflowConnection hook.
 */
export interface UseWorkflowConnectionReturn {
  /** Current connection status */
  status: ConnectionStatus;

  /** Initiate connection to SSE stream */
  connect: () => void;

  /** Disconnect from SSE stream */
  disconnect: () => void;

  /** Last contiguous sequence processed */
  lastContiguous: number;

  /** Number of events in pending buffer */
  pendingCount: number;

  /** Current retry count */
  retryCount: number;

  /** Last error that occurred */
  lastError: Error | null;
}

// ============================================================================
// Hook Implementation
// ============================================================================

/**
 * Workflow Connection provider hook.
 *
 * Wires useSequenceGuard + useConnectionManager together, providing a single
 * entry point for workflow SSE connections with ordered event delivery.
 *
 * Key behaviors:
 * - Gap detection triggers resync without 'connecting' flicker (R16)
 * - Overflow triggers recovery (R12)
 * - Resync guard prevents reconnect storms (R19)
 * - Unsequenced events flagged for idle-timer (6.6 handoff)
 *
 * @param options - Configuration options
 * @returns WorkflowConnectionReturn with status and controls
 */
export function useWorkflowConnection(
  options: UseWorkflowConnectionOptions
): UseWorkflowConnectionReturn {
  const {
    workflowId,
    onRefetchRequired,
    onDispatch,
    onUnsequencedEvent,
    onError,
    autoConnect = true,
    maxRetries = 5,
  } = options;

  // Sequence guard for ordered event processing
  const guard = useSequenceGuard<SSEEvent>();

  // Resync guard to prevent reconnect storms (R19)
  const resyncRequestedRef = useRef(false);

  // Stable reference to callbacks
  const callbacksRef = useRef({ onDispatch, onUnsequencedEvent, onError });
  callbacksRef.current = { onDispatch, onUnsequencedEvent, onError };

  // Ref to hold connectionManager for use in callbacks (avoids circular dependency)
  const connectionManagerRef = useRef<ReturnType<typeof useConnectionManager> | null>(null);

  /**
   * Handle canonical refetch.
   * Resets resync guard and clears buffer on success.
   */
  const handleRefetchRequired = useCallback(async (): Promise<{ success: boolean }> => {
    try {
      const result = await onRefetchRequired();
      // Reset resync guard on completion (success or fail)
      resyncRequestedRef.current = false;
      // Clear buffer on success (preserves lastContiguous per §16.6)
      if (result.success) {
        guard.clearBuffer();
      }
      return result;
    } catch {
      // Reset resync guard even on error
      resyncRequestedRef.current = false;
      return { success: false };
    }
  }, [onRefetchRequired, guard.clearBuffer]);

  /**
   * Handle incoming SSE event.
   * Processes through sequence guard and dispatches contiguous events.
   */
  const handleEvent = useCallback(
    (rawData: string) => {
      let event: SSEEvent;
      try {
        event = JSON.parse(rawData);
      } catch {
        // Non-JSON event — should not happen per spec, but handle gracefully
        return;
      }

      // Process through sequence guard
      const result = guard.process({
        sequence: event.sequence,
        payload: event,
      });

      // §16.4.1: Unsequenced events — flag for idle-timer (6.6 MUST handle)
      if (result.unsequenced) {
        callbacksRef.current.onUnsequencedEvent?.(event);
        return;
      }

      // R12/R8: Trigger resync on gap or overflow
      if ((result.gapDetected || result.overflowed) && !resyncRequestedRef.current) {
        resyncRequestedRef.current = true;
        // triggerResync() sets 'resyncing' status BEFORE reconnect (R16)
        connectionManagerRef.current?.triggerResync();
        return;
      }

      // Dispatch contiguous events
      if (result.dispatched.length > 0) {
        callbacksRef.current.onDispatch?.(result.dispatched);
      }
    },
    [guard.process]
  );

  // Connection manager handles EventSource lifecycle
  const connectionManager = useConnectionManager({
    workflowId,
    getLastContiguousSequence: guard.getLastContiguousSequence,
    onRefetchRequired: handleRefetchRequired,
    onEvent: handleEvent,
    onError: callbacksRef.current.onError,
    autoConnect,
    maxRetries,
  });

  // Store ref for use in callbacks (avoids circular dependency)
  connectionManagerRef.current = connectionManager;

  // Reset resync guard on 'failed' status
  useEffect(() => {
    if (connectionManager.status === 'failed') {
      resyncRequestedRef.current = false;
    }
  }, [connectionManager.status]);

  // Reset sequence guard AND resync guard on workflow change (R2, R19)
  // NOTE: Depend on guard.reset (stable useCallback), NOT guard object (recreated each render)
  useEffect(() => {
    guard.reset();
    resyncRequestedRef.current = false;
  }, [workflowId, guard.reset]);

  return {
    status: connectionManager.status,
    connect: connectionManager.connect,
    disconnect: connectionManager.disconnect,
    lastContiguous: guard.lastContiguous,
    pendingCount: guard.pendingCount,
    retryCount: connectionManager.retryCount,
    lastError: connectionManager.lastError,
  };
}
