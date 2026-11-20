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
import { lineNumbersIn } from '$lib/dom/keyboard';

/** Where the reader is reading: a line of what they read in, and how far below the top of the reading area it stands. */
export interface ReadingPlace {
	/** What they read in — a section of a file, a part of a story — by the key whoever draws it knows it by. */
	within: string;
	/** The line, by what its row is known by; null for the top of what draws no line there. */
	line: string | null;
	/** How far below the top of the reading area it stands, in pixels. */
	offset: number;
}

/** Where the reader is reading in what they read: its first line still showing at the top of the area, or its top. */
export function readingPlaceIn(key: string, readIn: HTMLElement, root: HTMLElement): ReadingPlace {
	const top = root.getBoundingClientRect().top;
	const line = lineNumbersIn(readIn).find((number) => number.getBoundingClientRect().bottom > top);
	const standing = line ?? readIn;
	return {
		within: key,
		line: line?.dataset.place ?? null,
		offset: standing.getBoundingClientRect().top - top
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

/**
 * Take the reader back to a place among what announced itself in a reading
 * area: to what they read in at once, so the rows near it are built, and
 * once that has come to rest, to the place as they saw it; `keyboardTo` is
 * then handed what they read in and its line, where that is drawn, to put
 * the keyboard on. Nowhere, for what is not drawn.
 */
export function goBackAmong<Said extends Announcement>(
	announced: Announced<Said>,
	jumps: Jumps,
	place: ReadingPlace,
	keyboardTo: (said: Said, line: HTMLElement | null) => void
): void {
	const said = announced.get(place.within);
	const area = announced.area;
	if (said === undefined || area === null) return;
	jumps.land(announced.band, said.element, () => keyboardTo(said, bringBack(place, said.element, area)));
}
