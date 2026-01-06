/**
 * SOLVER Web - Progress Query Hook
 *
 * TanStack Query hook for GET /workflows/{id}/progress
 * Package 6.5 deliverable per Development Directive v1.5.1.
 */

'use client';

import { useQuery } from '@tanstack/react-query';
import { fetchProgress } from '@/lib/api';
import type { ProgressResponse } from '@/lib/types';

/**
 * Query key factory for progress queries
 */
export const progressKeys = {
  all: ['progress'] as const,
  detail: (workflowId: string) => [...progressKeys.all, workflowId] as const,
};

/**
 * Hook to fetch workflow progress
 *
 * @param workflowId - Workflow ID to fetch progress for
 * @param options - Additional query options
 * @returns TanStack Query result with ProgressResponse
 */
export function useProgress(
  workflowId: string,
  options?: {
    enabled?: boolean;
    refetchInterval?: number | false;
  }
) {
  return useQuery<ProgressResponse, Error>({
    queryKey: progressKeys.detail(workflowId),
    queryFn: () => fetchProgress(workflowId),
    enabled: options?.enabled ?? !!workflowId,
    refetchInterval: options?.refetchInterval,
  });
}
