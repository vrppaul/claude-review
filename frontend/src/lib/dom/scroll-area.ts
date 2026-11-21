/**
 * The area a view of the review scrolls in, handed down once by the view
 * that owns it to every section drawn inside it.
 *
 * A section builds its rows as it comes near the area it scrolls in, so it
 * has to know which that is; nothing drawn between the view and the section
 * has any use for it, and does not carry it.
 */

import { getContext, setContext } from 'svelte';

/** Reads the area as it is now: null while it is not drawn yet. */
export type ScrollArea = () => HTMLElement | null;

const SCROLL_AREA = Symbol('scroll area');

/** Hand the area this view scrolls in down to every section drawn inside it. */
export function provideScrollArea(area: ScrollArea): void {
	setContext(SCROLL_AREA, area);
}

/** The area this section scrolls in, as the view it is drawn in said. */
export function useScrollArea(): ScrollArea {
	const area = getContext<ScrollArea | undefined>(SCROLL_AREA);
	if (area === undefined) {
		throw new Error('Drawn outside a scroll area: no view above said which it scrolls in');
	}
	return area;
}

/** The context a section drawn on its own needs: no area of its own, so the page itself is what it scrolls in. */
export function pageAsScrollArea(): Map<symbol, ScrollArea> {
	return new Map([[SCROLL_AREA, () => null]]);
}

/**
 * A box in the room of an area, in pixels from the start of all it scrolls: what stands there scrolls with what
 * the area holds.
 */
export interface AreaBox {
	left: number;
	top: number;
	width: number;
	height: number;
}

/** Whether two boxes are one: in the same place, as large. */
export function sameBox(first: AreaBox, second: AreaBox): boolean {
	return (
		first.left === second.left &&
		first.top === second.top &&
		first.width === second.width &&
		first.height === second.height
	);
}

/** A box of the window in the room of an area, as far as the area has scrolled now. */
export function boxInArea(area: HTMLElement, box: DOMRectReadOnly): AreaBox {
	const origin = area.getBoundingClientRect();
	return {
		left: box.left - origin.left + area.scrollLeft,
		top: box.top - origin.top + area.scrollTop,
		width: box.width,
		height: box.height
	};
}
