/**
 * SOLVER Web - Create Workflow Mutation Hook
 *
 * TanStack Query mutation for POST /workflows
 * Package 6.5 deliverable per Development Directive v1.5.1.
 */

'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createWorkflow } from '@/lib/api';
import type { CreateWorkflowRequest, WorkflowResponse } from '@/lib/types';
import { workflowKeys } from './use-workflow';

/**
 * Hook to create a new workflow
 *
 * @returns TanStack Query mutation for creating workflows
 */
export function useCreateWorkflow() {
  const queryClient = useQueryClient();

  return useMutation<WorkflowResponse, Error, CreateWorkflowRequest>({
    mutationFn: createWorkflow,
    onSuccess: (data) => {
      // Pre-populate the workflow query cache with the response
      queryClient.setQueryData(workflowKeys.detail(data.workflow_id), data);
    },
  });
}
