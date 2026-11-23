/**
 * Where the reader is reading, kept across a change to what is drawn, or
 * across a jump elsewhere and back.
 *
 * A new diff — a retake, another base — redraws the files above the reader
 * too. Kept at the same distance from the top, the reader would land in
 * another file; kept on the line they were reading, they stay where they
 * were. A reader the page took elsewhere comes back to the same: what they
 * saw, standing where it stood.
 */

import type { Announced, Announcement } from '$lib/dom/announced';
import type { Jumps } from '$lib/dom/jump';
import { lineNumbersIn, seenWhole } from '$lib/dom/keyboard';

/** Where the reader is reading: a line of what they read in, and how far below the top of the reading area it stands. */
export interface ReadingPlace {
	/** What they read in — a section of a file, a part of a story — by the key whoever draws it knows it by. */
	within: string;
	/** The line, by what its row is known by; null for the top of what draws no line there. */
	line: string | null;
	/** How far below the top of the reading area it stands, in pixels. */
	offset: number;
}

/** Whether going back to a place puts the keyboard on it, or leaves it on the control that stays, as the header's switch. */
export type KeyboardOnReturn = 'to-the-place' | 'where-it-is';

/**
 * Where the reader is reading in what they read: of its lines they see
 * whole, past what is kept in sight at the top of the area, the first that
 * `standsAlike` keeps, or else the first; or its top, where they see none.
 *
 * @param standsAlike whether a line, by the key its place is known by, is numbered alike in whatever is drawn
 *   when the reader comes back to it
 */
export function readingPlaceIn(
	key: string,
	readIn: HTMLElement,
	root: HTMLElement,
	standsAlike: (lineKey: string) => boolean
): ReadingPlace {
	const seen = lineNumbersIn(readIn).filter((number) => seenWhole(number, root));
	const alike = seen.find((number) => number.dataset.place !== undefined && standsAlike(number.dataset.place));
	const line = alike ?? seen.at(0);
	const standing = line ?? readIn;
	return {
		within: key,
		line: line?.dataset.place ?? null,
		offset: standing.getBoundingClientRect().top - root.getBoundingClientRect().top
	};
}

/**
 * Scroll an area so the line read stands where it stood, or the top of what
 * was read where no line was. A line no longer drawn leaves the reader at
 * the top of what they read in instead. Returns the line's number, where it
 * is drawn.
 */
export function bringBack(place: ReadingPlace, readIn: HTMLElement, root: HTMLElement): HTMLElement | null {
	const line = lineNumbersIn(readIn).find((number) => place.line !== null && number.dataset.place === place.line);
	const standing = line ?? readIn;
	const wanted = line !== undefined || place.line === null ? place.offset : 0;
	root.scrollTop += standing.getBoundingClientRect().top - root.getBoundingClientRect().top - wanted;
	return line ?? null;
}

/** Take the reader back to a place among what announced itself in a reading area, as they saw it. */
export function goBackAmong<Said extends Announcement>(
	announced: Announced<Said>,
	jumps: Jumps,
	place: ReadingPlace,
	keyboard: KeyboardOnReturn,
	keyboardTo: (said: Said, line: HTMLElement | null) => void
): void {
	const said = announced.get(place.within);
	const area = announced.area;
	if (said === undefined || area === null) return;
	jumps.land(announced.band, said.element, () => comeBack(place, said, area, keyboard, keyboardTo));
}

/** Put the reader back at a place in what announced itself, once at rest, and the keyboard on it where it goes there. */
function comeBack<Said extends Announcement>(
	place: ReadingPlace,
	said: Said,
	area: HTMLElement,
	keyboard: KeyboardOnReturn,
	keyboardTo: (said: Said, line: HTMLElement | null) => void
): void {
	const line = bringBack(place, said.element, area);
	if (keyboard === 'to-the-place') keyboardTo(said, line);
}
