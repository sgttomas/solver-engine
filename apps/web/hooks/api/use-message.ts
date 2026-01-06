/**
 * SOLVER Web - Message Mutation Hook
 *
 * TanStack Query mutation for POST /workflows/{id}/actions/message
 * Package 6.5 deliverable per Development Directive v1.5.1.
 *
 * Contract Requirements:
 * - Does NOT require expected_state_version (Tech Spec §16.7)
 * - Per V2.8.2: Returns minimal MessageResponse (not WorkflowResponse)
 *
 * P6.6 Note: messageKeys factory added for event-driven invalidation.
 * Messages list query deferred per P6.6-DEFER-001 (no GET endpoint in V2.8.2).
 */

'use client';

import { useMutation } from '@tanstack/react-query';
import { sendMessage } from '@/lib/api';
import type { MessageRequest, MessageResponse } from '@/lib/types';

/**
 * Query key factory for messages queries (P6.6)
 *
 * NOTE: Messages list query implementation deferred per P6.6-DEFER-001.
 * Tech Spec V2.8.2 does not define a messages list GET endpoint.
 * Keys are ready for invalidation when the endpoint exists.
 */
export const messageKeys = {
  all: ['messages'] as const,
  list: (workflowId: string) => [...messageKeys.all, workflowId] as const,
};

/**
 * Hook to send a message
 *
 * Note: Message action does NOT require expected_state_version per Tech Spec §16.7
 * Per V2.8.2: Message is non-state-mutating, returns {message_id, status} only.
 *
 * @param workflowId - Workflow ID to send message to
 * @returns TanStack Query mutation for sending messages
 */
export function useMessage(workflowId: string) {
  return useMutation<MessageResponse, Error, MessageRequest>({
    mutationFn: (request) => sendMessage(workflowId, request),
    // No cache update needed - message is non-state-mutating per Tech Spec §16.7
    // The MessageResponse only contains {message_id, status: "sent"}
  });
}
