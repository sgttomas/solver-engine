/**
 * SOLVER Web - Connection State Store
 *
 * Per Architectural Contract v3.4 Section 14.1: Connection Status.
 * Manages SSE connection state and retry tracking.
 *
 * Package 6.2: Connection Manager
 * NOTE: SequenceGuard is deferred to Package 6.3.
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

/**
 * Connection status per Contract Section 14.1
 *
 * Status semantics (C5):
 * - disconnected: No active connection
 * - connecting: Initial connection attempt
 * - connected: Stream established AND canonical refetch complete
 * - reconnecting: Transport recovery (network drop)
 * - resyncing: Correctness recovery (gap detected)
 * - failed: User intervention required
 */
export type ConnectionStatus =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'resyncing'
  | 'failed';

interface ConnectionState {
  // Connection state
  status: ConnectionStatus;
  workflowId: string | null;
  error: Error | null;

  // Retry tracking (Package 6.2)
  retryCount: number;
  lastConnectedAt: number | null;

  // Actions
  setStatus: (status: ConnectionStatus) => void;
  setWorkflowId: (id: string | null) => void;
  setError: (error: Error | null) => void;
  setRetryCount: (count: number) => void;
  incrementRetryCount: () => void;
  resetRetryCount: () => void;
  setLastConnectedAt: (timestamp: number | null) => void;
  reset: () => void;
}

const initialState = {
  status: 'disconnected' as ConnectionStatus,
  workflowId: null,
  error: null,
  retryCount: 0,
  lastConnectedAt: null,
};

export const useConnectionStore = create<ConnectionState>()(
  devtools(
    (set) => ({
      ...initialState,

      setStatus: (status) => set({ status }),
      setWorkflowId: (workflowId) => set({ workflowId }),
      setError: (error) => set({ error }),
      setRetryCount: (retryCount) => set({ retryCount }),
      incrementRetryCount: () => set((state) => ({ retryCount: state.retryCount + 1 })),
      resetRetryCount: () => set({ retryCount: 0 }),
      setLastConnectedAt: (lastConnectedAt) => set({ lastConnectedAt }),
      reset: () => set(initialState),
    }),
    { name: 'solver-connection' }
  )
);
