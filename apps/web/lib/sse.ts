/**
 * SOLVER Web - SSE Constants
 *
 * Server-Sent Events constants for streaming per Architectural Contract v3.4.
 * Package 6.2: Connection Manager
 *
 * NOTE: EventSource creation and URL building are INTERNAL to useConnectionManager hook.
 * This enforces §12.4 Reconnection Cursor Invariant at module boundary -
 * external code cannot pass arbitrary fromSequence values.
 */

/**
 * SSE stream endpoint path template.
 * Full URL: ${API_BASE_URL}${SSE_STREAM_PATH}/${workflowId}/stream
 */
export const SSE_STREAM_PATH = '/api/v1/workflows';
