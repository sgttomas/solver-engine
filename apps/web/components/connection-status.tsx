/**
 * SOLVER Web - Connection Status Component
 *
 * Displays SSE connection status with visual indicators.
 * Package 6.5 deliverable per Development Directive v1.5.1.
 *
 * Contract Requirements:
 * - §16.10/C5: Status indicators must be visible
 * - §16.10/C5: Failed state must provide recovery path (Retry button)
 */

'use client';

import type { ConnectionStatus as ConnectionStatusType } from '@/stores/connection';

// ============================================================================
// Props
// ============================================================================

export interface ConnectionStatusProps {
  /** Current connection status */
  status: ConnectionStatusType;
  /** Callback to initiate connection (for retry button) */
  onConnect: () => void;
  /** Last error that occurred (optional) */
  error?: Error | null;
  /** Current retry count (optional) */
  retryCount?: number;
}

// ============================================================================
// Status Configuration
// ============================================================================

interface StatusConfig {
  label: string;
  color: string;
  bgColor: string;
  showSpinner: boolean;
}

const STATUS_CONFIG: Record<ConnectionStatusType, StatusConfig> = {
  disconnected: {
    label: 'Disconnected',
    color: 'text-muted-foreground',
    bgColor: 'bg-muted',
    showSpinner: false,
  },
  connecting: {
    label: 'Connecting',
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-100',
    showSpinner: true,
  },
  connected: {
    label: 'Connected',
    color: 'text-green-600',
    bgColor: 'bg-green-100',
    showSpinner: false,
  },
  reconnecting: {
    label: 'Reconnecting',
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-100',
    showSpinner: true,
  },
  resyncing: {
    label: 'Syncing',
    color: 'text-blue-600',
    bgColor: 'bg-blue-100',
    showSpinner: true,
  },
  failed: {
    label: 'Connection Failed',
    color: 'text-destructive',
    bgColor: 'bg-destructive/10',
    showSpinner: false,
  },
};

// ============================================================================
// Component
// ============================================================================

/**
 * Connection status indicator with retry functionality.
 *
 * Per Contract §16.10/C5:
 * - Shows visual status indicator
 * - Failed state displays "Retry connection" button
 */
export function ConnectionStatus({
  status,
  onConnect,
  error,
  retryCount,
}: ConnectionStatusProps) {
  const config = STATUS_CONFIG[status];

  return (
    <div className={`flex items-center gap-2 px-3 py-2 rounded-md ${config.bgColor}`}>
      {/* Status indicator */}
      <div className="flex items-center gap-2">
        {config.showSpinner ? (
          <Spinner className={config.color} />
        ) : (
          <StatusDot status={status} />
        )}
        <span className={`text-sm font-medium ${config.color}`}>
          {config.label}
        </span>
      </div>

      {/* Retry count (if reconnecting) */}
      {(status === 'reconnecting' || status === 'connecting') && retryCount !== undefined && retryCount > 0 && (
        <span className="text-xs text-muted-foreground">
          (Attempt {retryCount + 1})
        </span>
      )}

      {/* Retry button for failed state per §16.10/C5 */}
      {status === 'failed' && (
        <button
          onClick={onConnect}
          className="ml-2 px-2 py-1 text-xs font-medium text-primary bg-background border border-border rounded hover:bg-accent transition-colors"
        >
          Retry connection
        </button>
      )}

      {/* Error tooltip/message */}
      {status === 'failed' && error && (
        <span className="text-xs text-destructive ml-2 truncate max-w-[200px]" title={error.message}>
          {error.message}
        </span>
      )}
    </div>
  );
}

// ============================================================================
// Sub-components
// ============================================================================

function StatusDot({ status }: { status: ConnectionStatusType }) {
  const dotColors: Record<ConnectionStatusType, string> = {
    disconnected: 'bg-muted-foreground',
    connecting: 'bg-yellow-500',
    connected: 'bg-green-500',
    reconnecting: 'bg-yellow-500',
    resyncing: 'bg-blue-500',
    failed: 'bg-destructive',
  };

  return (
    <span
      className={`w-2 h-2 rounded-full ${dotColors[status]}`}
      aria-hidden="true"
    />
  );
}

function Spinner({ className }: { className?: string }) {
  return (
    <svg
      className={`animate-spin h-4 w-4 ${className ?? ''}`}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
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
