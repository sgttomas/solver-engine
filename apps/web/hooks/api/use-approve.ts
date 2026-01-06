/**
 * SOLVER Web - Approve Mutation Hook
 *
 * TanStack Query mutation for POST /workflows/{id}/actions/approve
 * Package 6.5 deliverable per Development Directive v1.5.1.
 *
 * Contract Requirements:
 * - MUST include expected_state_version + expected_position (R18, §13.5)
 * - On 409: call explicit refetch() to get current state_version
 *
 * Note: Conflict handling is in mutationFn (not onError) because React Query's
 * onError does NOT transform the error that mutateAsync rejects with.
 */

'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { approveStep, StateConflictError } from '@/lib/api';
import type { ApproveRequest, WorkflowResponse } from '@/lib/types';
import { workflowKeys } from './use-workflow';
import { progressKeys } from './use-progress';
import { stalenessKeys } from './use-staleness';

/**
 * Error type returned when approval fails due to state conflict
 */
export interface ApproveConflictError {
  type: 'CONFLICT';
  message: string;
  currentStateVersion: number;
}

/**
 * Hook to approve current step
 *
 * @param workflowId - Workflow ID to approve
 * @returns TanStack Query mutation with 409 conflict handling
 */
export function useApprove(workflowId: string) {
  const queryClient = useQueryClient();

  return useMutation<WorkflowResponse, Error | ApproveConflictError, ApproveRequest>({
    mutationFn: async (request) => {
      try {
        return await approveStep(workflowId, request);
      } catch (error) {
        // Handle 409 conflict inside mutationFn so the transformed error
        // is what mutateAsync rejects with (onError doesn't transform errors)
        if (error instanceof StateConflictError) {
          // Explicit refetch to get current state_version
          await Promise.all([
            queryClient.refetchQueries({ queryKey: workflowKeys.detail(workflowId) }),
            queryClient.refetchQueries({ queryKey: progressKeys.detail(workflowId) }),
            queryClient.refetchQueries({ queryKey: stalenessKeys.detail(workflowId) }),
          ]);
          // Throw transformed error - this IS what mutateAsync rejects with
          throw {
            type: 'CONFLICT',
            message: 'State changed. Please review and try again.',
            currentStateVersion: error.conflictData.current_state_version,
          } as ApproveConflictError;
        }
        throw error;
      }
    },
    onSuccess: (data) => {
      // Update workflow cache with response
      queryClient.setQueryData(workflowKeys.detail(workflowId), data);
      // Explicit refetch (not invalidate) for progress and staleness
      queryClient.refetchQueries({ queryKey: progressKeys.detail(workflowId) });
      queryClient.refetchQueries({ queryKey: stalenessKeys.detail(workflowId) });
    },
  });
}

/**
 * Type guard for ApproveConflictError
 */
export function isApproveConflictError(error: unknown): error is ApproveConflictError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'type' in error &&
    (error as ApproveConflictError).type === 'CONFLICT'
  );
}
