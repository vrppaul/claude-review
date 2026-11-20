/**
 * A line known by where it is: its side, and its number on that side. Old
 * line 42 and new line 42 are different lines, and a line drawn anywhere —
 * in one column or two, with lines revealed above it or not — is the same
 * place.
 */

import type { LinePlace, LineSide } from '$lib/types';

// What stands between a place's side and its number in the key it is known by
const KEY_JOINER = ':';
// Every side a key may name
const SIDES: readonly LineSide[] = ['old', 'new'];

/** Whether two places are the same line. */
export function samePlace(one: LinePlace, other: LinePlace): boolean {
	return one.side === other.side && one.number === other.number;
}

/** What a place is known by wherever lines are looked up by where they are. */
export function placeKey(place: LinePlace): string {
	return `${place.side}${KEY_JOINER}${place.number}`;
}

/**
 * Whether a key names a line of the file as it stands, a new-side line:
 * numbered alike under every base, where a removed line's number under a
 * narrower base is that base's own.
 */
export function namesTheFileAsItStands(key: string): boolean {
	return placeOfKey(key)?.side === 'new';
}

/**
 * The place a key names, as a line's number on the page carries it: what
 * is known of a line read off the page. Null for a string no place is known by.
 */
export function placeOfKey(key: string): LinePlace | null {
	const [sideNamed, numberNamed] = key.split(KEY_JOINER);
	const side = SIDES.find((named) => named === sideNamed);
	const number = Number(numberNamed);
	return side === undefined || !Number.isInteger(number) ? null : { side, number };
}
