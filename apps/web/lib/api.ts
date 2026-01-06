/**
 * SOLVER Web - API Client
 *
 * REST API client for workflow operations.
 * Package 6.5 deliverable per Development Directive v1.5.1.
 */

import type {
  WorkflowResponse,
  MessageResponse,
  ProgressResponse,
  StalenessResponse,
  ArtifactResponse,
  CreateWorkflowRequest,
  ApproveRequest,
  ReviseRequest,
  MessageRequest,
  StateConflictResponse,
} from './types';

// ============================================================================
// Configuration
// ============================================================================

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_PREFIX = '/api/v1';

// ============================================================================
// Error Classes
// ============================================================================

/**
 * API error with status code and parsed response
 */
export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public data: unknown
  ) {
    super(`API Error ${status}: ${statusText}`);
    this.name = 'ApiError';
  }
}

/**
 * State conflict error (409)
 * Contains current position and state_version for retry
 */
export class StateConflictError extends ApiError {
  public readonly conflictData: StateConflictResponse;

  constructor(data: StateConflictResponse) {
    super(409, 'Conflict', data);
    this.name = 'StateConflictError';
    this.conflictData = data;
  }
}

// ============================================================================
// Fetch Helper
// ============================================================================

/**
 * Type-safe fetch wrapper with error handling
 *
 * @param path - API path (without base URL or prefix)
 * @param options - Fetch options
 * @returns Parsed response data
 * @throws ApiError for non-2xx responses
 * @throws StateConflictError for 409 responses
 */
export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${API_PREFIX}${path}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  // Parse response body
  let data: unknown;
  const contentType = response.headers.get('content-type');
  if (contentType?.includes('application/json')) {
    data = await response.json();
  } else {
    data = await response.text();
  }

  // Handle errors
  if (!response.ok) {
    // Special handling for 409 Conflict (state version mismatch)
    if (response.status === 409 && isStateConflictResponse(data)) {
      throw new StateConflictError(data);
    }

    throw new ApiError(response.status, response.statusText, data);
  }

  return data as T;
}

/**
 * Type guard for StateConflictResponse
 */
function isStateConflictResponse(data: unknown): data is StateConflictResponse {
  return (
    typeof data === 'object' &&
    data !== null &&
    'error_code' in data &&
    (data as StateConflictResponse).error_code === 'STATE_CONFLICT'
  );
}

// ============================================================================
// Workflow API Functions
// ============================================================================

/**
 * Get workflow by ID
 * GET /workflows/{id}
 */
export function fetchWorkflow(workflowId: string): Promise<WorkflowResponse> {
  return apiFetch<WorkflowResponse>(`/workflows/${workflowId}`);
}

/**
 * Get workflow progress
 * GET /workflows/{id}/progress
 */
export function fetchProgress(workflowId: string): Promise<ProgressResponse> {
  return apiFetch<ProgressResponse>(`/workflows/${workflowId}/progress`);
}

/**
 * Get workflow staleness
 * GET /workflows/{id}/staleness
 */
export function fetchStaleness(workflowId: string): Promise<StalenessResponse> {
  return apiFetch<StalenessResponse>(`/workflows/${workflowId}/staleness`);
}

/**
 * Get artifact by ID
 * GET /workflows/{id}/artifacts/{aid}
 * Per Tech Spec V2.8.0 Appendix C.4
 */
export function fetchArtifact(
  workflowId: string,
  artifactId: string
): Promise<ArtifactResponse> {
  return apiFetch<ArtifactResponse>(`/workflows/${workflowId}/artifacts/${artifactId}`);
}

/**
 * Create new workflow
 * POST /workflows
 */
export function createWorkflow(request: CreateWorkflowRequest): Promise<WorkflowResponse> {
  return apiFetch<WorkflowResponse>('/workflows', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * Approve current step
 * POST /workflows/{id}/actions/approve
 *
 * @throws StateConflictError on 409 (state_version mismatch)
 */
export function approveStep(
  workflowId: string,
  request: ApproveRequest
): Promise<WorkflowResponse> {
  return apiFetch<WorkflowResponse>(`/workflows/${workflowId}/actions/approve`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * Request revision of current step
 * POST /workflows/{id}/actions/revise
 *
 * @throws StateConflictError on 409 (state_version mismatch)
 */
export function reviseStep(
  workflowId: string,
  request: ReviseRequest
): Promise<WorkflowResponse> {
  return apiFetch<WorkflowResponse>(`/workflows/${workflowId}/actions/revise`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * Send message (does NOT require expected_state_version per Tech Spec §16.7)
 * POST /workflows/{id}/actions/message
 *
 * Per V2.8.2: Returns minimal MessageResponse, not full WorkflowResponse
 */
export function sendMessage(
  workflowId: string,
  request: MessageRequest
): Promise<MessageResponse> {
  return apiFetch<MessageResponse>(`/workflows/${workflowId}/actions/message`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}
