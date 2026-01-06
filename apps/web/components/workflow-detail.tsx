/**
 * SOLVER Web - Workflow Detail Component
 *
 * Main layout component for workflow detail view.
 * Package 6.5 + 6.6 deliverable per Development Directive v1.5.1.
 *
 * Contract Requirements:
 * - R7/C2: onRefetchRequired performs explicit refetch and verifies state_version consistency
 * - R14: canAct requires all canonical queries idle
 * - §14.3: Disabled buttons show reasons
 * - §16.10/C5: Failed state shows "Retry connection" button
 * - §9.2.1: Event dispatcher maps SSE events to query invalidations (P6.6)
 * - §16.4.1: Idle timeout detection via heartbeat events (P6.6)
 *
 * Integration:
 * - Uses useWorkflowQueries for canonical query bundle
 * - Uses useWorkflowConnection for SSE with event dispatch
 * - Uses useEventDispatcher for event-driven query invalidation (P6.6)
 * - Uses useCanAct/useCanMessage for action gating
 */

'use client';

import { useCallback } from 'react';
import Link from 'next/link';
import { useWorkflowQueries } from '@/hooks/use-workflow-queries';
import { useWorkflowConnection } from '@/hooks/useWorkflowConnection';
import { useEventDispatcher } from '@/hooks/useEventDispatcher';
import { useCanAct } from '@/hooks/useCanAct';
import { useCanMessage } from '@/hooks/useCanMessage';
import { ConnectionStatus } from './connection-status';
import { StepProgress } from './step-progress';
import { ArtifactDisplay } from './artifact-display';
import { ReviewPanel } from './review-panel';
import { MessagePanel } from './message-panel';

// ============================================================================
// Props
// ============================================================================

export interface WorkflowDetailProps {
  /** Workflow ID from route params */
  workflowId: string;
}

// ============================================================================
// Component
// ============================================================================

/**
 * Workflow detail view with all sub-components.
 *
 * Integrates:
 * - ConnectionStatus: Shows connection state, retry button for failed
 * - StepProgress: Timeline of workflow steps
 * - ArtifactDisplay: Current artifact (placeholder until 6.6 streaming)
 * - ReviewPanel: Approve/revise actions (when awaiting_review)
 * - MessagePanel: Message input (when awaiting_review or awaiting_clarification)
 */
export function WorkflowDetail({ workflowId }: WorkflowDetailProps) {
  // Canonical query bundle
  const queries = useWorkflowQueries(workflowId);

  /**
   * onRefetchRequired callback for connection lifecycle.
   *
   * Per R7/C2: Must complete canonical refetch AND verify state_version
   * consistency before returning { success: true }.
   *
   * State version mismatch returns { success: false } → 'failed' status.
   * User can then manually retry via the "Retry connection" button.
   */
  const handleRefetchRequired = useCallback(async (): Promise<{ success: boolean }> => {
    try {
      // Refetch all canonical queries
      const [workflowResult, progressResult, stalenessResult] = await Promise.all([
        queries.workflow.refetch(),
        queries.progress.refetch(),
        queries.staleness.refetch(),
      ]);

      // Verify state_version consistency per Tech Spec §9.1
      // "Clients should verify all three endpoints return the same state_version"
      const wfVersion = workflowResult.data?.state_version;
      const progVersion = progressResult.data?.state_version;
      const staleVersion = stalenessResult.data?.state_version;

      if (wfVersion !== progVersion || wfVersion !== staleVersion) {
        // Mismatch → return false → 'failed' status (no retry per useConnectionManager:254-261)
        // This is conservative per Design Intent §1.2: blocking > risking stale approvals
        console.warn('state_version mismatch in canonical refetch', {
          workflow: wfVersion,
          progress: progVersion,
          staleness: staleVersion,
        });
        return { success: false };
      }

      return { success: true };
    } catch (error) {
      console.error('Canonical refetch failed:', error);
      return { success: false };
    }
  }, [queries.workflow, queries.progress, queries.staleness]);

  // P6.6: Event dispatcher for SSE event-driven query invalidation
  const { handleEvents } = useEventDispatcher({
    workflowId,
    onDomainError: (error) => {
      // Per §16.9: Domain errors do NOT affect connection status
      // Log for debugging; future UI enhancement may display these
      console.warn('[WorkflowDetail] Domain error event:', error.payload);
    },
  });

  // SSE connection with event dispatch wired (P6.6)
  const connection = useWorkflowConnection({
    workflowId,
    onRefetchRequired: handleRefetchRequired,
    onDispatch: handleEvents,
  });

  // Action gating
  const { canAct, reason: actReason } = useCanAct({
    connection: { status: connection.status },
    workflowQuery: queries.workflow,
    progressQuery: queries.progress,
    stalenessQuery: queries.staleness,
  });

  const { canMessage, reason: msgReason } = useCanMessage({
    connection: { status: connection.status },
    position: queries.workflow.data?.position,
  });

  // Derived state
  const workflowData = queries.workflow.data;
  const progressData = queries.progress.data;
  const isAtReviewGate = workflowData?.position.status === 'awaiting_review';
  const isMessageable =
    workflowData?.position.status === 'awaiting_review' ||
    workflowData?.position.status === 'awaiting_clarification';

  // Find current step's artifact info from progress data
  const currentStepProgress = progressData?.steps.find(
    (s) =>
      s.step_number === workflowData?.position.step_number &&
      s.pass_type === workflowData?.position.pass_type
  );

  // Loading state
  if (queries.isLoading) {
    return <WorkflowDetailSkeleton />;
  }

  // Error state
  if (queries.error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="border border-destructive/30 bg-destructive/10 rounded-lg p-6 text-center">
          <h2 className="text-lg font-semibold text-destructive mb-2">
            Failed to load workflow
          </h2>
          <p className="text-sm text-destructive/80 mb-4">
            {queries.error.message}
          </p>
          <Link
            href="/workflows"
            className="inline-block px-4 py-2 text-sm font-medium rounded-md
                       bg-secondary text-secondary-foreground hover:bg-secondary/80"
          >
            Back to Launcher
          </Link>
        </div>
      </div>
    );
  }

  // No data state
  if (!workflowData) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="border border-border rounded-lg p-6 text-center">
          <p className="text-muted-foreground">Workflow not found</p>
          <Link
            href="/workflows"
            className="inline-block mt-4 px-4 py-2 text-sm font-medium rounded-md
                       bg-secondary text-secondary-foreground hover:bg-secondary/80"
          >
            Back to Launcher
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <Link
              href="/workflows"
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              &larr; Workflows
            </Link>
          </div>
          <h1 className="text-xl font-bold mt-2">
            {formatStepName(workflowData.position.step_name)}
          </h1>
          <p className="text-sm text-muted-foreground mt-1 font-mono">
            {workflowId}
          </p>
        </div>

        {/* Connection status */}
        <ConnectionStatus
          status={connection.status}
          onConnect={connection.connect}
          error={connection.lastError}
          retryCount={connection.retryCount}
        />
      </div>

      {/* Main content grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left column: Progress + Artifact */}
        <div className="lg:col-span-2 space-y-6">
          {/* Step Progress */}
          <div className="border border-border rounded-lg p-4">
            <h2 className="font-semibold text-sm mb-4">Workflow Progress</h2>
            <StepProgress
              steps={progressData?.steps ?? []}
              currentStepNumber={workflowData.position.step_number}
              currentPassType={workflowData.position.pass_type}
              isLoading={queries.progress.isLoading}
            />
          </div>

          {/* Artifact Display */}
          {currentStepProgress?.artifact_id && (
            <ArtifactDisplay
              workflowId={workflowId}
              artifactId={currentStepProgress.artifact_id}
              metadata={{
                artifact_id: currentStepProgress.artifact_id,
                step_name: currentStepProgress.step_name,
                pass_type: currentStepProgress.pass_type,
                revision: currentStepProgress.artifact_revision ?? 1,
                is_stale: currentStepProgress.is_stale,
                updated_at: currentStepProgress.updated_at,
              }}
            />
          )}
        </div>

        {/* Right column: Actions */}
        <div className="space-y-6">
          {/* Workflow info card */}
          <div className="border border-border rounded-lg p-4 space-y-3">
            <h2 className="font-semibold text-sm">Workflow Details</h2>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Status</dt>
                <dd className="font-medium">
                  <StatusBadge status={workflowData.position.status} />
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Pass</dt>
                <dd className="font-medium capitalize">
                  {workflowData.position.pass_type}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Phase</dt>
                <dd className="font-medium capitalize">
                  {workflowData.position.phase}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">State Version</dt>
                <dd className="font-mono text-xs">{workflowData.state_version}</dd>
              </div>
            </dl>
          </div>

          {/* Review Panel (when at gate) */}
          {isAtReviewGate && (
            <ReviewPanel
              workflowId={workflowId}
              workflowData={workflowData}
              canAct={canAct}
              disabledReason={actReason}
            />
          )}

          {/* Message Panel (when messageable) */}
          {isMessageable && (
            <MessagePanel
              workflowId={workflowId}
              canMessage={canMessage}
              disabledReason={msgReason}
            />
          )}

          {/* Problem statement */}
          <div className="border border-border rounded-lg p-4">
            <h2 className="font-semibold text-sm mb-2">Problem Statement</h2>
            <p className="text-sm text-muted-foreground whitespace-pre-wrap">
              {workflowData.original_problem}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Sub-components
// ============================================================================

function StatusBadge({ status }: { status: string }) {
  const statusColors: Record<string, string> = {
    not_started: 'bg-muted text-muted-foreground',
    pending: 'bg-muted text-muted-foreground',
    in_progress: 'bg-blue-100 text-blue-700',
    awaiting_clarification: 'bg-yellow-100 text-yellow-700',
    awaiting_review: 'bg-purple-100 text-purple-700',
    approved: 'bg-green-100 text-green-700',
    revision_requested: 'bg-orange-100 text-orange-700',
  };

  const colorClass = statusColors[status] ?? 'bg-muted text-muted-foreground';
  const label = status.replace(/_/g, ' ');

  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded ${colorClass} capitalize`}>
      {label}
    </span>
  );
}

function WorkflowDetailSkeleton() {
  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      {/* Header skeleton */}
      <div className="flex items-center justify-between">
        <div>
          <div className="h-4 w-20 bg-muted rounded animate-pulse" />
          <div className="h-6 w-48 bg-muted rounded animate-pulse mt-2" />
          <div className="h-4 w-64 bg-muted rounded animate-pulse mt-1" />
        </div>
        <div className="h-10 w-32 bg-muted rounded animate-pulse" />
      </div>

      {/* Content skeleton */}
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <div className="h-64 bg-muted/30 rounded-lg animate-pulse" />
          <div className="h-48 bg-muted/30 rounded-lg animate-pulse" />
        </div>
        <div className="space-y-6">
          <div className="h-32 bg-muted/30 rounded-lg animate-pulse" />
          <div className="h-48 bg-muted/30 rounded-lg animate-pulse" />
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
