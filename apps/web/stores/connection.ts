/**
 * SOLVER Web - Connection State Store
 *
 * Per Architectural Contract Section 14.1: Connection Status.
 * Manages SSE connection state.
 *
 * NOTE: SequenceGuard is deferred to Package 6.3.
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

/**
 * Connection status per Contract Section 14.1
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

  // Actions
  setStatus: (status: ConnectionStatus) => void;
  setWorkflowId: (id: string | null) => void;
  setError: (error: Error | null) => void;
  reset: () => void;
}

const initialState = {
  status: 'disconnected' as ConnectionStatus,
  workflowId: null,
  error: null,
};

export const useConnectionStore = create<ConnectionState>()(
  devtools(
    (set) => ({
      ...initialState,

      setStatus: (status) => set({ status }),
      setWorkflowId: (workflowId) => set({ workflowId }),
      setError: (error) => set({ error }),
      reset: () => set(initialState),
    }),
    { name: 'solver-connection' }
  )
);
