/**
 * SOLVER Web - Workflows Page
 *
 * Workflow launcher route.
 * Package 6.5 deliverable per Development Directive v1.5.1.
 */

import { WorkflowLauncher } from '@/components/workflow-launcher';

export default function WorkflowsPage() {
  return (
    <main className="min-h-screen py-12">
      <WorkflowLauncher />
    </main>
  );
}
