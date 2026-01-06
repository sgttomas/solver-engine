/**
 * SOLVER Web - Step Progress Component
 *
 * Renders workflow step timeline from progress endpoint data.
 * Package 6.5 deliverable per Development Directive v1.5.1.
 *
 * Features:
 * - Displays all steps with pass type (definition/execution)
 * - Highlights current step
 * - Shows stale indicator on stale steps
 * - Shows artifact status per step
 */

'use client';

import type { StepProgressEntry, PassType, StepStatus } from '@/lib/types';

// ============================================================================
// Props
// ============================================================================

export interface StepProgressProps {
  /** Steps array from progress endpoint */
  steps: StepProgressEntry[];
  /** Current step number for highlighting */
  currentStepNumber: number;
  /** Current pass type */
  currentPassType: PassType;
  /** Loading state */
  isLoading?: boolean;
}

// ============================================================================
// Status Configuration
// ============================================================================

interface StatusConfig {
  label: string;
  bgColor: string;
  textColor: string;
  borderColor: string;
}

const STATUS_CONFIG: Record<StepStatus, StatusConfig> = {
  not_started: {
    label: 'Not Started',
    bgColor: 'bg-muted',
    textColor: 'text-muted-foreground',
    borderColor: 'border-muted-foreground/30',
  },
  pending: {
    label: 'Pending',
    bgColor: 'bg-muted',
    textColor: 'text-muted-foreground',
    borderColor: 'border-muted-foreground/30',
  },
  in_progress: {
    label: 'In Progress',
    bgColor: 'bg-blue-100',
    textColor: 'text-blue-700',
    borderColor: 'border-blue-500',
  },
  awaiting_clarification: {
    label: 'Awaiting Input',
    bgColor: 'bg-yellow-100',
    textColor: 'text-yellow-700',
    borderColor: 'border-yellow-500',
  },
  awaiting_review: {
    label: 'Awaiting Review',
    bgColor: 'bg-purple-100',
    textColor: 'text-purple-700',
    borderColor: 'border-purple-500',
  },
  approved: {
    label: 'Approved',
    bgColor: 'bg-green-100',
    textColor: 'text-green-700',
    borderColor: 'border-green-500',
  },
  revision_requested: {
    label: 'Revision Requested',
    bgColor: 'bg-orange-100',
    textColor: 'text-orange-700',
    borderColor: 'border-orange-500',
  },
};

// ============================================================================
// Component
// ============================================================================

/**
 * Step progress timeline component.
 *
 * Renders steps grouped by pass type with visual status indicators.
 */
export function StepProgress({
  steps,
  currentStepNumber,
  currentPassType,
  isLoading,
}: StepProgressProps) {
  if (isLoading) {
    return <StepProgressSkeleton />;
  }

  if (!steps || steps.length === 0) {
    return (
      <div className="text-muted-foreground text-sm p-4">
        No steps available
      </div>
    );
  }

  // Group steps by pass type
  const definitionSteps = steps.filter((s) => s.pass_type === 'definition');
  const executionSteps = steps.filter((s) => s.pass_type === 'execution');

  return (
    <div className="space-y-6">
      {/* Definition Pass */}
      <PassSection
        title="Definition Pass"
        passType="definition"
        steps={definitionSteps}
        currentStepNumber={currentStepNumber}
        currentPassType={currentPassType}
      />

      {/* Execution Pass */}
      {executionSteps.length > 0 && (
        <PassSection
          title="Execution Pass"
          passType="execution"
          steps={executionSteps}
          currentStepNumber={currentStepNumber}
          currentPassType={currentPassType}
        />
      )}
    </div>
  );
}

// ============================================================================
// Sub-components
// ============================================================================

interface PassSectionProps {
  title: string;
  passType: PassType;
  steps: StepProgressEntry[];
  currentStepNumber: number;
  currentPassType: PassType;
}

function PassSection({
  title,
  passType,
  steps,
  currentStepNumber,
  currentPassType,
}: PassSectionProps) {
  const isCurrentPass = passType === currentPassType;

  return (
    <div>
      <h3 className={`text-sm font-semibold mb-3 ${isCurrentPass ? 'text-foreground' : 'text-muted-foreground'}`}>
        {title}
      </h3>
      <div className="space-y-2">
        {steps.map((step) => (
          <StepItem
            key={`${step.pass_type}-${step.step_number}`}
            step={step}
            isCurrent={isCurrentPass && step.step_number === currentStepNumber}
          />
        ))}
      </div>
    </div>
  );
}

interface StepItemProps {
  step: StepProgressEntry;
  isCurrent: boolean;
}

function StepItem({ step, isCurrent }: StepItemProps) {
  const config = STATUS_CONFIG[step.status];
  const stepLabel = formatStepName(step.step_name);

  return (
    <div
      className={`flex items-center gap-3 p-3 rounded-lg border-2 transition-all ${
        isCurrent ? `${config.borderColor} ${config.bgColor}` : 'border-transparent bg-muted/30'
      }`}
    >
      {/* Step number indicator */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
          isCurrent ? `${config.bgColor} ${config.textColor}` : 'bg-muted text-muted-foreground'
        }`}
      >
        {step.step_number}
      </div>

      {/* Step info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={`font-medium truncate ${isCurrent ? 'text-foreground' : 'text-muted-foreground'}`}>
            {stepLabel}
          </span>

          {/* Stale indicator */}
          {step.is_stale && (
            <span
              className="px-1.5 py-0.5 text-xs font-medium bg-orange-100 text-orange-700 rounded"
              title="This step has stale artifacts that need re-execution"
            >
              Stale
            </span>
          )}
        </div>

        {/* Status and artifact info */}
        <div className="flex items-center gap-2 mt-1 text-xs">
          <span className={config.textColor}>{config.label}</span>
          {step.has_artifact && (
            <span className="text-muted-foreground">
              Artifact v{step.artifact_revision}
            </span>
          )}
        </div>
      </div>

      {/* Phase indicator (for in-progress steps) */}
      {step.status === 'in_progress' && step.phase && (
        <span className="text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded">
          {formatPhase(step.phase)}
        </span>
      )}
    </div>
  );
}

function StepProgressSkeleton() {
  return (
    <div className="space-y-6">
      <div>
        <div className="h-4 w-32 bg-muted rounded animate-pulse mb-3" />
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-muted/30 rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Helpers
// ============================================================================

/**
 * Format step name for display (snake_case to Title Case)
 */
function formatStepName(name: string): string {
  return name
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Format phase for display
 */
function formatPhase(phase: string): string {
  return phase.charAt(0).toUpperCase() + phase.slice(1);
}
