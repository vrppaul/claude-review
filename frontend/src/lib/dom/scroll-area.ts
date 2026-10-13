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
