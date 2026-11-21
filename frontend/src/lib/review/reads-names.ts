import type { ReviewMode } from '$lib/types';

/**
 * Whether each kind of review reads the names in its code — looks one up, lists those the change touched: only a
 * review of a repository's change has a repository's code to read them in.
 */
export const READS_NAMES: Record<ReviewMode, boolean> = { diff: true, files: false, transcript: false };
