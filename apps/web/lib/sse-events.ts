/**
 * SOLVER Web - SSE Event Types
 *
 * Discriminated union types for SSE events per Tech Spec V2.8.2 §16.4.1 and §16.9.
 * Package 6.6 deliverable per Development Directive v1.5.1.
 *
 * Key invariants:
 * - Sequenced events MUST have sequence: number field
 * - Heartbeat events MUST NOT have sequence field (per §16.4.1)
 * - Heartbeat events are exempt from Appendix C.1 envelope (per P6.6-INTERP-001)
 */

import type { PositionResponse } from './types';

// ============================================================================
// Event Type Literals
// ============================================================================

/**
 * Sequenced event types per Tech Spec §16.4 and §9.2.1
 * All of these events REQUIRE a sequence number.
 */
export type SequencedEventType =
  | 'workflow.started'
  | 'workflow.completed'
  | 'step.started'
  | 'step.awaiting_clarification'
  | 'step.awaiting_review'
  | 'step.approved'
  | 'step.revision_requested'
  | 'step.reexecute_started'
  | 'artifact.delta'
  | 'artifact.final'
  | 'artifact.stale'
  | 'artifact.stale_cleared'
  | 'staleness_acknowledged'
  | 'message.created'
  | 'message.delta'
  | 'message.final'
  | 'error';

// ============================================================================
// Event Interfaces
// ============================================================================

/**
 * Sequenced SSE event (most events)
 *
 * Per Tech Spec Appendix C.1, sequenced events include:
 * - sequence: number (REQUIRED)
 * - position: PositionResponse
 * - workflow_id, timestamp, payload
 */
export interface SequencedSSEEvent {
  event_type: SequencedEventType;
  /** Sequence number - REQUIRED for sequenced events */
  sequence: number;
  workflow_id: string;
  timestamp: string;
  /** Current position per Appendix C.1 */
  position: PositionResponse;
  /** Event-specific payload */
  payload?: Record<string, unknown>;
  /** Actor who triggered the event (for user actions) */
  actor_id?: string;
  /** For message correlation (message.delta/message.final only) */
  reply_to_message_id?: string;
}

/**
 * Heartbeat event (unsequenced)
 *
 * Per Tech Spec §16.4.1:
 * - NO sequence field
 * - NO position field (exempt from C.1 envelope per P6.6-INTERP-001)
 * - Minimal payload: event_type, workflow_id, timestamp
 */
export interface HeartbeatEvent {
  event_type: 'heartbeat';
  workflow_id: string;
  timestamp: string;
  // NOTE: Explicitly NO sequence field per §16.4.1
  // NOTE: Explicitly NO position field (exempt from C.1)
}

/**
 * Union type for all SSE events
 *
 * Use type guards to discriminate between sequenced and unsequenced events.
 */
export type SSEEvent = SequencedSSEEvent | HeartbeatEvent;

// ============================================================================
// Type Guards
// ============================================================================

/**
 * Check if event is sequenced (has sequence number)
 *
 * Per §16.4.1, only heartbeats are unsequenced.
 */
export function isSequencedEvent(event: SSEEvent): event is SequencedSSEEvent {
  return 'sequence' in event && typeof event.sequence === 'number';
}

/**
 * Check if event is a heartbeat (unsequenced)
 *
 * Per §16.4.1, heartbeats carry no sequence number.
 */
export function isHeartbeat(event: SSEEvent): event is HeartbeatEvent {
  return event.event_type === 'heartbeat';
}

/**
 * Check if event is a message event (for reply_to_message_id correlation)
 */
export function isMessageEvent(
  event: SSEEvent
): event is SequencedSSEEvent & { event_type: 'message.created' | 'message.delta' | 'message.final' } {
  return (
    event.event_type === 'message.created' ||
    event.event_type === 'message.delta' ||
    event.event_type === 'message.final'
  );
}

/**
 * Check if event is a streaming delta (artifact or message)
 */
export function isDeltaEvent(
  event: SSEEvent
): event is SequencedSSEEvent & { event_type: 'artifact.delta' | 'message.delta' } {
  return event.event_type === 'artifact.delta' || event.event_type === 'message.delta';
}

/**
 * Check if event is an error event
 *
 * Per §16.9, error events are domain errors (not connection errors).
 * They should NOT change connection status.
 */
export function isErrorEvent(
  event: SSEEvent
): event is SequencedSSEEvent & { event_type: 'error' } {
  return event.event_type === 'error';
}
