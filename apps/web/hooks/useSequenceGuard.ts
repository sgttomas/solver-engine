/**
 * SOLVER Web - Sequence Guard Hook
 *
 * Enforces ordered SSE event processing with gap detection, buffering, and recovery
 * per Architectural Contract v3.4 §14.2 (Sequence Guard Contract).
 *
 * Package 6.3 deliverable per Development Directive v1.5.
 *
 * Contract Requirements Implemented:
 * - R1: Drop events with sequence <= lastContiguous (deduplication)
 * - R2: Guard resets only on workflow change, not reconnect
 * - R10: Deduplication uses lastContiguous, not maxSeen
 * - R12: Pending set bounded (~100 max); overflow triggers recovery
 * - R17: Out-of-order events buffered, NOT dispatched until contiguous
 * - §16.4.1: Unsequenced events flagged for idle-timer (6.6 handoff)
 */

'use client';

import { useCallback, useRef } from 'react';

// ============================================================================
// Constants
// ============================================================================

/**
 * Maximum pending events before overflow recovery (R12).
 * Per Architectural Contract v3.4 §13.3.
 */
export const MAX_PENDING_EVENTS = 100;

// ============================================================================
// Types
// ============================================================================

/**
 * Result of processing an event through the sequence guard.
 */
export interface ProcessResult<T> {
  /** Contiguous events ready for dispatch */
  dispatched: T[];
  /** True if this event created a gap (sequence > lastContiguous + 1) */
  gapDetected: boolean;
  /** True if pending >= MAX and event was NOT added (R12) */
  overflowed: boolean;
  /** True if event had no sequence field (§16.4.1 heartbeat) */
  unsequenced: boolean;
}

/**
 * Return type for useSequenceGuard hook.
 */
export interface UseSequenceGuardReturn<T> {
  /** Last contiguous sequence processed (correctness cursor) */
  lastContiguous: number;
  /** Highest sequence seen (telemetry only, NOT for correctness) */
  maxSeen: number;
  /** Number of events in pending buffer */
  pendingCount: number;

  /**
   * Process an incoming event.
   * @param event - Event with optional sequence and payload
   * @returns ProcessResult with dispatched events and status flags
   */
  process: (event: { sequence?: number; payload: T }) => ProcessResult<T>;

  /**
   * Get the last contiguous sequence number.
   * Used by useConnectionManager for replay cursor (§12.4).
   * Returns 0 before first event.
   */
  getLastContiguousSequence: () => number;

  /**
   * Reset guard state for workflow change (R2).
   * ONLY call on workflow change, NOT on reconnect.
   */
  reset: () => void;

  /**
   * Clear pending buffer after successful canonical refetch.
   * Preserves lastContiguous per §16.6.
   */
  clearBuffer: () => void;
}

/**
 * Internal state for the sequence guard.
 */
interface SequenceGuardState<T> {
  /** Last contiguous sequence processed (correctness cursor) */
  lastContiguous: number;
  /** Highest sequence seen (telemetry only) */
  maxSeen: number;
  /** Sequences received but not yet contiguous */
  pending: Set<number>;
  /** Payloads for pending sequences */
  buffer: Map<number, T>;
}

// ============================================================================
// Hook Implementation
// ============================================================================

/**
 * Sequence Guard hook for ordered SSE event processing.
 *
 * Enforces strict ordering guarantees per Architectural Contract v3.4 §14.2:
 * - Events are only dispatched when contiguous with lastContiguous
 * - Out-of-order events are buffered until gaps are filled
 * - Duplicate events (sequence <= lastContiguous) are dropped
 * - Pending buffer is bounded; overflow signals recovery
 *
 * @returns SequenceGuardReturn with process function and state
 */
export function useSequenceGuard<T>(): UseSequenceGuardReturn<T> {
  // Use ref to avoid re-renders on every event
  const stateRef = useRef<SequenceGuardState<T>>({
    lastContiguous: 0,
    maxSeen: 0,
    pending: new Set(),
    buffer: new Map(),
  });

  /**
   * Drain contiguous events from the pending buffer.
   * Called after advancing lastContiguous to flush any newly-contiguous events.
   */
  const drainContiguous = useCallback((): T[] => {
    const state = stateRef.current;
    const dispatched: T[] = [];

    while (state.pending.has(state.lastContiguous + 1)) {
      state.lastContiguous++;
      const payload = state.buffer.get(state.lastContiguous);
      if (payload !== undefined) {
        dispatched.push(payload);
      }
      state.pending.delete(state.lastContiguous);
      state.buffer.delete(state.lastContiguous);
    }

    return dispatched;
  }, []);

  /**
   * Process an incoming event through the sequence guard.
   * Implements all ordering guarantees from §14.2.
   */
  const process = useCallback(
    (event: { sequence?: number; payload: T }): ProcessResult<T> => {
      const { sequence, payload } = event;
      const state = stateRef.current;

      // §16.4.1: Unsequenced events (heartbeats) — drop but flag for idle-timer (6.6)
      if (sequence === undefined || sequence === null) {
        return { dispatched: [], gapDetected: false, overflowed: false, unsequenced: true };
      }

      // First sequenced event: initialize both cursors
      if (state.lastContiguous === 0 && state.pending.size === 0) {
        state.lastContiguous = sequence;
        state.maxSeen = sequence;
        return { dispatched: [payload], gapDetected: false, overflowed: false, unsequenced: false };
      }

      // R1/R10: Dedupe — drop if already processed
      if (sequence <= state.lastContiguous) {
        return { dispatched: [], gapDetected: false, overflowed: false, unsequenced: false };
      }

      // R12: Pre-add overflow check — MUST bound pending set
      // Only check when this would create a gap (otherwise we're about to dispatch, not buffer)
      if (sequence > state.lastContiguous + 1 && state.pending.size >= MAX_PENDING_EVENTS) {
        return { dispatched: [], gapDetected: false, overflowed: true, unsequenced: false };
      }

      // Update maxSeen (telemetry only — NOT for correctness per R10)
      state.maxSeen = Math.max(state.maxSeen, sequence);

      // Contiguous: advance and drain
      if (sequence === state.lastContiguous + 1) {
        state.lastContiguous = sequence;
        const drained = drainContiguous();
        return {
          dispatched: [payload, ...drained],
          gapDetected: false,
          overflowed: false,
          unsequenced: false,
        };
      }

      // Gap detected: buffer for later (R17)
      state.pending.add(sequence);
      state.buffer.set(sequence, payload);
      return { dispatched: [], gapDetected: true, overflowed: false, unsequenced: false };
    },
    [drainContiguous]
  );

  /**
   * Get the last contiguous sequence number.
   * Used by useConnectionManager for replay cursor (§12.4).
   */
  const getLastContiguousSequence = useCallback((): number => {
    return stateRef.current.lastContiguous;
  }, []);

  /**
   * Clear pending buffer after successful canonical refetch.
   * Preserves lastContiguous per §16.6 — we don't reset the cursor,
   * just discard pending events that will be re-delivered via replay.
   */
  const clearBuffer = useCallback((): void => {
    const state = stateRef.current;
    state.pending.clear();
    state.buffer.clear();
    // lastContiguous preserved per §16.6
  }, []);

  /**
   * Reset guard state for workflow change (R2).
   * ONLY call on workflow change, NOT on reconnect.
   */
  const reset = useCallback((): void => {
    const state = stateRef.current;
    state.lastContiguous = 0;
    state.maxSeen = 0;
    state.pending.clear();
    state.buffer.clear();
  }, []);

  return {
    get lastContiguous() {
      return stateRef.current.lastContiguous;
    },
    get maxSeen() {
      return stateRef.current.maxSeen;
    },
    get pendingCount() {
      return stateRef.current.pending.size;
    },
    process,
    getLastContiguousSequence,
    reset,
    clearBuffer,
  };
}
