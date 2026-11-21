/**
 * The line the reader reads from in a reading area, kept as they scroll: the
 * row at the top of what they see of the area, and the section it is drawn
 * in. Found by one look at that spot in a frame the area scrolled or was
 * drawn anew in, never by measuring every line of a long file: whatever
 * follows the line being read — the name it is in — follows it as it scrolls.
 */

import type { Announcement } from '$lib/dom/announced';
import { inSightFrom, TOUCHING_WITHIN } from '$lib/dom/in-sight';
import { LINE_NUMBER_ROLE } from '$lib/dom/keyboard';

// What each row that draws a line carries, its numbers inside it (RawView, SplitView)
export const LINE_ROW_ROLE = 'line-row';

const LINE_ROW = `[data-role="${LINE_ROW_ROLE}"]`;
const LINE_NUMBER = `[data-role="${LINE_NUMBER_ROLE}"]`;

// Where across the area the spot is looked at: its middle, which every row of a section reaches, in one layout or two
const ACROSS_THE_MIDDLE = 0.5;

// What the area is watched for besides its scroll: whatever is drawn in it or taken out, which moves the rows
const DRAWN_ANEW: MutationObserverInit = { childList: true, subtree: true };

/** The line read from: the section it is drawn in, by its key, and the keys of the places of the lines its row draws. */
export interface LineRead {
	section: string;
	lines: readonly string[];
}

/**
 * The element before another in the order of the page, stepping into what stands before it from its end, but never
 * into a line's row, which is what is looked for.
 */
function before(element: Element): Element | null {
	const sibling = element.previousElementSibling;
	if (sibling === null) return element.parentElement;
	let last = sibling;
	while (!last.matches(LINE_ROW) && last.lastElementChild !== null) last = last.lastElementChild;
	return last;
}

/**
 * The row of the line at an element in a section: the row it is in, or else the row of the line it hangs under — a
 * thread's card, a check's failure, the lines a hunk leaves out — the last before it; none above the first line.
 */
function rowAtOrAbove(element: Element, section: Element): Element | null {
	const inRow = element.closest(LINE_ROW);
	if (inRow !== null) return inRow;
	for (let looked: Element | null = element; looked !== null && looked !== section; looked = before(looked)) {
		if (looked.matches(LINE_ROW)) return looked;
	}
	return null;
}

/** The keys of the places of the lines a row draws, by its numbers: one, or two where it draws a line of each side. */
function linesOfRow(row: Element): readonly string[] {
	const numbers = row.querySelectorAll<HTMLElement>(LINE_NUMBER);
	return Array.from(numbers, (number) => number.dataset.place).filter((place) => place !== undefined);
}

export class LineReadFrom {
	#read = $state.raw<LineRead | null>(null);
	#area: HTMLElement | null = null;
	#frame: number | null = null;
	readonly #sectionHolding: (element: Element) => Announcement | null;
	readonly #lookAgain = (): void => this.#lookSoon();
	readonly #drawnAnew = new MutationObserver(this.#lookAgain);
	readonly #resized = new ResizeObserver(this.#lookAgain);

	/** @param sectionHolding the section an element is drawn in, where it is in one */
	constructor(sectionHolding: (element: Element) => Announcement | null) {
		this.#sectionHolding = sectionHolding;
	}

	/** The line read from; null where no line stands at or above the spot in its section, or no area is watched. */
	get read(): LineRead | null {
		return this.#read;
	}

	/** Follow the line read from as an area scrolls, is drawn anew or resized, from now on; returns how to stop. */
	watch(area: HTMLElement): () => void {
		this.#area = area;
		area.addEventListener('scroll', this.#lookAgain, { passive: true });
		// One area is read from at a time: what another was watched for is let go
		this.#drawnAnew.disconnect();
		this.#drawnAnew.observe(area, DRAWN_ANEW);
		this.#resized.observe(area);
		this.#lookSoon();
		return () => this.#stop(area);
	}

	/** Look at the spot once, in the next frame: however often the area changes before it, the look is one. */
	#lookSoon(): void {
		this.#frame ??= requestAnimationFrame(() => this.#look());
	}

	#look(): void {
		this.#frame = null;
		const area = this.#area;
		if (area === null) return;
		const box = area.getBoundingClientRect();
		const spotX = box.left + box.width * ACROSS_THE_MIDDLE;
		const spotY = inSightFrom(area) + TOUCHING_WITHIN;
		this.#read = this.#readAt(document.elementFromPoint(spotX, spotY));
	}

	/** The line read from where an element stands at the spot. */
	#readAt(atSpot: Element | null): LineRead | null {
		if (atSpot === null) return null;
		const section = this.#sectionHolding(atSpot);
		if (section === null) return null;
		const row = rowAtOrAbove(atSpot, section.element);
		return row === null ? null : { section: section.key, lines: linesOfRow(row) };
	}

	#stop(area: HTMLElement): void {
		area.removeEventListener('scroll', this.#lookAgain);
		this.#resized.unobserve(area);
		// Where another area is watched in place of this one, its line is the one read from
		if (this.#area !== area) return;
		this.#drawnAnew.disconnect();
		if (this.#frame !== null) cancelAnimationFrame(this.#frame);
		this.#frame = null;
		this.#area = null;
		this.#read = null;
	}
}
