/**
 * SOLVER Web - Workflow Detail Page
 *
 * Dynamic route for workflow detail view.
 * Package 6.5 deliverable per Development Directive v1.5.1.
 */

'use client';

import { useParams } from 'next/navigation';
import { WorkflowDetail } from '@/components/workflow-detail';

export default function WorkflowDetailPage() {
  const params = useParams<{ id: string }>();

  if (!params.id) {
    return (
      <main className="min-h-screen flex items-center justify-center">
        <p className="text-muted-foreground">Invalid workflow ID</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen">
      <WorkflowDetail workflowId={params.id} />
    </main>
  );
}
