/**
 * SOLVER Web - Home Page
 *
 * Package 6.5 updated navigation per Development Directive v1.5.1.
 */

import Link from 'next/link';

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <h1 className="text-4xl font-bold tracking-tight">SOLVER</h1>
      <p className="mt-4 text-lg text-muted-foreground">Structured Reasoning Workflow Engine</p>
      <div className="mt-8 flex gap-4">
        <Link
          href="/workflows"
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          Open Workflow Launcher
        </Link>
      </div>
    </main>
  );
}
