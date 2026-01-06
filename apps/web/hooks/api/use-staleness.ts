/**
 * SOLVER Web - Staleness Query Hook
 *
 * TanStack Query hook for GET /workflows/{id}/staleness
 * Package 6.5 deliverable per Development Directive v1.5.1.
 */

'use client';

import { useQuery } from '@tanstack/react-query';
import { fetchStaleness } from '@/lib/api';
import type { StalenessResponse } from '@/lib/types';

/**
 * Query key factory for staleness queries
 */
export const stalenessKeys = {
  all: ['staleness'] as const,
  detail: (workflowId: string) => [...stalenessKeys.all, workflowId] as const,
};

/**
 * Hook to fetch workflow staleness status
 *
 * @param workflowId - Workflow ID to fetch staleness for
 * @param options - Additional query options
 * @returns TanStack Query result with StalenessResponse
 */
export function useStaleness(
  workflowId: string,
  options?: {
    enabled?: boolean;
    refetchInterval?: number | false;
  }
) {
  return useQuery<StalenessResponse, Error>({
    queryKey: stalenessKeys.detail(workflowId),
    queryFn: () => fetchStaleness(workflowId),
    enabled: options?.enabled ?? !!workflowId,
    refetchInterval: options?.refetchInterval,
  });
}
