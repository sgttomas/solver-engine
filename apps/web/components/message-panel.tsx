/**
 * SOLVER Web - Message Panel Component
 *
 * Provides message input for awaiting_review/awaiting_clarification states.
 * Package 6.5 deliverable per Development Directive v1.5.1.
 *
 * Contract Requirements:
 * - §16.7: Message does NOT require expected_state_version
 * - §14.3: Shows disabled reason when canMessage=false
 */

'use client';

import { useState } from 'react';
import { useMessage } from '@/hooks/api/use-message';

// ============================================================================
// Props
// ============================================================================

export interface MessagePanelProps {
  /** Workflow ID */
  workflowId: string;
  /** Whether messaging is allowed */
  canMessage: boolean;
  /** Reason why messaging is disabled (shown in tooltip) */
  disabledReason: string | null;
}

// ============================================================================
// Component
// ============================================================================

/**
 * Message panel for sending commentary.
 *
 * Per Tech Spec §16.7, message action does NOT require expected_state_version
 * because it doesn't mutate workflow state.
 */
export function MessagePanel({
  workflowId,
  canMessage,
  disabledReason,
}: MessagePanelProps) {
  const [content, setContent] = useState('');
  const messageMutation = useMessage(workflowId);

  /**
   * Handle message send
   */
  const handleSend = async () => {
    if (!content.trim()) return;

    try {
      await messageMutation.mutateAsync({
        content: content.trim(),
      });
      // Clear input on success
      setContent('');
    } catch {
      // Error handled by mutation state
    }
  };

  /**
   * Handle Enter key (Shift+Enter for newline)
   */
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (canMessage && content.trim() && !messageMutation.isPending) {
        handleSend();
      }
    }
  };

  const isDisabled = !canMessage || messageMutation.isPending;

  return (
    <div className="border border-border rounded-lg p-4 space-y-3">
      <h3 className="font-semibold text-sm">Send Message</h3>

      {/* Error message */}
      {messageMutation.isError && (
        <div className="px-3 py-2 bg-destructive/10 border border-destructive/30 rounded text-sm text-destructive">
          Failed to send message: {messageMutation.error?.message ?? 'Unknown error'}
        </div>
      )}

      {/* Success message */}
      {messageMutation.isSuccess && (
        <div className="px-3 py-2 bg-green-100 border border-green-300 rounded text-sm text-green-700">
          Message sent successfully
        </div>
      )}

      {/* Input area */}
      <div className="space-y-2">
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Add a comment or ask a clarification question..."
          className="block w-full px-3 py-2 border border-input rounded-md text-sm
                     placeholder:text-muted-foreground
                     focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent
                     disabled:opacity-50 disabled:cursor-not-allowed resize-none"
          rows={3}
          disabled={isDisabled}
        />
        <div className="flex items-center justify-between">
          <p className="text-xs text-muted-foreground">
            Press Enter to send, Shift+Enter for new line
          </p>
          <button
            onClick={handleSend}
            disabled={isDisabled || !content.trim()}
            title={!canMessage && disabledReason ? disabledReason : undefined}
            className="px-4 py-2 text-sm font-medium rounded-md transition-colors
                       bg-primary text-primary-foreground hover:bg-primary/90
                       disabled:bg-primary/50 disabled:cursor-not-allowed disabled:opacity-60
                       focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
          >
            {messageMutation.isPending ? (
              <span className="flex items-center gap-2">
                <LoadingSpinner />
                Sending...
              </span>
            ) : (
              'Send'
            )}
          </button>
        </div>
      </div>

      {/* Disabled reason explanation */}
      {!canMessage && disabledReason && (
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
