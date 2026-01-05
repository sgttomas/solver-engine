/**
 * SOLVER Web - Root Layout
 */

import type { Metadata } from 'next';
import { Providers } from './providers';
import './globals.css';

export const metadata: Metadata = {
  title: 'SOLVER - Structured Reasoning Workflow Engine',
  description: 'Human-in-the-loop workflow orchestration for structured problem solving',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
