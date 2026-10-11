/**
 * A line known by where it is: its side, and its number on that side. Old
 * line 42 and new line 42 are different lines, and a line drawn anywhere —
 * in one column or two, with lines revealed above it or not — is the same
 * place.
 */

import type { LinePlace } from '$lib/types';

/** Whether two places are the same line. */
export function samePlace(one: LinePlace, other: LinePlace): boolean {
	return one.side === other.side && one.number === other.number;
}

/** What a place is known by wherever lines are looked up by where they are. */
export function placeKey(place: LinePlace): string {
	return `${place.side}:${place.number}`;
}
