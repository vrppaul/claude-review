/**
 * Positions in the review's telling: which run of the review, and how many
 * pushes into it. Each run numbers its pushes afresh, so a number means
 * nothing without its run, and positions in different runs are never
 * compared.
 */

import type { TellingByRun, TellingPosition } from '$lib/types';

/** Whether two positions are the same push. */
export function samePosition(position: TellingPosition, other: TellingPosition): boolean {
	return position.instance === other.instance && position.sequence === other.sequence;
}

/** Whether a position comes after another in the same run of the review. */
export function comesAfter(position: TellingPosition, other: TellingPosition): boolean {
	return position.instance === other.instance && position.sequence > other.sequence;
}

/**
 * How far the telling got in each run, with a position counted in. The
 * runs are kept in one order, so two tabs that agree write the same words.
 */
export function countedIn(byRun: TellingByRun, at: TellingPosition): TellingByRun {
	const held = byRun[at.instance];
	if (held !== undefined && held >= at.sequence) return byRun;
	const counted = Object.entries({ ...byRun, [at.instance]: at.sequence });
	return Object.fromEntries(counted.sort(([first], [second]) => first.localeCompare(second)));
}

/** Two records of how far the telling got as one: in every run, the further of the two. */
export function furtherByRun(one: TellingByRun, other: TellingByRun): TellingByRun {
	return Object.entries(other).reduce(
		(further, [instance, sequence]) => countedIn(further, { instance, sequence }),
		one
	);
}
