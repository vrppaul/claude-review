/**
 * Positions in the review's telling: which run of the review, and how many
 * pushes into it. Each run numbers its pushes afresh, so a number means
 * nothing without its run, and positions in different runs are never
 * compared.
 */

import type { TellingPosition } from '$lib/types';

/** Whether a position comes after another in the same run of the review. */
export function comesAfter(position: TellingPosition, other: TellingPosition): boolean {
	return position.instance === other.instance && position.sequence > other.sequence;
}

/** The later of two positions; one in another run, or none, leaves the one held. */
export function laterPosition(held: TellingPosition, other: TellingPosition | null): TellingPosition {
	return other !== null && comesAfter(other, held) ? other : held;
}
