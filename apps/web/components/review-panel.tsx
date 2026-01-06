/**
 * SOLVER Web - Review Panel Component
 *
 * Provides approve/revise actions at review gates.
 * Package 6.5 deliverable per Development Directive v1.5.1.
 *
 * Contract Requirements:
 * - R18: Approve/revise MUST include expected_state_version + expected_position
 * - §14.3: Disabled buttons show reasons
 * - 409 conflict: Displays inline error message after refetch
 */

'use client';

import { useState } from 'react';
import { useApprove, isApproveConflictError } from '@/hooks/api/use-approve';
import { useRevise, isReviseConflictError } from '@/hooks/api/use-revise';
import type { WorkflowResponse, ExpectedPosition } from '@/lib/types';

// ============================================================================
// Props
// ============================================================================

export interface ReviewPanelProps {
  /** Workflow ID */
  workflowId: string;
  /** Workflow data (for extracting OCC fields) */
  workflowData: WorkflowResponse;
  /** Whether actions are allowed */
  canAct: boolean;
  /** Reason why actions are disabled (shown in tooltip) */
  disabledReason: string | null;
}

// ============================================================================
// Component
// ============================================================================

/**
 * Review panel with approve/revise actions.
 *
 * Extracts expected_state_version and expected_position from workflow data
 * and includes them in mutation requests per R18.
 */
export function ReviewPanel({
  workflowId,
  workflowData,
  canAct,
  disabledReason,
}: ReviewPanelProps) {
  const [showReviseForm, setShowReviseForm] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [conflictError, setConflictError] = useState<string | null>(null);

  const approveMutation = useApprove(workflowId);
  const reviseMutation = useRevise(workflowId);

  // Extract OCC fields from workflow data
  const expectedPosition: ExpectedPosition = {
    pass_type: workflowData.position.pass_type,
    step_name: workflowData.position.step_name,
    step_number: workflowData.position.step_number,
    status: workflowData.position.status,
  };
  const expectedStateVersion = workflowData.state_version;

  /**
   * Handle approve action
   *
   * Note: Don't re-throw errors - mutation.error state handles display.
   * Re-throwing causes unhandled promise rejections.
   */
  const handleApprove = async () => {
    setConflictError(null);

    try {
      await approveMutation.mutateAsync({
        expected_state_version: expectedStateVersion,
        expected_position: expectedPosition,
      });
    } catch (error) {
      if (isApproveConflictError(error)) {
        setConflictError(error.message);
      }
      // Don't re-throw - mutation.error state handles generic error display
    }
  };

  /**
   * Handle revise action
   *
   * Note: Don't re-throw errors - mutation.error state handles display.
   * Re-throwing causes unhandled promise rejections.
   */
  const handleRevise = async () => {
    if (!feedback.trim()) return;
    setConflictError(null);

    try {
      await reviseMutation.mutateAsync({
        feedback: feedback.trim(),
        expected_state_version: expectedStateVersion,
        expected_position: expectedPosition,
      });
      // Clear form on success
      setFeedback('');
      setShowReviseForm(false);
    } catch (error) {
      if (isReviseConflictError(error)) {
        setConflictError(error.message);
      }
      // Don't re-throw - mutation.error state handles generic error display
    }
  };

  const isLoading = approveMutation.isPending || reviseMutation.isPending;

  return (
    <div className="border border-border rounded-lg p-4 space-y-4">
      <h3 className="font-semibold text-sm">Review Actions</h3>

      {/* Conflict error message (inline per spec) */}
      {conflictError && (
        <div className="px-3 py-2 bg-destructive/10 border border-destructive/30 rounded text-sm text-destructive">
          {conflictError}
        </div>
      )}

      {/* Generic error messages */}
      {approveMutation.isError && !isApproveConflictError(approveMutation.error) && (
        <div className="px-3 py-2 bg-destructive/10 border border-destructive/30 rounded text-sm text-destructive">
          Approve failed: {approveMutation.error?.message ?? 'Unknown error'}
        </div>
      )}
      {reviseMutation.isError && !isReviseConflictError(reviseMutation.error) && (
        <div className="px-3 py-2 bg-destructive/10 border border-destructive/30 rounded text-sm text-destructive">
          Revise failed: {reviseMutation.error?.message ?? 'Unknown error'}
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-3">
        <ActionButton
          onClick={handleApprove}
          disabled={!canAct || isLoading}
          disabledReason={disabledReason}
          isLoading={approveMutation.isPending}
          variant="primary"
        >
          Approve
        </ActionButton>

        <ActionButton
          onClick={() => setShowReviseForm(!showReviseForm)}
          disabled={!canAct || isLoading}
          disabledReason={disabledReason}
          variant="secondary"
        >
          {showReviseForm ? 'Cancel' : 'Request Revision'}
        </ActionButton>
      </div>

      {/* Revise form */}
      {showReviseForm && (
        <div className="space-y-3 pt-2 border-t border-border">
          <label className="block">
            <span className="text-sm font-medium text-foreground">
              Revision Feedback
            </span>
            <textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="Describe what needs to be revised..."
              className="mt-1 block w-full px-3 py-2 border border-input rounded-md text-sm
                         placeholder:text-muted-foreground
                         focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent
                         disabled:opacity-50 disabled:cursor-not-allowed"
              rows={3}
              disabled={!canAct || isLoading}
            />
          </label>
          <ActionButton
            onClick={handleRevise}
            disabled={!canAct || isLoading || !feedback.trim()}
            disabledReason={!feedback.trim() ? 'Feedback required' : disabledReason}
            isLoading={reviseMutation.isPending}
            variant="primary"
          >
            Submit Revision Request
          </ActionButton>
        </div>
      )}

      {/* Disabled reason explanation */}
      {!canAct && disabledReason && (
        <p className="text-xs text-muted-foreground">
          {disabledReason}
        </p>
      )}
    </div>
  );
}

// ============================================================================
// Sub-components
// ============================================================================

interface ActionButtonProps {
  children: React.ReactNode;
  onClick: () => void;
  disabled: boolean;
  disabledReason?: string | null;
  isLoading?: boolean;
  variant: 'primary' | 'secondary';
}

function ActionButton({
  children,
  onClick,
  disabled,
  disabledReason,
  isLoading,
  variant,
}: ActionButtonProps) {
  const baseClasses =
    'px-4 py-2 text-sm font-medium rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2';

  const variantClasses =
    variant === 'primary'
      ? 'bg-primary text-primary-foreground hover:bg-primary/90 disabled:bg-primary/50'
      : 'bg-secondary text-secondary-foreground hover:bg-secondary/80 disabled:bg-secondary/50';

  const disabledClasses = 'disabled:cursor-not-allowed disabled:opacity-60';

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={disabled && disabledReason ? disabledReason : undefined}
      className={`${baseClasses} ${variantClasses} ${disabledClasses}`}
    >
      {isLoading ? (
        <span className="flex items-center gap-2">
          <LoadingSpinner />
          {children}
        </span>
      ) : (
        children
      )}
    </button>
  );
}

function LoadingSpinner() {
  return (
    <svg
      className="animate-spin h-4 w-4"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}
