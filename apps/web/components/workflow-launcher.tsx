/**
 * SOLVER Web - Workflow Launcher Component
 *
 * Provides workflow creation and navigation.
 * Package 6.5 deliverable per Development Directive v1.5.1.
 *
 * Features:
 * - Create workflow form (problem statement input)
 * - Navigate to workflow by ID input field
 * - Shows created workflow ID after successful creation
 * - "Go to Workflow" button after creation
 *
 * Note: No list endpoint exists (by design decision), so this provides
 * a "navigation only" approach per plan approval.
 */

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useCreateWorkflow } from '@/hooks/api/use-create-workflow';

// ============================================================================
// Component
// ============================================================================

export function WorkflowLauncher() {
  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <div className="text-center">
        <h1 className="text-2xl font-bold">SOLVER Workflow</h1>
        <p className="text-muted-foreground mt-2">
          Create a new workflow or navigate to an existing one
        </p>
      </div>

      <div className="grid gap-8 md:grid-cols-2">
        <CreateWorkflowCard />
        <NavigateToWorkflowCard />
      </div>
    </div>
  );
}

// ============================================================================
// Create Workflow Card
// ============================================================================

function CreateWorkflowCard() {
  const router = useRouter();
  const [problem, setProblem] = useState('');
  const [createdBy, setCreatedBy] = useState('user');
  const [createdWorkflowId, setCreatedWorkflowId] = useState<string | null>(null);

  const createMutation = useCreateWorkflow();

  const handleCreate = async () => {
    if (!problem.trim()) return;

    try {
      const result = await createMutation.mutateAsync({
        problem: problem.trim(),
        created_by: createdBy.trim() || 'user',
      });
      setCreatedWorkflowId(result.workflow_id);
      setProblem('');
    } catch {
      // Error handled by mutation state
    }
  };

  const handleGoToWorkflow = () => {
    if (createdWorkflowId) {
      router.push(`/workflow/${createdWorkflowId}`);
    }
  };

  return (
    <div className="border border-border rounded-lg p-6 space-y-4">
      <h2 className="font-semibold text-lg">Create New Workflow</h2>

      {/* Error message */}
      {createMutation.isError && (
        <div className="px-3 py-2 bg-destructive/10 border border-destructive/30 rounded text-sm text-destructive">
          Failed to create workflow: {createMutation.error?.message ?? 'Unknown error'}
        </div>
      )}

      {/* Success state - show created workflow */}
      {createdWorkflowId ? (
        <div className="space-y-4">
          <div className="px-3 py-2 bg-green-100 border border-green-300 rounded">
            <p className="text-sm text-green-700 font-medium">Workflow created!</p>
            <p className="text-xs text-green-600 font-mono mt-1 break-all">
              ID: {createdWorkflowId}
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={handleGoToWorkflow}
              className="flex-1 px-4 py-2 text-sm font-medium rounded-md
                         bg-primary text-primary-foreground hover:bg-primary/90
                         focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
            >
              Go to Workflow
            </button>
            <button
              onClick={() => setCreatedWorkflowId(null)}
              className="px-4 py-2 text-sm font-medium rounded-md
                         bg-secondary text-secondary-foreground hover:bg-secondary/80
                         focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
            >
              Create Another
            </button>
          </div>
        </div>
      ) : (
        <>
          {/* Problem input */}
          <div>
            <label className="block text-sm font-medium mb-1">
              Problem Statement
            </label>
            <textarea
              value={problem}
              onChange={(e) => setProblem(e.target.value)}
              placeholder="Describe the problem to solve..."
              className="block w-full px-3 py-2 border border-input rounded-md text-sm
                         placeholder:text-muted-foreground
                         focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent
                         disabled:opacity-50"
              rows={4}
              disabled={createMutation.isPending}
            />
          </div>

          {/* Created by input */}
          <div>
            <label className="block text-sm font-medium mb-1">
              Created By
            </label>
            <input
              type="text"
              value={createdBy}
              onChange={(e) => setCreatedBy(e.target.value)}
              placeholder="Your name or identifier"
              className="block w-full px-3 py-2 border border-input rounded-md text-sm
                         placeholder:text-muted-foreground
                         focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent
                         disabled:opacity-50"
              disabled={createMutation.isPending}
            />
          </div>

          {/* Create button */}
          <button
            onClick={handleCreate}
            disabled={!problem.trim() || createMutation.isPending}
            className="w-full px-4 py-2 text-sm font-medium rounded-md
                       bg-primary text-primary-foreground hover:bg-primary/90
                       disabled:bg-primary/50 disabled:cursor-not-allowed disabled:opacity-60
                       focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
          >
            {createMutation.isPending ? (
              <span className="flex items-center justify-center gap-2">
                <LoadingSpinner />
                Creating...
              </span>
            ) : (
              'Create Workflow'
            )}
          </button>
        </>
      )}
    </div>
  );
}

// ============================================================================
// Navigate to Workflow Card
// ============================================================================

function NavigateToWorkflowCard() {
  const router = useRouter();
  const [workflowId, setWorkflowId] = useState('');

  const handleNavigate = () => {
    if (!workflowId.trim()) return;
    router.push(`/workflow/${workflowId.trim()}`);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && workflowId.trim()) {
      handleNavigate();
    }
  };

  return (
    <div className="border border-border rounded-lg p-6 space-y-4">
      <h2 className="font-semibold text-lg">Open Existing Workflow</h2>

      <p className="text-sm text-muted-foreground">
        Enter a workflow ID to view its details and status.
      </p>

      {/* Workflow ID input */}
      <div>
        <label className="block text-sm font-medium mb-1">
          Workflow ID
        </label>
        <input
          type="text"
          value={workflowId}
          onChange={(e) => setWorkflowId(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Enter workflow UUID..."
          className="block w-full px-3 py-2 border border-input rounded-md text-sm font-mono
                     placeholder:text-muted-foreground placeholder:font-sans
                     focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
        />
      </div>

      {/* Navigate button */}
      <button
        onClick={handleNavigate}
        disabled={!workflowId.trim()}
        className="w-full px-4 py-2 text-sm font-medium rounded-md
                   bg-secondary text-secondary-foreground hover:bg-secondary/80
                   disabled:bg-secondary/50 disabled:cursor-not-allowed disabled:opacity-60
                   focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
      >
        Go to Workflow
      </button>
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
