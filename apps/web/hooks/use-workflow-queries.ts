/**
 * SOLVER Web - Composed Workflow Queries Hook
 *
 * Bundles canonical queries (workflow, progress, staleness) for use with
 * useCanAct and connection lifecycle callbacks.
 * Package 6.5 deliverable per Development Directive v1.5.1.
 *
 * Contract Requirements:
 * - Provides refetch bundle for R7/C2 compliance (connection lifecycle)
 * - Tracks isAnyFetching for R14 (canAct gating)
 */

'use client';

import { useWorkflow, workflowKeys } from './api/use-workflow';
import { useProgress, progressKeys } from './api/use-progress';
import { useStaleness, stalenessKeys } from './api/use-staleness';

export { workflowKeys, progressKeys, stalenessKeys };

/**
 * Composed hook providing canonical query bundle
 *
 * Returns workflow, progress, and staleness queries with combined fetching state.
 * Used with useCanAct which requires all canonical queries to be idle before
 * allowing actions (R14).
 *
 * @param workflowId - Workflow ID to query
 * @param options - Query options
 * @returns Query results with combined fetching state
 */
export function useWorkflowQueries(
  workflowId: string,
  options?: {
    enabled?: boolean;
    refetchInterval?: number | false;
  }
) {
  const workflow = useWorkflow(workflowId, {
    enabled: options?.enabled,
    refetchInterval: options?.refetchInterval,
  });

  const progress = useProgress(workflowId, {
    enabled: options?.enabled,
    refetchInterval: options?.refetchInterval,
  });

  const staleness = useStaleness(workflowId, {
    enabled: options?.enabled,
    refetchInterval: options?.refetchInterval,
  });

  // Combined fetching state for R14 compliance (canAct requires all idle)
  const isAnyFetching =
    workflow.isFetching || progress.isFetching || staleness.isFetching;

  // Combined loading state (initial load)
  const isLoading =
    workflow.isLoading || progress.isLoading || staleness.isLoading;

  // Any error from canonical queries
  const error = workflow.error || progress.error || staleness.error;

  return {
    workflow,
    progress,
    staleness,
    isAnyFetching,
    isLoading,
    error,
  };
}
