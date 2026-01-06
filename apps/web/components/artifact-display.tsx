/**
 * SOLVER Web - Artifact Display Component
 *
 * Renders artifact content and metadata.
 * Package 6.5 deliverable per Development Directive v1.5.1.
 *
 * Fetches artifact content from GET /workflows/{id}/artifacts/{aid}
 * when workflowId and artifactId are provided.
 *
 * Content delivery:
 * - Fetches from artifact endpoint when artifactId is provided
 * - Shows placeholder when content is unavailable
 * - Future (6.6): Content may be delivered via SSE streaming
 */

'use client';

import { useArtifact } from '@/hooks/api/use-artifact';
import type { StepName, PassType, ArtifactResponse } from '@/lib/types';

// ============================================================================
// Props
// ============================================================================

/**
 * Artifact metadata from progress endpoint
 */
export interface ArtifactMetadata {
  artifact_id: string;
  step_name: StepName;
  pass_type: PassType;
  revision: number;
  is_stale: boolean;
  updated_at: string | null;
}

/**
 * Artifact content structure (when available)
 * Content can be structured JSON or markdown text
 */
export interface ArtifactContent {
  /** Content type: 'json' for structured data, 'markdown' for text */
  type: 'json' | 'markdown';
  /** The actual content */
  data: unknown;
}

export interface ArtifactDisplayProps {
  /** Workflow ID (required for fetching) */
  workflowId: string;
  /** Artifact ID */
  artifactId: string;
  /** Artifact metadata from progress data */
  metadata?: ArtifactMetadata;
  /** Artifact content override (optional - if provided, skips fetch) */
  content?: ArtifactContent;
  /** Whether artifact is currently streaming (6.6) */
  isStreaming?: boolean;
}

// ============================================================================
// Component
// ============================================================================

/**
 * Artifact display component.
 *
 * Fetches artifact content from API when workflowId and artifactId are provided.
 * If content prop is provided, uses that instead of fetching.
 */
export function ArtifactDisplay({
  workflowId,
  artifactId,
  metadata,
  content: contentOverride,
  isStreaming,
}: ArtifactDisplayProps) {
  // Fetch artifact content from API (skip if content override provided)
  const { data: artifactData, isLoading, error } = useArtifact(
    workflowId,
    contentOverride ? null : artifactId
  );

  // Transform API response to ArtifactContent format
  const content = contentOverride ?? transformArtifactResponse(artifactData);

  // Use metadata from props or derive from fetched data
  const displayMetadata = metadata ?? deriveMetadata(artifactData);

  if (isLoading) {
    return <ArtifactSkeleton />;
  }

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-muted/50 border-b border-border">
        <div className="flex items-center gap-3">
          <h3 className="font-medium text-sm">
            {displayMetadata ? formatStepName(displayMetadata.step_name) : 'Artifact'}
          </h3>
          {displayMetadata && (
            <span className="text-xs text-muted-foreground">
              v{displayMetadata.revision}
            </span>
          )}
          {displayMetadata?.is_stale && (
            <span className="px-1.5 py-0.5 text-xs font-medium bg-orange-100 text-orange-700 rounded">
              Stale
            </span>
          )}
          {isStreaming && (
            <span className="px-1.5 py-0.5 text-xs font-medium bg-blue-100 text-blue-700 rounded animate-pulse">
              Streaming...
            </span>
          )}
        </div>

        {/* Artifact ID (truncated) */}
        <span className="text-xs text-muted-foreground font-mono" title={artifactId}>
          {artifactId.slice(0, 8)}...
        </span>
      </div>

      {/* Content */}
      <div className="p-4">
        {error ? (
          <ArtifactError message={error.message} />
        ) : content ? (
          <ArtifactContentRenderer content={content} />
        ) : (
          <ArtifactPlaceholder />
        )}
      </div>

      {/* Footer with metadata */}
      {displayMetadata?.updated_at && (
        <div className="px-4 py-2 bg-muted/30 border-t border-border text-xs text-muted-foreground">
          Last updated: {formatDate(displayMetadata.updated_at)}
        </div>
      )}
    </div>
  );
}

/**
 * Transform ArtifactResponse to ArtifactContent format
 */
function transformArtifactResponse(
  data: ArtifactResponse | undefined
): ArtifactContent | undefined {
  if (!data?.content_jsonb) {
    return undefined;
  }

  // Check if this is a methodology doc (has markdown field)
  if ('markdown' in data.content_jsonb && typeof data.content_jsonb.markdown === 'string') {
    return {
      type: 'markdown',
      data: data.content_jsonb.markdown,
    };
  }

  // Step package - render as JSON
  return {
    type: 'json',
    data: data.content_jsonb,
  };
}

/**
 * Derive ArtifactMetadata from ArtifactResponse
 */
function deriveMetadata(data: ArtifactResponse | undefined): ArtifactMetadata | undefined {
  if (!data) {
    return undefined;
  }

  return {
    artifact_id: data.id,
    step_name: data.step_name,
    pass_type: data.pass_type,
    revision: data.revision,
    is_stale: data.stale,
    updated_at: data.updated_at,
  };
}

// ============================================================================
// Sub-components
// ============================================================================

function ArtifactContentRenderer({ content }: { content: ArtifactContent }) {
  if (content.type === 'markdown') {
    return (
      <div className="prose prose-sm max-w-none">
        <pre className="whitespace-pre-wrap text-sm font-mono bg-muted/30 p-3 rounded">
          {String(content.data)}
        </pre>
      </div>
    );
  }

  // JSON content - render as formatted JSON
  return (
    <div className="bg-muted/30 p-3 rounded overflow-x-auto">
      <pre className="text-sm font-mono">
        {JSON.stringify(content.data, null, 2)}
      </pre>
    </div>
  );
}

function ArtifactPlaceholder() {
  return (
    <div className="flex flex-col items-center justify-center py-8 text-center">
      <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-3">
        <svg
          className="w-6 h-6 text-muted-foreground"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
      </div>
      <p className="text-sm text-muted-foreground">
        Artifact content unavailable
      </p>
      <p className="text-xs text-muted-foreground mt-1">
        Content will appear when available
      </p>
    </div>
  );
}

function ArtifactError({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-8 text-center">
      <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center mb-3">
        <svg
          className="w-6 h-6 text-red-600"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
      </div>
      <p className="text-sm text-red-600">
        Failed to load artifact
      </p>
      <p className="text-xs text-muted-foreground mt-1">
        {message}
      </p>
    </div>
  );
}

function ArtifactSkeleton() {
  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <div className="px-4 py-3 bg-muted/50 border-b border-border">
        <div className="h-4 w-32 bg-muted rounded animate-pulse" />
      </div>
      <div className="p-4">
        <div className="space-y-2">
          <div className="h-4 w-full bg-muted/50 rounded animate-pulse" />
          <div className="h-4 w-3/4 bg-muted/50 rounded animate-pulse" />
          <div className="h-4 w-5/6 bg-muted/50 rounded animate-pulse" />
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Helpers
// ============================================================================

function formatStepName(name: string): string {
  return name
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function formatDate(dateString: string): string {
  try {
    const date = new Date(dateString);
    return date.toLocaleString();
  } catch {
    return dateString;
  }
}
