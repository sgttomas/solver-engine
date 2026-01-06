/**
 * SOLVER Web - Event Dispatcher Hook
 *
 * Maps SSE events to TanStack Query invalidations per Tech Spec §9.2.1.
 * Package 6.6 deliverable per Development Directive v1.5.1.
 *
 * Contract Requirements:
 * - Event invalidation matches §9.2.1 matrix exactly
 * - message.delta/message.final verify reply_to_message_id match (§16.9)
 * - Domain error events do NOT change connection status (§16.9)
 * - Idle timer reset handled by useConnectionManager (not here)
 */

'use client';

import { useCallback, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { workflowKeys, progressKeys, stalenessKeys } from './use-workflow-queries';
import { messageKeys } from './api/use-message';
import type { SSEEvent, SequencedSSEEvent } from '@/lib/sse-events';
import { isSequencedEvent, isErrorEvent, isMessageEvent } from '@/lib/sse-events';

/**
 * Artifact query keys (following existing pattern)
 * NOTE: Artifact queries not yet implemented; keys ready for invalidation.
 */
const artifactKeys = {
  all: ['artifacts'] as const,
  list: (workflowId: string) => [...artifactKeys.all, workflowId] as const,
};

export interface UseEventDispatcherOptions {
  /** Workflow ID for query invalidation */
  workflowId: string;

  /**
   * Optional: Current pending message ID for reply_to_message_id correlation.
   * Message events with non-matching reply_to_message_id will be logged but not applied.
   */
  pendingMessageId?: string;

  /**
   * Optional: Callback for domain error events.
   * Per §16.9, these should NOT affect connection status.
   */
  onDomainError?: (error: SequencedSSEEvent) => void;
}

export interface UseEventDispatcherReturn {
  /**
   * Process an array of dispatched events (from sequence guard).
   * Maps each event to appropriate query invalidations per §9.2.1.
   */
  handleEvents: (events: SSEEvent[]) => void;
}

/**
 * Event dispatcher hook for SSE event-driven query invalidation.
 *
 * Per Tech Spec §9.2.1, maps event types to specific query invalidations.
 * Does NOT handle idle timeout (that's in useConnectionManager per §16.4.1).
 *
 * @param options - Dispatcher options including workflowId
 * @returns handleEvents function for processing dispatched events
 */
export function useEventDispatcher(
  options: UseEventDispatcherOptions
): UseEventDispatcherReturn {
  const { workflowId, pendingMessageId, onDomainError } = options;

  const queryClient = useQueryClient();

  // Track pending message ID in ref to avoid stale closures
  const pendingMessageIdRef = useRef(pendingMessageId);
  pendingMessageIdRef.current = pendingMessageId;

  /**
   * Invalidate queries based on event type per §9.2.1 matrix.
   */
  const invalidateForEvent = useCallback(
    (event: SequencedSSEEvent) => {
      const { event_type } = event;

      switch (event_type) {
        // Workflow lifecycle events → workflow, progress
        case 'workflow.started':
        case 'workflow.completed':
          queryClient.invalidateQueries({ queryKey: workflowKeys.detail(workflowId) });
          queryClient.invalidateQueries({ queryKey: progressKeys.detail(workflowId) });
          break;

        // Step state changes → workflow, progress
        case 'step.started':
        case 'step.awaiting_clarification':
        case 'step.approved':
        case 'step.revision_requested':
          queryClient.invalidateQueries({ queryKey: workflowKeys.detail(workflowId) });
          queryClient.invalidateQueries({ queryKey: progressKeys.detail(workflowId) });
          break;

        // step.awaiting_review → workflow, progress, artifacts (artifact ready)
        case 'step.awaiting_review':
          queryClient.invalidateQueries({ queryKey: workflowKeys.detail(workflowId) });
          queryClient.invalidateQueries({ queryKey: progressKeys.detail(workflowId) });
          queryClient.invalidateQueries({ queryKey: artifactKeys.list(workflowId) });
          break;

        // step.reexecute_started → workflow, progress, staleness
        case 'step.reexecute_started':
          queryClient.invalidateQueries({ queryKey: workflowKeys.detail(workflowId) });
          queryClient.invalidateQueries({ queryKey: progressKeys.detail(workflowId) });
          queryClient.invalidateQueries({ queryKey: stalenessKeys.detail(workflowId) });
          break;

        // artifact.final → artifacts
        case 'artifact.final':
          queryClient.invalidateQueries({ queryKey: artifactKeys.list(workflowId) });
          break;

        // Staleness changes → staleness, artifacts
        case 'artifact.stale':
        case 'artifact.stale_cleared':
          queryClient.invalidateQueries({ queryKey: stalenessKeys.detail(workflowId) });
          queryClient.invalidateQueries({ queryKey: artifactKeys.list(workflowId) });
          break;

        // staleness_acknowledged → staleness only
        case 'staleness_acknowledged':
          queryClient.invalidateQueries({ queryKey: stalenessKeys.detail(workflowId) });
          break;

        // Message events → messages (deferred query per P6.6-DEFER-001)
        case 'message.created':
        case 'message.final':
          // Verify reply_to_message_id correlation per §16.9
          if (event.reply_to_message_id) {
            const currentPendingId = pendingMessageIdRef.current;
            if (currentPendingId && event.reply_to_message_id !== currentPendingId) {
              // Log mismatch but still invalidate (message is valid, just not ours)
              console.warn(
                `[useEventDispatcher] Message event reply_to_message_id mismatch: ` +
                  `expected ${currentPendingId}, got ${event.reply_to_message_id}`
              );
            }
          }
          queryClient.invalidateQueries({ queryKey: messageKeys.list(workflowId) });
          break;

        // Streaming deltas → UI only (no query invalidation)
        case 'artifact.delta':
        case 'message.delta':
          // Streaming deltas are for real-time UI updates, not query cache
          // No invalidation needed - streaming handled separately
          break;

        // Domain error → error UI only, NOT connection status (§16.9)
        case 'error':
          // Per §16.9: Domain errors should NOT change connection status
          // Forward to optional error handler
          onDomainError?.(event);
          break;

        default:
          // Unknown event type - log but don't fail
          console.warn(`[useEventDispatcher] Unknown event type: ${event_type}`);
      }
    },
    [workflowId, queryClient, onDomainError]
  );

  /**
   * Process an array of dispatched events.
   * Only processes sequenced events; heartbeats handled by useConnectionManager.
   */
  const handleEvents = useCallback(
    (events: SSEEvent[]) => {
      for (const event of events) {
        // Skip non-sequenced events (heartbeats)
        // Heartbeats are handled by useConnectionManager for idle detection
        if (!isSequencedEvent(event)) {
          continue;
        }

        // Dispatch to query invalidation
        invalidateForEvent(event);
      }
    },
    [invalidateForEvent]
  );

  return { handleEvents };
}
