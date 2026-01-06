/**
 * SOLVER Web - Exponential Backoff Utility
 *
 * Calculates retry delays with exponential backoff and jitter.
 * Per Architectural Contract v3.4 Section 14.1 (C4): bounded recovery attempts.
 */

export interface BackoffConfig {
  /** Base delay in milliseconds (default: 1000) */
  baseMs: number;
  /** Maximum delay in milliseconds (default: 30000) */
  maxMs: number;
  /** Jitter factor 0-1 to randomize delay (default: 0.1 = 10%) */
  jitterFactor: number;
}

export const DEFAULT_BACKOFF_CONFIG: BackoffConfig = {
  baseMs: 1000,
  maxMs: 30000,
  jitterFactor: 0.1,
};

/**
 * Calculate backoff delay for a given retry attempt.
 *
 * Uses exponential backoff: base * 2^retryCount, capped at maxMs,
 * with random jitter to prevent thundering herd.
 *
 * @param retryCount - Current retry attempt (0-indexed)
 * @param config - Backoff configuration
 * @returns Delay in milliseconds
 */
export function calculateBackoff(
  retryCount: number,
  config: BackoffConfig = DEFAULT_BACKOFF_CONFIG
): number {
  // Exponential: base * 2^retryCount
  const exponential = config.baseMs * Math.pow(2, retryCount);

  // Cap at max
  const capped = Math.min(exponential, config.maxMs);

  // Add jitter to prevent thundering herd
  const jitter = capped * config.jitterFactor * Math.random();

  return Math.floor(capped + jitter);
}
