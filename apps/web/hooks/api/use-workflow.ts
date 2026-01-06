/**
 * SOLVER Web - Workflow Query Hook
 *
 * TanStack Query hook for GET /workflows/{id}
 * Package 6.5 deliverable per Development Directive v1.5.1.
 */

'use client';

import { useQuery } from '@tanstack/react-query';
import { fetchWorkflow } from '@/lib/api';
import type { WorkflowResponse } from '@/lib/types';

/**
 * Query key factory for workflow queries
 */
export const workflowKeys = {
  all: ['workflows'] as const,
  detail: (id: string) => [...workflowKeys.all, id] as const,
};

/**
 * Hook to fetch workflow state
 *
 * @param workflowId - Workflow ID to fetch
 * @param options - Additional query options
 * @returns TanStack Query result with WorkflowResponse
 */
export function useWorkflow(
  workflowId: string,
  options?: {
    enabled?: boolean;
    refetchInterval?: number | false;
  }
) {
  return useQuery<WorkflowResponse, Error>({
    queryKey: workflowKeys.detail(workflowId),
    queryFn: () => fetchWorkflow(workflowId),
    enabled: options?.enabled ?? !!workflowId,
    refetchInterval: options?.refetchInterval,
  });
}
