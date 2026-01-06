/**
 * SOLVER Web - Artifact Query Hook
 *
 * TanStack Query hook for GET /workflows/{id}/artifacts/{aid}
 * Package 6.5 deliverable per Development Directive v1.5.1.
 */

'use client';

import { useQuery } from '@tanstack/react-query';
import { fetchArtifact } from '@/lib/api';
import type { ArtifactResponse } from '@/lib/types';

/**
 * Query key factory for artifact queries
 */
export const artifactKeys = {
  all: ['artifacts'] as const,
  detail: (workflowId: string, artifactId: string) =>
    [...artifactKeys.all, workflowId, artifactId] as const,
};

/**
 * Hook to fetch artifact content
 *
 * @param workflowId - Workflow ID the artifact belongs to
 * @param artifactId - Artifact ID to fetch (null/undefined to disable)
 * @param options - Additional query options
 * @returns TanStack Query result with ArtifactResponse
 */
export function useArtifact(
  workflowId: string,
  artifactId: string | null | undefined,
  options?: {
    enabled?: boolean;
  }
) {
  return useQuery<ArtifactResponse, Error>({
    queryKey: artifactKeys.detail(workflowId, artifactId ?? ''),
    queryFn: () => fetchArtifact(workflowId, artifactId!),
    enabled: (options?.enabled ?? true) && !!workflowId && !!artifactId,
  });
}
