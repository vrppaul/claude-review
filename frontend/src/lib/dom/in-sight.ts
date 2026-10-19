/**
 * What the reader sees of where an element is drawn.
 *
 * A reading area scrolls under what is kept in sight at its top — the bar
 * of a chapter, the header of the piece being read — which lies over
 * whatever scrolls under it; and every box that clips what it holds, as a
 * reading area does, hides what reaches past its edges. The keyboard steps
 * only onto lines the reader sees (keyboard.ts), and a pane is fitted into
 * what is seen where it is drawn (lib/ui/pane.ts): both ask here, so the two
 * never part ways over what is in sight.
 */

/**
 * What everything kept in sight at the top of a reading area carries, while
 * what it heads scrolls under it: the header of a section, the slot of a
 * chapter's bar. A line behind one is drawn, and the reader does not see it.
 * The role is what keeps it there: the stylesheet has one rule that does,
 * and it is the role's.
 */
export const KEPT_IN_SIGHT_ROLE = 'kept-in-sight';

// How near two edges stand that touch, in pixels: where an edge stands is not a whole number
export const TOUCHING_WITHIN = 1;

// What a box lets what it holds do at its edges where it hides none of it: show past them
const SHOWN_PAST_ITS_EDGES = 'visible';

/**
 * Where what the reader sees of a reading area begins: at its top edge, or
 * at the foot of what is kept in sight there, one thing under another — the
 * bar of a chapter, and under it the header of the piece being read. They
 * are looked at in the order the page draws them, which is down the area:
 * each one that begins no lower than what is seen so far takes its room too.
 */
export function inSightFrom(area: HTMLElement): number {
	let seenFrom = area.getBoundingClientRect().top;
	for (const kept of area.querySelectorAll(`[data-role="${KEPT_IN_SIGHT_ROLE}"]`)) {
		const box = kept.getBoundingClientRect();
		if (box.top - seenFrom < TOUCHING_WITHIN) seenFrom = Math.max(seenFrom, box.bottom);
	}
	return seenFrom;
}

/** Whether a box hides what it holds past its edges: it scrolls it, or clips it. */
function clipsWhatItHolds(box: HTMLElement): boolean {
	const { overflowX, overflowY } = getComputedStyle(box);
	return overflowX !== SHOWN_PAST_ITS_EDGES || overflowY !== SHOWN_PAST_ITS_EDGES;
}

/** Every element an element is drawn inside, the nearest first. */
function drawnInside(element: HTMLElement): HTMLElement[] {
	const around: HTMLElement[] = [];
	for (let holder = element.parentElement; holder !== null; holder = holder.parentElement) around.push(holder);
	return around;
}

/**
 * What is seen so far, cut to what a box that clips shows of it: inside its
 * edge and its scrollbars, and below what is kept in sight at its top.
 * Where the two do not meet, what is seen is no wide or no tall, never less:
 * a box of a width under none is read with its edges swapped.
 */
function cutTo(seen: DOMRect, clipping: HTMLElement): DOMRect {
	const box = clipping.getBoundingClientRect();
	const insideLeft = box.left + clipping.clientLeft;
	const insideTop = box.top + clipping.clientTop;
	const left = Math.max(seen.left, insideLeft);
	const top = Math.max(seen.top, insideTop, inSightFrom(clipping));
	const right = Math.min(seen.right, insideLeft + clipping.clientWidth);
	const bottom = Math.min(seen.bottom, insideTop + clipping.clientHeight);
	return new DOMRect(left, top, Math.max(0, right - left), Math.max(0, bottom - top));
}

/**
 * What of the window an element can be seen in, as a box on the screen: the
 * window, cut to what every box round the element that clips what it holds
 * shows — the reading area it scrolls in, and whatever holds that.
 */
export function seenIn(element: HTMLElement): DOMRect {
	return drawnInside(element)
		.filter(clipsWhatItHolds)
		.reduce(cutTo, new DOMRect(0, 0, innerWidth, innerHeight));
}
