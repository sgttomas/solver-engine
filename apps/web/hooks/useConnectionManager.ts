/**
 * SOLVER Web - Connection Manager Hook
 *
 * Manages SSE EventSource lifecycle per Architectural Contract v3.4 Section 14.1.
 * Package 6.2 deliverable per Development Directive v1.5.
 *
 * Contract Requirements Implemented:
 * - R7/C2: `connected` only after refetch completes
 * - R8: Gap reconnect uses from_sequence=lastContiguous
 * - R9: Drop events with wrong workflow ID
 * - R11: Handlers attached synchronously after construction (best-effort)
 * - R13: Failed refetch → `failed` status
 * - R16: Gap resync: no `connecting` flicker (hard guard)
 * - R19: Reentrancy guard for reconnect storms (retryScheduled)
 * - C4: Bounded recovery attempts
 * - C5: Status semantics preserved (reconnecting during transport recovery)
 * - §12.4: Cursor internal, never exposed as parameter
 */

'use client';

import { useCallback, useEffect, useRef } from 'react';
import { useConnectionStore, type ConnectionStatus } from '@/stores/connection';
import { API_BASE_URL } from '@/lib/api';
import { SSE_STREAM_PATH } from '@/lib/sse';
import { calculateBackoff, DEFAULT_BACKOFF_CONFIG, type BackoffConfig } from '@/lib/backoff';

// ============================================================================
// Types
// ============================================================================

/**
 * Connection mode for connectWithSequence.
 * Per C5: only 'initial' sets 'connecting'; others preserve current status.
 */
type ConnectMode = 'initial' | 'reconnect' | 'resync';

/**
 * Options for useConnectionManager hook.
 *
 * NOTE: getLastContiguousSequence and onRefetchRequired are REQUIRED
 * to enforce R7/C2 and §12.4.
 */
export interface UseConnectionManagerOptions {
  /** Workflow ID to connect to */
  workflowId: string;

  /**
   * REQUIRED: Get the last contiguous sequence number.
   * Returns 0 initially (before any events received).
   * Per §12.4: cursor computed internally from this callback only.
   */
  getLastContiguousSequence: () => number;

  /**
   * REQUIRED: Perform canonical refetch after stream established.
   * Per R7/C2: `connected` only after this succeeds.
   * Per R13: failure results in `failed` status.
   */
  onRefetchRequired: () => Promise<{ success: boolean }>;

  /**
   * Called when an SSE event is received.
   * Receives RAW event data (opaque string) - typing deferred to Package 6.6.
   */
  onEvent?: (rawEventData: string) => void;

  /**
   * Called when an error occurs.
   */
  onError?: (error: Error) => void;

  /** Auto-connect on mount (default: true) per Development Directive */
  autoConnect?: boolean;

  /** Maximum retry attempts before entering `failed` (default: 5) */
  maxRetries?: number;

  /** Base backoff delay in ms (default: 1000) */
  baseBackoffMs?: number;

  /** Maximum backoff delay in ms (default: 30000) */
  maxBackoffMs?: number;
}

export interface UseConnectionManagerReturn {
  /** Current connection status */
  status: ConnectionStatus;

  /** Initiate connection to SSE stream */
  connect: () => void;

  /** Disconnect from SSE stream */
  disconnect: () => void;

  /**
   * Trigger resync after gap detection.
   * No parameter - cursor from getLastContiguousSequence() per §12.4.
   */
  triggerResync: () => void;

  /** Current retry count */
  retryCount: number;

  /** Last error that occurred */
  lastError: Error | null;
}

/**
 * Internal state tracked via ref (not in Zustand to avoid unnecessary re-renders).
 */
interface ConnectionInternals {
  eventSource: EventSource | null;
  retryTimeout: ReturnType<typeof setTimeout> | null;
  retryScheduled: boolean; // R19: Guards against multiple concurrent timers (NOT sequential retries)
  isMounted: boolean;
}

// ============================================================================
// Internal Helpers (§12.4: cursor construction internal only)
// ============================================================================

/**
 * Build the full SSE stream URL.
 * INTERNAL to this hook - enforces §12.4 at module boundary.
 */
function buildStreamUrl(workflowId: string, fromSequence: number): string {
  return `${API_BASE_URL}${SSE_STREAM_PATH}/${workflowId}/stream?from_sequence=${fromSequence}`;
}

// ============================================================================
// Hook Implementation
// ============================================================================

export function useConnectionManager(
  options: UseConnectionManagerOptions
): UseConnectionManagerReturn {
  const {
    workflowId,
    getLastContiguousSequence,
    onRefetchRequired,
    onEvent,
    onError,
    autoConnect = true,
    maxRetries = 5,
    baseBackoffMs = DEFAULT_BACKOFF_CONFIG.baseMs,
    maxBackoffMs = DEFAULT_BACKOFF_CONFIG.maxMs,
  } = options;

  // Zustand store for UI-visible state
  const {
    status,
    error,
    retryCount,
    setStatus,
    setWorkflowId,
    setError,
    incrementRetryCount,
    resetRetryCount,
    setLastConnectedAt,
    reset,
  } = useConnectionStore();

  // Internal state (not triggering re-renders)
  const internalsRef = useRef<ConnectionInternals>({
    eventSource: null,
    retryTimeout: null,
    retryScheduled: false,
    isMounted: true,
  });

  // Stable reference to options for callbacks (prevents stale closures)
  const optionsRef = useRef(options);
  optionsRef.current = options;

  // Backoff config
  const backoffConfig: BackoffConfig = {
    baseMs: baseBackoffMs,
    maxMs: maxBackoffMs,
    jitterFactor: DEFAULT_BACKOFF_CONFIG.jitterFactor,
  };

  // ==========================================================================
  // Internal Helpers
  // ==========================================================================

  /**
   * Close the current EventSource and clear retry timeout.
   */
  const closeEventSource = useCallback(() => {
    const internals = internalsRef.current;

    if (internals.eventSource) {
      internals.eventSource.close();
      internals.eventSource = null;
    }

    if (internals.retryTimeout) {
      clearTimeout(internals.retryTimeout);
      internals.retryTimeout = null;
    }
  }, []);

  /**
   * Create EventSource and establish connection.
   *
   * @param fromSequence - Cursor for replay (from getLastContiguousSequence)
   * @param mode - Connection mode per C5 status semantics
   */
  const connectWithSequence = useCallback(
    (fromSequence: number, mode: ConnectMode) => {
      const internals = internalsRef.current;

      // Guard: don't connect if unmounted
      if (!internals.isMounted) {
        return;
      }

      // Close any existing connection
      closeEventSource();

      // C5 Status Semantics: only 'initial' sets 'connecting'
      // 'reconnect' keeps 'reconnecting', 'resync' keeps 'resyncing'
      if (mode === 'initial') {
        setStatus('connecting');
      }
      // For 'reconnect' and 'resync', status already set by caller

      setWorkflowId(workflowId);
      setError(null);

      // Build URL with cursor per §12.4 (internal function)
      const url = buildStreamUrl(workflowId, fromSequence);

      // R11 best-effort: Define handlers BEFORE EventSource construction
      // (EventSource connects on construction; handlers attached in same tick)
      const handleOpen = async () => {
        // Guard: check if still mounted and this is still our EventSource
        if (!internals.isMounted || internals.eventSource !== eventSource) {
          eventSource.close();
          return;
        }

        // R7/C2: Must await canonical refetch before entering 'connected'
        try {
          const result = await optionsRef.current.onRefetchRequired();

          // Guard: check again after async operation
          if (!internals.isMounted || internals.eventSource !== eventSource) {
            eventSource.close();
            return;
          }

          if (!result.success) {
            // R13: Failed refetch → failed status
            setStatus('failed');
            setError(new Error('Canonical refetch failed'));
            eventSource.close();
            internals.eventSource = null;
            return;
          }

          // Success: enter connected state
          const prevStatus = useConnectionStore.getState().status;
          resetRetryCount();
          setLastConnectedAt(Date.now());
          setStatus('connected');
          internals.retryScheduled = false;
        } catch (err) {
          // R13: Exception during refetch → failed
          if (!internals.isMounted) return;

          const error = err instanceof Error ? err : new Error(String(err));
          setStatus('failed');
          setError(error);
          optionsRef.current.onError?.(error);
          eventSource.close();
          internals.eventSource = null;
        }
      };

      const handleMessage = (event: MessageEvent) => {
        // Guard: check if still mounted and current
        if (!internals.isMounted || internals.eventSource !== eventSource) {
          return;
        }

        // R9: Parse ONLY to check workflow_id
        try {
          const parsed = JSON.parse(event.data);
          if (parsed.workflow_id && parsed.workflow_id !== workflowId) {
            // R9: Drop events for wrong workflow
            return;
          }
        } catch {
          // Non-JSON (heartbeats or malformed) - drop silently
          // NOTE: Heartbeat/idle-timeout handling deferred to 6.6
          return;
        }

        // Forward RAW data - no typing in 6.2
        optionsRef.current.onEvent?.(event.data);
      };

      const handleError = () => {
        // Guard: check if still mounted and current
        if (!internals.isMounted || internals.eventSource !== eventSource) {
          return;
        }

        const currentStatus = useConnectionStore.getState().status;

        // Close the failed connection
        eventSource.close();
        internals.eventSource = null;

        // Schedule reconnect (handled by scheduleReconnect)
        scheduleReconnect();
      };

      // Construct EventSource
      const eventSource = new EventSource(url);

      // CRITICAL (Fix 5): Assign to internals BEFORE attaching handlers
      // Handlers check internals.eventSource !== eventSource as guard
      internals.eventSource = eventSource;

      // Attach handlers synchronously (same tick as construction)
      eventSource.onopen = handleOpen;
      eventSource.onmessage = handleMessage;
      eventSource.onerror = handleError;
    },
    [
      workflowId,
      closeEventSource,
      setStatus,
      setWorkflowId,
      setError,
      resetRetryCount,
      setLastConnectedAt,
    ]
  );

  /**
   * Schedule a reconnection attempt with exponential backoff.
   * Implements R19 reentrancy guard and C4 bounded retries.
   *
   * Fix 1: Uses retryScheduled to guard against concurrent timers,
   * NOT sequential retries. Cleared before connect attempt.
   */
  const scheduleReconnect = useCallback(() => {
    const internals = internalsRef.current;

    // R19: Prevent multiple concurrent timers (not sequential retries)
    if (internals.retryScheduled) {
      return;
    }

    // C4: Check if max retries exceeded
    const currentRetryCount = useConnectionStore.getState().retryCount;
    if (currentRetryCount >= maxRetries) {
      internals.retryScheduled = false;
      setStatus('failed');
      setError(new Error(`Max retries (${maxRetries}) exceeded`));
      return;
    }

    internals.retryScheduled = true;
    setStatus('reconnecting');

    // Calculate backoff delay
    const backoffMs = calculateBackoff(currentRetryCount, backoffConfig);

    // Schedule retry
    internals.retryTimeout = setTimeout(() => {
      if (!internals.isMounted) return;

      // Fix 1: Clear BEFORE connect attempt - allows next onerror to schedule again
      internals.retryScheduled = false;

      incrementRetryCount();

      // Get cursor from SequenceGuard per §12.4
      const cursor = optionsRef.current.getLastContiguousSequence();
      // Fix 2: Use 'reconnect' mode to preserve 'reconnecting' status (C5)
      connectWithSequence(cursor, 'reconnect');
    }, backoffMs);
  }, [maxRetries, backoffConfig, setStatus, setError, incrementRetryCount, connectWithSequence]);

  // ==========================================================================
  // Public API
  // ==========================================================================

  /**
   * Initiate connection to SSE stream.
   */
  const connect = useCallback(() => {
    const internals = internalsRef.current;

    // Guard: already connecting/connected
    const currentStatus = useConnectionStore.getState().status;
    if (
      currentStatus === 'connecting' ||
      currentStatus === 'connected' ||
      currentStatus === 'reconnecting' ||
      currentStatus === 'resyncing'
    ) {
      return;
    }

    // Get initial cursor (0 if no events yet)
    const cursor = getLastContiguousSequence();
    connectWithSequence(cursor, 'initial');
  }, [getLastContiguousSequence, connectWithSequence]);

  /**
   * Disconnect from SSE stream.
   * Resets all state including retryCount.
   */
  const disconnect = useCallback(() => {
    closeEventSource();
    internalsRef.current.retryScheduled = false;
    reset();
  }, [closeEventSource, reset]);

  /**
   * Trigger resync after gap detection.
   * No parameter - cursor from getLastContiguousSequence() per §12.4.
   *
   * Per R16: Sets 'resyncing' BEFORE reconnect, does NOT transition through 'connecting'.
   */
  const triggerResync = useCallback(() => {
    const internals = internalsRef.current;

    // R19: Prevent reconnect storms (check if retry already scheduled)
    if (internals.retryScheduled) {
      return;
    }

    // R16: Set resyncing BEFORE reconnect, skip connecting
    setStatus('resyncing');

    closeEventSource();

    // §12.4: Cursor computed internally - NEVER passed as parameter
    const cursor = getLastContiguousSequence();
    // Use 'resync' mode to preserve 'resyncing' status (C5/R16)
    connectWithSequence(cursor, 'resync');
  }, [getLastContiguousSequence, closeEventSource, setStatus, connectWithSequence]);

  // ==========================================================================
  // Lifecycle
  // ==========================================================================

  // Track mount state
  useEffect(() => {
    internalsRef.current.isMounted = true;

    return () => {
      internalsRef.current.isMounted = false;
      closeEventSource();
    };
  }, [closeEventSource]);

  // Fix 4: Single effect handles mount, unmount, and workflow change
  // (Merged with workflow-change effect to avoid double-disconnect)
  useEffect(() => {
    if (autoConnect && workflowId) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, workflowId, connect, disconnect]);

  return {
    status,
    connect,
    disconnect,
    triggerResync,
    retryCount,
    lastError: error,
  };
}
