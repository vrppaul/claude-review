/**
 * Where the reader is reading, kept across a change to what is drawn above it.
 *
 * A new diff — a retake, another base — redraws the files above the reader
 * too. Kept at the same distance from the top, the reader would land in
 * another file; kept on the line they were reading, they stay where they were.
 */

import { LINE_NUMBER_ROLE } from '$lib/dom/keyboard';

/** Where the reader is reading: a line of a section, and how far below the top of the reading area it stands. */
export interface ReadingPlace {
	/** The section, by the key whoever draws it knows it by. */
	section: string;
	/** The line, by what its row is known by; null for the top of a section that draws no line there. */
	line: string | null;
	/** How far below the top of the reading area it stands, in pixels. */
	offset: number;
}

/** The numbers of a section's lines, one for each row, in the order the page draws them. */
function lineNumbersIn(section: HTMLElement): HTMLElement[] {
	return Array.from(section.querySelectorAll<HTMLElement>(`[data-role="${LINE_NUMBER_ROLE}"]`));
}

/** Where the reader is reading in a section: its first line still showing at the top of the area, or its top. */
export function readingPlaceIn(sectionKey: string, section: HTMLElement, root: HTMLElement): ReadingPlace {
	const top = root.getBoundingClientRect().top;
	const line = lineNumbersIn(section).find((number) => number.getBoundingClientRect().bottom > top);
	const standing = line ?? section;
	return {
		section: sectionKey,
		line: line?.dataset.place ?? null,
		offset: standing.getBoundingClientRect().top - top
	};
}

/**
 * Scroll an area so the line read stands where it stood. A line no longer
 * drawn leaves the reader at the top of its section instead.
 */
export function bringBack(place: ReadingPlace, section: HTMLElement, root: HTMLElement): void {
	const line = lineNumbersIn(section).find((number) => place.line !== null && number.dataset.place === place.line);
	const standing = line ?? section;
	const wanted = line ? place.offset : 0;
	root.scrollTop += standing.getBoundingClientRect().top - root.getBoundingClientRect().top - wanted;
}
