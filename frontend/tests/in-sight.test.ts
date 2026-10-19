import { afterEach, describe, it, expect } from 'vitest';
import { KEPT_IN_SIGHT_ROLE, seenIn } from '$lib/dom/in-sight';

// How a box treats what it holds past its edges: scrolls it, clips it, or shows it
type Overflow = 'auto' | 'hidden' | 'visible';

// A reading area beside the column of files, under the page's header, and the file's header kept in sight over it
const AREA = new DOMRect(240, 48, 746, 512);
const FILES_HEADER = new DOMRect(AREA.left, AREA.top, AREA.width, 43);
// A box round the reading area that clips it short of its right edge
const CLIPPED_AT = 900;
// A box that clips what it holds, standing clear of the reading area, above it and to its left
const CLEAR_OF_THE_AREA = new DOMRect(0, 0, 200, 40);

/** A box drawn inside another, laid out where a box on the screen says, treating what it holds past its edges so. */
function boxAt(inside: HTMLElement, at: DOMRect, overflow: Overflow): HTMLElement {
	const box = inside.appendChild(document.createElement('div'));
	// Each way by itself: jsdom does not spread the shorthand over the two
	box.style.overflowX = overflow;
	box.style.overflowY = overflow;
	box.getBoundingClientRect = () => at;
	Object.defineProperties(box, { clientWidth: { value: at.width }, clientHeight: { value: at.height } });
	return box;
}

/** A reading area drawn inside a box, its file's header kept in sight over its top. */
function readingAreaIn(inside: HTMLElement): HTMLElement {
	const area = boxAt(inside, AREA, 'auto');
	boxAt(area, FILES_HEADER, 'visible').dataset.role = KEPT_IN_SIGHT_ROLE;
	return area;
}

/** What drawn inside a box stands for a pane: a box that shows what it holds. */
function paneIn(inside: HTMLElement): HTMLElement {
	return boxAt(inside, new DOMRect(), 'visible');
}

/** A box on the screen by its edges. */
function edgesOf(box: DOMRect): number[] {
	return [box.left, box.top, box.right, box.bottom];
}

afterEach(() => {
	document.body.replaceChildren();
});

describe('what of the window an element is seen in', () => {
	it('in nothing that clips, is the whole window', () => {
		expect(edgesOf(seenIn(paneIn(document.body)))).toEqual([0, 0, innerWidth, innerHeight]);
	});

	it('in a reading area, is what the area shows under what is kept in sight at its top', () => {
		const pane = paneIn(readingAreaIn(document.body));

		expect(edgesOf(seenIn(pane))).toEqual([AREA.left, FILES_HEADER.bottom, AREA.right, AREA.bottom]);
	});

	it('in a reading area inside a box that clips it, is cut by that box too', () => {
		const clipping = boxAt(document.body, new DOMRect(0, 0, CLIPPED_AT, innerHeight), 'hidden');

		expect(seenIn(paneIn(readingAreaIn(clipping))).right).toBe(CLIPPED_AT);
	});

	it('inside a box that clips standing clear of it, is no room at all', () => {
		const clipping = boxAt(document.body, CLEAR_OF_THE_AREA, 'hidden');
		const seen = seenIn(paneIn(readingAreaIn(clipping)));

		expect([seen.width, seen.height]).toEqual([0, 0]);
	});
});
